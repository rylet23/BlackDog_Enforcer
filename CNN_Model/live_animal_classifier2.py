#!/usr/bin/env python3
"""
ZED Live Animal Classifier v2
Matches training architecture: 128x128 input, nn.Sequential structure.
Can output to GUI or console (JSON) for piping to car controller.
"""

import cv2
import time
import sys
import json
import argparse
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
    print(f"Loading model from {model_path}...", file=sys.stderr)
    model = SimpleCNN()

    try:
        state_dict = torch.load(model_path, map_location=torch.device('cpu'))
        model.load_state_dict(state_dict)
        model.eval()
        print("✓ Model loaded successfully!", file=sys.stderr)
        return model
    except Exception as e:
        print(f"ERROR loading model: {e}", file=sys.stderr)
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
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='ZED Live Animal Classifier')
    parser.add_argument('--mode', choices=['gui', 'console'], default='gui',
                        help='Output mode: gui (display window) or console (JSON output)')
    parser.add_argument('--confidence-threshold', type=float, default=0.80,
                        help='Confidence threshold for animal detection (default: 0.80)')
    parser.add_argument('--interval', type=float, default=0.3,
                        help='Inference interval in seconds (default: 0.3)')
    parser.add_argument('--model', default='animal_classifier.pth',
                        help='Path to model file (default: animal_classifier.pth)')

    args = parser.parse_args()

    # Preprocessing (Must be 128x128 to match your trainer)
    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    model = load_model(args.model)
    if model is None:
        return

    # Setup ZED / USB Camera
    print("Initializing camera...", file=sys.stderr)
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        print("ERROR: Camera failed to open", file=sys.stderr)
        return

    # Camera Config
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print("Camera initialized", file=sys.stderr)

    inference_interval = args.interval
    confidence_threshold = args.confidence_threshold
    last_inference_time = time.time()
    result = "Waiting..."
    confidence = 0.0

    if args.mode == 'gui':
        print(f"\n=== GUI MODE ===", file=sys.stderr)
        print(f"Confidence threshold: {confidence_threshold}", file=sys.stderr)
        print("Press 'q' to quit\n", file=sys.stderr)
    else:
        print(f"\n=== CONSOLE MODE (JSON) ===", file=sys.stderr)
        print(f"Confidence threshold: {confidence_threshold}", file=sys.stderr)
        print("Outputting JSON to stdout for piping to car controller", file=sys.stderr)
        print("Press Ctrl+C to quit\n", file=sys.stderr)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("WARNING: Frame grab failed", file=sys.stderr)
                time.sleep(0.1)
                continue

            # Inference logic
            current_time = time.time()
            if current_time - last_inference_time >= inference_interval:
                result, confidence = classify_frame(model, frame, transform)
                last_inference_time = current_time

                # CONSOLE MODE: Output JSON to stdout
                if args.mode == 'console':
                    output = {
                        'status': 'animal_detected' if (
                                    result == "ANIMAL" and confidence >= confidence_threshold) else 'no_animal',
                        'confidence': round(confidence, 3),
                        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                        'threshold': confidence_threshold
                    }

                    # Print JSON to stdout (can be piped)
                    print(json.dumps(output))
                    sys.stdout.flush()

                    # Also print to stderr for human readability
                    if output['status'] == 'animal_detected':
                        print(f"\033[91m[ALERT] ANIMAL DETECTED! Confidence: {confidence:.3f}\033[0m", file=sys.stderr)
                    else:
                        print(f"[INFO] {result} (Confidence: {confidence:.3f})", file=sys.stderr)

                # GUI MODE: No saving

            # GUI MODE: Show window
            if args.mode == 'gui':
                display_frame = frame.copy()

                # Determine color based on threshold
                if result == "ANIMAL" and confidence >= confidence_threshold:
                    color = (0, 0, 255)  # Red - above threshold
                    status = "ANIMAL DETECTED!"
                elif result == "ANIMAL":
                    color = (0, 165, 255)  # Orange - animal but below threshold
                    status = f"{result} (Low Conf)"
                else:
                    color = (0, 255, 0)  # Green
                    status = result

                # Draw overlay
                cv2.putText(display_frame, status, (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                cv2.putText(display_frame, f"Confidence: {confidence:.2%}", (20, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display_frame, f"Threshold: {confidence_threshold:.0%}", (20, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

                cv2.imshow("ZED Live Classifier", display_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
            else:
                # Console mode - small delay
                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\nStopped by user", file=sys.stderr)
    finally:
        cap.release()
        if args.mode == 'gui':
            cv2.destroyAllWindows()
        print("Classifier shutdown complete", file=sys.stderr)


if __name__ == "__main__":
    main()