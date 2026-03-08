import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

def detect_text_regions(frame):
    """
    Simple region detection - divide frame into 3 horizontal sections
    """
    try:
        height, width = frame.shape[:2]
        
        # Divide frame into 3 sections
        regions = [
            (0, 0, width, height//3),          # Top - Profile
            (0, height//3, width, 2*height//3), # Middle - Email
            (0, 2*height//3, width, height)     # Bottom - Ad
        ]
        
        return regions
        
    except Exception as e:
        logger.error(f"Region detection error: {str(e)}")
        return []
