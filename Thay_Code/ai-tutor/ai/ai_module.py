# ai/ai_module.py
"""
AI Module - Multi Provider
Hỗ trợ: OpenAI, Claude, Gemini, OpenRouter
Offline fallback khi không có API key
Lazy import - chỉ import khi cần
"""
import os
import json
import re
import random
from dotenv import load_dotenv

load_dotenv()

# ── Lazy imports - chỉ import khi cần ───────────────
# Tránh lỗi nếu chưa cài package
# VS Code có thể báo warning nhưng code vẫn chạy OK

def _import_openai():
    try:
        import openai        # type: ignore
        return openai
    except ImportError:
        return None

def _import_anthropic():
    try:
        import anthropic     # type: ignore
        return anthropic
    except ImportError:
        return None

def _import_gemini():
    try:
        from google import genai  # type: ignore
        return genai
    except ImportError:
        return None


class AIModule:

    # Cấu hình mặc định cho từng provider.
    # Model và base_url có thể override qua .env (xem __init__).
    PROVIDERS = {
        "openai": {
            "env_key"     : "OPENAI_API_KEY",
            "package"     : "openai",
            "chat_model"  : "gpt-4o-mini",
            "vision_model": "gpt-4o",
            "base_url"    : "",                  # OPENAI_BASE_URL để dùng proxy
        },
        "claude": {
            "env_key"     : "CLAUDE_API_KEY",
            "package"     : "anthropic",
            "chat_model"  : "claude-sonnet-4-5",
            "vision_model": "claude-sonnet-4-5",
            "base_url"    : "",                  # CLAUDE_BASE_URL để dùng proxy (LiteLLM...)
        },
        "gemini": {
            "env_key"     : "GEMINI_API_KEY",
            "package"     : "google-genai",
            "chat_model"  : "gemini-2.5-flash",
            "vision_model": "gemini-2.5-flash",
            "base_url"    : "",
        },
        "openrouter": {
            "env_key"     : "OPENROUTER_API_KEY",
            "package"     : "openai",
            "chat_model"  : "openai/gpt-4o-mini",
            "vision_model": "openai/gpt-4o",
            "base_url"    : "https://openrouter.ai/api/v1",
        },
    }

    # Map env var prefix → provider key (để đọc override từ .env)
    _ENV_PREFIX = {
        "openai"    : "OPENAI",
        "claude"    : "CLAUDE",
        "gemini"    : "GEMINI",
        "openrouter": "OPENROUTER",
    }

    def __init__(self):
        self.student_name = os.getenv(
            "STUDENT_NAME", "bạn"
        )
        self.preferred = os.getenv(
            "AI_PROVIDER", "auto"
        ).lower()

        self.provider    = None
        self.enabled     = False
        self.client      = None
        self.history     = []
        self.MAX_HISTORY = 10

        # Áp dụng override model/base_url từ .env trước khi init
        self._apply_env_overrides()

        # System prompt — persona gia sư AI
        self.system_prompt = (
            f"You are a smart AI tutor named 'Thầy AI'.\n"
            f"Student name: {self.student_name}\n\n"
            f"Tasks:\n"
            f"- Remind when distracted\n"
            f"- Answer study questions\n"
            f"- Encourage and motivate\n\n"
            f"Style: Friendly, concise, max 3 sentences. "
            f"Always respond in Vietnamese."
        )

        self._init_provider()

    # ── Override model/base_url từ .env ──────────────

    def _apply_env_overrides(self):
        """
        Đọc các env var để override model và base_url.

        Ví dụ .env:
            CLAUDE_CHAT_MODEL=claude-opus-4-5
            CLAUDE_VISION_MODEL=claude-sonnet-4-5
            CLAUDE_BASE_URL=http://localhost:4000    ← LiteLLM proxy
            OPENAI_CHAT_MODEL=gpt-4o
        """
        for provider, prefix in self._ENV_PREFIX.items():
            cfg = self.PROVIDERS[provider]

            chat_model = os.getenv(f"{prefix}_CHAT_MODEL", "").strip()
            vis_model  = os.getenv(f"{prefix}_VISION_MODEL", "").strip()
            base_url   = os.getenv(f"{prefix}_BASE_URL", "").strip()

            if chat_model:
                cfg["chat_model"]   = chat_model
            if vis_model:
                cfg["vision_model"] = vis_model
            if base_url:
                cfg["base_url"]     = base_url

    # ── Kiểm tra package ─────────────────────────────

    def _is_package_installed(
        self,
        package: str
    ) -> bool:
        """
        Kiểm tra package đã cài chưa
        KHÔNG gây lỗi nếu chưa cài
        """
        import importlib

        # Map tên package pip → tên import
        import_names = {
            "openai"            : "openai",
            "anthropic"         : "anthropic",
            "google-genai"        : "google.genai",
        }

        import_name = import_names.get(package, package)

        try:
            importlib.import_module(import_name)
            return True
        except ImportError:
            return False

    # ── Khởi tạo Provider ────────────────────────────

    def _init_provider(self):
        """Tự động tìm và khởi tạo provider"""

        # Dùng provider được chỉ định
        if self.preferred != "auto":
            if self._try_init(self.preferred):
                return
            print(
                f"⚠️  '{self.preferred}' thất bại "
                f"→ Thử provider khác"
            )

        # Auto: thử lần lượt
        for p in ["openai", "claude",
                  "gemini", "openrouter"]:
            if self._try_init(p):
                return

        # Không có provider nào
        self._print_offline_info()

    def _try_init(self, name: str) -> bool:
        """
        Thử khởi tạo 1 provider.
        Kiểm tra theo thứ tự:
        1. Có API key không?
        2. Có cài package chưa?
        3. Khởi tạo client (có thể qua proxy nếu BASE_URL được set)
        """
        if name not in self.PROVIDERS:
            return False

        cfg      = self.PROVIDERS[name]
        api_key  = os.getenv(cfg["env_key"], "").strip()
        base_url = cfg.get("base_url", "").strip()

        # Không có API key → bỏ qua
        if not api_key:
            return False

        package = cfg["package"]

        # Kiểm tra package cần thiết
        if not self._is_package_installed(package):
            print(
                f"⚠️  Có {cfg['env_key']} nhưng chưa cài package!\n"
                f"    Chạy: pip install {package}"
            )
            return False

        # ── Khởi tạo client ─────────────────────────────────────────
        try:
            if name == "openai":
                import openai
                kwargs = {"api_key": api_key}
                if base_url:
                    kwargs["base_url"] = base_url
                self.client = openai.OpenAI(**kwargs)

            elif name == "claude":
                import anthropic
                # base_url: nếu có → dùng proxy server (Anthropic-compatible)
                # Anthropic SDK hỗ trợ sẵn tham số này — không cần đổi gì thêm
                kwargs = {"api_key": api_key}
                if base_url:
                    kwargs["base_url"] = base_url
                self.client = anthropic.Anthropic(**kwargs)

            elif name == "gemini":
                from google import genai
                self.client = genai.Client(api_key=api_key)
                self._gemini_model = cfg["chat_model"]

            elif name == "openrouter":
                import openai
                self.client = openai.OpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://openrouter.ai/api/v1",
                )

            self.provider = name
            self.enabled  = True

            proxy_str = f"\n   Proxy    : {base_url}" if base_url else ""
            print(
                f"✅ AI Module: Online\n"
                f"   Provider : {name}{proxy_str}\n"
                f"   Chat     : {cfg['chat_model']}\n"
                f"   Vision   : {cfg['vision_model']}"
            )
            return True

        except Exception as e:
            print(f"❌ Lỗi khởi tạo {name}: {e}")
            return False

    def _print_offline_info(self):
        """In thông tin khi offline"""

        # Kiểm tra từng provider
        available   = []
        need_install = []
        no_key      = []

        for name, cfg in self.PROVIDERS.items():
            has_key     = bool(os.getenv(cfg["env_key"], ""))
            has_package = self._is_package_installed(cfg["package"])

            if has_key and has_package:
                available.append(name)
            elif has_key and not has_package:
                need_install.append(
                    f"{name} (pip install {cfg['package']})"
                )
            else:
                no_key.append(name)

        print("\n" + "─" * 40)
        print("⚠️  AI Module: Offline")

        if need_install:
            print(
                "\n📦 Có API key nhưng chưa cài:\n" +
                "\n".join(
                    f"   {x}" for x in need_install
                )
            )

        if no_key:
            print(
                "\n🔑 Chưa có API key:\n" +
                "\n".join(
                    f"   {x}" for x in no_key
                )
            )

        print(
            "\n💡 Để kích hoạt AI:\n"
            "   1. Thêm API key vào .env\n"
            "   2. pip install [package]\n"
            "   3. Restart chương trình"
        )
        print("─" * 40 + "\n")

    # ── Public Methods ────────────────────────────────

    def chat(self, user_message: str) -> str:
        """Chat với học sinh"""
        if not self.enabled:
            return self._offline_response()

        try:
            if self.provider in ["openai",
                                  "openrouter"]:
                return self._chat_openai(user_message)
            elif self.provider == "claude":
                return self._chat_claude(user_message)
            elif self.provider == "gemini":
                return self._chat_gemini(user_message)
        except Exception as e:
            print(f"❌ Lỗi chat: {e}")
            return "Xin lỗi, mình đang gặp sự cố!"

        return self._offline_response()

    def read_content(self, image_base64: str) -> str:
        """
        Đọc nội dung văn bản/hình ảnh từ ảnh chụp.
        Dùng để OCR màn hình, sách, vở, bảng viết...
        Returns: chuỗi mô tả nội dung đọc được (text thuần)
        """
        if not self.enabled:
            return "AI chưa kích hoạt — thêm API key vào .env để dùng tính năng đọc nội dung."

        # Prompt đọc nội dung bài tập từ ảnh
        prompt = (
            "Focus on the STUDENT'S WORKSPACE in the image (desk, screen, books, notebooks).\n"
            "IGNORE: signs, wall/ceiling text, stickers, logos, room labels, decorations.\n\n"
            "Analyze and respond in these sections:\n\n"
            "**1. Current activity:**\n"
            "What is the student doing? (typing on computer, writing, reading, using phone, "
            "chatting, idle, ...)\n\n"
            "**2. Is the student doing homework/assignments?**\n"
            "Answer Yes/No/Unclear. If Yes, briefly describe.\n\n"
            "**3. Homework content details (if visible):**\n"
            "- Read the exact content on screen/paper/book\n"
            "- Math: which problem/exercise, what type (equations, geometry, ...)\n"
            "- Literature/Essay: what topic, which paragraph\n"
            "- English: what type of exercise (grammar, vocabulary, reading comprehension, ...)\n"
            "- Programming: what language, which part of code\n"
            "- Other subjects: specific visible content\n\n"
            "**4. Subject / Field:** Identify the subject if possible.\n\n"
            "**5. Progress:** Estimate completion level if visible "
            "(e.g., working on problem 3/10, half a page written, ...).\n\n"
            "If content is not clearly visible, state 'Content not clearly visible'.\n"
            "Respond in Vietnamese."
        )

        try:
            if self.provider in ["openai", "openrouter"]:
                return self._read_content_openai(image_base64, prompt)
            elif self.provider == "claude":
                return self._read_content_claude(image_base64, prompt)
            elif self.provider == "gemini":
                return self._read_content_gemini(image_base64, prompt)
        except Exception as e:
            return f"Lỗi đọc nội dung: {e}"

        return "Không hỗ trợ provider này."

    def _read_content_openai(self, image_base64: str, prompt: str) -> str:
        model = self.PROVIDERS[self.provider]["vision_model"]
        resp = self.client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            "detail": "high"
                        }
                    }
                ]
            }],
            max_tokens=2000
        )
        return resp.choices[0].message.content

    def _read_content_claude(self, image_base64: str, prompt: str) -> str:
        """Claude read_content — dùng trực tiếp hoặc qua proxy (base_url)."""
        model = self.PROVIDERS["claude"]["vision_model"]
        resp = self.client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        return resp.content[0].text

    def _read_content_gemini(self, image_base64: str, prompt: str) -> str:
        import base64
        from google.genai import types

        model = self.PROVIDERS["gemini"]["vision_model"]
        image_part = types.Part.from_bytes(
            data=base64.b64decode(image_base64),
            mime_type="image/jpeg"
        )
        resp = self.client.models.generate_content(
            model=model,
            contents=[prompt, image_part],
        )
        return resp.text

    def analyze_image(
        self,
        frame_base64: str
    ) -> dict:
        """Phân tích ảnh từ camera"""
        default = {
            "is_focused"    : True,
            "needs_reminder": False,
            "message"       : ""
        }

        if not self.enabled:
            return default

        try:
            if self.provider in ["openai",
                                  "openrouter"]:
                return self._vision_openai(
                    frame_base64
                )
            elif self.provider == "claude":
                return self._vision_claude(
                    frame_base64
                )
            elif self.provider == "gemini":
                return self._vision_gemini(
                    frame_base64
                )
        except Exception as e:
            print(f"❌ Lỗi vision: {e}")

        return default

    # ── Homework Analysis ──────────────────────────────

    def analyze_homework(
        self,
        image_base64: str,
        homework_context: dict = None,
    ) -> dict:
        """
        Phân tích ảnh chụp bài tập của học sinh.

        Args:
            image_base64: ảnh JPEG base64
            homework_context: dict context tuỳ chọn, ví dụ:
                {"subject": "Math", "grade": 8, "task": "page 45 ex3"}

        Returns: dict
            {
                "doing_hw"  : True/False/None,
                "subject"   : "Math"|"Literature"|"English"|...|None,
                "grade"     : "8"|"10"|None,
                "hw_type"   : "exercises"|"essay"|...,
                "progress"  : 0-100,
                "correct"   : True/False/None,
                "help"      : "brief help suggestion"|None,
                "confidence": 0.0-1.0,
            }
        """
        default = {
            "doing_hw"  : None,
            "subject"   : None,
            "grade"     : None,
            "hw_type"   : None,
            "progress"  : 0,
            "correct"   : None,
            "help"      : None,
            "confidence": 0.0,
        }

        if not self.enabled:
            return default

        prompt = self._build_homework_prompt(homework_context)

        try:
            if self.provider in ["openai", "openrouter"]:
                text = self._read_content_openai(image_base64, prompt)
            elif self.provider == "claude":
                text = self._read_content_claude(image_base64, prompt)
            elif self.provider == "gemini":
                text = self._read_content_gemini(image_base64, prompt)
            else:
                return default

            return self._parse_homework_response(text, default)

        except Exception as e:
            print(f"❌ Lỗi analyze_homework: {e}")
            return default

    def _build_homework_prompt(self, ctx: dict = None) -> str:
        """
        Prompt phân tích bài tập — ngắn gọn, tiết kiệm token.
        ~80 input tokens (không kể context). Response ~60 tokens.
        """
        parts = [
            "Analyze student homework image. Reply JSON only, no markdown.\n"
        ]

        if ctx:
            tags = []
            if ctx.get("subject"): tags.append(f"subject:{ctx['subject']}")
            if ctx.get("grade"):   tags.append(f"grade:{ctx['grade']}")
            if ctx.get("task"):    tags.append(f"task:{ctx['task']}")
            if tags:
                parts.append(f"[CTX] {' | '.join(tags)}\n")

        # Compact schema — abbreviated keys để giảm output token
        parts.append(
            '{"hw":<true/false/null>,'
            '"subj":"<Math/Literature/English/Physics/Chemistry/'
            'Biology/History/Geography/other/null>",'
            '"grade":"<e.g.6,10,12,null>",'
            '"type":"<exercises/essay/reading/other/null>",'
            '"prog":<0-100>,'
            '"ok":<true/false/null>,'
            '"help":"<max 12 words or null>",'
            '"conf":<0.0-1.0>}'
        )

        return "\n".join(parts)

    def _parse_homework_response(self, text: str, default: dict) -> dict:
        """Parse JSON response từ AI → full keys."""
        try:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if not m:
                return default

            raw = json.loads(m.group())

            return {
                "doing_hw"  : raw.get("hw"),
                "subject"   : raw.get("subj"),
                "grade"     : str(raw.get("grade")) if raw.get("grade") else None,
                "hw_type"   : raw.get("type"),
                "progress"  : int(raw.get("prog", 0)),
                "correct"   : raw.get("ok"),
                "help"      : raw.get("help"),
                "confidence": float(raw.get("conf", 0.0)),
            }
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"⚠️ Parse homework response failed: {e}")
            return default

    def generate_reminder(
        self,
        activity: str,
        seconds: int
    ) -> str:
        """Tạo nhắc nhở - hoạt động cả offline"""
        return self._get_reminder(activity, seconds)

    def clear_history(self):
        self.history = []
        print("🗑️  Đã xóa lịch sử chat")

    def get_status(self) -> dict:
        return {
            "enabled"    : self.enabled,
            "provider"   : self.provider or "none",
            "mode"       : (
                "online" if self.enabled
                else "offline"
            ),
            "history_len": len(self.history)
        }

    # ── Chat theo Provider ────────────────────────────

    def _chat_openai(self, message: str) -> str:
        """OpenAI và OpenRouter"""
        self._add_history("user", message)

        model = self.PROVIDERS[
            self.provider
        ]["chat_model"]

        resp = self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role"   : "system",
                    "content": self.system_prompt
                }
            ] + self.history,
            max_tokens=300,
            temperature=0.7
        )

        reply = resp.choices[0].message.content
        self._add_history("assistant", reply)
        return reply

    def _chat_claude(self, message: str) -> str:
        """Anthropic Claude — dùng trực tiếp hoặc qua proxy (base_url)."""
        self._add_history("user", message)
        model = self.PROVIDERS["claude"]["chat_model"]

        resp = self.client.messages.create(
            model=model,
            max_tokens=300,
            system=self.system_prompt,
            messages=self.history
        )

        reply = resp.content[0].text
        self._add_history("assistant", reply)
        return reply

    def _chat_gemini(self, message: str) -> str:
        """Google Gemini (google-genai SDK)"""
        self._add_history("user", message)
        model = self.PROVIDERS["gemini"]["chat_model"]

        # Build contents from history
        contents = []
        for h in self.history:
            role = "user" if h["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": h["content"]}]})

        resp = self.client.models.generate_content(
            model=model, contents=contents
        )
        reply = resp.text
        self._add_history("assistant", reply)
        return reply

    # ── Vision theo Provider ──────────────────────────

    def _vision_openai(
        self,
        frame_base64: str
    ) -> dict:
        """OpenAI / OpenRouter Vision"""
        model = self.PROVIDERS[
            self.provider
        ]["vision_model"]

        resp = self.client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self._vision_prompt()
                    },
                    {
                        "type"     : "image_url",
                        "image_url": {
                            "url": (
                                "data:image/jpeg;"
                                f"base64,{frame_base64}"
                            ),
                            "detail": "low"
                        }
                    }
                ]
            }],
            max_tokens=150
        )

        return self._parse_vision(
            resp.choices[0].message.content
        )

    def _vision_claude(
        self,
        frame_base64: str
    ) -> dict:
        """Claude Vision — dùng trực tiếp hoặc qua proxy (base_url)."""
        model = self.PROVIDERS["claude"]["vision_model"]

        resp = self.client.messages.create(
            model=model,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type"  : "image",
                        "source": {
                            "type"      : "base64",
                            "media_type": "image/jpeg",
                            "data"      : frame_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": self._vision_prompt()
                    }
                ]
            }]
        )

        return self._parse_vision(
            resp.content[0].text
        )

    def _vision_gemini(
        self,
        frame_base64: str
    ) -> dict:
        """Gemini Vision (google-genai SDK)"""
        import base64
        from google.genai import types

        model = self.PROVIDERS["gemini"]["vision_model"]
        image_part = types.Part.from_bytes(
            data=base64.b64decode(frame_base64),
            mime_type="image/jpeg"
        )

        resp = self.client.models.generate_content(
            model=model,
            contents=[self._vision_prompt(), image_part],
        )

        return self._parse_vision(resp.text)

    # ── Helpers ───────────────────────────────────────

    def _add_history(
        self,
        role: str,
        content: str
    ):
        """Thêm vào lịch sử, giữ giới hạn"""
        self.history.append({
            "role"   : role,
            "content": content
        })
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[
                -self.MAX_HISTORY:
            ]

    def _vision_prompt(self) -> str:
        """Prompt phân tích ảnh — realtime focus detection"""
        return (
            "Analyze student image:\n"
            "1. Is the student focused?\n"
            "2. Need a reminder?\n\n"
            "Reply JSON:\n"
            '{"is_focused": true/false, '
            '"needs_reminder": true/false, '
            '"message": "reminder in Vietnamese if needed"}'
        )

    def _parse_vision(self, text: str) -> dict:
        """Parse JSON từ vision response"""
        try:
            match = re.search(
                r'\{.*\}', text, re.DOTALL
            )
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        return {
            "is_focused"    : True,
            "needs_reminder": False,
            "message"       : ""
        }

    def _offline_response(self) -> str:
        """Fallback khi không có API key"""
        return random.choice([
            "AI đang offline. Thêm API key vào .env!",
            "Chưa kết nối AI. Kiểm tra file .env nhé!",
        ])

    def _get_reminder(
        self,
        activity: str,
        seconds: int
    ) -> str:
        """Tạo nhắc nhở theo hoạt động"""
        name = self.student_name

        all_reminders = {
            "distracted": [
                f"{name} ơi, tập trung lại nhé! 📚",
                f"Này {name}, bài vẫn đang chờ! 💪",
                f"{name} đang nghĩ gì vậy? 😄",
                f"Tập trung nào {name}! 🎯",
            ],
            "absent": [
                (
                    f"{name} đi đâu vậy? "
                    f"Nghỉ {seconds}s rồi đó!"
                ),
                f"Mau quay lại học thôi {name}! 📖",
            ],
            "drowsy": [
                (
                    f"{name} ơi, buồn ngủ rồi à? "
                    f"Rửa mặt rồi học tiếp nhé!"
                ),
                f"Đứng dậy vận động chút đi {name}! 🏃",
            ],
            "looking_away": [
                f"Nhìn vào bài đi {name}! 👀",
                f"{name} ơi, tập trung nào! 🎯",
            ],
            "long_absent": [
                (
                    f"{name} đi lâu quá! "
                    f"{seconds // 60} phút rồi đó!"
                ),
                f"Quay lại học ngay đi {name}!",
            ],
        }

        msgs = all_reminders.get(
            activity,
            all_reminders["distracted"]
        )
        return random.choice(msgs)