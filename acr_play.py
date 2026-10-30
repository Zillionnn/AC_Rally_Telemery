"""Play a recording inside the client: PyAV decode + PortAudio output.

One thread decodes and writes audio; writing to the sound card blocks at
exactly the rate samples are consumed, which paces the decoder. Decoded video
frames go into a short queue that the GUI drains on a timer against that audio
clock, so picture and sound stay together without the video thread ever
blocking the audio thread.
"""

from __future__ import annotations

import threading
import time
from collections import deque

import numpy as np
from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QImage

from acr_i18n import tr

FRAME_QUEUE = 6


class _DecodeThread(QThread):
    frame = Signal(QImage, float)
    clock = Signal(float)
    ended = Signal()
    failed = Signal(str)

    def __init__(self, container, vstream, astream, out_stream, start_at=0.0,
                 parent=None):
        super().__init__(parent)
        self.container = container
        self.vstream = vstream
        self.astream = astream
        self.out = out_stream
        self.frames = deque(maxlen=FRAME_QUEUE)
        self.lock = threading.Lock()
        self.pause = threading.Event()
        self.stop_flag = threading.Event()
        self.seek_to = None
        self.volume = 0.8
        self.playhead = float(start_at)
        self.start_at = float(start_at)
        self.wall_base = time.perf_counter()

    def request_seek(self, seconds: float) -> None:
        self.seek_to = max(0.0, float(seconds))

    def request_stop(self) -> None:
        self.stop_flag.set()
        self.pause.clear()

    def take_frames(self, not_after: float) -> list:
        """Pop every decoded frame that is due by the current clock."""
        ready = []
        with self.lock:
            while self.frames and self.frames[0][1] <= not_after + 0.03:
                ready.append(self.frames.popleft())
        return ready

    # --- thread body ------------------------------------------------------
    def run(self) -> None:  # noqa: D102
        import av

        try:
            self._loop(av)
        except Exception as exc:  # noqa: BLE001
            if not self.stop_flag.is_set():
                self.failed.emit(f"{type(exc).__name__}: {exc}")

    def _loop(self, av) -> None:
        streams = [self.vstream]
        if self.astream is not None:
            streams.append(self.astream)
        while not self.stop_flag.is_set():
            if self.seek_to is not None:
                self._apply_seek(av)
            produced = False
            for packet in self.container.demux(*streams):
                if self.stop_flag.is_set() or self.seek_to is not None:
                    break
                try:
                    decoded = list(packet.decode())
                except EOFError:
                    # raised once the decoder has fully drained past end of
                    # file; treat it as "nothing left" rather than a failure
                    decoded = []
                for frame in decoded:
                    produced = True
                    if isinstance(frame, av.VideoFrame):
                        self._push(frame)
                    elif self.out is not None:
                        if not self._write_audio(frame):
                            return
            if not produced:
                self.ended.emit()
                return

    def _apply_seek(self, av) -> None:
        target = self.seek_to
        self.seek_to = None
        try:
            self.container.seek(int(target / self.vstream.time_base),
                                stream=self.vstream)
        except Exception:
            try:
                self.container.seek(int(target * av.time_base))
            except Exception:
                pass
        if self.out is not None:
            try:
                self.out.abort_stream()
            except Exception:
                pass
        with self.lock:
            self.frames.clear()
        self.playhead = target
        self.start_at = target

    def _push(self, frame) -> None:
        when = float(frame.pts * frame.time_base)
        while self.pause.is_set() and not self.stop_flag.is_set():
            time.sleep(0.03)
        if self.stop_flag.is_set():
            return
        if self.out is None:
            # no sound card to pace the decoder: follow the wall clock per frame
            delay = self.wall_base + (when - self.start_at) - time.perf_counter()
            if delay > 0:
                time.sleep(min(delay, 0.25))
            self.playhead = max(self.playhead, when)
            self.clock.emit(self.playhead)
        array = frame.to_ndarray(format="rgb24")
        image = QImage(array.data, array.shape[1], array.shape[0],
                       array.strides[0], QImage.Format.Format_RGB888).copy()
        with self.lock:
            # The deque drops the oldest when full: blocking here would wedge
            # the thread at end of file, where the audio clock has stopped.
            self.frames.append((image, when))

    def _write_audio(self, frame) -> bool:
        while self.pause.is_set() and not self.stop_flag.is_set():
            time.sleep(0.03)
        if self.stop_flag.is_set():
            return False
        array = frame.to_ndarray().astype(np.float32) * self.volume
        pcm = (np.clip(array.T.reshape(-1), -1.0, 1.0) * 32767.0).astype("<i2")
        try:
            self.out.write(pcm.tobytes())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(tr("音频输出失败：{error}").format(
                error=type(exc).__name__))
            return False
        end = float((frame.pts + frame.samples) * frame.time_base)
        self.playhead = max(self.playhead, end)
        self.clock.emit(self.playhead)
        return True


class VideoPlayer(QObject):
    frame_ready = Signal(QImage, float)
    position_changed = Signal(float)
    state_changed = Signal(str)
    duration_changed = Signal(float)
    error = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thread: _DecodeThread | None = None
        self._container = None
        self._vstream = None
        self._astream = None
        self._out = None
        self._pa = None
        self._path = None
        self.volume = 0.8
        self.muted = False
        self.state = "stopped"
        self.duration = 0.0
        self._timer = None

    @property
    def path(self):
        return self._path

    @property
    def state_name(self) -> str:
        return self.state

    # --- media ------------------------------------------------------------
    def load(self, path) -> bool:
        import av

        self.stop()
        try:
            container = av.open(str(path))
        except Exception:  # noqa: BLE001
            self.error.emit(tr("打不开这个录像文件"))
            return False
        try:
            vstream = container.streams.video[0]
            vstream.thread_type = "AUTO"
        except IndexError:
            container.close()
            self.error.emit(tr("录像里没有画面"))
            return False
        try:
            astream = container.streams.audio[0]
        except IndexError:
            astream = None
        duration = 0.0
        if container.duration:
            duration = float(container.duration) / av.time_base
        if not 0.0 < duration < 36000.0:
            duration = 0.0
        if not duration:
            for stream in (vstream, astream):
                if stream is not None and stream.duration and stream.time_base:
                    duration = float(stream.duration * stream.time_base)
                    break
        self._container = container
        self._vstream = vstream
        self._astream = astream
        self._out = self._open_output(astream)
        self._path = str(path)
        self.duration = duration
        self._show_first_frame()
        self.duration_changed.emit(duration)
        return True

    def _open_output(self, astream):
        if astream is None:
            return None
        try:
            import pyaudiowpatch as pa
        except Exception:  # noqa: BLE001
            return None
        rate = int(astream.codec_context.sample_rate or 48000)
        channels = max(1, int(astream.codec_context.channels or 2))
        try:
            self._pa = pa.PyAudio()
            return self._pa.open(format=pa.paInt16, channels=channels, rate=rate,
                                 output=True, frames_per_buffer=1024)
        except Exception:
            self._pa = None
            return None

    def _show_first_frame(self) -> None:
        import av

        try:
            self._container.seek(0, stream=self._vstream)
            for frame in self._container.decode(video=0):
                array = frame.to_ndarray(format="rgb24")
                image = QImage(array.data, array.shape[1], array.shape[0],
                               array.strides[0], QImage.Format.Format_RGB888).copy()
                self.frame_ready.emit(image, 0.0)
                break
        except Exception:
            pass
        try:
            self._container.seek(0, stream=self._vstream)
        except Exception:
            pass

    # --- transport --------------------------------------------------------
    def play(self, from_seconds: float | None = None) -> None:
        if self._container is None or self._thread is not None:
            return
        start = float(from_seconds or 0.0)
        # Always rewind: the previous run may have consumed the file to EOF.
        try:
            self._container.seek(int(start / self._vstream.time_base),
                                 stream=self._vstream)
        except Exception:
            pass
        thread = _DecodeThread(self._container, self._vstream, self._astream,
                               self._out, start_at=start, parent=self)
        thread.volume = 0.0 if self.muted else self.volume
        thread.frame.connect(self._on_frame)
        thread.clock.connect(self.position_changed.emit)
        thread.ended.connect(self._on_end)
        thread.failed.connect(self.error.emit)
        thread.start()
        self._thread = thread
        self._start_timer()
        self._set_state("playing")

    def _start_timer(self) -> None:
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.setInterval(16)
            self._timer.timeout.connect(self._drain)
        self._timer.start()

    def _drain(self) -> None:
        thread = self._thread
        if thread is None:
            return
        ready = thread.take_frames(thread.playhead)
        if ready:
            image, when = ready[-1]
            self.frame_ready.emit(image, when)

    def _on_frame(self, image: QImage, when: float) -> None:
        pass  # frames reach the GUI through _drain

    def _on_end(self) -> None:
        thread = self._thread
        if thread is not None:
            # show the tail the audio clock never reached
            for image, when in thread.take_frames(1e9):
                self.frame_ready.emit(image, when)
        self._stop_thread()
        self._set_state("stopped")

    def pause(self) -> None:
        if self._thread is not None:
            self._thread.pause.set()
            self._set_state("paused")

    def resume(self) -> None:
        if self._thread is not None:
            self._thread.pause.clear()
            self._set_state("playing")

    def toggle(self) -> None:
        if self.state == "playing":
            self.pause()
        elif self.state == "paused":
            self.resume()
        elif self._container is not None:
            self.play()

    def seek(self, seconds: float) -> None:
        seconds = max(0.0, float(seconds))
        if self.duration:
            seconds = min(seconds, max(0.0, self.duration - 0.05))
        if self._thread is not None:
            self._thread.request_seek(seconds)
            if self.state == "paused":
                self.resume()
        elif self._container is not None:
            self.play(from_seconds=seconds)
        self.position_changed.emit(seconds)

    def set_volume(self, value: float) -> None:
        self.volume = max(0.0, min(1.0, float(value)))
        if self._thread is not None and not self.muted:
            self._thread.volume = self.volume

    def set_muted(self, muted: bool) -> None:
        self.muted = bool(muted)
        if self._thread is not None:
            self._thread.volume = 0.0 if muted else self.volume

    def stop(self) -> None:
        self._stop_thread()
        for closeable in (self._out, self._container):
            try:
                if closeable is not None:
                    closeable.close()
            except Exception:
                pass
        self._out = None
        self._container = None
        self._vstream = None
        self._astream = None
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
        self._path = None
        self.duration = 0.0
        self._set_state("stopped")

    def _stop_thread(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        thread = self._thread
        self._thread = None
        if thread is None:
            return
        thread.request_stop()
        thread.wait(3000)
        thread.deleteLater()

    def _set_state(self, state: str) -> None:
        self.state = state
        self.state_changed.emit(state)
