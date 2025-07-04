import cv2
import numpy as np
import base64
import os
import json
import signal
import sys
from collections import deque

from flask import Flask, render_template, request, jsonify
from datetime import datetime
from PIL import Image
from io import BytesIO
from openai import OpenAI
from pydantic import BaseModel

MINIMUM_BOX_AREA = 75000
VALID_BOUNDING_BOXES_REQUIRED = 8
STABILITY_PIXEL_MOVEMENT_ALLOWED = 100
SHARPNESS_THRESHOLD = 150 # threshold for Laplacian variance

app = Flask(__name__)
app.config.from_file("config.json", load=json.load)

yolo_cfg = 'model/yolov4-tiny-custom.cfg'
yolo_weights = 'model/yolov4-tiny-custom_last.weights'
yolo_names = 'model/obj.names'

# For development/demo use only: global queue to track VALID_BOUNDING_BOXES_REQUIRED number of bounding boxes
# In production/multiclient, use per-session or per-client storage
boxes_queue = deque(maxlen=VALID_BOUNDING_BOXES_REQUIRED)

# Load class labels
with open(yolo_names, 'r') as f:
    LABELS = [line.strip() for line in f.readlines()]

# Load YOLOv4-tiny model
net = cv2.dnn.readNetFromDarknet(yolo_cfg, yolo_weights)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

layer_names = net.getLayerNames()
unconnected = net.getUnconnectedOutLayers()
if not isinstance(unconnected, np.ndarray):
    unconnected = np.array(unconnected)
output_layers = [layer_names[int(i) - 1] for i in unconnected.flatten()]

def cleanup(*args):
    print('\nCleaning up resources...')
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

client = OpenAI(
    api_key=app.config["OPENAI_API_KEY"]   
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_frame', methods=['POST'])
def process_frame():
    global boxes_queue
    data = request.get_json()
    img_data = data['image'].split(',')[1]
    img_bytes = base64.b64decode(img_data)
    img = Image.open(BytesIO(img_bytes))
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    (frame_h, frame_w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    layer_outputs = net.forward(output_layers)

    boxes = []
    confidences = []
    classIDs = []

    for output in layer_outputs:
        for detection in output:
            scores = detection[5:]
            classID = np.argmax(scores)
            confidence = scores[classID]
            if confidence > 0.75:  # threshold
                box = detection[0:4] * np.array([frame_w, frame_h, frame_w, frame_h])
                (centerX, centerY, width, height) = box.astype('int')
                x = int(centerX - (width / 2))
                y = int(centerY - (height / 2))
                boxes.append([x, y, int(width), int(height)])
                confidences.append(float(confidence))
                classIDs.append(classID)

    idxs = cv2.dnn.NMSBoxes(boxes, confidences, 0.3, 0.4)
    idxs = np.asarray(idxs)
    if len(idxs) > 0:
        idxs_flat = idxs.flatten()
        best_idx = idxs_flat[np.argmax([confidences[i] for i in idxs_flat])]
        x, y, w, h = boxes[best_idx]
        classID = classIDs[best_idx]
        label = LABELS[classID]
        confidence = confidences[best_idx]
        # Crop detected object for return
        x1, y1, x2, y2 = max(0, x), max(0, y), min(frame_w, x+w), min(frame_h, y+h)
        cropped = frame[y1:y2, x1:x2]
        _, buffer = cv2.imencode('.png', cropped)
        base_64_image = base64.b64encode(buffer).decode()
        rect = {"x": int(x), "y": int(y), "w": int(w), "h": int(h), "label": label, "confidence": float(confidence)}

        # --- Detection confirmation logic ---
        area = w * h
        stable = False
        is_sharp = False
        
        if area >= MINIMUM_BOX_AREA:
            boxes_queue.append((x, y, w, h))

            if len(boxes_queue) == VALID_BOUNDING_BOXES_REQUIRED:
                xs = [b[0] for b in boxes_queue]
                ys = [b[1] for b in boxes_queue]
                # Check if movement is within 100 pixels for all pairs
                stable = all(
                    abs(xs[i] - xs[i - 1]) <= STABILITY_PIXEL_MOVEMENT_ALLOWED
                    and abs(ys[i] - ys[i - 1]) <= STABILITY_PIXEL_MOVEMENT_ALLOWED
                     for i in range(1, VALID_BOUNDING_BOXES_REQUIRED)
                )
                if not stable:
                    boxes_queue.popleft()
                    # todo: split queue at latest point not stable

            gray_crop = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray_crop, cv2.CV_64F).var()
            is_sharp = laplacian_var > SHARPNESS_THRESHOLD
        else:
            boxes_queue.clear()
            
        if area >= MINIMUM_BOX_AREA and stable and is_sharp:
            boxes_queue.clear()
            return jsonify(success=True, image=base_64_image, rect=rect)
        else:
            boxes_queue_len = int(len(boxes_queue))
            return jsonify(success=False, image=base_64_image, rect=rect, boxes_queue_len=boxes_queue_len, is_sharp=bool(is_sharp))
        # --- End detection confirmation logic ---
    else:
        boxes_queue.clear()
        return jsonify(success=False, rect=None)

@app.route('/generate_game_info', methods=['POST'])
def generate_game_info():
    data = request.get_json()
    image = data.get('image')

    if not image:
        return jsonify({'success': False, 'error': 'Missing image'}), 400
    
    class GameDetails(BaseModel):
        reasoning: str
        isItAVideoGame: bool
        title: str | None=None
        system: str | None=None
        genre: str | None=None
        publisher: str | None=None
        releaseYear: int | None=None
        labelCode: str | None=None
        region: str | None=None

    response = client.responses.parse(
        # model="gpt-4.1",
        model="gpt-4o-mini",
        temperature=0,
        input=[
            {"role": "system", "content": "You are an expert video game identifier. \
             Consider the game cartridge type and label text, \
             alongside your knowledge to identify the game in the image provided. \
             isItAVideoGame: if this is false, return '' for title, system, publisher, releaseYear and labelCode. \
             title: the game's title. \
             system: do not include manufacturer (i.e. return Game Boy not Nintendo Game Boy, or return Mega Drive not Sega Mega Drive) \
             genre: a one or two word summary of the game's primary genre (i.e. Puzzle, Platformer, Action-Adventure, RPG etc) \
             publisher: the game's publisher on this particular system, usually but not always displayed on the label text \
             releaseYear: the game's release year on this particular system and region \
             labelCode: the game's label code (if present) in the acknowledged system format (i.e. a DMG code for Game Boy) \
             region: based on cartridge type, artwork and label, return the region (i.e. Europe, United Kingdom, Japan, United States etc) \
             Return '' if you are not sure about any field."},
            {"role": "user",
                "content": [
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{image}"}
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
    app.run(debug=True, host='127.0.0.1', port=5001)
