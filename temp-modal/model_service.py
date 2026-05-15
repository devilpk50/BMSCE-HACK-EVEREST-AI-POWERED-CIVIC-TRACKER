# ============================================================
# SEGMENT 1: DEPENDENCIES
# ============================================================
import torch
import imagehash
from PIL import Image
from ultralytics import YOLO
import os

# ============================================================
# SEGMENT 2: THE AI CORE (YOLO + HARDWARE)
# ============================================================
class CivicModel:
    def __init__(self, model_weights='best.pt'):
        """
        Loads your custom-trained 'best.pt'.
        Defaults to your GTX 1650 (CUDA) but switches to CPU for judges.
        """
        if not os.path.exists(model_weights):
            raise FileNotFoundError(f"Weights file '{model_weights}' not found. Make sure best.pt is in the project root!")

        self.model = YOLO(model_weights)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        
        # We no longer need target_ids = [39, 41, 67]
        # Your model is now a single-purpose 'Trash Detector'
        print(f"Model successfully loaded on {self.device}")

    # ============================================================
    # SEGMENT 3: DETECTION & REJECTION LOGIC
    # ============================================================
    def _run_detection(self, image_path):
        """
        Internal: Runs the actual visual check using your custom model.
        """
        results = self.model(image_path, device=self.device, verbose=False)
        
        detected_garbage = False
        highest_conf = 0.0

        for result in results:
            # Check if the model found any boxes at all
            if len(result.boxes) > 0:
                # Get the highest confidence score from all detections in this image
                conf_list = result.boxes.conf.tolist()
                max_conf = max(conf_list)
                
                # Validation Threshold: Only accept if AI is more than 50% sure
                if max_conf > 0.5:
                    detected_garbage = True
                    highest_conf = max_conf
                    break # We found a valid pile, no need to keep looping

        if detected_garbage:
            return True, highest_conf, "Verification Successful: Civic issue identified."
        
        return False, 0.0, "Rejected: No significant garbage detected in the image."

    # ============================================================
    # SEGMENT 4: ANTI-FRAUD (STRUCTURAL FINGERPRINT)
    # ============================================================
    def _get_phash(self, image_path):
        """
        Internal: Creates a unique fingerprint of the image structure.
        Prevents users from uploading slightly edited copies of old photos.
        """
        img = Image.open(image_path)
        return str(imagehash.phash(img))

    # ============================================================
    # SEGMENT 5: PUBLIC INTERFACE (FOR THE BACKEND)
    # ============================================================
    def validate_submission(self, image_path):
        """
        The main method your teammates will call.
        """
        is_valid, confidence, message = self._run_detection(image_path)
        fingerprint = self._get_phash(image_path)

        return {
            "status": "VALIDATED" if is_valid else "REJECTED",
            "is_valid": is_valid,
            "confidence": round(confidence, 2),
            "message": message,
            "p_hash": fingerprint
        }

# ============================================================
# SEGMENT 6: LOCAL TEST ON SYSTEM
# ============================================================
if __name__ == "__main__":
    try:
        # Create the instance - will now look for 'best.pt' automatically
        brain = CivicModel()
        
        # TIP: Copy any image from your 'dataset/val/images' folder 
        # and rename it to 'test.jpg' to run this test.
        test_image = "test3.jpg" 
        
        if os.path.exists(test_image):
            print(f"--- Running Local Validation on {test_image} ---")
            import time
            start_time = time.time()
            
            # Run the actual validation
            report = brain.validate_submission(test_image)
            
            duration = (time.time() - start_time) * 1000
            print(f"Result: {report['status']}")
            print(f"Confidence Score: {report['confidence']}")
            print(f"AI Note: {report['message']}")
            print(f"Fingerprint: {report['p_hash']}")
            print(f"Processing Time: {duration:.2f}ms")
        else:
            print(f"Result: Test file '{test_image}' not found.")
            print("Action: Move an image to this folder and rename it 'test.jpg' to verify your model works!")
            
    except Exception as e:
        print(f"Setup Error: {e}")
