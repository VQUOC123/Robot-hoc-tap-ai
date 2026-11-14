import numpy as np

def calculate_ear_single_eye(eye_points):
    """
    Tính Eye Aspect Ratio (EAR) cho một bên mắt theo công thức chuẩn:
    EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
    
    eye_points: list/tuple 6 tọa độ (x, y) theo thứ tự:
    [p1_corner_left, p2_top_1, p3_top_2, p4_corner_right, p5_bottom_2, p6_bottom_1]
    """
    p1, p2, p3, p4, p5, p6 = [np.array(pt) for pt in eye_points]
    
    # Khoảng cách thẳng đứng
    vert_1 = np.linalg.norm(p2 - p6)
    vert_2 = np.linalg.norm(p3 - p5)
    
    # Khoảng cách bề ngang mi mắt
    horiz = np.linalg.norm(p1 - p4)
    
    if horiz == 0:
        return 0.0
        
    ear = (vert_1 + vert_2) / (2.0 * horiz)
    return float(ear)

def estimate_head_pose_yaw_pitch(face_landmarks_2d, image_w, image_h):
    """
    Ước lượng nhanh góc quay đầu (Yaw / Pitch) dựa trên mốc mũi và 2 bên má / tai.
    Mốc cơ bản: Mũi (1), Cằm (152), Mép trái (234), Mép phải (454)
    Trả về:
    - yaw_ratio: > 0.6 hoặc < 0.4 thể hiện đầu quay ngang sang trái hoặc phải
    - is_looking_away: True nếu quay mặt khỏi sách vở/màn hình
    """
    nose = face_landmarks_2d[1]
    left_cheek = face_landmarks_2d[234]
    right_cheek = face_landmarks_2d[454]
    
    dist_left = abs(nose[0] - left_cheek[0])
    dist_right = abs(right_cheek[0] - nose[0])
    total_w = dist_left + dist_right
    
    if total_w == 0:
        return 0.5, False
        
    yaw_ratio = dist_left / total_w
    # Nếu yaw_ratio lệch xa mốc 0.5 (nhìn thẳng) -> Đang quay đầu nhìn chỗ khác
    is_looking_away = yaw_ratio < 0.28 or yaw_ratio > 0.72
    return float(yaw_ratio), is_looking_away
