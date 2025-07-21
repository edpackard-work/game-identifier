import cv2
import numpy as np
import base64
from PIL import Image
from io import BytesIO
from typing import Tuple, TypedDict, Sequence, Deque, Any, NotRequired
from constants import Constants
import logging


class Rect(TypedDict):
    x: int
    y: int
    w: int
    h: int
    label: str
    confidence: float


class PostProcessResponseBody(TypedDict):
    success: bool
    image: NotRequired[str | None]
    rect: NotRequired[Rect | None]
    is_sharp: NotRequired[bool | None]
    boxes_queue_len: NotRequired[int | None]


Detection = Tuple[int, int, int, int, str, float] | None
BoxesQueue = Deque[Tuple[int, int, int, int]]


def load_yolo(cfg: str, weights: str, names: str) -> Tuple[cv2.dnn.Net, Sequence[str], list[str]]:
    logging.info("Loading YOLO model...")
    try:
        net = cv2.dnn.readNetFromDarknet(cfg, weights)
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        with open(names, 'r') as f:
            labels = [line.strip() for line in f.readlines()]
        layer_names = net.getLayerNames()
        unconnected: np.typing.ArrayLike = np.array(net.getUnconnectedOutLayers())
        output_layers = [layer_names[int(i) - 1] for i in unconnected.flatten()]
        logging.info("YOLO model loaded successfully")
        return net, output_layers, labels
    except Exception:
        logging.exception("Error loading YOLO model")
        raise


def get_frame(data: str) -> cv2.typing.MatLike:
    img_data = data.split(',')[1]
    img_bytes = base64.b64decode(img_data)
    img = Image.open(BytesIO(img_bytes))
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    return frame


def detect(frame: cv2.typing.MatLike, net: cv2.dnn.Net, output_layers: Sequence[str], labels: list[str], constants: Constants) -> Detection:
    try:
        (H, W) = frame.shape[:2]
        size = constants['YOLO_INPUT_SIZE']
        blob = cv2.dnn.blobFromImage(
            frame, 1/255.0, (size, size), swapRB=True, crop=False)
        net.setInput(blob)
        layer_outputs: Sequence[cv2.typing.MatLike] = net.forward(output_layers)
        boxes: list[list[int]] = []
        confidences: list[float] = []
        classIDs: list[np.intp] = []
        output: np.typing.NDArray[Any]

        for output in layer_outputs:
            for detection in output:
                scores = detection[5:]
                classID = np.argmax(scores)
                confidence = scores[classID]
                if confidence > constants['YOLO_CONFIDENCE']:
                    box = detection[0:4] * np.array([W, H, W, H])
                    (centerX, centerY, width, height) = box.astype('int')
                    x = int(centerX - (width / 2))
                    y = int(centerY - (height / 2))
                    boxes.append([x, y, int(width), int(height)])
                    confidences.append(float(confidence))
                    classIDs.append(classID)

        idxs = cv2.dnn.NMSBoxes(
            boxes, confidences, constants['YOLO_NMS'], constants['YOLO_OVERLAP'])
        idxs = np.asarray(idxs)

        if len(idxs) > 0:
            idxs_flat = idxs.flatten()
            best_idx: np.typing.NDArray[np.int_] = idxs_flat[np.argmax(
                [confidences[int(i)] for i in idxs_flat])]
            x, y, w, h = boxes[best_idx]
            classID = classIDs[best_idx]
            label = labels[classID]
            confidence = confidences[best_idx]
            logging.debug("Detection complete, found %d objects", len(idxs))
            return x, y, w, h, label, confidence
        return None
    except Exception:
        logging.exception("Error during detection")
        raise


def postprocess(frame: cv2.typing.MatLike, detection: Detection, constants: Constants, boxes_queue: BoxesQueue) -> PostProcessResponseBody:
    if detection is None:
        boxes_queue.clear()
        responseBody: PostProcessResponseBody = {"success": False}
        return responseBody

    x, y, w, h, label, confidence = detection
    (H, W) = frame.shape[:2]
    x1, y1, x2, y2 = max(0, x), max(0, y), min(W, x+w), min(H, y+h)
    
    # Validate cropping coordinates
    if x1 >= x2 or y1 >= y2:
        boxes_queue.clear()
        return {"success": False}
    
    cropped = frame[y1:y2, x1:x2]
    
    # Validate cropped image is not empty
    if cropped.size == 0:
        boxes_queue.clear()
        return {"success": False}
    
    _, buffer = cv2.imencode('.png', cropped)
    base_64_image = base64.b64encode(buffer).decode()
    rect: Rect = {"x": int(x), "y": int(y), "w": int(w), "h": int(
        h), "label": label, "confidence": float(confidence)}
    area = w * h
    stable = False
    is_sharp = False

    if area >= constants['DETECTION_MIN_AREA']:
        boxes_queue.append((x, y, w, h))
        if len(boxes_queue) == constants['DETECTION_STABILITY_FRAMES']:
            xs = [b[0] for b in boxes_queue]
            ys = [b[1] for b in boxes_queue]
            stable = all(
                abs(xs[i] - xs[i-1]) <= constants['DETECTION_MAX_MOVEMENT'] and
                abs(ys[i] - ys[i-1]) <= constants['DETECTION_MAX_MOVEMENT']
                for i in range(1, constants['DETECTION_STABILITY_FRAMES'])
            )
            if not stable:
                boxes_queue.popleft()
        gray_crop = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray_crop, cv2.CV_64F).var()
        is_sharp = laplacian_var > constants['DETECTION_SHARPNESS']
    else:
        boxes_queue.clear()

    final_response: PostProcessResponseBody = {
        'success': True,
        'image': base_64_image,
        'rect': rect,
        'is_sharp': bool(is_sharp),
        'boxes_queue_len': len(boxes_queue)
    }

    if area >= constants['DETECTION_MIN_AREA'] and stable and is_sharp:
        boxes_queue.clear()
        final_response['success'] = True
    else:
        final_response['success'] = False

    return final_response
