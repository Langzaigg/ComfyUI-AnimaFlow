"""XPU 设备守护：识别 Level Zero 上下文丢失并结束自身进程，交给外部守护拉起。

Arc 上跑 MOSS-Image 这类「单文件 checkpoint = 9.7 GB 文本编码器 + 5.4 GB DiT」的模型时，
16 GB 卡装不下全部权重，每次改提示词都要把 TE 与 DiT 换进换出。换页时若显存已经吃紧，
Level Zero 会直接复位上下文并报 `UR_RESULT_ERROR_DEVICE_LOST`。上下文一旦丢失，进程里
所有后续 xpu 调用都会失败（连 soft_empty_cache 里的 synchronize 也会炸），只能重启进程。

这里不自己拉新进程：检测到设备丢失就干净地退出，由外部守护（systemd / docker restart /
机器人 watchdog / 手动启动脚本）拉起。为避免驱动抖动误杀，探活要连续两次失败才判定；
为避免崩溃循环，30 分钟内重启次数超限后只标记状态、不再自行退出。
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("anima_tool.device_guard")

# Level Zero / torch XPU 的上下文丢失文案（不同驱动版本措辞略有差异）
DEVICE_LOST_MARKERS = (
    "UR_RESULT_ERROR_DEVICE_LOST",
    "level_zero backend failed",
    "DEVICE_LOST",
    "device lost",
    "ze_result_error_device_lost",
)


def is_device_lost(text: Any) -> bool:
    """判断异常或日志文本是否为设备上下文丢失。"""
    blob = str(text or "")
    return any(marker.lower() in blob.lower() for marker in DEVICE_LOST_MARKERS)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    return default


class DeviceGuard:
    """XPU 探活 + 失败退出。

    环境变量：
    - ANIMATOOL_DEVICE_GUARD=0 关闭守护（默认开）
    - ANIMATOOL_DEVICE_GUARD_INTERVAL=20 探活间隔（秒）
    - ANIMATOOL_DEVICE_GUARD_GRACE=60 启动后多久开始探活（秒）
    - ANIMATOOL_DEVICE_RESTART_MODE=exit|off
        exit  判定丢失后结束进程，由外部守护拉起（默认）
        off   只记录状态，不动进程（排查问题时用）
    - ANIMATOOL_DEVICE_RESTART_COOLDOWN=300 两次退出之间的最小间隔（秒）
    - ANIMATOOL_DEVICE_RESTART_LIMIT=3 30 分钟内最多退出次数，超过则只标记不退出
    """

    _instance: Optional["DeviceGuard"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.enabled = _env_bool("ANIMATOOL_DEVICE_GUARD", True)
        self.interval = max(5, _env_int("ANIMATOOL_DEVICE_GUARD_INTERVAL", 20))
        self.grace = max(0, _env_int("ANIMATOOL_DEVICE_GUARD_GRACE", 60))
        mode = (os.environ.get("ANIMATOOL_DEVICE_RESTART_MODE") or "exit").strip().lower()
        # 兼容旧值：relaunch / supervisor 一律按 exit 处理（不再自己拉新进程）
        self.mode = "off" if mode == "off" else "exit"
        self.cooldown = max(0, _env_int("ANIMATOOL_DEVICE_RESTART_COOLDOWN", 300))
        self.limit = max(1, _env_int("ANIMATOOL_DEVICE_RESTART_LIMIT", 3))

        self._state = "ok"
        self._failures = 0
        self._last_error = ""
        self._last_probe = 0.0
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._marker = Path(__file__).resolve().parent / "outputs" / ".device_guard.json"

    # -------------------------
    # 单例与生命周期
    # -------------------------
    @classmethod
    def instance(cls) -> "DeviceGuard":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        if not self._xpu_available():
            logger.info("[device-guard] 无 XPU，跳过设备探活")
            return
        self._thread = threading.Thread(target=self._loop, name="anima-device-guard", daemon=True)
        self._thread.start()
        logger.info(
            "[device-guard] 已启动：interval=%ss grace=%ss mode=%s",
            self.interval, self.grace, self.mode,
        )

    @staticmethod
    def _xpu_available() -> bool:
        try:
            import torch

            return bool(hasattr(torch, "xpu") and torch.xpu.is_available())
        except Exception:
            return False

    # -------------------------
    # 探活
    # -------------------------
    def _loop(self) -> None:
        if self.grace:
            self._stop.wait(self.grace)
        while not self._stop.is_set():
            self.probe()
            self._stop.wait(self.interval)

    def probe(self) -> str:
        """探一次设备：返回 ok / dead / error。连续两次失败才判定丢失。"""
        import torch

        self._last_probe = time.time()
        try:
            torch.xpu.synchronize()
        except Exception as exc:
            if is_device_lost(exc):
                self._failures += 1
                self._last_error = str(exc)[:300]
                logger.warning(
                    "[device-guard] XPU 探活失败 %d/2：%s", self._failures, self._last_error
                )
                if self._failures >= 2:
                    self._state = "dead"
                    self._recover(self._last_error)
                return "dead"
            self._last_error = str(exc)[:300]
            logger.warning("[device-guard] 探活异常（非设备丢失）：%s", self._last_error)
            return "error"

        self._failures = 0
        self._state = "ok"
        return "ok"

    # -------------------------
    # 恢复：结束进程，交给外部守护
    # -------------------------
    def notify_device_lost(self, detail: str = "") -> None:
        """业务侧（例如执行失败）上报一次设备丢失，稍后结束进程。

        延后 1 秒，让调用方还能把错误响应写回客户端。
        """
        self._failures += 1
        self._last_error = str(detail or "device lost")[:300]
        self._state = "dead"
        threading.Thread(
            target=lambda: (time.sleep(1.0), self._recover(self._last_error)),
            name="anima-device-guard-recover", daemon=True,
        ).start()

    def force_restart(self, reason: str = "manual restart") -> None:
        """手动触发（接口 /device/restart），仍受冷却与次数上限约束。"""
        self._state = "restarting"
        threading.Thread(
            target=lambda: (time.sleep(0.3), self._recover(reason)),
            name="anima-device-guard-manual", daemon=True,
        ).start()

    def _recent_restarts(self) -> list:
        try:
            data = json.loads(self._marker.read_text(encoding="utf-8"))
        except Exception:
            return []
        stamps = data.get("restarts") or []
        now = time.time()
        return [t for t in stamps if isinstance(t, (int, float)) and now - t < 1800]

    def _record_restart(self) -> None:
        stamps = self._recent_restarts()
        stamps.append(time.time())
        try:
            self._marker.parent.mkdir(parents=True, exist_ok=True)
            self._marker.write_text(json.dumps({"restarts": stamps[-10:]}), encoding="utf-8")
        except Exception:
            pass

    def _recover(self, reason: str) -> None:
        if self.mode == "off":
            logger.error("[device-guard] 设备丢失（mode=off，不退出）：%s", reason)
            return

        recent = self._recent_restarts()
        if len(recent) >= self.limit:
            logger.error(
                "[device-guard] 30 分钟内已退出 %d 次，停止自动退出（避免崩溃循环）：%s",
                len(recent), reason,
            )
            self._state = "dead_blocked"
            return

        self._record_restart()
        logger.error(
            "[device-guard] 设备上下文丢失，结束进程由外部守护拉起（30 分钟内第 %d 次）：%s",
            len(self._recent_restarts()), reason,
        )
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass
        os._exit(1)

    # -------------------------
    # 对外状态
    # -------------------------
    def health(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "state": self._state,
            "mode": self.mode,
            "consecutive_failures": self._failures,
            "exits_in_window": len(self._recent_restarts()),
            "exit_limit": self.limit,
            "last_error": self._last_error,
            "last_probe": self._last_probe,
            "interval_s": self.interval,
        }


def get_guard() -> DeviceGuard:
    """取全局守护实例（未启动过也会 start 一次）。"""
    guard = DeviceGuard.instance()
    guard.start()
    return guard
