import os
import base64
import time
import json
from pathlib import Path

# ==============================================================
# TEST GỌI LLM VISION VỚI ẢNH TRANG SÁCH MẪU (TASK 8.0 - TUẦN 1)
# ==============================================================
# Nguyen tac bat buoc:
# 1. API key doc tu bien moi truong hoac file .env (KHONG HARDCODE).
# 2. Chi gui anh trang sach sach, khong gui anh co mat nguoi.
# ==============================================================

def encode_image(image_path: str) -> str:
    """Ma hoa anh thanh chuoi base64 de gui qua API"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def test_claude_vision(image_path: str):
    """Goi API Claude (Anthropic) voi prompt huong dan su pham"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[!] Chua co ANTHROPIC_API_KEY trong moi truong.")
        print("    Hay chay: export ANTHROPIC_API_KEY='your-key-here'")
        return

    try:
        import anthropic
    except ImportError:
        print("[!] Chua cai thu vien anthropic: chay 'pip install anthropic'")
        return

    client = anthropic.Anthropic(api_key=api_key)
    base64_image = encode_image(image_path)
    
    # Prompt su pham danh cho tre 6-12 tuoi theo tai lieu
    system_prompt = (
        "Ban la tro ly hoc tap AI than thien cho tre 6-12 tuoi. "
        "Giong dieu vui ve, khuyen khich. "
        "TUYET DOI khong dua dap an thang ma hay goi y tung buoc de tre tu giai. "
        "Neu chu viet tay khong doc duoc thi noi 'khong chac, con chup lai nhe' thay vi doan."
    )
    
    print(f"[*] Dang gui anh {image_path} len Claude Vision API...")
    start_time = time.time()
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Con khong biet lam bai nay, huong dan con voi!",
                    },
                ],
            }
        ],
    )
    
    latency = time.time() - start_time
    print(f"[✓] Nhan ket qua sau {latency:.2f} giay:")
    print("--------------------------------------------------")
    print(response.content[0].text)
    print("--------------------------------------------------")
    print(f"Tokens in: {response.usage.input_tokens} | Tokens out: {response.usage.output_tokens}")

if __name__ == "__main__":
    print("Huong dan test Task 8.0:")
    print("1. Chup 1 anh trang sach vo dat vao thu muc nay (vi du: sample_page.jpg)")
    print("2. Set API key: export ANTHROPIC_API_KEY='sk-...' hoac OPENAI_API_KEY='sk-...'")
    print("3. Chay: python test_llm_vision.py")
