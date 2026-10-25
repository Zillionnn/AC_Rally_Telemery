#!/usr/bin/env python3
"""Read Assetto Corsa Rally's AC-compatible shared memory telemetry.

Examples:
    python acr_telemetry.py --probe
    python acr_telemetry.py --duration 60
    python acr_telemetry.py --out telemetry
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import json
import sys
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from typing import Any

IS_WINDOWS = sys.platform == "win32"

FILE_MAP_READ = 0x0004
WHEELS = ("fl", "fr", "rl", "rr")

float2 = ctypes.c_float * 2
float3 = ctypes.c_float * 3
float4 = ctypes.c_float * 4
float5 = ctypes.c_float * 5
float4x3 = (ctypes.c_float * 3) * 4
wchar15 = ctypes.c_wchar * 15
wchar33 = ctypes.c_wchar * 33


class Physics(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packet_id", ctypes.c_int),
        ("gas", ctypes.c_float),
        ("brake", ctypes.c_float),
        ("fuel", ctypes.c_float),
        ("gear", ctypes.c_int),
        ("rpms", ctypes.c_int),
        ("steer_angle", ctypes.c_float),
        ("speed_kmh", ctypes.c_float),
        ("velocity", float3),
        ("acc_g", float3),
        ("wheel_slip", float4),
        ("wheel_load", float4),
        ("wheels_pressure", float4),
        ("wheel_angular_speed", float4),
        ("tyre_wear", float4),
        ("tyre_dirty", float4),
        ("tyre_core_temp", float4),
        ("camber_rad", float4),
        ("suspension_travel", float4),
        ("drs", ctypes.c_float),
        ("tc", ctypes.c_float),
        ("heading", ctypes.c_float),
        ("pitch", ctypes.c_float),
        ("roll", ctypes.c_float),
        ("cg_height", ctypes.c_float),
        ("car_damage", float5),
        ("number_of_tyres_out", ctypes.c_int),
        ("pit_limiter_on", ctypes.c_int),
        ("abs", ctypes.c_float),
        ("kers_charge", ctypes.c_float),
        ("kers_input", ctypes.c_float),
        ("auto_shifter_on", ctypes.c_int),
        ("ride_height", float2),
        ("turbo_boost", ctypes.c_float),
        ("ballast", ctypes.c_float),
        ("air_density", ctypes.c_float),
        ("air_temp", ctypes.c_float),
        ("road_temp", ctypes.c_float),
        ("local_angular_vel", float3),
        ("final_ff", ctypes.c_float),
        ("performance_meter", ctypes.c_float),
        ("engine_brake", ctypes.c_int),
        ("ers_recovery_level", ctypes.c_int),
        ("ers_power_level", ctypes.c_int),
        ("ers_heat_charging", ctypes.c_int),
        ("ers_is_charging", ctypes.c_int),
        ("kers_current_kj", ctypes.c_float),
        ("drs_available", ctypes.c_int),
        ("drs_enabled", ctypes.c_int),
        ("brake_temp", float4),
        ("clutch", ctypes.c_float),
        ("tyre_temp_i", float4),
        ("tyre_temp_m", float4),
        ("tyre_temp_o", float4),
        ("is_ai_controlled", ctypes.c_int),
        ("tyre_contact_point", float4x3),
        ("tyre_contact_normal", float4x3),
        ("tyre_contact_heading", float4x3),
        ("brake_bias", ctypes.c_float),
        ("local_velocity", float3),
    ]


class Graphics(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packet_id", ctypes.c_int),
        ("status", ctypes.c_int),
        ("session", ctypes.c_int),
        ("current_time", wchar15),
        ("last_time", wchar15),
        ("best_time", wchar15),
        ("split", wchar15),
        ("completed_laps", ctypes.c_int),
        ("position", ctypes.c_int),
        ("i_current_time", ctypes.c_int),
        ("i_last_time", ctypes.c_int),
        ("i_best_time", ctypes.c_int),
        ("session_time_left", ctypes.c_float),
        ("distance_traveled", ctypes.c_float),
        ("is_in_pit", ctypes.c_int),
        ("current_sector_index", ctypes.c_int),
        ("last_sector_time", ctypes.c_int),
        ("number_of_laps", ctypes.c_int),
        ("tyre_compound", wchar33),
        ("replay_time_multiplier", ctypes.c_float),
        ("normalized_car_position", ctypes.c_float),
        ("car_coordinates", float3),
        ("penalty_time", ctypes.c_float),
        ("flag", ctypes.c_int),
        ("ideal_line_on", ctypes.c_int),
        ("is_in_pit_lane", ctypes.c_int),
        ("surface_grip", ctypes.c_float),
        ("mandatory_pit_done", ctypes.c_int),
        ("wind_speed", ctypes.c_float),
        ("wind_direction", ctypes.c_float),
    ]


class StaticInfo(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("sm_version", wchar15),
        ("ac_version", wchar15),
        ("number_of_sessions", ctypes.c_int),
        ("num_cars", ctypes.c_int),
        ("car_model", wchar33),
        ("track", wchar33),
        ("player_name", wchar33),
        ("player_surname", wchar33),
        ("player_nick", wchar33),
        ("sector_count", ctypes.c_int),
        ("max_torque", ctypes.c_float),
        ("max_power", ctypes.c_float),
        ("max_rpm", ctypes.c_int),
        ("max_fuel", ctypes.c_float),
        ("suspension_max_travel", float4),
        ("tyre_radius", float4),
        ("max_turbo_boost", ctypes.c_float),
        ("deprecated_1", ctypes.c_float),
        ("deprecated_2", ctypes.c_float),
        ("penalties_enabled", ctypes.c_int),
        ("aid_fuel_rate", ctypes.c_float),
        ("aid_tire_rate", ctypes.c_float),
        ("aid_mechanical_damage", ctypes.c_float),
        ("aid_allow_tyre_blankets", ctypes.c_int),
        ("aid_stability", ctypes.c_float),
        ("aid_auto_clutch", ctypes.c_int),
        ("aid_auto_blip", ctypes.c_int),
        ("has_drs", ctypes.c_int),
        ("has_ers", ctypes.c_int),
        ("has_kers", ctypes.c_int),
        ("kers_max_j", ctypes.c_float),
        ("engine_brake_settings_count", ctypes.c_int),
        ("ers_power_controller_count", ctypes.c_int),
        ("track_spline_length", ctypes.c_float),
        ("track_configuration", wchar33),
        ("ers_max_j", ctypes.c_float),
        ("is_timed_race", ctypes.c_int),
        ("has_extra_lap", ctypes.c_int),
        ("car_skin", wchar33),
        ("reversed_grid_positions", ctypes.c_int),
        ("pit_window_start", ctypes.c_int),
        ("pit_window_end", ctypes.c_int),
        ("is_online", ctypes.c_int),
    ]


if IS_WINDOWS:
    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]


    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.OpenFileMappingW.restype = wintypes.HANDLE
    kernel32.MapViewOfFile.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_size_t,
    ]
    kernel32.MapViewOfFile.restype = ctypes.c_void_p
    kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
    kernel32.UnmapViewOfFile.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.VirtualQuery.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(MEMORY_BASIC_INFORMATION),
        ctypes.c_size_t,
    ]
    kernel32.VirtualQuery.restype = ctypes.c_size_t


class SharedMemory:
    def __init__(self, name: str):
        if not IS_WINDOWS:
            raise OSError("Windows is required for named shared memory.")
        self.name = name
        self._handle = kernel32.OpenFileMappingW(FILE_MAP_READ, False, name)
        if not self._handle:
            err = ctypes.get_last_error()
            raise OSError(err, f"OpenFileMappingW({name!r}) failed: {ctypes.FormatError(err)}")
        self._addr = kernel32.MapViewOfFile(self._handle, FILE_MAP_READ, 0, 0, 0)
        if not self._addr:
            err = ctypes.get_last_error()
            kernel32.CloseHandle(self._handle)
            raise OSError(err, f"MapViewOfFile({name!r}) failed: {ctypes.FormatError(err)}")
        info = MEMORY_BASIC_INFORMATION()
        if kernel32.VirtualQuery(self._addr, ctypes.byref(info), ctypes.sizeof(info)):
            self.size = int(info.RegionSize)
        else:
            self.size = 4096

    def read(self) -> bytes:
        return ctypes.string_at(self._addr, self.size)

    def read_stable(self, attempts: int = 2) -> bytes:
        raw = self.read()
        pid = raw[:4]
        for _ in range(attempts - 1):
            next_raw = self.read()
            if next_raw[:4] == pid:
                return next_raw
            raw = next_raw
            pid = raw[:4]
        return raw

    def close(self) -> None:
        if getattr(self, "_addr", None):
            kernel32.UnmapViewOfFile(self._addr)
            self._addr = None
        if getattr(self, "_handle", None):
            kernel32.CloseHandle(self._handle)
            self._handle = None


def parse_structure(structure: type[ctypes.Structure], raw: bytes) -> Any:
    size = ctypes.sizeof(structure)
    if len(raw) < size:
        raise ValueError(f"shared memory page is {len(raw)} bytes, need {size}")
    return structure.from_buffer_copy(raw[:size])


def as_text(value: Any) -> str:
    if isinstance(value, str):
        return value.split("\x00", 1)[0]
    return "".join(value).split("\x00", 1)[0]


def open_optional(name: str) -> SharedMemory | None:
    try:
        return SharedMemory(name)
    except OSError as exc:
        print(f"[!] {name}: {exc}", file=sys.stderr)
        return None


def graphics_values(g: Graphics | None) -> dict[str, Any]:
    if g is None:
        return {
            "gfx_packet_id": 0,
            "gfx_status": 0,
            "gfx_session": 0,
            "completed_laps": 0,
            "position": 0,
            "i_current_time": 0,
            "i_last_time": 0,
            "i_best_time": 0,
            "session_time_left": 0.0,
            "distance_traveled": 0.0,
            "is_in_pit": 0,
            "current_sector_index": 0,
            "last_sector_time": 0,
            "number_of_laps": 0,
            "normalized_car_position": 0.0,
            "car_x": 0.0,
            "car_y": 0.0,
            "car_z": 0.0,
            "flag": 0,
            "is_in_pit_lane": 0,
            "surface_grip": 0.0,
            "tyre_compound": "",
            "current_time_str": "",
            "last_time_str": "",
            "best_time_str": "",
            "split_str": "",
        }
    return {
        "gfx_packet_id": g.packet_id,
        "gfx_status": g.status,
        "gfx_session": g.session,
        "completed_laps": g.completed_laps,
        "position": g.position,
        "i_current_time": g.i_current_time,
        "i_last_time": g.i_last_time,
        "i_best_time": g.i_best_time,
        "session_time_left": round(g.session_time_left, 4),
        "distance_traveled": round(g.distance_traveled, 4),
        "is_in_pit": g.is_in_pit,
        "current_sector_index": g.current_sector_index,
        "last_sector_time": g.last_sector_time,
        "number_of_laps": g.number_of_laps,
        "normalized_car_position": round(g.normalized_car_position, 6),
        "car_x": round(g.car_coordinates[0], 4),
        "car_y": round(g.car_coordinates[1], 4),
        "car_z": round(g.car_coordinates[2], 4),
        "flag": g.flag,
        "is_in_pit_lane": g.is_in_pit_lane,
        "surface_grip": round(g.surface_grip, 4),
        "tyre_compound": as_text(g.tyre_compound),
        "current_time_str": as_text(g.current_time),
        "last_time_str": as_text(g.last_time),
        "best_time_str": as_text(g.best_time),
        "split_str": as_text(g.split),
    }


def make_row(
    p: Physics,
    g: Graphics | None,
    wall_time: str,
    t_ms: float,
    dt_ms: float,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "wall_time": wall_time,
        "t_ms": round(t_ms, 3),
        "dt_ms": round(dt_ms, 3),
        "packet_id": p.packet_id,
        "speed_kmh": round(p.speed_kmh, 4),
        "gas": round(p.gas, 4),
        "brake": round(p.brake, 4),
        "steer_angle": round(p.steer_angle, 5),
        "gear": p.gear,
        "rpms": p.rpms,
        "fuel": round(p.fuel, 4),
        "acc_g_x": round(p.acc_g[0], 4),
        "acc_g_y": round(p.acc_g[1], 4),
        "acc_g_z": round(p.acc_g[2], 4),
        "velocity_x": round(p.velocity[0], 4),
        "velocity_y": round(p.velocity[1], 4),
        "velocity_z": round(p.velocity[2], 4),
        "local_velocity_x": round(p.local_velocity[0], 4),
        "local_velocity_y": round(p.local_velocity[1], 4),
        "local_velocity_z": round(p.local_velocity[2], 4),
        "heading": round(p.heading, 5),
        "pitch": round(p.pitch, 5),
        "roll": round(p.roll, 5),
        "yaw_rate": round(p.local_angular_vel[2], 5),
        "cg_height": round(p.cg_height, 4),
        "brake_bias": round(p.brake_bias, 4),
        "clutch": round(p.clutch, 4),
        "turbo_boost": round(p.turbo_boost, 4),
        "ballast": round(p.ballast, 4),
        "air_density": round(p.air_density, 5),
        "air_temp": round(p.air_temp, 3),
        "road_temp": round(p.road_temp, 3),
        "final_ff": round(p.final_ff, 5),
        "performance_meter": round(p.performance_meter, 5),
        "drs": round(p.drs, 4),
        "tc": round(p.tc, 4),
        "abs": round(p.abs, 4),
        "kers_charge": round(p.kers_charge, 4),
        "kers_input": round(p.kers_input, 4),
        "auto_shifter_on": p.auto_shifter_on,
        "engine_brake": p.engine_brake,
        "is_ai_controlled": p.is_ai_controlled,
        "drs_available": p.drs_available,
        "drs_enabled": p.drs_enabled,
        "number_of_tyres_out": p.number_of_tyres_out,
        "pit_limiter_on": p.pit_limiter_on,
    }
    for i, wheel in enumerate(WHEELS):
        row[f"car_damage_{wheel}"] = round(p.car_damage[i], 4)

    for name, values in (
        ("wheel_slip", p.wheel_slip),
        ("wheel_load", p.wheel_load),
        ("tyre_pressure", p.wheels_pressure),
        ("tyre_core_temp", p.tyre_core_temp),
        ("suspension_travel", p.suspension_travel),
        ("brake_temp", p.brake_temp),
        ("tyre_temp_m", p.tyre_temp_m),
    ):
        for i, wheel in enumerate(WHEELS):
            row[f"{name}_{wheel}"] = round(values[i], 4)

    row.update(graphics_values(g))
    return row


COLUMNS = list(make_row(Physics(), None, "", 0.0, 0.0).keys())


def static_metadata(s: StaticInfo | None) -> dict[str, Any]:
    if s is None:
        return {"present": False}
    return {
        "present": True,
        "sm_version": as_text(s.sm_version),
        "ac_version": as_text(s.ac_version),
        "number_of_sessions": s.number_of_sessions,
        "num_cars": s.num_cars,
        "car_model": as_text(s.car_model),
        "track": as_text(s.track),
        "track_configuration": as_text(s.track_configuration),
        "player_name": as_text(s.player_name),
        "player_nick": as_text(s.player_nick),
        "car_skin": as_text(s.car_skin),
        "sector_count": s.sector_count,
        "max_torque": s.max_torque,
        "max_power": s.max_power,
        "max_rpm": s.max_rpm,
        "max_fuel": s.max_fuel,
        "track_spline_length": s.track_spline_length,
        "is_timed_race": s.is_timed_race,
        "is_online": s.is_online,
    }


def plausibility(p: Physics) -> tuple[bool, list[str]]:
    problems = []
    if not -1 <= p.gear <= 12:
        problems.append(f"gear={p.gear}")
    if not 0 <= p.speed_kmh <= 500:
        problems.append(f"speed_kmh={p.speed_kmh:.2f}")
    if not -0.1 <= p.gas <= 1.1:
        problems.append(f"gas={p.gas:.3f}")
    if not -0.1 <= p.brake <= 1.1:
        problems.append(f"brake={p.brake:.3f}")
    if not 0 <= p.rpms <= 30000:
        problems.append(f"rpms={p.rpms}")
    return not problems, problems


def probe(physics: SharedMemory, graphics: SharedMemory | None, static: SharedMemory | None, seconds: float) -> int:
    print("=== AC Rally shared memory probe ===")
    print(f"physics:  {physics.name}  ok  mapping={physics.size}  struct={ctypes.sizeof(Physics)}")
    print(f"graphics: {'ok' if graphics else 'missing'}")
    print(f"static:   {'ok' if static else 'missing'}")

    static_info = None
    if static is not None:
        static_info = parse_structure(StaticInfo, static.read())
        meta = static_metadata(static_info)
        print(
            "static:   sm={sm_version!r} ac={ac_version!r} car={car_model!r} "
            "track={track!r} config={track_configuration!r}".format(**meta)
        )

    print("\n t_ms    packet  speed   gas    brake   gear  rpm    steer    gfx_time  best_time")
    start = time.perf_counter()
    last_pid = None
    printed = 0
    last_problems: list[str] = []
    while time.perf_counter() - start < seconds:
        p = parse_structure(Physics, physics.read_stable())
        g = parse_structure(Graphics, graphics.read_stable()) if graphics else None
        if p.packet_id != last_pid:
            last_pid = p.packet_id
            ok, last_problems = plausibility(p)
            if printed < 12:
                print(
                    f"{(time.perf_counter() - start) * 1000:8.1f} {p.packet_id:6d} "
                    f"{p.speed_kmh:7.2f} {p.gas:6.3f} {p.brake:6.3f} {p.gear:5d} "
                    f"{p.rpms:6d} {p.steer_angle:8.4f} "
                    f"{(as_text(g.current_time) if g else ''):>8} "
                    f"{(as_text(g.best_time) if g else ''):>9}"
                )
                printed += 1
        time.sleep(0.001)

    if last_pid is None:
        print("\n[!] packetId did not change. Is the game paused or still loading?")
        return 1
    ok, problems = plausibility(parse_structure(Physics, physics.read_stable()))
    if not ok:
        print(f"\n[!] Layout check failed: {', '.join(problems)}")
        print("    AC Rally may use a different shared-memory layout. Do not trust the CSV yet.")
        return 1
    print("\n[+] Layout check passed. You can record with: python acr_telemetry.py --duration 60")
    return 0


def record(
    physics: SharedMemory,
    graphics: SharedMemory | None,
    static: SharedMemory | None,
    out_dir: Path,
    duration: float,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"acr_telemetry_{stamp}.csv"
    meta_path = csv_path.with_suffix(".meta.json")

    static_info = parse_structure(StaticInfo, static.read()) if static else None
    meta = static_metadata(static_info)
    if static_info is not None:
        print(
            f"[+] {meta.get('car_model', '?')} @ {meta.get('track', '?')} "
            f"({meta.get('track_configuration', '')})"
        )

    rows = 0
    dropped = 0
    first_pid = None
    last_pid = None
    last_t_ms = 0.0
    start = time.perf_counter()
    last_flush = start
    last_wall = datetime.now().isoformat(timespec="milliseconds")

    print(f"[+] recording to {csv_path}")
    print("[+] press Ctrl+C to stop")
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        try:
            while True:
                now = time.perf_counter()
                elapsed = now - start
                if duration > 0 and elapsed >= duration:
                    break
                raw = physics.read_stable()
                pid = int.from_bytes(raw[:4], "little", signed=True)
                if pid == last_pid:
                    time.sleep(0.001)
                    continue
                p = parse_structure(Physics, raw)
                g = parse_structure(Graphics, graphics.read_stable()) if graphics else None
                t_ms = elapsed * 1000.0
                dt_ms = t_ms - last_t_ms if rows else 0.0
                if first_pid is None:
                    first_pid = p.packet_id
                elif p.packet_id > last_pid:
                    dropped += max(0, p.packet_id - last_pid - 1)
                last_pid = p.packet_id
                last_t_ms = t_ms
                last_wall = datetime.now().isoformat(timespec="milliseconds")
                writer.writerow(make_row(p, g, last_wall, t_ms, dt_ms))
                rows += 1
                if now - last_flush >= 1.0:
                    fh.flush()
                    last_flush = now
        except KeyboardInterrupt:
            print("\n[+] interrupted")

    elapsed = time.perf_counter() - start
    meta.update(
        {
            "started_at": stamp,
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "duration_s": round(elapsed, 3),
            "rows": rows,
            "rate_hz": round(rows / elapsed, 2) if elapsed > 0 else 0.0,
            "dropped_packets": dropped,
            "first_packet_id": first_pid,
            "last_packet_id": last_pid,
            "physics_mapping_size": physics.size,
            "physics_struct_size": ctypes.sizeof(Physics),
            "graphics_struct_size": ctypes.sizeof(Graphics),
            "static_struct_size": ctypes.sizeof(StaticInfo),
            "graphics_present": graphics is not None,
            "columns": COLUMNS,
        }
    )
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[+] {rows} rows, {elapsed:.1f}s, {meta['rate_hz']:.1f} Hz, dropped={dropped}")
    print(f"[+] csv:  {csv_path}")
    print(f"[+] meta: {meta_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--probe", action="store_true", help="validate the shared-memory layout and print samples")
    parser.add_argument("--duration", type=float, default=0.0, help="seconds to record (0 = until Ctrl+C)")
    parser.add_argument("--out", type=Path, default=Path("telemetry"), help="output directory (default: telemetry)")
    args = parser.parse_args(argv)

    if not IS_WINDOWS:
        print("[!] This tool only runs on Windows.", file=sys.stderr)
        return 1

    try:
        physics = SharedMemory(r"Local\acpmf_physics")
    except OSError as exc:
        print("[!] Cannot open Local\\acpmf_physics.", file=sys.stderr)
        print(f"    {exc}", file=sys.stderr)
        print("    Start Assetto Corsa Rally and get into a session first.", file=sys.stderr)
        return 2

    graphics = open_optional(r"Local\acpmf_graphics")
    static = open_optional(r"Local\acpmf_static")
    try:
        if args.probe:
            return probe(physics, graphics, static, args.duration or 5.0)
        return record(physics, graphics, static, args.out, args.duration)
    finally:
        if graphics:
            graphics.close()
        if static:
            static.close()
        physics.close()


if __name__ == "__main__":
    raise SystemExit(main())
