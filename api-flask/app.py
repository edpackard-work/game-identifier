import os
from collections import deque

from flask import Flask, request, jsonify, current_app, Response
from flask_cors import CORS
from openai import OpenAI

from yolo import load_yolo, detect, postprocess, get_frame
from generate_game_info import generate_game_info
from constants import get_constants, Constants

from typing import cast, Tuple

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logging.getLogger('openai').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)


logging.info("Starting Flask app...")

ApiResponse = Tuple[Response, int]


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)
    if os.getenv('OPENAI_API_KEY'):
        app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    constants: Constants = get_constants()
    setattr(app, 'constants', constants)
    net, output_layers, labels = load_yolo(
        constants['YOLO_CFG'],
        constants['YOLO_WEIGHTS'],
        constants['YOLO_NAMES']
    )
    setattr(app, 'yolo_net', net)
    setattr(app, 'yolo_output_layers', output_layers)
    setattr(app, 'yolo_labels', labels)
    setattr(app, 'boxes_queue', deque(
        maxlen=constants['DETECTION_STABILITY_FRAMES']))
    setattr(app, 'openai_client', OpenAI(
        api_key=cast(str, app.config['OPENAI_API_KEY'])))
    register_routes(app)
    return app


def register_routes(app: Flask):
    @app.route('/process_frame', methods=['POST'])
    def process_frame() -> ApiResponse:  # type: ignore
        try:
            data = request.get_json()
            frame = get_frame(data['image'])
            net = getattr(current_app, 'yolo_net')
            output_layers = getattr(current_app, 'yolo_output_layers')
            labels = getattr(current_app, 'yolo_labels')
            boxes_queue = getattr(current_app, 'boxes_queue')
            constants = getattr(current_app, 'constants')
            detection = detect(frame, net, output_layers, labels, constants)
            responseBody = postprocess(
                frame, detection, constants, boxes_queue)
            return jsonify(responseBody), 200
        except Exception as e:
            logging.exception("An error occurred in process_frame")
            return jsonify(success=False, error=str(e)), 500

    @app.route('/generate_game_info', methods=['POST'])
    def generate_game_info_route() -> ApiResponse:  # type: ignore
        data = request.get_json()
        image = data.get('image')
        openai_client = getattr(current_app, 'openai_client')
        responseBody = generate_game_info(
            openai_client, image, current_app.debug)
        if responseBody['success']:
            return jsonify(responseBody), 200
        else:
            return jsonify(responseBody), 400


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5001)
