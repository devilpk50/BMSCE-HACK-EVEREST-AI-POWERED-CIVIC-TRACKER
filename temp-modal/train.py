import torch
from ultralytics import YOLO
import os

def start_training():
    # 1. Path Configuration
    # Ensure this matches your data.yaml location
    YAML_PATH = 'data.yaml' 
    
    # 2. Hardware Check
    if not torch.cuda.is_available():
        print("CRITICAL: CUDA not detected. Check your WSL NVIDIA drivers!")
        return
    
    print(f"🚀 Training on: {torch.cuda.get_device_name(0)}")
    print(f"Memory allocated: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")

    # 3. Load Model (YOLOv8 Nano - light & fast)
    model = YOLO('yolov8n.pt') 

    # 4. The Training Execution
    model.train(
        data=YAML_PATH,
        epochs=100,
        imgsz=640,
        batch=16,       # Batch size 16 for 4GB VRAM
        workers=0,      # CRITICAL: Fix for OSError [Errno 95] on Z: drive
        device=0,       # Use the GTX 1650
        project='civic_tracker_runs',
        name='indian_trash_v1',
        augment=True,   # Helps with diverse trash textures
        patience=20     # Stops early if the model stops improving
    )

if __name__ == "__main__":
    start_training()