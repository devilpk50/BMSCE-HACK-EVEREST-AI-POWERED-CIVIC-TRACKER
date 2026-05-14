import torch
from ultralytics import YOLO
import imagehash
from PIL import Image

class CivicAI:
    def __init__(self):
        # Load the lightest model for maximum speed on the 1650
        self.model = YOLO('yolov8n.pt') 
        
        # Ensure it uses the GPU
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        
        # Target classes from the COCO dataset: 
        # 39: bottle, 41: cup, 45: bowl, 67: dining table (often has trash)
        # You can expand this list or fine-tune later
        self.garbage_classes = [39, 41, 45, 67]

    def validate_report(self, image_path):
        """
        Analyzes the image for garbage and generates a unique fingerprint.
        """
        # 1. Detection
        results = self.model(image_path, device=self.device, verbose=False)
        is_verified = False
        confidence = 0.0
        
        for result in results:
            for box in result.boxes:
                if int(box.cls[0]) in self.garbage_classes and box.conf[0] > 0.5:
                    is_verified = True
                    confidence = float(box.conf[0])
                    break

        # 2. Perceptual Hashing (Anti-Fraud)
        # Generates a fingerprint based on image structure
        img = Image.open(image_path)
        fingerprint = str(imagehash.phash(img))

        return {
            "is_valid": is_verified,
            "confidence": confidence,
            "fingerprint": fingerprint
        }

if __name__ == "__main__":
    # Quick internal test
    # ai = CivicAI()
    # print(ai.validate_report("test.jpg"))
    pass
