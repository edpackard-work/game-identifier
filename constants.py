from typing import TypedDict


class Constants(TypedDict):
    YOLO_INPUT_SIZE: int
    YOLO_CONFIDENCE: float
    YOLO_NMS: float
    YOLO_OVERLAP: float
    DETECTION_MIN_AREA: int
    DETECTION_STABILITY_FRAMES: int
    DETECTION_MAX_MOVEMENT: int
    DETECTION_SHARPNESS: int
    YOLO_CFG: str
    YOLO_WEIGHTS: str
    YOLO_NAMES: str


def get_constants() -> Constants:
    return {
        "YOLO_CFG": "model/yolov4-tiny-custom.cfg",
        "YOLO_WEIGHTS": "model/yolov4-tiny-custom_last.weights",
        "YOLO_NAMES": "model/obj.names",
        'YOLO_INPUT_SIZE': 416,
        'YOLO_CONFIDENCE': 0.75,
        'YOLO_NMS': 0.3,
        'YOLO_OVERLAP': 0.4,
        'DETECTION_MIN_AREA': 75000,
        'DETECTION_STABILITY_FRAMES': 8,
        'DETECTION_MAX_MOVEMENT': 100,
        'DETECTION_SHARPNESS': 150,
    }
