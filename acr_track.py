"""Reconstruct the stage path from telemetry so slow points can be placed on it.

The game exposes no usable world position: `car_x` is always 0 and `car_y` only
updates every few packets, so the map is built by integrating the world-frame
velocity. That was checked against the recorded distance (path 10251m against a
10380m stage) and against `speed_kmh`, which the integrated path reproduces.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TrackPath:
    dist: np.ndarray
    time: np.ndarray
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    speed: np.ndarray
    length: float
    elev_gain: float

    def index_at_dist(self, distance: float) -> int:
        if not len(self.dist):
            return -1
        return int(np.clip(np.searchsorted(self.dist, distance), 0, len(self.dist) - 1))

    def index_at_time(self, stage_time: float) -> int:
        if not len(self.time):
            return -1
        return int(np.clip(np.searchsorted(self.time, stage_time), 0, len(self.time) - 1))

    def point_at_dist(self, distance: float) -> tuple[float, float] | None:
        index = self.index_at_dist(distance)
        if index < 0:
            return None
        return float(self.x[index]), float(self.y[index])

    def window(self, centre: float, radius: float) -> np.ndarray:
        """Boolean mask of points within radius metres of centre distance."""
        return np.abs(self.dist - centre) <= radius


def _orientation(x: np.ndarray, y: np.ndarray) -> float:
    """Angle that lays the stage out left-to-right, without mirroring it.

    Start to finish is the intuitive axis. When the two nearly coincide the
    principal axis of the shape is used instead. Rotation only: a mirror would
    turn every left-hand corner into a right-hand one.
    """
    dx, dy = x[-1] - x[0], y[-1] - y[0]
    span = float(np.hypot(x.max() - x.min(), y.max() - y.min()))
    if span > 0 and float(np.hypot(dx, dy)) >= span * 0.15:
        return float(np.arctan2(dy, dx))
    cov = np.cov(np.vstack((x, y)))
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    main = eigenvectors[:, int(np.argmax(eigenvalues))]
    angle = float(np.arctan2(main[1], main[0]))
    if np.cos(angle) < 0:
        angle += np.pi
    return angle


def build_path(run) -> TrackPath | None:
    traces = getattr(run, "traces", None)
    if not traces or "vx" not in traces or len(traces["x"]) < 10:
        return None
    t = np.asarray(traces["t"], dtype=np.float64)
    vx = np.asarray(traces["vx"], dtype=np.float64)
    vy = np.asarray(traces["vy"], dtype=np.float64)
    vz = np.asarray(traces["vz"], dtype=np.float64)
    if not (np.any(vx) or np.any(vz)):
        return None

    dt = np.diff(t, prepend=t[0])
    dt[0] = 0.0
    dt = np.clip(dt, 0.0, 0.5)
    east = np.concatenate([[0.0], np.cumsum(vx[1:] * dt[1:])])
    north = np.concatenate([[0.0], np.cumsum(vz[1:] * dt[1:])])
    up = np.concatenate([[0.0], np.cumsum(vy[1:] * dt[1:])])
    if float(np.hypot(np.ptp(east), np.ptp(north))) < 20.0:
        return None

    angle = _orientation(east, north)
    cos_a, sin_a = np.cos(-angle), np.sin(-angle)
    x = east * cos_a - north * sin_a
    y = east * sin_a + north * cos_a
    x -= float(x.mean())
    y -= float(y.mean())

    dist = np.asarray(traces["x"], dtype=np.float64)
    step = np.hypot(np.diff(x), np.diff(y))
    return TrackPath(
        dist=dist,
        time=t,
        x=x,
        y=y,
        z=up - float(up[0]),
        speed=np.asarray(traces["speed"], dtype=np.float32),
        length=float(step.sum()),
        elev_gain=float(np.sum(np.clip(np.diff(up), 0.0, None))),
    )


def delta_kinds(path: TrackPath, grid: np.ndarray, delta: np.ndarray,
                window: float = 100.0, threshold: float = 0.2) -> np.ndarray:
    """Per point: 1 where this run lost time, -1 where it gained, else 0.

    `delta` is the cumulative time difference, which only ever grows on a run
    that is slower overall and would paint the whole map red. Colouring the
    time lost inside a `window`-metre stretch instead matches the Gains/Losses
    zone list and points at the corner that actually cost the time.
    """
    if path is None or grid is None or delta is None:
        return np.zeros(len(path.dist) if path else 0, dtype=np.int8)
    grid = np.asarray(grid, dtype=float)
    delta = np.asarray(delta, dtype=float)
    if len(grid) < 3:
        return np.zeros(len(path.dist), dtype=np.int8)
    local = delta - np.interp(grid - window, grid, delta)
    at_points = np.interp(path.dist, grid, local)
    return np.where(at_points > threshold, 1,
                    np.where(at_points < -threshold, -1, 0)).astype(np.int8)
