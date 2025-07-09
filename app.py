import cv2
import numpy as np
import base64
import json
from collections import deque

from flask import Flask, render_template, request, jsonify, current_app
from PIL import Image
from io import BytesIO
from openai import OpenAI
from pydantic import BaseModel

from yolo import load_yolo, detect

def create_app():
    app = Flask(__name__)
    app.config.from_file('config.json', load=json.load)
    
    net, output_layers, labels = load_yolo(
        app.config['YOLO_CFG'],
        app.config['YOLO_WEIGHTS'],
        app.config['YOLO_NAMES']
    )
    setattr(app, 'yolo_net', net)
    setattr(app, 'yolo_output_layers', output_layers)
    setattr(app, 'yolo_labels', labels)
    # For development/demo use only: single global queue
    # For multi-user support, use per-user queues (e.g., session, Redis, etc.)
    setattr(app, 'boxes_queue', deque(maxlen=app.config['DETECTION_STABILITY_FRAMES']))
    setattr(app, 'openai_client', OpenAI(api_key=app.config['OPENAI_API_KEY']))
    register_routes(app)
    return app

def register_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/process_frame', methods=['POST'])
    def process_frame():
        try:
            data = request.get_json()
            img_data = data['image'].split(',')[1]
            img_bytes = base64.b64decode(img_data)
            img = Image.open(BytesIO(img_bytes))
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            detection = detect(
                frame,
                getattr(current_app, 'yolo_net'),
                getattr(current_app, 'yolo_output_layers'),
                getattr(current_app, 'yolo_labels'),
                current_app.config
            )
            boxes_queue = getattr(current_app, 'boxes_queue')
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
                if area >= current_app.config['DETECTION_MIN_AREA']:
                    boxes_queue.append((x, y, w, h))
                    if len(boxes_queue) == current_app.config['DETECTION_STABILITY_FRAMES']:
                        xs = [b[0] for b in boxes_queue]
                        ys = [b[1] for b in boxes_queue]
                        stable = all(
                            abs(xs[i] - xs[i-1]) <= current_app.config['DETECTION_MAX_MOVEMENT'] and
                            abs(ys[i] - ys[i-1]) <= current_app.config['DETECTION_MAX_MOVEMENT']
                            for i in range(1, current_app.config['DETECTION_STABILITY_FRAMES'])
                        )
                        if not stable:
                            boxes_queue.popleft()
                    gray_crop = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
                    laplacian_var = cv2.Laplacian(gray_crop, cv2.CV_64F).var()
                    is_sharp = laplacian_var > current_app.config['DETECTION_SHARPNESS']
                else:
                    boxes_queue.clear()
                if area >= current_app.config['DETECTION_MIN_AREA'] and stable and is_sharp:
                    boxes_queue.clear()
                    return jsonify(success=True, image=base_64_image, rect=rect, boxes_queue_len=len(boxes_queue), is_sharp=bool(is_sharp))
                else:
                    return jsonify(success=False, image=None, rect=rect, boxes_queue_len=len(boxes_queue), is_sharp=bool(is_sharp))
            else:
                boxes_queue.clear()
                return jsonify(success=False, image=None, rect=None, boxes_queue_len=None, is_sharp=None)
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
        response = getattr(current_app, 'openai_client').responses.parse(
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
        if current_app.config.get("CV2_DEBUG") == True:
            print(responseJson)
        return responseJson

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5001)
