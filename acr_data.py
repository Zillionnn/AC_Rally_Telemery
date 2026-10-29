from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np


def app_dir() -> Path:
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT = app_dir()
TELEMETRY_DIR = ROOT / "telemetry"
WHEELS = ("FL", "FR", "RL", "RR")
KELVIN_OFFSET = 273.15
TRACE_HZ = 20.0
DELTA_STEP_M = 5.0
IMPACT_G = 30.0
MAJOR_IMPACT_G = 80.0
# bump when parsing or run-building changes, so old caches are ignored
CACHE_VERSION = 1
CACHE_DIR = ".acr_cache"
TRACE_KEYS = (
    "x", "t", "speed", "gas", "brake", "gear", "rpm", "steer",
    "agx", "agy", "agz", "yaw", "vx", "vy", "vz",
)
TRACE_LISTS = ("tt", "press", "btemp")

COLUMNS = (
    "packet_id",
    "current_time_str",
    "distance_traveled",
    "speed_kmh",
    "gas",
    "brake",
    "gear",
    "rpms",
    "steer_angle",
    "acc_g_x",
    "acc_g_y",
    "acc_g_z",
    "velocity_x",
    "velocity_y",
    "velocity_z",
    "yaw_rate",
    "tyre_core_temp_fl",
    "tyre_core_temp_fr",
    "tyre_core_temp_rl",
    "tyre_core_temp_rr",
    "tyre_pressure_fl",
    "tyre_pressure_fr",
    "tyre_pressure_rl",
    "tyre_pressure_rr",
    "brake_temp_fl",
    "brake_temp_fr",
    "brake_temp_rl",
    "brake_temp_rr",
)


@dataclass(slots=True)
class Row:
    pid: int
    t: float
    dist: float
    speed: float
    gas: float
    brake: float
    gear: int
    rpm: int
    steer: float
    agx: float
    agy: float
    agz: float
    yaw: float
    tt: tuple[float, float, float, float]
    press: tuple[float, float, float, float]
    btemp: tuple[float, float, float, float]
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0


@dataclass
class Segment:
    rows: list[Row]
    min_t: float
    max_t: float
    min_pid: int
    max_pid: int
    mtime: float
    name: str


@dataclass
class Run:
    id: str
    label: str
    started: str
    source_files: list[str]
    summary: dict
    traces: dict
    full_x: np.ndarray
    full_t: np.ndarray
    incidents: list[dict]
    meta: dict


def parse_time(text: str) -> float | None:
    try:
        parts = text.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except (AttributeError, ValueError):
        return None
    return None


def format_time(seconds: float) -> str:
    minutes, rest = divmod(max(0.0, float(seconds)), 60.0)
    hours, minutes = divmod(int(minutes), 60)
    if hours:
        return f"{hours}:{minutes:02d}:{rest:06.3f}"
    return f"{minutes}:{rest:06.3f}"


def _f(row: list[str], index: int) -> float:
    if index < 0 or index >= len(row):
        return 0.0
    try:
        return float(row[index])
    except ValueError:
        return 0.0


def _i(row: list[str], index: int) -> int:
    return int(_f(row, index))


def _celsius(value: float) -> float:
    return value - KELVIN_OFFSET if value > 200.0 else float("nan")


def _trace_g(value: float) -> float:
    return max(-10.0, min(10.0, value))


def _make_segment(rows: list[Row], path: Path) -> Segment:
    stat = path.stat()
    return Segment(
        rows=rows,
        min_t=min(r.t for r in rows),
        max_t=max(r.t for r in rows),
        min_pid=min(r.pid for r in rows),
        max_pid=max(r.pid for r in rows),
        mtime=stat.st_mtime,
        name=path.name,
    )


def _read_segments(path: Path) -> list[Segment]:
    segments: list[Segment] = []
    current: list[Row] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if not header:
            return segments
        index = {name: header.index(name) if name in header else -1 for name in COLUMNS}
        i_pid = index["packet_id"]
        i_time = index["current_time_str"]
        i_dist = index["distance_traveled"]
        i_speed = index["speed_kmh"]
        i_gas = index["gas"]
        i_brake = index["brake"]
        i_gear = index["gear"]
        i_rpm = index["rpms"]
        i_steer = index["steer_angle"]
        i_agx = index["acc_g_x"]
        i_agy = index["acc_g_y"]
        i_agz = index["acc_g_z"]
        i_vx = index["velocity_x"]
        i_vy = index["velocity_y"]
        i_vz = index["velocity_z"]
        i_yaw = index["yaw_rate"]
        i_tt = [index[f"tyre_core_temp_{w.lower()}"] for w in WHEELS]
        i_press = [index[f"tyre_pressure_{w.lower()}"] for w in WHEELS]
        i_btemp = [index[f"brake_temp_{w.lower()}"] for w in WHEELS]

        for parts in reader:
            t = parse_time(parts[i_time]) if 0 <= i_time < len(parts) else None
            if t is None:
                continue
            row = Row(
                pid=_i(parts, i_pid),
                t=t,
                dist=_f(parts, i_dist),
                speed=_f(parts, i_speed),
                gas=_f(parts, i_gas),
                brake=_f(parts, i_brake),
                gear=_i(parts, i_gear),
                rpm=_i(parts, i_rpm),
                steer=_f(parts, i_steer),
                agx=_f(parts, i_agx),
                agy=_f(parts, i_agy),
                agz=_f(parts, i_agz),
                yaw=_f(parts, i_yaw),
                tt=tuple(_f(parts, i) for i in i_tt),
                press=tuple(_f(parts, i) for i in i_press),
                btemp=tuple(_f(parts, i) for i in i_btemp),
                vx=_f(parts, i_vx),
                vy=_f(parts, i_vy),
                vz=_f(parts, i_vz),
            )
            if current and t < current[-1].t - 1.0:
                segments.append(_make_segment(current, path))
                current = []
            current.append(row)
    if current:
        segments.append(_make_segment(current, path))
    return segments


def _source_started(sources: list[str]) -> datetime | None:
    stamps = []
    for name in sources:
        match = re.search(r"acr_telemetry_(\d{8})_(\d{6})", name)
        if not match:
            continue
        try:
            stamps.append(datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S"))
        except ValueError:
            continue
    return min(stamps) if stamps else None


def _group_segments(segments: list[Segment]) -> list[list[Segment]]:
    groups: list[list[Segment]] = []
    current: list[Segment] = []
    max_t = 0.0
    min_pid = 0
    max_pid = 0
    for seg in sorted(segments, key=lambda s: (s.mtime, s.min_pid)):
        reset = False
        if current:
            reset = (
                (seg.min_t < 5.0 and max_t > 5.0)
                or seg.min_pid < min_pid - 50000
                or (seg.min_t < max_t - 5.0 and seg.min_pid > max_pid + 5000)
            )
        if reset:
            groups.append(current)
            current = []
            max_t = 0.0
            min_pid = 0
            max_pid = 0
        if not current:
            min_pid = seg.min_pid
            max_pid = seg.max_pid
        current.append(seg)
        max_t = max(max_t, seg.max_t)
        max_pid = max(max_pid, seg.max_pid)
    if current:
        groups.append(current)
    return groups


def _detect_incidents(rows: list[Row], start_dist: float) -> list[dict]:
    incidents: list[dict] = []

    for before, after in zip(rows, rows[1:]):
        if after.dist < before.dist - 5.0:
            incidents.append(
                {
                    "kind": "respawn",
                    "t": after.t,
                    "distance": max(0.0, after.dist - start_dist),
                    "major": True,
                    "delta_m": before.dist - after.dist,
                    "detail": f"距离回退 {before.dist - after.dist:.0f}m",
                }
            )

    clusters: list[list[Row]] = []
    current: list[Row] = []
    for row in rows:
        peak = max(abs(row.agx), abs(row.agy), abs(row.agz))
        if peak > IMPACT_G:
            if current and row.t - current[-1].t > 1.0:
                clusters.append(current)
                current = []
            current.append(row)
        elif current and row.t - current[-1].t > 1.0:
            clusters.append(current)
            current = []
    if current:
        clusters.append(current)

    for cluster in clusters:
        peak = max(max(abs(r.agx), abs(r.agy), abs(r.agz)) for r in cluster)
        speed0 = cluster[0].speed
        speed1 = min(r.speed for r in cluster)
        drop = max(0.0, speed0 - speed1)
        if peak < 50.0 and drop < 20.0:
            continue
        incidents.append(
            {
                "kind": "impact",
                "t": cluster[0].t,
                "distance": max(0.0, cluster[0].dist - start_dist),
                "major": peak >= MAJOR_IMPACT_G or drop >= 30.0,
                "peak": peak,
                "speed0": speed0,
                "speed1": speed1,
                "detail": f"峰值 {peak:.0f}G · {speed0:.0f}→{speed1:.0f} km/h",
            }
        )

    stops: list[list[Row]] = []
    current = []
    for row in rows:
        if row.speed < 1.0:
            if current and row.t - current[-1].t > 0.5:
                stops.append(current)
                current = []
            current.append(row)
        elif current and row.t - current[-1].t > 0.5:
            stops.append(current)
            current = []
    if current:
        stops.append(current)
    for stop in stops:
        duration = stop[-1].t - stop[0].t
        if duration < 0.5:
            continue
        incidents.append(
            {
                "kind": "stop",
                "t": stop[0].t,
                "distance": max(0.0, stop[0].dist - start_dist),
                "major": duration >= 1.0,
                "duration": duration,
                "detail": f"静止 {duration:.1f}s",
            }
        )

    return sorted(incidents, key=lambda item: (item["t"], item["kind"]))


def _build_run(segments: list[Segment], number: int) -> Run | None:
    merged: list[Row] = []
    seen: set[tuple[int, float, float]] = set()
    for seg in segments:
        for row in seg.rows:
            key = (row.pid, round(row.t, 3), round(row.dist, 2))
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
    merged.sort(key=lambda r: r.pid)

    first = next((i for i, row in enumerate(merged) if row.t > 0.01), None)
    if first is None:
        return None
    max_t = max(row.t for row in merged[first:])
    first_max = next(i for i, row in enumerate(merged[first:], start=first) if row.t == max_t)
    rows = merged[first : first_max + 1]
    start_dist = rows[0].dist
    progress = rows[-1].dist - start_dist
    if max_t < 5.0 or progress < 100.0:
        return None

    incidents = _detect_incidents(rows, start_dist)
    sources = sorted({seg.name for seg in segments})
    started_dt = _source_started(sources) or datetime.fromtimestamp(min(seg.mtime for seg in segments))
    started = started_dt.strftime("%m-%d %H:%M")
    label = f"{started} · {format_time(max_t)}"
    run_id = f"run-{rows[0].pid}-{int(max_t * 1000)}"

    full_x: list[float] = []
    full_t: list[float] = []
    trace_x: list[float] = []
    trace_t: list[float] = []
    trace_speed: list[float] = []
    trace_gas: list[float] = []
    trace_brake: list[float] = []
    trace_gear: list[float] = []
    trace_rpm: list[float] = []
    trace_steer: list[float] = []
    trace_agx: list[float] = []
    trace_agy: list[float] = []
    trace_agz: list[float] = []
    trace_yaw: list[float] = []
    trace_vx: list[float] = []
    trace_vy: list[float] = []
    trace_vz: list[float] = []
    trace_tt = [[] for _ in WHEELS]
    trace_press = [[] for _ in WHEELS]
    trace_btemp = [[] for _ in WHEELS]
    max_progress = -1.0
    last_trace_t = -1e9
    for row in rows:
        point = row.dist - start_dist
        if point <= max_progress + 0.01:
            continue
        max_progress = point
        full_x.append(point)
        full_t.append(row.t)
        if row.t - last_trace_t >= 1.0 / TRACE_HZ or point >= progress - 0.01:
            last_trace_t = row.t
            trace_x.append(point)
            trace_t.append(row.t)
            trace_speed.append(row.speed)
            trace_gas.append(row.gas * 100.0)
            trace_brake.append(row.brake * 100.0)
            trace_gear.append(float(row.gear))
            trace_rpm.append(float(row.rpm))
            trace_steer.append(row.steer * 100.0)
            trace_agx.append(_trace_g(row.agx))
            trace_agy.append(_trace_g(row.agy))
            trace_agz.append(_trace_g(row.agz))
            trace_yaw.append(row.yaw)
            trace_vx.append(row.vx)
            trace_vy.append(row.vy)
            trace_vz.append(row.vz)
            for i in range(4):
                trace_tt[i].append(_celsius(row.tt[i]))
                trace_press[i].append(row.press[i])
                trace_btemp[i].append(_celsius(row.btemp[i]))

    if not trace_x:
        return None

    traces = {
        "x": np.asarray(trace_x, dtype=np.float32),
        "t": np.asarray(trace_t, dtype=np.float32),
        "speed": np.asarray(trace_speed, dtype=np.float32),
        "gas": np.asarray(trace_gas, dtype=np.float32),
        "brake": np.asarray(trace_brake, dtype=np.float32),
        "gear": np.asarray(trace_gear, dtype=np.float32),
        "rpm": np.asarray(trace_rpm, dtype=np.float32),
        "steer": np.asarray(trace_steer, dtype=np.float32),
        "agx": np.asarray(trace_agx, dtype=np.float32),
        "agy": np.asarray(trace_agy, dtype=np.float32),
        "agz": np.asarray(trace_agz, dtype=np.float32),
        "yaw": np.asarray(trace_yaw, dtype=np.float32),
        "vx": np.asarray(trace_vx, dtype=np.float32),
        "vy": np.asarray(trace_vy, dtype=np.float32),
        "vz": np.asarray(trace_vz, dtype=np.float32),
        "tt": [np.asarray(v, dtype=np.float32) for v in trace_tt],
        "press": [np.asarray(v, dtype=np.float32) for v in trace_press],
        "btemp": [np.asarray(v, dtype=np.float32) for v in trace_btemp],
    }
    full_x_arr = np.asarray(full_x, dtype=np.float64)
    full_t_arr = np.asarray(full_t, dtype=np.float64)

    count = len(rows)
    rate = (count - 1) / (rows[-1].t - rows[0].t) if rows[-1].t > rows[0].t else 333.333
    speeds = np.asarray([r.speed for r in rows], dtype=np.float32)
    g_values = np.asarray(
        [max(abs(r.agx), abs(r.agy), abs(r.agz)) for r in rows], dtype=np.float32
    )
    temp_values = [
        _celsius(r.tt[i])
        for r in rows
        for i in range(4)
        if r.tt[i] > 200.0
    ]
    pressure_values = [r.press[i] for r in rows for i in range(4) if r.press[i] > 0]
    brake_values = [
        _celsius(r.btemp[i])
        for r in rows
        for i in range(4)
        if r.btemp[i] > 200.0
    ]
    gears = Counter(r.gear for r in rows)
    gear_pct = {int(g): round(c / count * 100.0, 1) for g, c in sorted(gears.items())}
    summary = {
        "time": max_t,
        "distance": progress,
        "start_distance": start_dist,
        "end_distance": rows[-1].dist,
        "avg_speed": progress / max_t * 3.6 if max_t else 0.0,
        "max_speed": float(speeds.max()) if len(speeds) else 0.0,
        "full_pct": sum(1 for r in rows if r.gas >= 0.95) / count * 100.0,
        "brake_pct": sum(1 for r in rows if r.brake >= 0.2) / count * 100.0,
        "coast_pct": sum(
            1 for r in rows if r.gas < 0.05 and r.brake < 0.05 and r.speed > 5.0
        )
        / count
        * 100.0,
        "stationary_s": sum(1 for r in rows if r.speed < 1.0) / rate,
        "slow20_s": sum(1 for r in rows if r.speed < 20.0) / rate,
        "samples": count,
        "rate": rate,
        "max_g": float(g_values.max()) if len(g_values) else 0.0,
        "g99": float(np.percentile(g_values, 99.0)) if len(g_values) else 0.0,
        "max_yaw": max(abs(r.yaw) for r in rows),
        "gears": gear_pct,
        "temp_avg": float(np.mean(temp_values)) if temp_values else 0.0,
        "temp_max": float(np.max(temp_values)) if temp_values else 0.0,
        "pressure_avg": float(np.mean(pressure_values)) if pressure_values else 0.0,
        "brake_max": float(np.max(brake_values)) if brake_values else 0.0,
        "incidents": len(incidents),
        "clean": not incidents,
        "files": sources,
    }
    return Run(
        id=run_id,
        label=label,
        started=started,
        source_files=sources,
        summary=summary,
        traces=traces,
        full_x=full_x_arr,
        full_t=full_t_arr,
        incidents=incidents,
        meta={},
    )


def _cache_root(directory: Path) -> Path:
    return directory / CACHE_DIR


def _write_json(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:  # noqa: BLE001
        pass


def _read_file_index(directory: Path) -> dict[str, dict]:
    try:
        data = json.loads(
            (_cache_root(directory) / "files.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    if data.get("version") != CACHE_VERSION:
        return {}
    files = data.get("files")
    return files if isinstance(files, dict) else {}


def _segment_info(seg: Segment) -> dict:
    return {"min_t": seg.min_t, "max_t": seg.max_t,
            "min_pid": seg.min_pid, "max_pid": seg.max_pid}


def _group_signature(group: list[Segment], files: dict[str, dict]) -> str:
    parts = [str(CACHE_VERSION)]
    for info in group:
        entry = files.get(info.name, {})
        parts.append(
            f"{info.name}:{entry.get('size', 0)}:{entry.get('mtime_ns', 0)}:"
            f"{info.min_pid}:{info.max_pid}:{info.min_t!r}:{info.max_t!r}")
    return "|".join(parts)


def _run_cache_path(directory: Path, signature: str) -> Path:
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:20]
    return _cache_root(directory) / "runs" / f"{digest}.npz"


def _save_run_cache(directory: Path, signature: str, run: Run) -> None:
    path = _run_cache_path(directory, signature)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = {
            "v": CACHE_VERSION,
            "id": run.id,
            "label": run.label,
            "started": run.started,
            "source_files": run.source_files,
            "summary": run.summary,
            "incidents": run.incidents,
        }
        arrays = {
            "meta": np.asarray(json.dumps(meta, ensure_ascii=False)),
            "full_x": run.full_x,
            "full_t": run.full_t,
        }
        for key in TRACE_KEYS:
            arrays[key] = run.traces[key]
        for key in TRACE_LISTS:
            for i, values in enumerate(run.traces[key]):
                arrays[f"{key}_{i}"] = values
        tmp = path.with_name(path.name[:-4] + ".tmp.npz")
        np.savez(tmp, **arrays)
        os.replace(tmp, path)
    except Exception:  # noqa: BLE001
        pass


def _load_run_cache(directory: Path, signature: str) -> Run | None:
    path = _run_cache_path(directory, signature)
    if not path.exists():
        return None
    try:
        with np.load(path) as data:
            meta = json.loads(str(data["meta"].item()))
            if meta.get("v") != CACHE_VERSION:
                return None
            traces = {key: data[key] for key in TRACE_KEYS}
            for key in TRACE_LISTS:
                traces[key] = [data[f"{key}_{i}"] for i in range(4)]
            return Run(
                id=str(meta["id"]),
                label=str(meta["label"]),
                started=str(meta["started"]),
                source_files=list(meta["source_files"]),
                summary=dict(meta["summary"]),
                traces=traces,
                full_x=data["full_x"],
                full_t=data["full_t"],
                incidents=list(meta["incidents"]),
                meta={},
            )
    except Exception:  # noqa: BLE001
        return None


def load_runs(directory: Path = TELEMETRY_DIR) -> list[Run]:
    directory = Path(directory)
    paths = sorted(directory.glob("*.csv"), key=lambda p: p.stat().st_mtime)
    index = _read_file_index(directory)
    parsed: dict[str, list[Segment]] = {}
    files: dict[str, dict] = {}
    infos: list[Segment] = []
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            continue
        size = int(stat.st_size)
        mtime_ns = int(stat.st_mtime_ns)
        entry = index.get(path.name)
        if entry and entry.get("size") == size and entry.get("mtime_ns") == mtime_ns:
            descs = entry.get("segments") or []
        else:
            try:
                segments = _read_segments(path)
            except Exception:  # noqa: BLE001
                continue
            parsed[path.name] = segments
            descs = [_segment_info(seg) for seg in segments]
        files[path.name] = {"size": size, "mtime_ns": mtime_ns, "segments": descs}
        for desc in descs:
            infos.append(
                Segment(
                    rows=[],
                    min_t=desc["min_t"],
                    max_t=desc["max_t"],
                    min_pid=desc["min_pid"],
                    max_pid=desc["max_pid"],
                    mtime=stat.st_mtime,
                    name=path.name,
                )
            )

    def rows_for(group: list[Segment]) -> list[Segment]:
        out: list[Segment] = []
        for info in group:
            if info.name not in parsed:
                try:
                    parsed[info.name] = _read_segments(directory / info.name)
                except Exception:  # noqa: BLE001
                    parsed[info.name] = []
            match = next(
                (seg for seg in parsed[info.name]
                 if seg.min_pid == info.min_pid and seg.max_pid == info.max_pid
                 and seg.min_t == info.min_t and seg.max_t == info.max_t),
                None,
            )
            if match is not None:
                out.append(match)
        return out

    runs: list[Run] = []
    for i, group in enumerate(_group_segments(infos)):
        signature = _group_signature(group, files)
        run = _load_run_cache(directory, signature)
        if run is None:
            run = _build_run(rows_for(group), i + 1)
            if run is not None:
                _save_run_cache(directory, signature, run)
        if run is None:
            continue
        for name in run.source_files:
            meta_path = directory / (Path(name).stem + ".meta.json")
            try:
                if meta_path.exists():
                    run.meta.update(json.loads(meta_path.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                pass
        runs.append(run)

    _write_json(_cache_root(directory) / "files.json",
                {"version": CACHE_VERSION, "files": files})
    return runs


def _group_time_zones(bins: list[dict], gain: bool) -> list[dict]:
    groups: list[list[dict]] = []
    current: list[dict] = []
    for item in bins:
        match = item["delta"] < 0 if gain else item["delta"] > 0
        if match:
            if current and item["start"] - current[-1]["end"] > 1.0:
                groups.append(current)
                current = []
            current.append(item)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    zones = []
    for group in groups:
        delta = sum(item["delta"] for item in group)
        if abs(delta) < 0.05:
            continue
        zones.append(
            {
                "start": group[0]["start"],
                "end": group[-1]["end"],
                "delta": delta,
                "current": sum(item["current"] for item in group),
                "reference": sum(item["reference"] for item in group),
            }
        )
    zones.sort(key=lambda z: z["delta"], reverse=not gain)
    return zones[:5]


def _segment_analysis(current: Run, reference: Run) -> dict:
    limit = min(current.full_x[-1], reference.full_x[-1]) if len(current.full_x) and len(reference.full_x) else 0.0
    if limit <= 0:
        return {
            "theoretical_time": 0.0,
            "potential_gain": 0.0,
            "top_gains": [],
            "top_losses": [],
        }
    step = 100.0
    edges = np.arange(0.0, limit + step * 0.5, step)
    if edges[-1] < limit - 1e-6:
        edges = np.append(edges, limit)
    if len(edges) < 2:
        return {
            "theoretical_time": 0.0,
            "potential_gain": 0.0,
            "top_gains": [],
            "top_losses": [],
        }
    exclusions = []
    for incident in reference.incidents:
        radius = 200.0 if incident["kind"] == "impact" else 150.0
        exclusions.append(
            (incident["distance"] - radius, incident["distance"] + radius)
        )

    def reference_is_clean(start: float, end: float) -> bool:
        midpoint = (start + end) * 0.5
        return not any(lo <= midpoint <= hi for lo, hi in exclusions)

    current_t = np.interp(edges, current.full_x, current.full_t)
    reference_t = np.interp(edges, reference.full_x, reference.full_t)
    current_bins = np.diff(current_t)
    reference_bins = np.diff(reference_t)
    bins = []
    for i in range(len(current_bins)):
        start = float(edges[i])
        end = float(edges[i + 1])
        clean = reference_is_clean(start, end)
        bins.append(
            {
                "start": start,
                "end": end,
                "current": float(current_bins[i]),
                "reference": float(reference_bins[i]),
                "delta": float(current_bins[i] - reference_bins[i]),
                "reference_clean": clean,
            }
        )

    best_bins = np.asarray(
        [
            min(current_bins[i], reference_bins[i])
            if bins[i]["reference_clean"]
            else current_bins[i]
            for i in range(len(bins))
        ]
    )
    theoretical = float(np.sum(best_bins))
    potential = max(0.0, float(current.summary["time"] - theoretical))
    clean_bins = [
        {**item, "delta": item["delta"] if item["reference_clean"] else 0.0}
        for item in bins
    ]
    return {
        "theoretical_time": theoretical,
        "potential_gain": potential,
        "top_gains": _group_time_zones(clean_bins, True),
        "top_losses": _group_time_zones(clean_bins, False),
    }


def _braking_zones(current: Run, reference: Run) -> list[dict]:
    trace = current.traces
    ref_trace = reference.traces
    if not len(trace["x"]):
        return []
    brake = np.asarray(trace["brake"])
    indices = np.where(brake >= 20.0)[0]
    if not len(indices):
        return []

    groups: list[list[int]] = []
    group: list[int] = []
    for idx in indices:
        if group and trace["t"][idx] - trace["t"][group[-1]] > 0.35:
            groups.append(group)
            group = []
        group.append(int(idx))
    if group:
        groups.append(group)

    exclusions = []
    for incident in reference.incidents:
        radius = 200.0 if incident["kind"] == "impact" else 150.0
        exclusions.append(
            (incident["distance"] - radius, incident["distance"] + radius)
        )

    zones = []
    max_distance = min(current.full_x[-1], reference.full_x[-1])
    for group in groups:
        start = float(trace["x"][group[0]])
        brake_end = float(trace["x"][group[-1]])
        if brake_end - start < 3.0:
            continue
        if trace["t"][group[-1]] - trace["t"][group[0]] < 0.2:
            continue
        end = min(brake_end + 80.0, max_distance)
        current_t0 = float(np.interp(start, current.full_x, current.full_t))
        current_t1 = float(np.interp(end, current.full_x, current.full_t))
        reference_t0 = float(np.interp(start, reference.full_x, reference.full_t))
        reference_t1 = float(np.interp(end, reference.full_x, reference.full_t))
        current_entry = float(np.interp(start, trace["x"], trace["speed"]))
        reference_entry = float(np.interp(start, ref_trace["x"], ref_trace["speed"]))
        current_exit = float(np.interp(end, trace["x"], trace["speed"]))
        reference_exit = float(np.interp(end, ref_trace["x"], ref_trace["speed"]))
        current_mask = (trace["x"] >= start) & (trace["x"] <= end)
        reference_mask = (ref_trace["x"] >= start) & (ref_trace["x"] <= end)
        current_min = (
            float(np.min(trace["speed"][current_mask]))
            if current_mask.any()
            else current_entry
        )
        reference_min = (
            float(np.min(ref_trace["speed"][reference_mask]))
            if reference_mask.any()
            else reference_entry
        )
        midpoint = (start + brake_end) * 0.5
        near_incident = any(lo <= midpoint <= hi for lo, hi in exclusions)
        zones.append(
            {
                "start": start,
                "end": end,
                "brake_end": brake_end,
                "delta": (current_t1 - current_t0) - (reference_t1 - reference_t0),
                "current_entry": current_entry,
                "reference_entry": reference_entry,
                "current_min": current_min,
                "reference_min": reference_min,
                "current_exit": current_exit,
                "reference_exit": reference_exit,
                "reference_incident": near_incident,
            }
        )
    zones.sort(key=lambda z: (z["reference_incident"], -z["delta"]))
    return zones[:8]


def compare_runs(current: Run, reference: Run) -> dict:
    limit = min(current.full_x[-1], reference.full_x[-1]) if len(current.full_x) and len(reference.full_x) else 0.0
    if limit <= 0:
        return {
            "distance": np.asarray([]),
            "delta": np.asarray([]),
            "splits": [],
            "analysis": {
                "theoretical_time": 0.0,
                "potential_gain": 0.0,
                "top_gains": [],
                "top_losses": [],
                "braking_zones": [],
            },
        }
    grid = np.arange(0.0, limit + 0.001, DELTA_STEP_M)
    if grid[-1] < limit:
        grid = np.append(grid, limit)
    current_t = np.interp(grid, current.full_x, current.full_t)
    reference_t = np.interp(grid, reference.full_x, reference.full_t)
    delta = current_t - reference_t

    splits = []
    points = list(np.arange(1000.0, limit, 1000.0))
    if not points or points[-1] < limit - 1.0:
        points.append(limit)
    for point in points:
        finish = point >= limit - 1e-6
        if finish:
            ref_t = reference.summary["time"]
            cur_t = current.summary["time"]
        else:
            ref_t = float(np.interp(point, reference.full_x, reference.full_t))
            cur_t = float(np.interp(point, current.full_x, current.full_t))
        splits.append(
            {
                "distance": float(point),
                "reference": ref_t,
                "current": cur_t,
                "delta": cur_t - ref_t,
                "finish": finish,
            }
        )
    analysis = _segment_analysis(current, reference)
    analysis["braking_zones"] = _braking_zones(current, reference)
    return {
        "distance": grid,
        "delta": delta,
        "splits": splits,
        "total_delta": current.summary["time"] - reference.summary["time"],
        "analysis": analysis,
    }
