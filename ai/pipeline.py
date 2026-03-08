import cv2
import numpy as np
import logging
from datetime import datetime
import os

from .detector import detect_text_regions
from .ocr import (
    extract_text_from_image, extract_player_id, extract_profile_date,
    extract_email_date, extract_email_content, extract_ad_content
)

logger = logging.getLogger(__name__)

def process_video(video_path):
    """
    Main video processing pipeline
    """
    try:
        logger.info(f"Starting video processing: {video_path}")
        start_time = datetime.now()
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        logger.info(f"Video duration: {duration:.1f}s, FPS: {fps:.1f}, Frames: {total_frames}")
        
        # Process every 1 second
        all_texts = []
        frames_processed = 0
        
        for second in range(0, int(duration) + 1, 1):
            # Set frame position
            frame_pos = int(second * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            frames_processed += 1
            
            # Resize for faster processing
            h, w = frame.shape[:2]
            if w > 1280:
                scale = 1280 / w
                new_w = 1280
                new_h = int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h))
            
            # Get text from frame
            texts = extract_text_from_image(frame)
            all_texts.extend(texts)
        
        cap.release()
        
        # Remove duplicates
        all_texts = list(set(all_texts))
        
        # Extract specific information
        result = {
            "player_id": extract_player_id(all_texts),
            "profile_date": extract_profile_date(all_texts),
            "email_date": extract_email_date(all_texts),
            "email_lines": extract_email_content(all_texts),
            "ad_lines": extract_ad_content(all_texts),
            "all_text": all_texts[:20],  # Top 20 lines
            "metadata": {
                "frames_processed": frames_processed,
                "duration_seconds": duration,
                "processing_time_seconds": (datetime.now() - start_time).total_seconds()
            }
        }
        
        logger.info(f"Processing completed in {result['metadata']['processing_time_seconds']:.1f}s")
        return result
        
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        return {"error": str(e)}
    finally:
        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)
