from __future__ import annotations

import csv
import json
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal

import acr_data
import acr_telemetry
from acr_i18n import tr


class AutoRecorder(QThread):
    live = Signal(dict)
    finished_run = Signal(str, float)
    connection = Signal(bool)
    video_event = Signal(dict)

    def __init__(self, out_dir: Path):
        super().__init__()
        self.out_dir = Path(out_dir)
        self._stop = False
        self._auto = True
        self._record = None
        self.video_dir = self.out_dir / "videos"
        self._video_enabled = True
        self._video_quality = {"fps": 60, "width": 1920, "height": 1080,
                               "bitrate_mbps": 8.0}
        self._capture_window = None
        self._recorder = None

    def set_auto(self, enabled: bool) -> None:
        self._auto = bool(enabled)

    def set_video(self, enabled: bool = None, window: str = None,
                  **quality) -> None:
        if enabled is not None:
            self._video_enabled = bool(enabled)
        if window is not None:
            self._capture_window = window or None
        for key in ("fps", "width", "height", "bitrate_mbps"):
            if key in quality:
                self._video_quality[key] = quality[key]

    def video_settings(self) -> dict:
        return {"enabled": self._video_enabled,
                "window": self._capture_window, **self._video_quality}

    def is_recording(self) -> bool:
        return self._record is not None

    def stop(self) -> None:
        self._stop = True
        self.wait(4000)
        if self._recorder is not None:
            try:
                self._recorder.stop()
            except Exception:
                pass
            self._recorder = None

    def _emit(
        self,
        state: str,
        message: str,
        stage_time: float = 0.0,
        speed: float = 0.0,
        gear: int = 0,
        gas: float = 0.0,
        brake: float = 0.0,
        rows: int = 0,
    ) -> None:
        self.live.emit(
            {
                "state": state,
                "message": message,
                "stage_time": stage_time,
                "speed": speed,
                "gear": gear,
                "gas": gas,
                "brake": brake,
                "rows": rows,
            }
        )

    def run(self) -> None:
        while not self._stop:
            physics = graphics = static = None
            try:
                physics = acr_telemetry.SharedMemory(r"Local\acpmf_physics")
                graphics = acr_telemetry.SharedMemory(r"Local\acpmf_graphics")
                try:
                    static = acr_telemetry.SharedMemory(r"Local\acpmf_static")
                except OSError:
                    static = None
                self.connection.emit(True)
                self._connected_loop(physics, graphics, static)
            except OSError:
                self._finish("disconnected", emit=False)
                self.connection.emit(False)
                self._emit("waiting", tr("等待 AC Rally …"))
                time.sleep(1.0)
            except Exception:
                self._finish("error", emit=False)
                self.connection.emit(False)
                self._emit("waiting", tr("等待 AC Rally …"))
                time.sleep(1.0)
            finally:
                self._finish("closed", emit=False)
                if graphics is not None:
                    graphics.close()
                if static is not None:
                    static.close()
                if physics is not None:
                    physics.close()

    def _initial_stage_time(self, graphics) -> float:
        g = acr_telemetry.parse_structure(
            acr_telemetry.Graphics, graphics.read_stable()
        )
        return acr_data.parse_time(acr_telemetry.as_text(g.current_time)) or 0.0

    def _connected_loop(self, physics, graphics, static) -> None:
        try:
            initial_stage = self._initial_stage_time(graphics)
        except Exception:
            initial_stage = 0.0
        waiting_for_next = initial_stage > 2.0
        if waiting_for_next:
            self._emit("waiting", tr("检测到赛段进行中 · 等待下一次"))
        else:
            self._emit("armed", tr("已连接 · 进入赛段自动录制"))

        last_pid = None
        last_live = 0.0
        last_stage = None
        last_change = time.perf_counter()

        while not self._stop:
            raw = physics.read_stable()
            pid = int.from_bytes(raw[:4], "little", signed=True)
            if pid == last_pid:
                time.sleep(0.001)
                continue
            last_pid = pid
            p = acr_telemetry.parse_structure(acr_telemetry.Physics, raw)
            g = acr_telemetry.parse_structure(
                acr_telemetry.Graphics, graphics.read_stable()
            )
            stage = acr_data.parse_time(acr_telemetry.as_text(g.current_time)) or 0.0
            now = time.perf_counter()

            if last_stage is None or stage > last_stage + 0.0005:
                last_stage = stage
                last_change = now

            if self._record is not None and not self._auto:
                self._finish("auto off", emit=False)
                waiting_for_next = True
                self._emit("waiting", tr("自动录制已关闭"))

            if waiting_for_next:
                if stage < 0.5:
                    waiting_for_next = False
                    last_stage = stage
                    last_change = now
                    if self._auto:
                        self._emit("armed", tr("已连接 · 进入赛段自动录制"))
                    else:
                        self._emit("waiting", tr("自动录制已关闭"))
            elif self._record is None:
                if self._auto and stage > 0.05:
                    self._start(p, g, static, stage)
            else:
                self._write(p, g, stage)
                if stage < 0.5 and self._record and self._record["last_stage"] > 2.0:
                    self._finish("stage reset", discard=True, emit=False)
                    last_stage = stage
                    last_change = now
                    self._emit("armed", tr("赛段重置 · 等待下一次"))
                elif now - last_change > 3.0 and p.speed_kmh < 2.0:
                    duration = self._record["last_stage"] if self._record else stage
                    self._finish("finish")
                    waiting_for_next = True
                    self._emit(
                        "saved",
                        tr("已保存 {time} · 分析更新中…").format(
                            time=acr_data.format_time(duration)),
                        duration,
                        p.speed_kmh,
                        p.gear,
                        p.gas * 100.0,
                        p.brake * 100.0,
                    )

            if now - last_live >= 0.1:
                last_live = now
                if self._record is not None:
                    record = self._record
                    self._emit(
                        "recording",
                        tr("录制中"),
                        stage,
                        p.speed_kmh,
                        p.gear,
                        p.gas * 100.0,
                        p.brake * 100.0,
                        record["rows"],
                    )
                elif not self._auto:
                    self._emit("waiting", tr("自动录制已关闭"), stage)
                elif waiting_for_next:
                    self._emit("waiting", tr("等待下一次赛段"), stage)
                else:
                    self._emit(
                        "armed", tr("已连接 · 进入赛段自动录制"), stage
                    )
            time.sleep(0.001)

    def _start(self, p, g, static, stage: float) -> None:
        static_owned = False
        if static is None:
            try:
                static = acr_telemetry.SharedMemory(r"Local\acpmf_static")
                static_owned = True
            except OSError:
                static = None
        self.out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.out_dir / f"acr_telemetry_{stamp}.csv"
        suffix = 1
        while path.exists():
            path = self.out_dir / f"acr_telemetry_{stamp}_{suffix}.csv"
            suffix += 1
        fh = path.open("w", newline="", encoding="utf-8")
        writer = csv.DictWriter(
            fh, fieldnames=acr_telemetry.COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        self._record = {
            "fh": fh,
            "writer": writer,
            "path": path,
            "rows": 0,
            "last_stage": stage,
            "last_flush": time.perf_counter(),
            "static": static,
            "static_owned": static_owned,
            "started": datetime.now().isoformat(timespec="seconds"),
        }
        self._write(p, g, stage)
        self._video_start(path, stage)
        self._emit(
            "recording",
            tr("录制中"),
            stage,
            p.speed_kmh,
            p.gear,
            p.gas * 100.0,
            p.brake * 100.0,
            1,
        )

    def _write(self, p, g, stage: float) -> None:
        record = self._record
        if record is None:
            return
        wall = datetime.now().isoformat(timespec="milliseconds")
        t_ms = stage * 1000.0
        dt_ms = (
            (stage - record["last_stage"]) * 1000.0 if record["rows"] else 0.0
        )
        row = acr_telemetry.make_row(p, g, wall, t_ms, dt_ms)
        record["writer"].writerow(row)
        record["rows"] += 1
        record["last_stage"] = stage
        if time.perf_counter() - record["last_flush"] >= 1.0:
            record["fh"].flush()
            record["last_flush"] = time.perf_counter()

    def _video_start(self, csv_path: Path, stage: float) -> None:
        """Start the paired screen recording. Telemetry never depends on it."""
        record = self._record
        record["video"] = None
        record["video_offset"] = 0.0
        self._recorder = None
        if not self._video_enabled:
            return
        try:
            import acr_video

            self.video_dir.mkdir(parents=True, exist_ok=True)
            out = self.video_dir / f"{csv_path.stem}.mp4"
            recorder = acr_video.VideoRecorder(**self._video_quality)
            hwnd = None
            if self._capture_window:
                hit = acr_video.find_window((self._capture_window,))
                if hit is None:
                    raise RuntimeError(tr("找不到窗口「{title}」").format(
                        title=self._capture_window))
                hwnd = hit[0]
            if not recorder.start(out, hwnd=hwnd):
                raise RuntimeError(tr("录像启动失败"))
            self._recorder = recorder
            record["video"] = out.name
            record["video_offset"] = float(stage)
            self.video_event.emit({
                "state": "recording",
                "path": str(out),
                "target": recorder.target[1] if recorder.target else None,
            })
        except Exception as exc:  # noqa: BLE001
            self._recorder = None
            self.video_event.emit({
                "state": "error",
                "error": f"{type(exc).__name__}: {exc}",
            })

    def _video_stop(self, discard: bool = False) -> dict:
        recorder, self._recorder = self._recorder, None
        if recorder is None:
            return {}
        try:
            result = recorder.stop()
        except Exception as exc:  # noqa: BLE001
            result = dict(recorder.last_result or {})
            result["error"] = f"{type(exc).__name__}: {exc}"
        path = result.get("path")
        if discard and path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
            result["discarded"] = True
        self.video_event.emit({
            "state": "idle",
            "seconds": result.get("seconds"),
            "mb": result.get("mb"),
            "error": result.get("error"),
            "discarded": bool(result.get("discarded")),
        })
        return result

    def _close_record_static(self, record) -> None:
        if record.get("static_owned") and record.get("static") is not None:
            try:
                record["static"].close()
            except Exception:
                pass
            record["static"] = None

    def _finish(self, reason: str, discard: bool = False, emit: bool = True) -> None:
        record = self._record
        if record is None:
            return
        self._record = None
        try:
            record["fh"].flush()
            record["fh"].close()
        except Exception:
            pass
        duration = float(record["last_stage"])
        video = self._video_stop(discard=discard)
        if discard:
            self._close_record_static(record)
            try:
                record["path"].unlink(missing_ok=True)
                record["path"].with_suffix(".meta.json").unlink(missing_ok=True)
            except Exception:
                pass
            return
        meta = {
            "stage_time": duration,
            "rows": record["rows"],
            "csv": record["path"].name,
            "started": record["started"],
            "finished": datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "incomplete": reason != "finish",
        }
        if record.get("video") and not video.get("error"):
            meta.update({
                "video": record["video"],
                "video_offset": round(float(record.get("video_offset", 0.0)), 3),
                "video_seconds": video.get("seconds"),
                "video_fps": self._video_quality["fps"],
                "video_size": f'{self._video_quality["width"]}x{self._video_quality["height"]}',
                "video_mb": video.get("mb"),
            })
        elif record.get("video"):
            meta["video_error"] = video.get("error")
        try:
            if record["static"] is not None:
                static_info = acr_telemetry.parse_structure(
                    acr_telemetry.StaticInfo, record["static"].read()
                )
                meta.update(
                    acr_telemetry.static_metadata(static_info)
                )
        except Exception:
            pass
        try:
            record["path"].with_suffix(".meta.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass
        self._close_record_static(record)
        if emit and duration >= 5.0 and record["rows"] > 100:
            self.finished_run.emit(str(record["path"]), duration)
