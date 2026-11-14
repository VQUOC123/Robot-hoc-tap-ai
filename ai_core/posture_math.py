import math
import numpy as np

def calculate_angle_2d(p1, p2, p3):
    """
    Tính góc tạo bởi 3 điểm p1 - p2 - p3 (đỉnh tại p2) trên mặt phẳng 2D.
    p = (x, y)
    Kết quả trả về góc tính bằng độ (0 - 180).
    """
    a = np.array([p1[0] - p2[0], p1[1] - p2[1]])
    b = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    cosine_angle = np.dot(a, b) / (norm_a * norm_b)
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.degrees(np.arccos(cosine_angle))
    return float(angle)

def calculate_shoulder_tilt(left_shoulder, right_shoulder):
    """
    Tính độ nghiêng vai (so với phương ngang).
    left_shoulder, right_shoulder: (x, y)
    Nếu vai lệch quá 10 độ -> Cột sống bị vẹo.
    """
    dx = right_shoulder[0] - left_shoulder[0]
    dy = right_shoulder[1] - left_shoulder[1]
    if dx == 0:
        return 90.0
    angle_rad = math.atan2(abs(dy), abs(dx))
    return float(math.degrees(angle_rad))

def calculate_neck_tilt(ear, shoulder):
    """
    Tính góc gập cổ so với phương thẳng đứng.
    ear: (x, y) của tai gần camera nhất
    shoulder: (x, y) của vai tương ứng
    Nếu góc gập > 25 độ -> Bé đang cúi gục đầu quá sát bàn.
    """
    dx = ear[0] - shoulder[0]
    dy = ear[1] - shoulder[1]
    
    # Góc so với phương thẳng đứng (trục y hướng xuống)
    angle_from_vertical = math.degrees(math.atan2(abs(dx), abs(dy)))
    return float(angle_from_vertical)
