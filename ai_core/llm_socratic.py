"""
Module đánh giá Prompt sư phạm LLM Vision cho bài tập tiểu học.
Tuân thủ tuyệt đối:
1. Không đưa ngay đáp án trực tiếp.
2. Phương pháp gợi mở Socratic từng bước.
3. Nếu chữ mờ hoặc không chắc chắn thì yêu cầu bé chụp lại, không đoán mò.
4. Lời lẽ động viên, thân thiện, vui vẻ.
"""

SOCRATIC_SYSTEM_PROMPT = """Bạn là Robot gia sư AI thông minh và thân thiện đồng hành cùng các bạn học sinh tiểu học (6-12 tuổi).
Phong cách của bạn:
- Xưng hô thân mật: "Robot" và "con" hoặc "bạn nhỏ".
- Giọng điệu ấm áp, vui vẻ, khen ngợi và động viên khi bé nỗ lực.
- NGUYÊN TẮC VÀNG: TUYỆT ĐỐI KHÔNG giải hộ hay đưa ra đáp án cuối cùng ngay lập tức.
- Hãy dùng phương pháp gợi mở (Socratic): Đặt câu hỏi nhỏ, gợi ý từng bước để bé tự suy nghĩ và tìm ra lời giải.
- ĐỘ TIN CẬY: Nếu chữ viết tay hoặc đề bài bị mờ, hãy thành thật trả lời: "Robot nhìn chưa rõ chỗ này, bạn nhỏ chụp lại rõ nét hơn để Robot xem cùng nhé!".
"""

SAMPLE_TEST_SCENARIOS = [
    {
        "id": "TC01_MATH_ADDITION",
        "title": "Toán lớp 1: Phép cộng có nhớ trong phạm vi 20",
        "mock_question": "Đề bài: 8 + 5 = ? (Bé đang phân vân chưa biết tính)",
        "expected_guidance": "Gợi ý tách số 5 thành 2 + 3 để gộp 8 + 2 = 10, rồi cộng 3."
    },
    {
        "id": "TC02_VIETNAMESE_SPELLING",
        "title": "Tiếng Việt lớp 2: Phân biệt ch / tr",
        "mock_question": "Bé hỏi: 'Cây ...e' điền ch hay tr?",
        "expected_guidance": "Gợi ý nhớ lại hình ảnh cây tre dẻo dai ở làng quê."
    },
    {
        "id": "TC03_UNCLEAR_IMAGE",
        "title": "Ảnh bị mờ hoặc che khuất",
        "mock_question": "[Ảnh chụp trang vở bị lóa sáng, không đọc được số]",
        "expected_guidance": "Nhắc bé chụp lại, từ chối đoán mò đáp án."
    }
]

def format_prompt_test(scenario_index: int = 0):
    tc = SAMPLE_TEST_SCENARIOS[scenario_index]
    return {
        "system": SOCRATIC_SYSTEM_PROMPT,
        "scenario": tc
    }
