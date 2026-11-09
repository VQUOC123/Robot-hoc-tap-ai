#!/usr/bin/env python3
# scripts/export_onnx.py
# Xuất YOLO .pt → .onnx để tăng tốc inference ~2.75× trên RPi5.
#
# Benchmark RPi5:
#   PyTorch .pt  : ~110ms/inference
#   ONNX Runtime : ~40ms/inference  (2.75× speedup)
#
# Cách dùng:
#   cd /home/pi/ai-tutor
#   source venv/bin/activate
#   python3 scripts/export_onnx.py
#
# Kết quả:
#   yolo26n.onnx              (cạnh yolo26n.pt)
#   yolo26n-objv1-150.onnx   (cạnh yolo26n-objv1-150.pt)
#
# Sau khi xuất: set YOLO_PREFER_ONNX=True trong .env (mặc định đã True).
# YoloDetector._resolve_onnx_path() tự động detect .onnx, không cần đổi config.
#
# Ghi chú:
#   - Cần ultralytics >= 8.4.32 (NMS-free E2E export)
#   - ONNX export có thể mất 1-5 phút lần đầu (optimization pass)
#   - File .onnx ~lớn hơn .pt một chút (TF flatten weights)

import os
import sys
import argparse

# ── Thêm project root vào path ─────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.config import Config


def export_model(pt_path: str, input_size: int, label: str) -> bool:
    """
    Xuất một model .pt → .onnx.

    Args:
        pt_path    : Đường dẫn file .pt (tuyệt đối hoặc tương đối so với ROOT).
        input_size : Kích thước input YOLO (pixel, hình vuông).
        label      : Tên hiển thị trong log.

    Returns:
        True nếu xuất thành công, False nếu thất bại.
    """
    # Resolve path
    if not os.path.isabs(pt_path):
        pt_path = os.path.join(ROOT, pt_path)

    if not os.path.exists(pt_path):
        print(f"⚠️  Bỏ qua {label}: không tìm thấy {pt_path}")
        return False

    onnx_path = pt_path[:-3] + ".onnx"

    if os.path.exists(onnx_path):
        size_mb = os.path.getsize(onnx_path) / 1024 / 1024
        print(f"✅ {label}: {onnx_path} đã tồn tại ({size_mb:.1f}MB) — bỏ qua")
        return True

    print(f"\n📦 Xuất {label}...")
    print(f"   Nguồn : {pt_path}")
    print(f"   Đích   : {onnx_path}")
    print(f"   imgsz  : {input_size}×{input_size}")

    try:
        from ultralytics import YOLO
        model = YOLO(pt_path, verbose=False)
        result = model.export(
            format="onnx",
            imgsz=input_size,
            dynamic=False,      # static shape — nhanh hơn trên RPi
            simplify=True,      # onnx-simplifier — giảm ops không cần thiết
            opset=12,           # opset 12 tương thích tốt với onnxruntime 1.x
        )
        if result and os.path.exists(onnx_path):
            size_mb = os.path.getsize(onnx_path) / 1024 / 1024
            print(f"   ✓ Xuất thành công: {onnx_path} ({size_mb:.1f}MB)")
            return True
        else:
            print(f"   ❌ Xuất thất bại — không tìm thấy output file")
            return False
    except Exception as e:
        print(f"   ❌ Lỗi khi xuất: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Xuất YOLO .pt → .onnx để tăng tốc inference trên RPi5",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Xuất lại dù .onnx đã tồn tại",
    )
    args = parser.parse_args()

    # Xóa .onnx cũ nếu --force
    if args.force:
        for model_path in [Config.YOLO_MODEL_PATH, Config.YOLO_SECONDARY_MODEL_PATH]:
            if not model_path:
                continue
            pt = model_path if os.path.isabs(model_path) else os.path.join(ROOT, model_path)
            onnx = pt[:-3] + ".onnx" if pt.endswith(".pt") else None
            if onnx and os.path.exists(onnx):
                os.remove(onnx)
                print(f"🗑  Đã xóa {onnx} (--force)")

    print("=" * 55)
    print("  YOLO ONNX Export Tool — AI Tutor RPi5")
    print("=" * 55)

    results = []

    # Primary model
    results.append(export_model(
        pt_path    = Config.YOLO_MODEL_PATH,
        input_size = Config.YOLO_INPUT_SIZE,
        label      = "Primary model",
    ))

    # Secondary model
    if Config.YOLO_SECONDARY_MODEL_PATH:
        results.append(export_model(
            pt_path    = Config.YOLO_SECONDARY_MODEL_PATH,
            input_size = Config.YOLO_INPUT_SIZE,
            label      = "Secondary model",
        ))

    # Summary
    print("\n" + "=" * 55)
    success = sum(results)
    total   = len(results)
    print(f"  Kết quả: {success}/{total} model xuất thành công")

    if success == total:
        print("  ✅ Tất cả model đã sẵn sàng dùng ONNX")
        print()
        print("  Để kích hoạt: thêm vào .env:")
        print("    YOLO_PREFER_ONNX=true")
        print()
        print("  (Mặc định đã True trong constants.py —")
        print("   YoloDetector tự detect .onnx bên cạnh .pt)")
    else:
        print("  ⚠️  Một số model chưa xuất được — hệ thống vẫn chạy với .pt")
    print("=" * 55)


if __name__ == "__main__":
    main()
