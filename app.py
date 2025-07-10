import json
import os
from collections import deque

from flask import Flask, render_template, request, jsonify, current_app, Response
from openai import OpenAI

from yolo import load_yolo, detect, postprocess, get_frame
from generate_game_info import generate_game_info

from typing import Sequence, cast, Union, Tuple

ApiResponse = Union[Response, Tuple[Response, int]]


def create_app() -> Flask:
    app = Flask(__name__)
    if os.path.exists('config.json'):
        app.config.from_file('config.json', load=json.load)
    if os.getenv('OPENAI_API_KEY'):
        app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    net, output_layers, labels = load_yolo(
        cast(str, app.config['YOLO_CFG']),
        cast(str, app.config['YOLO_WEIGHTS']),
        cast(str, app.config['YOLO_NAMES'])
    )
    setattr(app, 'yolo_net', net)
    setattr(app, 'yolo_output_layers', output_layers)
    setattr(app, 'yolo_labels', labels)
    setattr(app, 'boxes_queue', deque(
        maxlen=cast(int, app.config['DETECTION_STABILITY_FRAMES'])))
    setattr(app, 'openai_client', OpenAI(
        api_key=cast(str, app.config['OPENAI_API_KEY'])))
    register_routes(app)
    return app


def register_routes(app: Flask):
    @app.route('/')
    def index() -> str:  # type: ignore
        return render_template('index.html')

    @app.route('/process_frame', methods=['POST'])
    def process_frame() -> ApiResponse:  # type: ignore
        try:
            data = request.get_json()
            frame = get_frame(data['image'])
            net = getattr(current_app, 'yolo_net')
            output_layers: Sequence[str] = getattr(
                current_app, 'yolo_output_layers')
            labels = getattr(current_app, 'yolo_labels')
            boxes_queue = getattr(current_app, 'boxes_queue')
            config = current_app.config
            detection = detect(frame, net, output_layers, labels, config)
            success, base_64_image, rect, is_sharp = postprocess(
                frame, detection, config, boxes_queue)
            return jsonify(success=success, image=base_64_image, rect=rect, is_sharp=is_sharp, boxes_queue_len=len(boxes_queue))
        except Exception as e:
            print(e)
            return jsonify(success=False, error=str(e)), 500

    @app.route('/generate_game_info', methods=['POST'])
    def generate_game_info_route() -> ApiResponse:  # type: ignore
        data = request.get_json()
        image = data.get('image')
        openai_client = getattr(current_app, 'openai_client')
        config = current_app.config
        response = generate_game_info(openai_client, image, config)
        return response


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5001)
