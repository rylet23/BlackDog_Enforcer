#!/usr/bin/env python3
"""
ZED Live Animal Classifier v2
Matches training architecture: 128x128 input, nn.Sequential structure.
"""

import cv2
import time
import os
import torch
from torch import nn
from torchvision import transforms
from PIL import Image

# 1. CNN Model Definition (Matches your training script exactly)
class SimpleCNN(nn.Module):
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.main = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(64 * 16 * 16, 128), nn.ReLU(),
            nn.Linear(128, 1), nn.Sigmoid()
        )
        
    def forward(self, x):
        return self.main(x)

def load_model(model_path='animal_classifier.pth'):
    """Load the trained CNN model"""
    print(f"Loading model from {model_path}...")
    model = SimpleCNN()
    
    try:
        # Load the weights (map_location ensures it works on CPU/Pi)
        state_dict = torch.load(model_path, map_location=torch.device('cpu'))
        model.load_state_dict(state_dict)
        model.eval()
        print("✓ Model loaded successfully!")
        return model
    except Exception as e:
        print(f"ERROR loading model: {e}")
        return None

def classify_frame(model, frame, transform):
    """
    Classify a single frame
    Returns: (prediction_string, confidence_score)
    """
    # Convert BGR (OpenCV) to RGB (PIL)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb)
    
    # Apply 128x128 preprocessing
    input_tensor = transform(pil_image).unsqueeze(0)
    
    # Run inference
    with torch.no_grad():
        output = model(input_tensor)
        confidence = output.squeeze().item()
        
        # Note: In your training script, binary_labels = (labels > 0)
        # This usually means the second folder loaded is the "Positive" (1) class.
        prediction = (confidence > 0.5)
    
    result = "ANIMAL" if prediction else "NOT ANIMAL"
    return result, confidence

def main():
    # 2. Preprocessing (Must be 128x128 to match your trainer)
    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    model = load_model('animal_classifier.pth')
    if model is None:
        return
    
    # Setup ZED / USB Camera
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        print("ERROR: Camera failed to open")
        return

    # Camera Config
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Storage for detections
    save_dir = "captured_frames"
    os.makedirs(save_dir, exist_ok=True)
    
    inference_interval = 0.3  # Reduced interval for faster feedback
    last_inference_time = time.time()
    result = "Waiting..."
    confidence = 0.0
    save_detections = False

    print("\nStarting Live Feed. Press 'q' to quit, 's' to save detections.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret: break

            # Inference logic
            current_time = time.time()
            if current_time - last_inference_time >= inference_interval:
                # Use the original frame for classification (it gets resized in classify_frame)
                result, confidence = classify_frame(model, frame, transform)
                last_inference_time = current_time
                
                if result == "ANIMAL" and save_detections:
                    fn = os.path.join(save_dir, f"det_{int(time.time())}.jpg")
                    cv2.imwrite(fn, frame)

            # --- UI Overlay ---
            color = (0, 0, 255) if result == "ANIMAL" else (0, 255, 0)
            cv2.putText(frame, f"{result} ({confidence:.2f})", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            if save_detections:
                cv2.putText(frame, "RECORDING ON", (20, 450), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            cv2.imshow("ZED Live Classifier", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'): break
            if key == ord('s'): save_detections = not save_detections

    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
