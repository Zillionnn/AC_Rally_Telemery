from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

TRACK_KEYS = (
    "bollene",
    "elatia",
    "hafren",
    "loutraki",
    "munster",
    "saverne",
    "sisteron",
)
BRAKE_TOKENS = {
    "Brake",
    "SlowDown",
    "Caution",
    "StopAtMarshals",
    "Sudden",
    "OverCrest",
    "IntoDip",
    "BadCamber",
}
TURN_PREFIXES = ("Left", "Right", "Kinks", "And", "Into", "Keep")


@dataclass(frozen=True, slots=True)
class Note:
    distance: float
    length: float
    tokens: tuple[str, ...]
    link: bool

    @property
    def text(self) -> str:
        return " · ".join(self.tokens) if self.tokens else "—"

    @property
    def category(self) -> str:
        tokens = set(self.tokens)
        if "Finish" in tokens:
            return "finish"
        if tokens & BRAKE_TOKENS:
            return "brake"
        if any(token.startswith(TURN_PREFIXES) for token in self.tokens):
            return "turn"
        if any(token.startswith("Dist") for token in self.tokens):
            return "distance"
        return "other"


@dataclass(frozen=True, slots=True)
class Stage:
    key: str
    notes: tuple[Note, ...]

    @property
    def start(self) -> float:
        return self.notes[0].distance

    @property
    def end(self) -> float:
        return self.notes[-1].distance

    @property
    def label(self) -> str:
        return display_name(self.key)


@dataclass
class PaceNoteBook:
    stages: dict[str, Stage]
    error: str | None = None


def data_path() -> Path:
    here = Path(__file__).resolve().parent
    for base in (here, Path(sys.executable).resolve().parent, Path.cwd()):
        candidate = base / "pacenotes" / "pacenotes.json"
        if candidate.exists():
            return candidate
    return here / "pacenotes" / "pacenotes.json"


def load(path: Path | None = None) -> PaceNoteBook:
    target = Path(path) if path is not None else data_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
        stages = {}
        for key, value in raw.get("stages", {}).items():
            notes = tuple(
                Note(
                    distance=float(row[0]),
                    length=float(row[1]),
                    tokens=tuple(str(token) for token in row[2]),
                    link=bool(row[3]),
                )
                for row in value["rows"]
            )
            if notes:
                stages[key] = Stage(key, notes)
        return PaceNoteBook(stages)
    except Exception as exc:
        return PaceNoteBook({}, f"{type(exc).__name__}: {exc}")


def display_name(key: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key)
    text = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", text)
    return text


def _hint(run) -> str:
    meta = getattr(run, "meta", {}) or {}
    values = []
    for key in (
        "track",
        "track_configuration",
        "stage",
        "stage_name",
        "track_name",
        "configuration",
    ):
        value = meta.get(key)
        if isinstance(value, str):
            values.append(value)
    return " ".join(values).lower()


def _hint_penalty(stage: Stage, hint: str) -> int:
    if not hint:
        return 0
    key = stage.key.lower()
    penalty = 0
    if "reverse" in hint and "reverse" not in key:
        penalty += 50000
    if "forward" in hint and "forward" not in key:
        penalty += 50000
    if "north" in hint and "north" not in key:
        penalty += 30000
    if "south" in hint and "south" not in key:
        penalty += 30000
    for token in TRACK_KEYS:
        if token in hint and token not in key:
            penalty += 50000
    for index in (1, 2, 3):
        if re.search(rf"cut[\s_-]*{index}\b", hint) and f"cut{index}" not in key:
            penalty += 20000
    return penalty


def auto_stage(run, book: PaceNoteBook) -> str | None:
    if run is None or not book.stages:
        return None
    summary = run.summary
    start = float(summary.get("start_distance", 0.0))
    end = float(summary.get("end_distance", start + summary.get("distance", 0.0)))
    hint = _hint(run)

    def score(stage: Stage) -> float:
        distance_error = abs(stage.start - start) + abs(stage.end - end)
        return distance_error + _hint_penalty(stage, hint)

    return min(book.stages, key=lambda key: score(book.stages[key]))


def relative_notes(stage: Stage, start_distance: float) -> list[tuple[Note, float]]:
    return [(note, note.distance - start_distance) for note in stage.notes]
