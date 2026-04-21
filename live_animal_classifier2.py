#!/usr/bin/env python3
import cv2, os, sys, argparse, torch
from torch import nn
from torchvision import transforms, models
from PIL import Image

def get_model():
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(0.2),
        nn.Sequential(
            nn.Linear(in_features, 1),
            nn.Sigmoid()
        )
    )
    return model

def load_model(model_path):
    print(f"Loading model from {model_path}...", file=sys.stderr)
    model = get_model()
    try:
        state_dict = torch.load(model_path, map_location='cpu')
        model.load_state_dict(state_dict)
        model.eval()
        print("Model loaded successfully!", file=sys.stderr)
        return model
    except Exception as e:
        print(f"CRITICAL ERROR loading model: {e}", file=sys.stderr)
        return None

def classify_frame(model, frame, transform, threshold):
    img = transform(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))).unsqueeze(0)
    with torch.no_grad():
        out = model(img)
        confidence = out.squeeze().item() if out.shape[1] == 1 else out.softmax(dim=1)[0][1].item()
    result = "ANIMAL" if confidence >= threshold else "NOT ANIMAL"
    return result, confidence

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['gui', 'console', 'single_inference'], default='console')
    parser.add_argument('--confidence-threshold', type=float, default=0.60)
    parser.add_argument('--model', default='animal_classifier.pth')
    args = parser.parse_args()

    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = args.model if os.path.isabs(args.model) else os.path.join(script_dir, args.model)
    model = load_model(model_path)
    if model is None:
        sys.exit(1)

    if args.mode == 'single_inference':
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("ERROR: Camera failed to open", file=sys.stderr)
            sys.exit(1)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            print("ERROR: Failed to capture frame", file=sys.stderr)
            sys.exit(1)
        result, confidence = classify_frame(model, frame, transform, args.confidence_threshold)
        if result == "ANIMAL":
            print(f"ANIMAL_DETECTED confidence:{confidence:.4f}")
        else:
            print(f"NOT_ANIMAL confidence:{confidence:.4f}")
        sys.exit(0)

    # Continuous modes
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Camera failed to open", file=sys.stderr)
        return
    print(f"=== {args.mode.upper()} MODE ACTIVE ===")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            result, confidence = classify_frame(model, frame, transform, args.confidence_threshold)
            print(f"[INFO] {result} ({confidence:.3f})", file=sys.stderr)
            if args.mode == 'gui':
                cv2.imshow("ZED Classifier", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
