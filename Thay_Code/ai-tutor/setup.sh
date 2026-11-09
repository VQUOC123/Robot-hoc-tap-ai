#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  AI Tutor — Setup Script cho Raspberry Pi 5
#  Chạy một lần để cài đặt đầy đủ môi trường
#
#  Cách dùng:
#    chmod +x setup.sh
#    ./setup.sh
#
#  Tùy chọn:
#    ./setup.sh --with-claude      # Cài thêm Anthropic SDK
#    ./setup.sh --with-openai      # Cài thêm OpenAI SDK
#    ./setup.sh --with-gemini      # Cài thêm Google Gemini SDK
#    ./setup.sh --with-all-ai      # Cài tất cả AI providers
#    ./setup.sh --skip-system      # Bỏ qua bước cài apt (nếu đã cài)
# ═══════════════════════════════════════════════════════════════════

set -e   # Dừng nếu có lỗi

# ── Màu sắc ────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'  # No Color

ok()   { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${CYAN}ℹ  $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
step() { echo -e "\n${BLUE}━━━ $1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
fail() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# ── Parse arguments ────────────────────────────────────────────────
WITH_CLAUDE=false
WITH_OPENAI=false
WITH_GEMINI=false
SKIP_SYSTEM=false

for arg in "$@"; do
    case $arg in
        --with-claude)   WITH_CLAUDE=true ;;
        --with-openai)   WITH_OPENAI=true ;;
        --with-gemini)   WITH_GEMINI=true ;;
        --with-all-ai)   WITH_CLAUDE=true; WITH_OPENAI=true; WITH_GEMINI=true ;;
        --skip-system)   SKIP_SYSTEM=true ;;
        --help|-h)
            echo "Dùng: $0 [--with-claude] [--with-openai] [--with-gemini] [--with-all-ai] [--skip-system]"
            exit 0 ;;
    esac
done

# ── Banner ─────────────────────────────────────────────────────────
echo -e "${BLUE}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║      AI Tutor — Setup Script         ║"
echo "  ║      Raspberry Pi 5 Edition          ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# ── Kiểm tra môi trường ────────────────────────────────────────────
step "Kiểm tra môi trường"

# Phải là Python 3.9+
PYTHON=$(command -v python3 || fail "Không tìm thấy python3")
PY_VER=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$($PYTHON -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$($PYTHON -c 'import sys; print(sys.version_info.minor)')

info "Python: $PY_VER ($PYTHON)"

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]); then
    fail "Cần Python 3.9+. Phiên bản hiện tại: $PY_VER"
fi
ok "Python $PY_VER — hợp lệ"

# Kiểm tra có phải Raspberry Pi không (không bắt buộc)
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    RPI_MODEL=$(grep "Model" /proc/cpuinfo | head -1 | sed 's/.*: //')
    ok "Raspberry Pi: $RPI_MODEL"
else
    warn "Không phát hiện Raspberry Pi — vẫn tiếp tục"
fi

# Xác định thư mục project
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
info "Thư mục project: $SCRIPT_DIR"

# ── Cài system packages ────────────────────────────────────────────
if [ "$SKIP_SYSTEM" = false ]; then
    step "Cài system packages (apt)"

    if ! command -v apt-get &>/dev/null; then
        warn "Không có apt — bỏ qua bước cài system packages"
    else
        info "Cập nhật danh sách package..."
        sudo apt-get update -qq

        SYSTEM_PKGS=(
            # Python build tools
            python3-pip
            python3-venv

            # Camera (Raspberry Pi)
            python3-picamera2
            libcamera-apps

            # OpenCV dependencies
            libatlas-base-dev
            libhdf5-dev
            libhdf5-serial-dev

            # Audio — TTS offline (espeak) + audio player (mpg123)
            espeak
            espeak-ng
            mpg123

            # Các thư viện hệ thống cho numpy/scipy
            libopenblas-dev
            liblapack-dev

            # Git (để clone / update)
            git
        )

        info "Cài các package: ${SYSTEM_PKGS[*]}"
        sudo apt-get install -y -qq "${SYSTEM_PKGS[@]}" 2>&1 | tail -5
        ok "System packages đã cài"
    fi
else
    warn "Bỏ qua cài system packages (--skip-system)"
fi

# ── Tạo virtual environment ────────────────────────────────────────
step "Virtual environment"

VENV_DIR="$SCRIPT_DIR/venv"

if [ -d "$VENV_DIR" ]; then
    warn "venv đã tồn tại tại $VENV_DIR"
    read -p "   Tạo lại venv từ đầu? [y/N] " RECREATE
    if [[ "$RECREATE" =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        info "Đã xóa venv cũ"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    info "Tạo virtual environment..."
    $PYTHON -m venv "$VENV_DIR" --system-site-packages
    # --system-site-packages: cho phép dùng picamera2 từ system Python
    ok "Virtual environment tạo thành công: $VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"
PYTHON="$VENV_DIR/bin/python3"
PIP="$VENV_DIR/bin/pip"
ok "Virtual environment đã kích hoạt"

# Upgrade pip
info "Upgrade pip..."
$PIP install --upgrade pip -q
ok "pip đã cập nhật"

# ── Cài Python packages ────────────────────────────────────────────
step "Cài Python packages"

info "Cài từ requirements.txt..."
$PIP install -r "$SCRIPT_DIR/requirements.txt"
ok "Đã cài xong requirements.txt"

# ultralytics tự kéo opencv-python (yêu cầu numpy>=2), xung đột với picamera2/simplejpeg.
# Gỡ opencv-python nếu bị kéo vào — chỉ dùng opencv-python-headless.
if $PIP show opencv-python &>/dev/null; then
    info "Gỡ opencv-python (xung đột numpy, thay bằng opencv-python-headless)..."
    $PIP uninstall opencv-python -y -q
    ok "Đã gỡ opencv-python"
fi

# ── Cài AI providers (tuỳ chọn) ───────────────────────────────────
step "AI Providers"

if [ "$WITH_CLAUDE" = true ]; then
    info "Cài Anthropic (Claude)..."
    $PIP install "anthropic>=0.40.0"
    ok "anthropic đã cài"
fi

if [ "$WITH_OPENAI" = true ]; then
    info "Cài OpenAI..."
    $PIP install "openai>=1.30.0"
    ok "openai đã cài"
fi

if [ "$WITH_GEMINI" = true ]; then
    info "Cài Google Gemini SDK (google-genai)..."
    $PIP install "google-genai>=1.0.0"
    # Gỡ package cũ (deprecated) nếu có
    $PIP uninstall google-generativeai google-ai-generativelanguage -y 2>/dev/null || true
    ok "google-genai đã cài"
fi

if [ "$WITH_CLAUDE" = false ] && [ "$WITH_OPENAI" = false ] && [ "$WITH_GEMINI" = false ]; then
    warn "Chưa chọn AI provider nào"
    info "Chạy lại với flag để cài: --with-claude / --with-openai / --with-gemini"
    info "Hoặc cài thủ công sau: pip install anthropic"
fi

# ── Download YOLO models ───────────────────────────────────────────
step "Download YOLO models"

download_model() {
    local MODEL="$1"
    local DESC="$2"
    if [ -f "$SCRIPT_DIR/$MODEL" ]; then
        ok "$MODEL đã có sẵn ($(du -sh "$SCRIPT_DIR/$MODEL" | cut -f1)) — $DESC"
    else
        info "Đang download $MODEL (~5MB) — $DESC..."
        cd "$SCRIPT_DIR" && $PYTHON -c "from ultralytics import YOLO; YOLO('$MODEL')" 2>&1 \
            | grep -E "Downloading|✅|❌|Error" || true
        [ -f "$SCRIPT_DIR/$MODEL" ] && ok "$MODEL download thành công" \
            || warn "$MODEL chưa download được — sẽ tự download khi chạy lần đầu"
    fi
}

download_model "yolo26n.pt"              "primary (COCO 80 lớp: phone, mouse, keyboard...)"
download_model "yolo26n-objv1-150.pt"   "secondary (Object365: pen, notepaper)"

# ── Xuất ONNX (tăng tốc inference ~2.75× trên RPi5) ───────────────
step "Xuất ONNX models (PyTorch → ONNX, ~40ms vs ~110ms/inference)"

EXPORT_SCRIPT="$SCRIPT_DIR/scripts/export_onnx.py"
if [ -f "$EXPORT_SCRIPT" ]; then
    info "Đang xuất .onnx (có thể mất 1-5 phút lần đầu)..."
    if $PYTHON "$EXPORT_SCRIPT"; then
        ok "ONNX export hoàn tất — YOLO sẽ tự dùng .onnx khi khởi động"
    else
        warn "ONNX export thất bại — hệ thống vẫn dùng .pt (chậm hơn ~2.75×)"
        info "Thử lại thủ công: python3 scripts/export_onnx.py"
    fi
else
    warn "Không tìm thấy scripts/export_onnx.py — bỏ qua bước ONNX"
fi

# ── Tạo thư mục cần thiết ─────────────────────────────────────────
step "Tạo thư mục"

mkdir -p "$SCRIPT_DIR/logs"
ok "Thư mục logs/"

# ── Tạo file .env ─────────────────────────────────────────────────
step "Cấu hình .env"

ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        ok ".env tạo từ .env.example"
    else
        # Tạo .env mẫu
        cat > "$ENV_FILE" << 'ENVEOF'
# ═══════════════════════════════════════════════════
#  AI Tutor — Cấu hình môi trường
#  Sửa file này theo setup thực tế của bạn
# ═══════════════════════════════════════════════════

# ── AI Provider (chọn 1) ────────────────────────────
# CLAUDE_API_KEY=sk-ant-...
# CLAUDE_BASE_URL=https://your-proxy.example.com   # Proxy server (tuỳ chọn)
# CLAUDE_CHAT_MODEL=claude-sonnet-4-5              # Đổi model (tuỳ chọn)
# CLAUDE_VISION_MODEL=claude-sonnet-4-5

# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=AIza...

# ── Camera ──────────────────────────────────────────
# CAMERA_WIDTH=1280
# CAMERA_HEIGHT=720
# CAMERA_FPS=30

# ── Vắng mặt ────────────────────────────────────────
# ABSENCE_SHORT_THRESHOLD=60    # Giây → "rời chỗ ngắn"
# ABSENCE_LONG_THRESHOLD=300    # Giây → "vắng mặt"

# ── Học sinh ────────────────────────────────────────
# STUDENT_NAME=bạn

# ── Multi-person (thử nghiệm) ───────────────────────
# MULTI_PERSON_ENABLED=false
# MAX_PERSONS=3
ENVEOF
        ok ".env mẫu đã tạo: $ENV_FILE"
    fi
    warn "Nhớ điền API key vào file .env trước khi chạy!"
else
    info ".env đã tồn tại — không ghi đè"
fi

# ── Kiểm tra import ────────────────────────────────────────────────
step "Kiểm tra các package đã cài"

check_import() {
    local pkg=$1
    local label=${2:-$1}
    if $PYTHON -c "import $pkg" 2>/dev/null; then
        ok "$label"
    else
        warn "$label — KHÔNG import được (kiểm tra lại)"
    fi
}

check_import cv2        "OpenCV (cv2)"
check_import mediapipe  "MediaPipe"
check_import flask      "Flask"
check_import numpy      "NumPy"
check_import PIL        "Pillow (PIL)"
check_import dotenv     "python-dotenv"
check_import gtts       "gTTS"

# picamera2 đặc biệt — có thể chỉ có trong system Python
if $PYTHON -c "import picamera2" 2>/dev/null; then
    ok "picamera2"
else
    warn "picamera2 — không tìm thấy trong venv"
    if python3 -c "import picamera2" 2>/dev/null; then
        ok "picamera2 — có trong system Python (dùng --system-site-packages OK)"
    else
        warn "picamera2 chưa cài. Thử: sudo apt install python3-picamera2"
    fi
fi

# AI providers (tuỳ chọn)
for pkg in anthropic openai google.genai; do
    label=$(echo $pkg | sed 's/\..*//; s/google/google-genai/')
    if $PYTHON -c "import $pkg" 2>/dev/null; then
        ok "$pkg (AI provider)"
    fi
done

# espeak
if command -v espeak &>/dev/null || command -v espeak-ng &>/dev/null; then
    ok "espeak (TTS offline)"
else
    warn "espeak chưa cài. Chạy: sudo apt install espeak"
fi

# ── Tạo script chạy nhanh ─────────────────────────────────────────
step "Tạo script khởi động"

RUN_SCRIPT="$SCRIPT_DIR/run.sh"
cat > "$RUN_SCRIPT" << RUNEOF
#!/usr/bin/env bash
# Khởi động AI Tutor (dùng virtual environment)
cd "$(dirname "\$0")"
source venv/bin/activate
python3 main.py "\$@"
RUNEOF
chmod +x "$RUN_SCRIPT"
ok "Tạo run.sh — chạy ứng dụng bằng: ./run.sh"

# ── Tóm tắt ────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ Setup hoàn tất!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${CYAN}Bước tiếp theo:${NC}"
echo -e "  1. Điền API key vào file ${YELLOW}.env${NC}"
echo -e "  2. Chạy ứng dụng:"
echo -e "     ${GREEN}./run.sh${NC}"
echo -e "     hoặc: ${GREEN}source venv/bin/activate && python3 main.py${NC}"
echo ""
echo -e "  ${CYAN}Dashboard:${NC} http://$(hostname -I | awk '{print $1}'):5000"
echo ""
