import requests
import json
import time

class BackendEventPublisher:
    """
    Client bắn tín hiệu sự kiện từ AI Edge sang Backend Go / FastAPI.
    Được thiết kế theo nguyên tắc:
    - Non-blocking hoặc timeout ngắn để không giật lag frame xử lý AI.
    - TUYỆT ĐỐI KHÔNG gửi trường 'image' hay dữ liệu nhạy cảm (Luật bảo vệ trẻ em 2026 - Q11).
    """
    def __init__(self, backend_url="http://localhost:8080/api/v1/events"):
        self.backend_url = backend_url
        self.device_id = "rpi5_robot_01"

    def send_posture_alert(self, reasons: list, bad_duration: float, angles: dict):
        payload = {
            "device_id": self.device_id,
            "event_type": "BAD_POSTURE_ALERT",
            "timestamp": int(time.time()),
            "data": {
                "bad_duration_seconds": round(bad_duration, 1),
                "reasons": reasons,
                "neck_tilt_deg": round(angles.get("neck", 0.0), 1),
                "shoulder_tilt_deg": round(angles.get("shoulder", 0.0), 1)
            }
        }
        try:
            # Gửi với timeout ngắn 0.5s để không bao giờ lag camera AI
            response = requests.post(self.backend_url, json=payload, timeout=0.5)
            return response.status_code == 200
        except Exception:
            # Khi BE chưa bật, AI vẫn chạy bình thường không bị crash
            return False

    def send_attention_alert(self, state: str, duration: float):
        payload = {
            "device_id": self.device_id,
            "event_type": "ATTENTION_ALERT",
            "timestamp": int(time.time()),
            "data": {
                "state": state,  # "DROWSY" (buồn ngủ) hoặc "DISTRACTED" (quay đầu)
                "duration_seconds": round(duration, 1)
            }
        }
        try:
            response = requests.post(self.backend_url, json=payload, timeout=0.5)
            return response.status_code == 200
        except Exception:
            return False
