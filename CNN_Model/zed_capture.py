import cv2
import time
import os

save_dir = "captured_frames"
os.makedirs(save_dir, exist_ok=True)

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

if not cap.isOpened():
    print("ERROR: Camera failed to open")
    exit(1)

# Force MJPG and safe resolution for Pi
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

# Initialize counters
num_frames_to_capture = 10000
captured_count = 0

# Time interval between screenshots
interval = 0.25  # seconds

print("Starting capture... Press 'q' to quit early.")

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        print("Frame grab failed")
        break

    # Resize for CNN
    cnn_frame = cv2.resize(frame, (224, 224))

    # Show live window
    cv2.imshow("ZED Image", cnn_frame)

    # Save frame every interval until 100 images

    if captured_count < 10000:
        filename = os.path.join(save_dir, f"img_{captured_count+1:03d}.jpg")
        cv2.imwrite(filename, cnn_frame)
        captured_count += 1
        time.sleep(.1)  # wait 0.25 seconds

    # Exit if 'q' pressed or all frames captured
    if cv2.waitKey(1) & 0xFF == ord('q') or captured_count >= num_frames_to_capture:
        break

cap.release()
cv2.destroyAllWindows()
print(f"Captured {captured_count} frames in '{save_dir}'")
