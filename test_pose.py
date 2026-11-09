import os
import time
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

def main():
    print("=== TEST MEDIAPIPE POSE (AI TEAM) ===")
    print("Khoi tao Google MediaPipe PoseLandmarker...")

    model_path = os.path.join(os.path.dirname(__file__), "pose_landmarker_lite.task")
    if not os.path.exists(model_path):
        print(f"Loi: Khong tim thay file model tai {model_path}")
        return

    # Cau hinh PoseLandmarker theo chuan Google Tasks API moi nhat
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        num_poses=1
    )

    detector = vision.PoseLandmarker.create_from_options(options)
    print("Model AI khoi tao thanh cong!")
    print("Dang ket noi webcam laptop... Nhan 'q' de thoat.")

    # 0 la camera mac dinh cua laptop
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Loi: Khong the mo webcam laptop. Vui long kiem tra quyen truy cap camera.")
        detector.close()
        return

    prev_time = time.time()

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Khong doc duoc frame tu camera.")
                break

            # Tinh FPS
            curr_time = time.time()
            fps = 1.0 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
            prev_time = curr_time

            # Chuyen BGR sang RGB de dua vao MediaPipe Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

            # Nhan dien tu the nguoi
            detection_result = detector.detect(mp_image)

            # Ve khung xuong len nguoi
            if detection_result.pose_landmarks:
                for pose_landmarks in detection_result.pose_landmarks:
                    vision.drawing_utils.draw_landmarks(
                        image=frame,
                        landmark_list=pose_landmarks,
                        connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
                        landmark_drawing_spec=vision.drawing_styles.get_default_pose_landmarks_style()
                    )

                cv2.putText(frame, f"FPS: {int(fps)}", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, "Nhan 'q' de thoat", (20, 80), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.putText(frame, "Dang tim nguoi...", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)

            # Hien thi cua so video
            cv2.imshow("Robot AI - MediaPipe Pose Test", frame)

            # Nhan 'q' de thoat
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()
        print("Da ket thuc chuong trinh test.")

if __name__ == "__main__":
    main()
