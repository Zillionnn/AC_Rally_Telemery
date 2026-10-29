"""Record the game window plus system audio into a seekable MP4.

Built from the spike that proved this stack on this machine: Windows Graphics
Capture for the picture, WASAPI loopback for everything the machine plays, and
PyAV for H.264 (NVENC when present) + AAC. The traps the spike found are all
handled here and noted where they matter.
"""

from __future__ import annotations

import ctypes
import queue
import threading
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_PATTERNS = ("Assetto Corsa Rally", "AC Rally", "Assettocorsa")
AUDIO_CHUNK = 1024


def list_windows() -> list[tuple[int, str]]:
    user32 = ctypes.windll.user32
    user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
    user32.IsWindowVisible.restype = ctypes.c_bool
    user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    found: list[tuple[int, str]] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visit(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, ctypes.byref(buffer), length + 1)
        title = buffer.value.strip()
        if title:
            # ctypes sign-extends c_void_p; kernel handles only use 32 bits.
            found.append((int(hwnd) & 0xFFFFFFFF, title))
        return True

    user32.EnumWindows(visit, 0)
    return found


def find_window(patterns=DEFAULT_PATTERNS) -> tuple[int, str] | None:
    windows = list_windows()
    for pattern in patterns:
        needle = pattern.lower()
        for hwnd, title in windows:
            if needle in title.lower():
                return hwnd, title
    return None


class VideoRecorder:
    """One recording at a time; start()/stop() are called from the Qt thread."""

    def __init__(self, fps: int = 60, width: int = 1920, height: int = 1080,
                 bitrate_mbps: float = 8.0, encoder: str = "auto",
                 audio: bool = True) -> None:
        self.fps = int(fps)
        self.width = int(width)
        self.height = int(height)
        self.bitrate_mbps = float(bitrate_mbps)
        self.encoder = encoder
        self.audio_enabled = bool(audio)
        self.running = False
        self.target: tuple[int, str | None] | None = None
        self.last_result: dict[str, Any] = {}
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._threads: list[threading.Thread] = []
        self._state: dict[str, Any] = {}
        self._pix_fmt = "nv12"
        self._encoder_name = None

    # --- public -----------------------------------------------------------
    def start(self, out_path: Path, hwnd: int | None = None,
              patterns=DEFAULT_PATTERNS) -> bool:
        if self.running:
            return False
        self._stop.clear()
        self._state = {
            "out": Path(out_path), "error": None, "frames": 0, "duplicated": 0,
            "dropped": 0, "audio_blocks": 0, "encoder": None, "hwnd": None,
        }
        try:
            self._begin(hwnd, patterns)
        except Exception as exc:  # noqa: BLE001
            self._state["error"] = f"{type(exc).__name__}: {exc}"
            self._cleanup()
            self.running = False
            return False
        self.running = True
        return True

    def stop(self) -> dict:
        if not self.running:
            return self.last_result
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=6.0)
        result = self._finish()
        self.running = False
        self.last_result = result
        return result

    # --- internals --------------------------------------------------------
    def _begin(self, hwnd: int | None, patterns) -> None:
        import av
        from windows_capture import WindowsCapture

        target = (hwnd, None) if hwnd else find_window(patterns)
        if not target:
            raise RuntimeError("找不到游戏窗口")
        self.target = (int(target[0]), target[1] if len(target) > 1 else None)
        self._state["hwnd"] = int(target[0])

        self._container = av.open(str(self._state["out"]), "w")
        self._vstream, self._encoder_name = self._add_video_stream(av)
        self._astream, self._audio = self._add_audio_stream(av)
        self._queue: queue.Queue = queue.Queue(maxsize=120)

        capture = WindowsCapture(window_hwnd=self._state["hwnd"],
                                 cursor_capture=True)

        @capture.event
        def on_frame_arrived(frame, control) -> None:
            if self._stop.is_set():
                control.stop()
                return
            self._on_video(frame)

        @capture.event
        def on_closed() -> None:
            pass

        self._control = capture.start_free_threaded()
        self._threads = [threading.Thread(target=self._pump, daemon=True),
                         threading.Thread(target=self._writer, daemon=True)]
        if self._audio is not None:
            self._threads.append(threading.Thread(target=self._read_audio,
                                                  daemon=True))
        for thread in self._threads:
            thread.start()

    def _add_video_stream(self, av):
        name = self.encoder
        candidates = (["h264_nvenc", "libx264"] if name in ("auto", "nvenc")
                      else [name])
        last_error = None
        for candidate in candidates:
            try:
                stream = self._container.add_stream(candidate, rate=self.fps)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue
            is_nvenc = candidate.endswith("_nvenc")
            stream.width, stream.height = self.width, self.height
            stream.pix_fmt = "nv12" if is_nvenc else "yuv420p"
            stream.options = {"g": str(self.fps), "bf": "0"}
            if is_nvenc:
                stream.options.update({
                    "preset": "p5", "tune": "hq", "rc": "cbr",
                    "b": f"{int(self.bitrate_mbps * 1_000_000)}",
                    "profile": "main",
                })
            else:
                stream.options.update({
                    "preset": "veryfast", "tune": "zerolatency",
                    "crf": str(max(18, 26 - int(self.bitrate_mbps))),
                })
            self._pix_fmt = "nv12" if is_nvenc else "yuv420p"
            return stream, candidate
        raise RuntimeError(f"没有可用的 H.264 编码器: {last_error}")

    def _add_audio_stream(self, av):
        if not self.audio_enabled:
            return None, None
        try:
            import pyaudiowpatch as pa
        except Exception:  # noqa: BLE001
            return None, None
        self._pa = pa.PyAudio()
        try:
            device = self._pa.get_default_wasapi_loopback()
        except Exception as exc:  # noqa: BLE001
            self._pa.terminate()
            self._pa = None
            self._state["error"] = f"音频设备不可用: {exc}"
            return None, None
        rate = int(device["defaultSampleRate"])
        channels = max(1, int(device["maxInputChannels"]))
        stream = self._pa.open(
            format=pa.paInt16, channels=channels, rate=rate, input=True,
            input_device_index=device["index"], frames_per_buffer=AUDIO_CHUNK,
        )
        out = self._container.add_stream("aac", rate=rate)
        out.layout = "stereo"
        out.bit_rate = 192000
        return out, {
            "raw": stream, "rate": rate, "channels": channels, "pts": 0,
        }

    def _slot_for(self, now: float) -> tuple[int | None, int]:
        """Wall-clock CFR slot; WGC delivers on repaint, not at a fixed rate."""
        state = self._state
        with self._lock:
            if state.get("t0") is None:
                state["t0"] = now
            return state.get("last_slot"), int((now - state["t0"]) * self.fps)

    def _on_video(self, frame) -> None:
        import av

        now = time.perf_counter()
        last, slot = self._slot_for(now)
        if last is not None and slot <= last:
            return
        state = self._state
        try:
            buffer = frame.frame_buffer
            if not buffer.flags["C_CONTIGUOUS"]:
                buffer = np.ascontiguousarray(buffer)
            source = av.VideoFrame.from_ndarray(buffer, format="bgra")
            # swscale would otherwise grab every core and steal the game's CPU.
            converted = source.reformat(width=self.width, height=self.height,
                                        format=self._pix_fmt, threads=2)
        except Exception as exc:  # noqa: BLE001
            state.setdefault("convert_errors", []).append(
                f"{type(exc).__name__}: {exc}")
            return
        with self._lock:
            # The pump may have advanced the timeline while this frame was
            # being converted, so never let it step backwards.
            state["last_slot"] = max(slot, (state.get("last_slot") or -1) + 1)
            state["prev"] = converted
        state["size"] = (frame.width, frame.height)
        self._emit(("v", converted, now))

    def _pump(self) -> None:
        """Repeat the last frame while the window sits still, so video time is
        real time and stays aligned with the telemetry."""
        while not self._stop.is_set():
            time.sleep(0.5 / self.fps)
            state = self._state
            now = time.perf_counter()
            with self._lock:
                if state.get("t0") is None or state.get("prev") is None:
                    continue
                want = int((now - state["t0"]) * self.fps)
                last = state.get("last_slot")
                if last is None or want <= last:
                    continue
                missing = min(want - last, self.fps * 5)
                prev = state["prev"]
                state["last_slot"] = last + missing
            for _ in range(missing):
                self._emit(("v", prev, now))
                state["duplicated"] += 1

    def _read_audio(self) -> None:
        audio = self._audio
        stream = audio["raw"]
        while not self._stop.is_set():
            try:
                available = stream.get_read_available()
            except Exception as exc:  # noqa: BLE001
                self._state.setdefault("errors", []).append(f"audio: {exc}")
                return
            if available < AUDIO_CHUNK:
                # a blocking read() never returns while the endpoint is
                # silent, and close() on another thread then crashes PortAudio
                time.sleep(0.002)
                continue
            try:
                data = stream.read(min(available, AUDIO_CHUNK),
                                   exception_on_overflow=False)
            except Exception as exc:  # noqa: BLE001
                self._state.setdefault("errors", []).append(f"audio: {exc}")
                return
            now = time.perf_counter()
            with self._lock:
                if self._state.get("t0") is None:
                    self._state["t0"] = now
            self._emit(("a", data, now))
            self._state["audio_blocks"] += 1

    def _emit(self, item) -> None:
        try:
            self._queue.put_nowait(item)
            if item[0] == "v":
                self._state["frames"] += 1
        except queue.Full:
            self._state["dropped"] += 1

    def _writer(self) -> None:
        import av

        audio = self._audio
        while True:
            try:
                kind, payload, _now = self._queue.get(timeout=0.2)
            except queue.Empty:
                if self._stop.is_set():
                    break
                continue
            try:
                if kind == "v":
                    payload.pts = self._state.get("v_pts", 0)
                    payload.time_base = Fraction(1, self.fps)
                    self._state["v_pts"] = payload.pts + 1
                    for packet in self._vstream.encode(payload):
                        self._container.mux(packet)
                elif audio is not None:
                    samples = np.frombuffer(payload, dtype="<i2").astype(np.float32)
                    samples /= 32768.0
                    channels = audio["channels"]
                    if channels == 2:
                        planar = np.ascontiguousarray(samples.reshape(-1, 2).T)
                        layout = "stereo"
                    else:
                        planar = np.ascontiguousarray(samples.reshape(1, -1))
                        layout = "mono"
                    frame = av.AudioFrame.from_ndarray(planar, format="fltp",
                                                       layout=layout)
                    frame.sample_rate = audio["rate"]
                    frame.pts = audio["pts"]
                    frame.time_base = Fraction(1, audio["rate"])
                    audio["pts"] += planar.shape[1]
                    muxed = 0
                    for packet in self._astream.encode(frame):
                        self._container.mux(packet)
                        muxed += 1
                    self._state["audio_packets"] = (
                        self._state.get("audio_packets", 0) + muxed)
            except Exception as exc:  # noqa: BLE001
                self._state.setdefault("errors", []).append(
                    f"writer: {type(exc).__name__}: {exc}")
                return

    def _finish(self) -> dict:
        state = self._state
        try:
            self._control.stop()
            self._control.wait()
        except Exception:  # noqa: BLE001
            pass
        if self._audio is not None:
            try:
                self._audio["raw"].stop_stream()
                self._audio["raw"].close()
            except Exception:  # noqa: BLE001
                pass
        for stream in (self._vstream, self._astream):
            if stream is None:
                continue
            try:
                for packet in stream.encode(None):
                    self._container.mux(packet)
            except Exception as exc:  # noqa: BLE001
                state.setdefault("errors", []).append(f"flush: {exc}")
        try:
            self._container.close()
        except Exception as exc:  # noqa: BLE001
            state.setdefault("errors", []).append(f"close: {exc}")
        if getattr(self, "_pa", None) is not None:
            try:
                self._pa.terminate()
            except Exception:  # noqa: BLE001
                pass
            self._pa = None

        seconds = (state.get("v_pts", 0) / self.fps) if state else 0.0
        path = state.get("out")
        errors = list(state.get("errors", []))
        if state.get("convert_errors"):
            errors.append("转换失败 x%d: %s" % (
                len(state["convert_errors"]), state["convert_errors"][0]))
        mb = path.stat().st_size / 1048576.0 if path and path.exists() else 0.0
        result = {
            "path": str(path) if path else None,
            "seconds": round(seconds, 2),
            "frames": state.get("v_pts", 0),
            "duplicated": state.get("duplicated", 0),
            "dropped": state.get("dropped", 0),
            "mb": round(mb, 1),
            "encoder": self._encoder_name,
            "source": ("%dx%d" % state["size"]) if state.get("size") else None,
            "audio": bool(self._audio is not None),
            "audio_samples": (self._audio or {}).get("pts", 0) if self._audio else 0,
            "audio_packets": state.get("audio_packets", 0),
            "error": "; ".join(errors[:3]) if errors else state.get("error"),
        }
        self._cleanup()
        return result

    def _cleanup(self) -> None:
        self._threads = []

