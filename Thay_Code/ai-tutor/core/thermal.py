# core/thermal.py
# ThermalManager — đọc nhiệt độ CPU RPi5 và trả về mức throttle
# cho YOLO background thread và main detection loop.
#
# Nhiệt độ đọc từ sysfs: /sys/class/thermal/thermal_zone0/temp
# Giá trị trả về (milli-Celsius) được chia 1000 → Celsius.
#
# Throttle tiers:
#   < THERMAL_WARN_TEMP  (75°C): bình thường
#   < THERMAL_HIGH_TEMP  (82°C): cảnh báo — tăng YOLO skip nhẹ
#   < THERMAL_CRITICAL   (88°C): throttle mạnh — tăng skip + sleep main loop
#   >= THERMAL_CRITICAL  (88°C): tắt YOLO hoàn toàn

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import Config


class ThermalManager:
    """
    Quản lý nhiệt độ CPU RPi5.
    Gọi get_throttle() định kỳ (mỗi THERMAL_READ_INTERVAL frame)
    từ camera loop để điều chỉnh tần suất YOLO.
    """

    _SYSFS_PATH = "/sys/class/thermal/thermal_zone0/temp"

    def __init__(self):
        self._last_temp = -1.0
        self._warn_logged  = False
        self._high_logged  = False
        self._crit_logged  = False

    def read_cpu_temp(self) -> float:
        """
        Đọc nhiệt độ CPU từ sysfs.
        Trả về nhiệt độ (°C). -1.0 nếu không đọc được.
        """
        try:
            with open(self._SYSFS_PATH) as f:
                self._last_temp = int(f.read().strip()) / 1000.0
                return self._last_temp
        except OSError:
            return -1.0

    def get_throttle(self) -> tuple:
        """
        Đọc nhiệt độ và trả về (extra_yolo_skip, extra_main_sleep).

        extra_yolo_skip : int   — cộng thêm vào YOLO_SKIP_FRAMES
        extra_main_sleep: float — giây sleep thêm vào main loop

        Gọi mỗi THERMAL_READ_INTERVAL frame từ camera loop.
        """
        temp = self.read_cpu_temp()
        if temp < 0:
            return 0, 0.0   # không đọc được → không throttle

        if temp >= Config.THERMAL_CRITICAL_TEMP:
            if not self._crit_logged:
                print(f"\n🔥 NHIỆT ĐỘ NGUY HIỂM {temp:.1f}°C — TẮT YOLO!")
                self._crit_logged = True
            return 999, Config.THERMAL_HIGH_EXTRA_SLEEP

        self._crit_logged = False

        if temp >= Config.THERMAL_HIGH_TEMP:
            if not self._high_logged:
                print(f"\n⚠️  Nhiệt độ cao {temp:.1f}°C — Throttle YOLO mạnh")
                self._high_logged = True
            self._warn_logged = False
            return Config.THERMAL_HIGH_EXTRA_SKIP, Config.THERMAL_HIGH_EXTRA_SLEEP

        self._high_logged = False

        if temp >= Config.THERMAL_WARN_TEMP:
            if not self._warn_logged:
                print(f"\n🌡️  Nhiệt độ cảnh báo {temp:.1f}°C — Tăng YOLO skip")
                self._warn_logged = True
            return Config.THERMAL_WARN_EXTRA_SKIP, 0.0

        self._warn_logged = False
        return 0, 0.0

    @property
    def last_temp(self) -> float:
        """Nhiệt độ lần đọc gần nhất (°C)."""
        return self._last_temp
