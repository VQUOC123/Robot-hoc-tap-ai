# realtime_stream.py
from flask import Flask, Response, jsonify
from picamera2 import Picamera2
import cv2
import numpy as np
import time
import threading

app = Flask(__name__)

# ─── Khởi động Camera ───────────────────────────────
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (1280, 720), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
time.sleep(2)
print("✅ Camera sẵn sàng!")

# ─── Load Models nhận diện ──────────────────────────
# Nhận diện khuôn mặt
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)
# Nhận diện mắt
eye_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_eye.xml'
)
# Nhận diện toàn thân
body_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_fullbody.xml'
)

# ─── Biến trạng thái ────────────────────────────────
status = {
    "face_count": 0,
    "is_focused": False,
    "eyes_detected": False,
    "fps": 0,
    "message": "Đang quan sát..."
}
frame_lock = threading.Lock()
current_frame = None

# ─── Xử lý Frame ────────────────────────────────────
def process_frame(frame_rgb):
    """Xử lý frame: nhận diện khuôn mặt, mắt, trạng thái"""
    global status
    
    # Convert màu
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    
    # ── Nhận diện khuôn mặt ──
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )
    
    face_count = len(faces)
    eyes_found = False
    is_focused = False
    
    for (x, y, w, h) in faces:
        # Vẽ khung khuôn mặt
        cv2.rectangle(frame_bgr, (x, y), (x+w, y+h), 
                     (0, 255, 0), 2)
        
        # Label khuôn mặt
        cv2.putText(frame_bgr, "Khuon mat", (x, y-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                   (0, 255, 0), 2)
        
        # ── Nhận diện mắt trong khuôn mặt ──
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame_bgr[y:y+h, x:x+w]
        
        eyes = eye_cascade.detectMultiScale(
            roi_gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(20, 20)
        )
        
        if len(eyes) >= 1:
            eyes_found = True
            is_focused = True
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color,
                            (ex, ey), (ex+ew, ey+eh),
                            (255, 165, 0), 2)
    
    # ── Cập nhật status ──
    status["face_count"] = face_count
    status["is_focused"] = is_focused
    status["eyes_detected"] = eyes_found
    
    if face_count == 0:
        status["message"] = "⚠️ Không thấy học sinh"
        msg_color = (0, 0, 255)
    elif is_focused:
        status["message"] = "✅ Đang tập trung"
        msg_color = (0, 255, 0)
    else:
        status["message"] = "😴 Mất tập trung"
        msg_color = (0, 165, 255)
    
    # ── Vẽ thông tin lên frame ──
    # Background cho text
    overlay = frame_bgr.copy()
    cv2.rectangle(overlay, (0, 0), (500, 120), 
                 (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame_bgr, 0.5, 
                   0, frame_bgr)
    
    # Hiển thị thông tin
    cv2.putText(frame_bgr, 
                f"Khuon mat: {face_count}", 
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, 
                (255, 255, 255), 2)
    
    cv2.putText(frame_bgr,
                status["message"],
                (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                msg_color, 2)
    
    cv2.putText(frame_bgr,
                f"FPS: {status['fps']:.1f}",
                (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (200, 200, 200), 2)
    
    # Timestamp
    timestamp = time.strftime("%H:%M:%S")
    cv2.putText(frame_bgr, timestamp,
                (frame_bgr.shape[1]-120, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (200, 200, 200), 2)
    
    return frame_bgr

# ─── Camera Loop Thread ──────────────────────────────
def camera_loop():
    """Vòng lặp capture và xử lý frame"""
    global current_frame
    fps_counter = 0
    fps_start = time.time()
    
    while True:
        try:
            # Capture frame từ camera
            frame_rgb = picam2.capture_array()
            
            # Xử lý nhận diện
            processed = process_frame(frame_rgb)
            
            # Tính FPS
            fps_counter += 1
            if time.time() - fps_start >= 1.0:
                status["fps"] = fps_counter
                fps_counter = 0
                fps_start = time.time()
            
            # Encode JPEG
            ret, buffer = cv2.imencode(
                '.jpg', processed,
                [cv2.IMWRITE_JPEG_QUALITY, 75]
            )
            
            with frame_lock:
                current_frame = buffer.tobytes()
                
        except Exception as e:
            print(f"Lỗi camera: {e}")
            time.sleep(0.1)

# Chạy camera loop trong thread riêng
camera_thread = threading.Thread(
    target=camera_loop, 
    daemon=True
)
camera_thread.start()

# ─── Flask Routes ────────────────────────────────────
def generate():
    """Generator cho MJPEG stream"""
    while True:
        with frame_lock:
            if current_frame is None:
                time.sleep(0.1)
                continue
            frame = current_frame
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n'
               + frame +
               b'\r\n')
        
        time.sleep(0.033)  # ~30fps

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Tutor - Camera Monitor</title>
        <meta charset="UTF-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                background: #1a1a2e; 
                font-family: Arial, sans-serif;
                color: white;
            }
            .header {
                background: #16213e;
                padding: 15px 30px;
                display: flex;
                align-items: center;
                gap: 15px;
                border-bottom: 2px solid #0f3460;
            }
            h1 { font-size: 1.5rem; color: #e94560; }
            .container {
                display: flex;
                gap: 20px;
                padding: 20px;
            }
            .camera-box {
                flex: 1;
            }
            .camera-box img {
                width: 100%;
                border-radius: 10px;
                border: 2px solid #0f3460;
            }
            .info-box {
                width: 280px;
                display: flex;
                flex-direction: column;
                gap: 15px;
            }
            .card {
                background: #16213e;
                border-radius: 10px;
                padding: 15px;
                border: 1px solid #0f3460;
            }
            .card h3 {
                color: #e94560;
                margin-bottom: 10px;
                font-size: 0.9rem;
                text-transform: uppercase;
            }
            .status-value {
                font-size: 1.8rem;
                font-weight: bold;
                color: #00d4aa;
            }
            .status-label {
                font-size: 0.85rem;
                color: #888;
                margin-top: 5px;
            }
            .focused { color: #00d4aa; }
            .not-focused { color: #e94560; }
            .log-box {
                background: #0d0d1a;
                border-radius: 8px;
                padding: 10px;
                height: 200px;
                overflow-y: auto;
                font-size: 0.8rem;
                font-family: monospace;
                color: #00ff88;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎓 AI Tutor - Camera Monitor</h1>
            <span style="color:#888; font-size:0.9rem">
                RPi 5 + IMX219 Camera
            </span>
        </div>
        
        <div class="container">
            <!-- Camera Stream -->
            <div class="camera-box">
                <img src="/video_feed" 
                     alt="Camera Stream">
            </div>
            
            <!-- Info Panel -->
            <div class="info-box">
                <div class="card">
                    <h3>Trạng thái</h3>
                    <div class="status-value" id="status">
                        --
                    </div>
                    <div class="status-label">
                        Mức độ tập trung
                    </div>
                </div>
                
                <div class="card">
                    <h3>Thống kê</h3>
                    <p>Khuôn mặt: 
                        <span id="faces" 
                              style="color:#00d4aa">
                            --
                        </span>
                    </p>
                    <p>Mắt: 
                        <span id="eyes" 
                              style="color:#00d4aa">
                            --
                        </span>
                    </p>
                    <p>FPS: 
                        <span id="fps" 
                              style="color:#00d4aa">
                            --
                        </span>
                    </p>
                </div>
                
                <div class="card">
                    <h3>Activity Log</h3>
                    <div class="log-box" id="log"></div>
                </div>
            </div>
        </div>
        
        <script>
            // Cập nhật status mỗi 1 giây
            function updateStatus() {
                fetch('/status')
                .then(r => r.json())
                .then(data => {
                    // Cập nhật status
                    const statusEl = 
                        document.getElementById('status');
                    statusEl.textContent = data.message;
                    statusEl.className = 
                        'status-value ' + 
                        (data.is_focused ? 
                            'focused' : 'not-focused');
                    
                    // Cập nhật stats
                    document.getElementById('faces')
                        .textContent = data.face_count;
                    document.getElementById('eyes')
                        .textContent = 
                            data.eyes_detected ? 'Có' : 'Không';
                    document.getElementById('fps')
                        .textContent = 
                            data.fps.toFixed(1);
                    
                    // Log
                    const log = 
                        document.getElementById('log');
                    const time = 
                        new Date().toLocaleTimeString();
                    log.innerHTML = 
                        `[${time}] ${data.message}\\n` + 
                        log.innerHTML;
                    
                    // Giới hạn log
                    const lines = 
                        log.innerHTML.split('\\n');
                    if (lines.length > 20) {
                        log.innerHTML = 
                            lines.slice(0, 20).join('\\n');
                    }
                });
            }
            
            setInterval(updateStatus, 1000);
            updateStatus();
        </script>
    </body>
    </html>
    '''

@app.route('/video_feed')
def video_feed():
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/status')
def get_status():
    return jsonify(status)

if __name__ == '__main__':
    print("\n🚀 AI Tutor Camera Monitor")
    print("━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📱 Open browser and connect:")
    print(f"   http://192.168.2.82:5000")
    print("━━━━━━━━━━━━━━━━━━━━━━━━\n")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )