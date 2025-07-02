import cv2
import numpy as np
import base64
import os
import json

from flask import Flask, render_template, request, jsonify
from datetime import datetime
from PIL import Image
from io import BytesIO
from openai import OpenAI
from pydantic import BaseModel

app = Flask(__name__)
app.config.from_file("config.json", load=json.load)

CAPTURED_DIR = 'static/captured'
TARGET_BOX = (120, 40, 400, 400)

# cv2 parameters
MINIMUM_CONTOUR_AREA = 500
AREA_PERCENTAGE = 0.45
REQUIRED_CONSECUTIVE_FRAMES = 2
KERNEL_WIDTH = 9
KERNEL_HEIGHT = 9
LOWER_THRESHOLD = 50
UPPER_THRESHOLD = 150

detection_counter = 0

client = OpenAI(
    api_key=app.config["OPENAI_API_KEY"]   
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_frame', methods=['POST'])
def process_frame():
    global detection_counter

    data = request.get_json()
    img_data = data['image'].split(',')[1]
    img_bytes = base64.b64decode(img_data)
    img = Image.open(BytesIO(img_bytes))
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    x, y, w, h = TARGET_BOX
    green_square_area = w * h
    roi = frame[y:y+h, x:x+w]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, LOWER_THRESHOLD, UPPER_THRESHOLD)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (KERNEL_WIDTH, KERNEL_HEIGHT))
    edges = cv2.dilate(edges, kernel, iterations=1)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rect = None
    if contours:
        valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > MINIMUM_CONTOUR_AREA]
        if valid_contours:
            largest = max(valid_contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            x_obj, y_obj, w_obj, h_obj = cv2.boundingRect(largest)
            rect = {"x": int(x_obj + x), "y": int(y_obj + y), "w": int(w_obj), "h": int(h_obj)} if app.config["CV2_DEBUG"] == True else None 
            if area / green_square_area >= AREA_PERCENTAGE:
                detection_counter += 1
                if detection_counter >= REQUIRED_CONSECUTIVE_FRAMES:
                    cropped = roi[y_obj:y_obj + h_obj, x_obj:x_obj + w_obj]
                    
                    filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    path = os.path.join(CAPTURED_DIR, filename)
                    cv2.imwrite(path, cropped)

                    if app.config["CV2_DEBUG"] == True:
                        path2 = os.path.join(CAPTURED_DIR, f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}-captured_image.png")
                        path3 = os.path.join(CAPTURED_DIR, f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}-cv2_edges.png")
                        path4 = os.path.join(CAPTURED_DIR, f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}-settings.txt")
                        
                        cv2.imwrite(path2, np.array(img))
                        cv2.imwrite(path3, edges)
                        settings_string = f"MINIMUM CONTOUR AREA: {MINIMUM_CONTOUR_AREA}\n"\
                        + f"AREA_PERCENTAGE: {AREA_PERCENTAGE}\n"\
                        + f"REQUIRED_CONSECUTIVE_FRAMES: {REQUIRED_CONSECUTIVE_FRAMES}\n"\
                        + f"KERNEL_WIDTH: {KERNEL_WIDTH};\n"\
                        + f"KERNEL_HEIGHT: {KERNEL_HEIGHT}\n"\
                        + f"UPPER_THRESHOLD: {UPPER_THRESHOLD}\n"\
                        + f"LOWER_THRESHOLD: {LOWER_THRESHOLD}"
                        with open(path4, 'w') as f:
                            f.write(settings_string)

                    return jsonify(success=True, image_url=f'/static/captured/{filename}')
            else:
                detection_counter = 0
        else:
            detection_counter = 0
    else:
        detection_counter = 0

    return jsonify(success=False, rect=rect, detected_frames=detection_counter)

@app.route('/process_uploaded_image', methods=['POST'])
def process_uploaded_image():
    data = request.get_json()
    filename = data.get('filename')

    if not filename:
        return jsonify({'success': False, 'error': 'Missing filename'}), 400

    local_path = os.path.join(CAPTURED_DIR, filename)
    if not os.path.exists(local_path):
        return jsonify({'success': False, 'error': 'File not found'}), 404

    with open(local_path, 'rb') as img_file:
        encoded_image = base64.b64encode(img_file.read()).decode()

    class GameDetails(BaseModel):
        reasoning: str
        isItAVideoGame: bool
        title: str | None=None
        system: str | None=None
        publisher: str | None=None
        releaseYear: int | None=None
        labelCode: str | None=None
        region: str | None=None

    response = client.responses.parse(
        # model="gpt-4.1",
        # model="gpt-4o"
        model="gpt-4o",
        temperature=0,
        input=[
            {"role": "system", "content": "You are an expert video game identifier. \
             Consider the game cartridge type and label text, \
             alongside your knowledge to identify the game in the image provided. \
             isItAVideoGame: if this is false, return '' for title, system, publisher, releaseYear and labelCode. \
             title: the game's title. \
             system: do not include manufacturer (i.e. return Game Boy not Nintendo Game Boy, or return Mega Drive not Sega Mega Drive) \
             publisher: the game's publisher on this particular system, usually but not always displayed on the label text \
             releaseYear: the game's release year on this particular system and region \
             labelCode: the game's label code (if present) in the acknowledged system format (i.e. a DMG code for Game Boy) \
             region: based on cartridge type, artwork and label, return the region (i.e. Europe, United Kingdom, Japan, United States etc) \
             Return '' if you are not sure about any field."},
            {"role": "user",
                "content": [
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded_image}"}
                ]
            }
        ],
        text_format=GameDetails,
    )

    success = {'success': True}
    reply = response.output_parsed
    
    responseJson = {**success, **reply.model_dump(mode='json')}
    if app.config["CV2_DEBUG"] == True:
        print(responseJson)
    return responseJson

if __name__ == '__main__':
    if not os.path.exists(CAPTURED_DIR):
        os.makedirs(CAPTURED_DIR)
    app.run(debug=True)
