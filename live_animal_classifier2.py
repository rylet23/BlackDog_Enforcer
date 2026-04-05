#!/usr/bin/env python3
"""
ZED Live Animal Classifier v2
Matches training architecture: 128x128 input, nn.Sequential structure.
Calls Car_Controller.py directly as a subprocess when animal detected above threshold.
Works in both GUI and console mode.
"""

import cv2
import os
import time
import sys
import argparse
import subprocess
import torch
from torch import nn
from torchvision import transforms
from PIL import Image


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
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb)
    input_tensor = transform(pil_image).unsqueeze(0)
    with torch.no_grad():
        output = model(input_tensor)
        confidence = output.squeeze().item()
        prediction = (confidence > 0.9)
    result = "ANIMAL" if prediction else "NOT ANIMAL"
    return result, confidence


def trigger_car(car_controller_path, last_drive_time, cooldown):
    """Launch Car_Controller if cooldown has elapsed. Returns updated last_drive_time."""
    now = time.time()
    if now - last_drive_time >= cooldown:
        print(f"\033[91m[ALERT] ANIMAL DETECTED — Calling Car Controller\033[0m", file=sys.stderr)
        subprocess.Popen(['python3', car_controller_path])
        return now
    else:
        remaining = cooldown - (now - last_drive_time)
        print(f"[INFO] Animal detected but cooldown active ({remaining:.1f}s remaining)", file=sys.stderr)
        return last_drive_time


def main():
    parser = argparse.ArgumentParser(description='ZED Live Animal Classifier')
    parser.add_argument('--mode', choices=['gui', 'console'], default='gui',
                        help='Output mode: gui (display window) or console (text output)')
    parser.add_argument('--confidence-threshold', type=float, default=0.90,
                        help='Confidence threshold for animal detection (default: 0.90)')
    parser.add_argument('--interval', type=float, default=0.3,
                        help='Inference interval in seconds (default: 0.3)')
    parser.add_argument('--model', default='animal_classifier.pth',
                        help='Path to model file (default: animal_classifier.pth)')
    args = parser.parse_args()

    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    model = load_model(args.model)
    if model is None:
        return

    print("Initializing camera...", file=sys.stderr)
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        print("ERROR: Camera failed to open", file=sys.stderr)
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print("Camera initialized", file=sys.stderr)

    confidence_threshold = args.confidence_threshold
    inference_interval = args.interval
    last_inference_time = time.time()
    result = "Waiting..."
    confidence = 0.0
    last_drive_time = 0
    COOLDOWN = 5.0  # seconds between drives

    car_controller_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'Car_Controller.py'
    )

    if args.mode == 'gui':
        print(f"\n=== GUI MODE ===", file=sys.stderr)
        print(f"Confidence threshold: {confidence_threshold}", file=sys.stderr)
        print("Press 'q' to quit\n", file=sys.stderr)
    else:
        print(f"\n=== CONSOLE MODE ===", file=sys.stderr)
        print(f"Confidence threshold: {confidence_threshold}", file=sys.stderr)
        print("Press Ctrl+C to quit\n", file=sys.stderr)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("WARNING: Frame grab failed", file=sys.stderr)
                time.sleep(0.1)
                continue

            current_time = time.time()
            if current_time - last_inference_time >= inference_interval:
                result, confidence = classify_frame(model, frame, transform)
                last_inference_time = current_time

                # --- Trigger car in EITHER mode when threshold met ---
                if result == "ANIMAL" and confidence >= confidence_threshold:
                    last_drive_time = trigger_car(car_controller_path, last_drive_time, COOLDOWN)
                else:
                    print(f"[INFO] {result} (Confidence: {confidence:.3f})", file=sys.stderr)

            # GUI: show window
            if args.mode == 'gui':
                display_frame = frame.copy()

                if result == "ANIMAL" and confidence >= confidence_threshold:
                    color = (0, 0, 255)
                    status = "ANIMAL DETECTED!"
                elif result == "ANIMAL":
                    color = (0, 165, 255)
                    status = f"{result} (Low Conf)"
                else:
                    color = (0, 255, 0)
                    status = result

                cv2.putText(display_frame, status, (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                cv2.putText(display_frame, f"Confidence: {confidence:.2%}", (20, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display_frame, f"Threshold: {confidence_threshold:.0%}", (20, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

                cv2.imshow("ZED Live Classifier", display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
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