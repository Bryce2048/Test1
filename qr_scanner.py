import cv2
import numpy as np
from pyzbar.pyzbar import decode

def start_qr_scanner(callback):
    """
    Starts the webcam QR code scanner in a separate thread.
    Calls `callback(decoded_text)` when a QR code is detected.
    """
    cap = cv2.VideoCapture(0)  # Open webcam (0 = default camera)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Convert frame to grayscale (improves detection)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Decode QR codes
        qr_codes = decode(gray_frame)
        for qr_code in qr_codes:
            qr_data = qr_code.data.decode("utf-8")  # Extract QR code text
            callback(qr_data)  # Send scanned data to Flet
            cap.release()
            cv2.destroyAllWindows()
            return  # Stop scanning after detecting a QR code

        # Show video feed (for debugging)
        cv2.imshow("QR Scanner", frame)

        # Stop when 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
