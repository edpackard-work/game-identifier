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
TARGET_BOX = (170, 90, 400, 400)
REQUIRED_CONSECUTIVE_FRAMES = 2

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
    edges = cv2.Canny(gray, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 500]
        if valid_contours:
            largest = max(valid_contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            if area / green_square_area >= 0.33:
                detection_counter += 1
                if detection_counter >= REQUIRED_CONSECUTIVE_FRAMES:
                    x_obj, y_obj, w_obj, h_obj = cv2.boundingRect(largest)
                    cropped = roi[y_obj:y_obj + h_obj, x_obj:x_obj + w_obj]
                    filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    path = os.path.join(CAPTURED_DIR, filename)
                    cv2.imwrite(path, cropped)
                    return jsonify(success=True, image_url=f'/static/captured/{filename}')
            else:
                detection_counter = 0
    else:
        detection_counter = 0

    return jsonify(success=False)

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
        title: str | None=None
        system: str | None=None
        publisher: str | None=None
        releaseYear: int | None=None
        labelCode: str | None=None

    response = client.responses.parse(
        model="gpt-4.1",
        # model="gpt-4o-mini",
        temperature=0,
        input=[
            {"role": "system", "content": "You are an expert video game identifier. Use the game cartridge label text to identify the game's title and system, label code and publisher. Use your knowledge of the game for the release year. Return '' if you are not sure about any field."},
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
    return responseJson

if __name__ == '__main__':
    if not os.path.exists(CAPTURED_DIR):
        os.makedirs(CAPTURED_DIR)
    app.run(debug=True)
