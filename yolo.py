import cv2
import numpy as np

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