from ultralytics import YOLO
import cv2
import numpy as np

# Load pre-trained YOLOv8 model
model = YOLO("yolov8n.pt")

def detect_text_regions(frame):
    """
    Detect regions in frame that likely contain text.
    Returns list of bounding boxes [x1, y1, x2, y2].
    """
    height, width = frame.shape[:2]
    # Divide frame into 3 sections
    boxes = [
        [0, 0, width, height//3],          # Top section (Profile)
        [0, height//3, width, 2*height//3], # Middle (Email)
        [0, 2*height//3, width, height]     # Bottom (Ad)
    ]
    return boxes