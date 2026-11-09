#!/usr/bin/env python3
# scripts/export_imx500.py
#
# Xuất model YOLO sang định dạng .rpk cho Raspberry Pi AI Camera (Sony IMX500).
#
# Thứ tự thử:
#   1. yolo26n.pt  → model.export(format='imx') — YOLO26n native (Ultralytics hỗ trợ)
#   2. yolov8n.pt → fallback nếu YOLO26n thất bại (YOLOv8n được document chính thức)
#
# Yêu cầu:
#   sudo apt install -y imx500-all
#   pip install "ultralytics>=8.4.32"
#
# Sử dụng:
#   cd /home/pi/ai-tutor
#   source venv/bin/activate
#   python3 scripts/export_imx500.py
#   python3 scripts/export_imx500.py --model yolo26n.pt --imgsz 320
#   python3 scripts/export_imx500.py --model yolov8n.pt --imgsz 640
#
# Sau khi export:
#   1. File .rpk tự động copy vào --output (default: models/yolov8n_imx500.rpk)
#   2. Thêm vào .env:
#        CAMERA_IMX500_ENABLED=true
#        YOLO_IMX500_MODEL_PATH=models/yolov8n_imx500.rpk
#   3. Chạy: ./run.sh

import argparse
import shutil
import sys
from pathlib import Path


DEFAULT_MODEL  = "yolo26n.pt"
FALLBACK_MODEL = "yolov8n.pt"
DEFAULT_IMGSZ  = 320          # 320×320 khuyến nghị cho RPi performance
MODELS_DIR     = Path("models")
DEFAULT_OUTPUT = str(MODELS_DIR / "yolov8n_imx500.rpk")


def _check_dependencies() -> bool:
    """Kiểm tra các dependency cần thiết trước khi export."""
    try:
        import ultralytics
        ver = tuple(int(x) for x in ultralytics.__version__.split(".")[:2])
        if ver < (8, 4):
            print(f"⚠️  ultralytics {ultralytics.__version__} quá cũ. Cần >=8.4.32")
            print("   Cập nhật: pip install 'ultralytics>=8.4.32'")
            return False
    except ImportError:
        print("❌ Thiếu ultralytics. Cài đặt: pip install 'ultralytics>=8.4.32'")
        return False

    # Kiểm tra imx500-tools (optional — Ultralytics tự gọi nếu cần)
    import subprocess
    result = subprocess.run(
        ["dpkg", "-l", "imx500-all"],
        capture_output=True, text=True
    )
    if "ii  imx500-all" not in result.stdout:
        print("⚠️  imx500-all chưa được cài. Cài đặt:")
        print("   sudo apt install -y imx500-all")
        print("   (Tiếp tục thử export, Ultralytics có thể tự xử lý...)\n")

    return True


def _export_model(model_path: str, imgsz: int) -> Path | None:
    """
    Export YOLO model sang IMX500 format.
    Trả về Path của output directory/file, hoặc None nếu thất bại.
    """
    from ultralytics import YOLO

    print(f"📦 Export: {model_path} → IMX500")
    print(f"   Input size: {imgsz}×{imgsz} | INT8 quantization (bắt buộc cho IMX500)")
    try:
        model = YOLO(model_path)
        result = model.export(
            format="imx",
            data="coco8.yaml",     # Dataset config để calibrate INT8 quantization
            imgsz=imgsz,
            int8=True,             # IMX500 yêu cầu INT8
        )
        return Path(result) if result else None
    except Exception as e:
        print(f"   ⚠️  Thất bại: {e}")
        return None


def _find_rpk(search_path: Path) -> Path | None:
    """
    Tìm file .rpk trong output directory của Ultralytics export.
    Một số phiên bản output là packerOut.zip (cần extract thủ công).
    """
    if search_path.is_file():
        # Trường hợp export() trả về file path trực tiếp
        if search_path.suffix == ".rpk":
            return search_path
        search_dir = search_path.parent
    else:
        search_dir = search_path

    # Tìm .rpk trong thư mục export
    for rpk in search_dir.rglob("*.rpk"):
        return rpk

    # Fallback: packerOut.zip → dùng imx500-package để tạo .rpk
    for zpk in search_dir.rglob("packerOut.zip"):
        print(f"\n📦 Tìm thấy packerOut.zip: {zpk} — đang pack thành .rpk...")
        rpk = _pack_rpk(zpk)
        if rpk:
            return rpk
        print("   ⚠️  imx500-package thất bại. Extract thủ công:")
        print(f"   imx500-package -i {zpk} -o {zpk.parent}")
        return zpk

    return None


def _pack_rpk(packerout_zip: Path) -> Path | None:
    """Chạy imx500-package để convert packerOut.zip → .rpk."""
    import subprocess
    out_dir = packerout_zip.parent / "_rpk_out"
    out_dir.mkdir(exist_ok=True)
    result = subprocess.run(
        ["imx500-package", "-i", str(packerout_zip), "-o", str(out_dir)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"   imx500-package stderr: {result.stderr[:500]}")
        return None
    for rpk in out_dir.rglob("*.rpk"):
        return rpk
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Export YOLO model → IMX500 .rpk cho Raspberry Pi AI Camera"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Path to YOLO .pt model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=DEFAULT_IMGSZ,
        help=f"Input image size (default: {DEFAULT_IMGSZ})",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output .rpk path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Không thử fallback yolov8n.pt nếu model chính thất bại",
    )
    args = parser.parse_args()

    print("🤖 IMX500 Model Export Tool")
    print("━" * 40)

    # Kiểm tra dependencies
    if not _check_dependencies():
        sys.exit(1)

    MODELS_DIR.mkdir(exist_ok=True)

    # Thử export model chỉ định
    result_path = _export_model(args.model, args.imgsz)

    # Fallback nếu thất bại
    if result_path is None and not args.no_fallback and args.model != FALLBACK_MODEL:
        print(f"\n🔄 Thử fallback: {FALLBACK_MODEL}...")
        result_path = _export_model(FALLBACK_MODEL, args.imgsz)

    if result_path is None:
        print("\n❌ Export thất bại. Kiểm tra lỗi ở trên và thử:")
        print("   sudo apt install -y imx500-all")
        print("   pip install 'ultralytics>=8.4.32'")
        sys.exit(1)

    # Tìm và copy .rpk
    rpk_src = _find_rpk(result_path)
    if rpk_src and rpk_src.suffix == ".rpk":
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rpk_src, output_path)
        print(f"\n✅ Export hoàn tất!")
        print(f"   Model: {output_path}")
        print(f"\n📋 Bước tiếp theo:")
        print(f"   1. Thêm vào .env:")
        print(f"      CAMERA_IMX500_ENABLED=true")
        print(f"      YOLO_IMX500_MODEL_PATH={output_path}")
        print(f"   2. Chạy ứng dụng:")
        print(f"      ./run.sh")
        print(f"\n💡 Ghi chú:")
        print(f"   - IMX500 primary YOLO chạy trên camera chip (~20ms, không dùng CPU)")
        print(f"   - Secondary/tertiary YOLO (pen, book) vẫn chạy CPU async thread")
        print(f"   - MediaPipe (face, pose, hands) không thay đổi")
    else:
        print(f"\n⚠️  Export hoàn tất nhưng không tìm được .rpk tự động.")
        print(f"   Output directory: {result_path}")
        print(f"   Tìm file .rpk trong thư mục đó và copy sang: {args.output}")


if __name__ == "__main__":
    main()
