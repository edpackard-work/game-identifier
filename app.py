import cv2
import numpy as np
import base64
import os
import json
import signal
import sys
from collections import deque

from flask import Flask, render_template, request, jsonify
from PIL import Image
from io import BytesIO
from openai import OpenAI
from pydantic import BaseModel

YOLO_CONFIG = {
    'cfg_path': 'model/yolov4-tiny-custom.cfg',
    'weights_path': 'model/yolov4-tiny-custom_last.weights',
    'names_path': 'model/obj.names',
    'confidence_threshold': 0.3,
    'nms_threshold': 0.3,
    'nms_overlap': 0.4,
    'input_size': (416, 416)
}

DETECTION_CONFIG = {
    'min_area': 75000,
    'stability_frames': 8,
    'max_movement': 100,
    'sharpness_threshold': 150
}

app = Flask(__name__)
app.config.from_file("config.json", load=json.load)
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', app.config.get('OPENAI_API_KEY'))

# For development/demo use only: global queue to track last N bounding boxes
# In production/multiclient, use per-session or per-client storage
boxes_queue = deque(maxlen=DETECTION_CONFIG['stability_frames'])

# Load class labels
with open(YOLO_CONFIG['names_path'], 'r') as f:
    LABELS = [line.strip() for line in f.readlines()]

# Load YOLOv4-tiny model
net = cv2.dnn.readNetFromDarknet(YOLO_CONFIG['cfg_path'], YOLO_CONFIG['weights_path'])
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

def yolo_detect(frame, net, output_layers, labels, config):
    (H, W) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, config['input_size'], swapRB=True, crop=False)
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
            if confidence > config['confidence_threshold']:
                box = detection[0:4] * np.array([W, H, W, H])
                (centerX, centerY, width, height) = box.astype('int')
                x = int(centerX - (width / 2))
                y = int(centerY - (height / 2))
                boxes.append([x, y, int(width), int(height)])
                confidences.append(float(confidence))
                classIDs.append(classID)
    idxs = cv2.dnn.NMSBoxes(boxes, confidences, config['nms_threshold'], config['nms_overlap'])
    idxs = np.asarray(idxs)
    if len(idxs) > 0:
        idxs_flat = idxs.flatten()
        best_idx = idxs_flat[np.argmax([confidences[i] for i in idxs_flat])]
        x, y, w, h = boxes[best_idx]
        classID = classIDs[best_idx]
        label = labels[classID]
        confidence = confidences[best_idx]
        return x, y, w, h, label, confidence
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_frame', methods=['POST'])
def process_frame():
    try:
        global boxes_queue
        data = request.get_json()
        img_data = data['image'].split(',')[1]
        img_bytes = base64.b64decode(img_data)
        img = Image.open(BytesIO(img_bytes))
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        detection = yolo_detect(frame, net, output_layers, LABELS, YOLO_CONFIG)
        if detection:
            x, y, w, h, label, confidence = detection
            (H, W) = frame.shape[:2]
            x1, y1, x2, y2 = max(0, x), max(0, y), min(W, x+w), min(H, y+h)
            cropped = frame[y1:y2, x1:x2]
            _, buffer = cv2.imencode('.png', cropped)
            base_64_image = base64.b64encode(buffer).decode()
            rect = {"x": int(x), "y": int(y), "w": int(w), "h": int(h), "label": label, "confidence": float(confidence), "boxes_queue_len": len(boxes_queue)}
            area = w * h
            stable = False
            is_sharp = False
            if area >= DETECTION_CONFIG['min_area']:
                boxes_queue.append((x, y, w, h))
                if len(boxes_queue) == DETECTION_CONFIG['stability_frames']:
                    xs = [b[0] for b in boxes_queue]
                    ys = [b[1] for b in boxes_queue]
                    stable = all(abs(xs[i] - xs[i-1]) <= DETECTION_CONFIG['max_movement'] and abs(ys[i] - ys[i-1]) <= DETECTION_CONFIG['max_movement'] for i in range(1, DETECTION_CONFIG['stability_frames']))
                    if not stable:
                        boxes_queue.popleft()
                gray_crop = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
                laplacian_var = cv2.Laplacian(gray_crop, cv2.CV_64F).var()
                is_sharp = laplacian_var > DETECTION_CONFIG['sharpness_threshold']
            else:
                boxes_queue.clear()
            if area >= DETECTION_CONFIG['min_area'] and stable and is_sharp:
                return jsonify(success=True, image=base_64_image, rect=rect)
            else:
                return jsonify(success=False, image=base_64_image, rect=rect)
        else:
            boxes_queue.clear()
            return jsonify(success=False, rect=None)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

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
