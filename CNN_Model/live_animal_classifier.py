#!/usr/bin/env python3
"""
ZED Live Animal Classifier
Captures frames from ZED camera and classifies them in real-time using trained CNN model.
"""

import cv2
import time
import os
import torch
from torch import nn
from torchvision import transforms
from PIL import Image

# CNN Model Definition (must match training architecture)
class SimpleCNN(nn.Module):
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.fc1 = nn.Linear(64 * 28 * 28, 512)
        self.fc2 = nn.Linear(512, 1)
    
        self.pool = nn.MaxPool2d(2, 2)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        x = self.relu(self.conv3(x))
        x = self.pool(x)
    
        x = x.view(-1, 64 * 28 * 28)
        x = self.relu(self.fc1(x))
        x = self.sigmoid(self.fc2(x))
        return x


def load_model(model_path='animal_classifier.pth'):
    """Load the trained CNN model"""
    print(f"Loading model from {model_path}...")
    model = SimpleCNN()
    
    try:
        model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        model.eval()
        print("✓ Model loaded successfully!")
        return model
    except FileNotFoundError:
        print(f"ERROR: Model file '{model_path}' not found!")
        print("Please train the model first using cnn-determine.py")
        return None
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
    
    # Apply same preprocessing as training
    input_tensor = transform(pil_image).unsqueeze(0)
    
    # Run inference
    with torch.no_grad():
        output = model(input_tensor)
        confidence = output.squeeze().item()
        prediction = (confidence > 0.5)
    
    result = "ANIMAL" if prediction else "NOT ANIMAL"
    return result, confidence


def main():
    """Main function - runs live classification"""
    
    # Image preprocessing (same as training)
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Load trained model
    model = load_model('animal_classifier.pth')
    if model is None:
        return
    
    # Setup camera
    print("\nInitializing ZED camera...")
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    
    if not cap.isOpened():
        print("ERROR: Camera failed to open")
        print("Check that camera is connected and /dev/video0 exists")
        return
    
    # Configure camera settings
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("✓ Camera initialized")
    
    # Optional: Create directory for saving detections
    save_dir = "captured_frames"
    os.makedirs(save_dir, exist_ok=True)
    
    # Configuration
    inference_interval = 0.5  # Run classification every 0.5 seconds
    save_detections = False   # Toggle with 's' key
    
    print("\n" + "="*50)
    print("LIVE ANIMAL CLASSIFICATION")
    print("="*50)
    print("Controls:")
    print("  'q' - Quit")
    print("  's' - Toggle saving animal detections")
    print("  'c' - Clear console output")
    print("="*50 + "\n")
    
    # State variables
    last_inference_time = time.time()
    frame_count = 0
    detection_count = 0
    result = "Initializing..."
    confidence = 0.0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("WARNING: Frame grab failed")
                time.sleep(0.1)
                continue
            
            # Resize for CNN (224x224)
            cnn_frame = cv2.resize(frame, (224, 224))
            
            # Run classification periodically (not every frame for performance)
            current_time = time.time()
            if current_time - last_inference_time >= inference_interval:
                result, confidence = classify_frame(model, cnn_frame, transform)
                
                # Print result
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] {result} (Confidence: {confidence:.3f})")
                
                # Save frame if animal detected and saving is enabled
                if result == "ANIMAL" and save_detections:
                    filename = os.path.join(save_dir, f"detection_{detection_count:04d}.jpg")
                    cv2.imwrite(filename, frame)
                    print(f"  └─ Saved: {filename}")
                    detection_count += 1
                
                last_inference_time = current_time
                frame_count += 1
            
            # Create display frame with overlay
            display_frame = frame.copy()
            
            # Color based on result
            if result == "ANIMAL":
                color = (0, 0, 255)      # Red
                bg_color = (0, 0, 200)   # Dark red background
            else:
                color = (0, 255, 0)      # Green
                bg_color = (0, 150, 0)   # Dark green background
            
            # Draw semi-transparent background for text
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (5, 5), (400, 100), bg_color, -1)
            cv2.addWeighted(overlay, 0.4, display_frame, 0.6, 0, display_frame)
            
            # Draw text
            cv2.putText(display_frame, result, (15, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
            cv2.putText(display_frame, f"Confidence: {confidence:.2%}", (15, 75), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show frame count and save status
            status_text = f"Frames: {frame_count} | Saved: {detection_count}"
            if save_detections:
                status_text += " | SAVING: ON"
            cv2.putText(display_frame, status_text, (15, display_frame.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Display
            cv2.imshow("ZED Live Animal Classifier", display_frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nQuitting...")
                break
            elif key == ord('s'):
                save_detections = not save_detections
                status = "ON" if save_detections else "OFF"
                print(f"\n>>> Saving detections: {status}\n")
            elif key == ord('c'):
                os.system('clear' if os.name == 'posix' else 'cls')
                print("="*50)
                print("LIVE ANIMAL CLASSIFICATION")
                print("="*50 + "\n")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    finally:
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        
        print("\n" + "="*50)
        print("SESSION SUMMARY")
        print("="*50)
        print(f"Total frames classified: {frame_count}")
        print(f"Animal detections saved: {detection_count}")
        print("="*50)


if __name__ == "__main__":
    main()
