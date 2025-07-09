import cv2
import numpy as np
import base64
from PIL import Image
from io import BytesIO

def load_yolo(cfg, weights, names):
    net = cv2.dnn.readNetFromDarknet(cfg, weights)
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    with open(names, 'r') as f:
        labels = [line.strip() for line in f.readlines()]
    layer_names = net.getLayerNames()
    unconnected = net.getUnconnectedOutLayers()
    if not isinstance(unconnected, np.ndarray):
        unconnected = np.array(unconnected)
    output_layers = [layer_names[i - 1] for i in unconnected.flatten()]
    return net, output_layers, labels

def get_frame(data):
    img_data = data['image'].split(',')[1]
    img_bytes = base64.b64decode(img_data)
    img = Image.open(BytesIO(img_bytes))
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    return frame

def detect(frame, net, output_layers, labels, config):
    (H, W) = frame.shape[:2]
    size = (config['YOLO_INPUT_SIZE'], config['YOLO_INPUT_SIZE'])
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, size, swapRB=True, crop=False)
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
            if confidence > config['YOLO_CONFIDENCE']:
                box = detection[0:4] * np.array([W, H, W, H])
                (centerX, centerY, width, height) = box.astype('int')
                x = int(centerX - (width / 2))
                y = int(centerY - (height / 2))
                boxes.append([x, y, int(width), int(height)])
                confidences.append(float(confidence))
                classIDs.append(classID)
    idxs = cv2.dnn.NMSBoxes(boxes, confidences, config['YOLO_NMS'], config['YOLO_OVERLAP'])
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

def postprocess(frame, detection, config, boxes_queue):
    if detection is None:
        boxes_queue.clear()
        return False, None, None, None
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
    if area >= config['DETECTION_MIN_AREA']:
        boxes_queue.append((x, y, w, h))
        if len(boxes_queue) == config['DETECTION_STABILITY_FRAMES']:
            xs = [b[0] for b in boxes_queue]
            ys = [b[1] for b in boxes_queue]
            stable = all(
                abs(xs[i] - xs[i-1]) <= config['DETECTION_MAX_MOVEMENT'] and
                abs(ys[i] - ys[i-1]) <= config['DETECTION_MAX_MOVEMENT']
                for i in range(1, config['DETECTION_STABILITY_FRAMES'])
            )
            if not stable:
                boxes_queue.popleft()
        gray_crop = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray_crop, cv2.CV_64F).var()
        is_sharp = laplacian_var > config['DETECTION_SHARPNESS']
    else:
        boxes_queue.clear()
    if area >= config['DETECTION_MIN_AREA'] and stable and is_sharp:
        boxes_queue.clear()
        return True, base_64_image, rect, bool(is_sharp)
    else:
        return False, base_64_image, rect, bool(is_sharp)