from paddleocr import PaddleOCR
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import cv2
import numpy as np

# Initialize OCR engines
paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")

def extract_text_paddle(image):
    """Use PaddleOCR for general text (email content)."""
    result = paddle_ocr.ocr(image, cls=True)
    texts = []
    if result and result[0]:
        for line in result[0]:
            texts.append(line[1][0])
    return texts

def extract_all_text(frame):
    """Master function to extract all text."""
    texts = extract_text_paddle(frame)
    return texts