from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from html import escape as html_escape
from pathlib import Path

os.environ.setdefault("PYQTGRAPH_QT_LIB", "PySide6")

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, QLockFile, QSize, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsItem,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QSplitterHandle,
    QSystemTrayIcon,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import acr_data
import acr_i18n
import acr_pacenotes
import acr_play
import acr_track
from acr_i18n import tr
from acr_live import AutoRecorder
from acr_version import __version__ as APP_VERSION


_LANG_OVERRIDE = None


C = {
    "bg": "#070b12",
    "panel": "#0f172a",
    "panel2": "#0b1220",
    "border": "#1e293b",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
    "dim": "#64748b",
    "green": "#22c55e",
    "green_dim": "#4ade80",
    "red": "#ef4444",
    "red_dim": "#f87171",
    "amber": "#f59e0b",
    "blue": "#38bdf8",
    "purple": "#a78bfa",
    "pink": "#fb7185",
    "yellow": "#facc15",
    "cursor": "#475569",
}

STYLE = """
QMainWindow, QWidget {
    background: #070b12;
    color: #e2e8f0;
    font-family: "Segoe UI";
    font-size: 9pt;
}
QFrame#header {
    background: #0b1220;
    border-bottom: 1px solid #1e293b;
}
QFrame#readout {
    background: #0b1220;
    border-bottom: 1px solid #1e293b;
}
QFrame#liveBar {
    background: #0b1220;
    border-bottom: 1px solid #1e293b;
}
QLabel#liveDot {
    font-size: 15pt;
}
QLabel#liveState {
    color: #64748b;
    font-size: 9.5pt;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#liveDetail {
    color: #cbd5e1;
    font-family: "Consolas";
    font-size: 10.5pt;
}
QCheckBox {
    color: #94a3b8;
    font-size: 9pt;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #334155;
    border-radius: 3px;
    background: #0b1220;
}
QCheckBox::indicator:checked {
    background: #22c55e;
    border-color: #22c55e;
}
QMenu {
    background: #0f172a;
    color: #e2e8f0;
    border: 1px solid #1e293b;
}
QMenu::item {
    padding: 6px 22px;
}
QMenu::item:selected {
    background: #1e293b;
}
QFrame#card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
}
QFrame#chartCard {
    background: #0b1220;
    border: 1px solid #1e293b;
    border-radius: 8px;
}
QFrame#replayPanel {
    background: #0b1220;
    border: 1px solid #1e293b;
    border-radius: 8px;
}
QLabel#videoView {
    color: #64748b;
    background: #070b12;
    border: 1px solid #172033;
    border-radius: 6px;
    font-size: 8.5pt;
}
QLabel#cardSubTitle {
    color: #94a3b8;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#cardHint {
    color: #64748b;
    font-size: 7.5pt;
}
QLabel#videoInfo {
    color: #94a3b8;
    font-size: 8pt;
}
QLabel#videoInfo:hover {
    color: #38bdf8;
}
QFrame#stat {
    background: #0b1220;
    border: 1px solid #172033;
    border-radius: 6px;
}
QLabel#brand {
    color: #e2e8f0;
    font-size: 19pt;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#subtitle {
    color: #64748b;
    font-size: 9.5pt;
    letter-spacing: 1px;
}
QLabel#selectorLabel {
    color: #64748b;
    font-size: 9pt;
}
QLabel#cardTitle {
    color: #64748b;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#bigTime {
    color: #f8fafc;
    font-family: "Consolas";
    font-size: 27pt;
    font-weight: 700;
}
QLabel#delta {
    font-family: "Consolas";
    font-size: 11pt;
    font-weight: 600;
}
QLabel#muted {
    color: #64748b;
    font-size: 8pt;
}
QLabel#statCaption {
    color: #64748b;
    font-size: 7.5pt;
}
QLabel#statValue {
    color: #e2e8f0;
    font-family: "Consolas";
    font-size: 12pt;
    font-weight: 600;
}
QLabel#trackLabel {
    font-size: 9pt;
}
QLabel#readoutCaption {
    color: #64748b;
    font-size: 8pt;
    letter-spacing: 1px;
}
QLabel#readoutValue {
    color: #e2e8f0;
    font-family: "Consolas";
    font-size: 12.5pt;
    font-weight: 600;
}
QComboBox {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 5px 10px;
    color: #cbd5e1;
    font-size: 10pt;
    min-height: 24px;
}
QComboBox:hover {
    border-color: #334155;
}
QComboBox QAbstractItemView {
    background: #0f172a;
    color: #e2e8f0;
    border: 1px solid #334155;
    selection-background-color: #1e293b;
}
QTabWidget::pane {
    border: 1px solid #1e293b;
    border-radius: 4px;
    top: -1px;
}
QTabBar::tab {
    background: #0b1220;
    color: #64748b;
    padding: 5px 10px;
    border: 1px solid #1e293b;
    border-bottom: none;
}
QTabBar::tab:selected {
    color: #e2e8f0;
    background: #111c2e;
    border-color: #334155;
}
QTabBar::tab:hover {
    color: #cbd5e1;
}
QPushButton {
    background: #111c2e;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 6px 12px;
    color: #cbd5e1;
    font-size: 9.5pt;
}
QPushButton:hover {
    background: #16243a;
    border-color: #334155;
}
QPushButton:disabled {
    color: #475569;
}
QListWidget {
    background: transparent;
    border: none;
    color: #cbd5e1;
    outline: none;
}
QListWidget::item {
    padding: 6px 4px;
    border-bottom: 1px solid #172033;
}
QListWidget::item:selected {
    background: #1e293b;
    color: #f8fafc;
}
QTableWidget {
    background: transparent;
    border: none;
    color: #cbd5e1;
    gridline-color: #172033;
    outline: none;
}
QHeaderView::section {
    background: transparent;
    border: none;
    border-bottom: 1px solid #1e293b;
    color: #64748b;
    padding: 4px 2px;
    font-size: 7.5pt;
}
QTableWidget::item {
    padding: 3px 2px;
    border-bottom: 1px solid #172033;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #334155;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
}
QScrollBar::handle:horizontal {
    background: #334155;
    min-width: 24px;
    border-radius: 4px;
}
QSplitter::handle {
    background: #1b2537;
    width: 8px;
    height: 8px;
}
QSplitter::handle:hover {
    background: #2b3a52;
}
QScrollArea#chartScroll, QWidget#chartContent {
    background: #070b12;
    border: none;
}
QFrame#chartHandle {
    background: #0b1220;
    border-top: 1px solid #1e293b;
    border-bottom: 1px solid #0b1220;
}
QFrame#chartHandle:hover {
    background: #1e293b;
    border-top-color: #475569;
}
QStatusBar {
    background: #0b1220;
    color: #475569;
    border-top: 1px solid #1e293b;
    font-size: 8pt;
}
QToolTip {
    background: #0f172a;
    color: #e2e8f0;
    border: 1px solid #334155;
}
"""


class GripHandle(QSplitterHandle):
    """Splitter handle with the same little bar as the chart height handles."""

    drag_started = Signal()
    drag_finished = Signal()

    def __init__(self, orientation, parent) -> None:
        super().__init__(orientation, parent)
        self._dragging = False

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = "#e2e8f0" if self.underMouse() else "#94a3b8"
        painter.setPen(QPen(QColor(color), 2))
        x = self.width() // 2
        y = self.height() // 2
        if self.orientation() == Qt.Orientation.Vertical:
            painter.drawLine(x - 28, y, x + 28, y)
        else:
            painter.drawLine(x, y - 28, x, y + 28)

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event) -> None:
        # only a real drag freezes the charts; a plain click must not blank them
        if not self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self._dragging = True
            self.drag_started.emit()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if self._dragging:
            self._dragging = False
            self.drag_finished.emit()

    def event(self, event) -> bool:
        # never leave the charts frozen if the grab is lost mid-drag
        if event.type() == QEvent.Type.UngrabMouse and self._dragging:
            self._dragging = False
            self.drag_finished.emit()
        return super().event(event)


class GripSplitter(QSplitter):
    def __init__(self, orientation) -> None:
        super().__init__(orientation)
        self.setHandleWidth(10)

    def createHandle(self) -> QSplitterHandle:
        return GripHandle(self.orientation(), self)


class ChartResizeHandle(QFrame):
    def __init__(self, window, index: int):
        super().__init__()
        self._window = window
        self._index = index
        self._start_y = None
        self._start_height = 0.0
        self.setObjectName("chartHandle")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(8)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setToolTip(tr("拖动调整上方图表高度"))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = "#475569" if self.underMouse() else "#334155"
        painter.setPen(QPen(QColor(color), 1))
        y = self.height() // 2
        center = self.width() // 2
        painter.drawLine(center - 14, y, center + 14, y)

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_y = float(event.globalPosition().y())
            self._start_height = float(self._window._chart_heights[self._index])
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._start_y is None:
            super().mouseMoveEvent(event)
            return
        delta = float(event.globalPosition().y()) - self._start_y
        self._window._set_chart_height(self._index, self._start_height + delta)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._start_y is not None:
            self._start_y = None
            self._window._save_chart_layout()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class TrackMap(pg.PlotWidget):
    """Stage path rebuilt from telemetry, so a slow point can be found on track."""

    distance_clicked = Signal(float)
    distance_hovered = Signal(float)

    def __init__(self) -> None:
        super().__init__(background=C["bg"])
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: transparent;")
        plot = self.getPlotItem()
        plot.hideButtons()
        plot.setMenuEnabled(False)
        plot.showGrid(x=False, y=False)
        for name in ("left", "right", "top", "bottom"):
            plot.getAxis(name).hide()
        self.setAspectLocked(True)
        plot.vb.setMouseEnabled(x=False, y=False)

        self.path: acr_track.TrackPath | None = None
        self._hover_distance = -1.0
        self._dx: np.ndarray | None = None
        self._dy: np.ndarray | None = None
        self._angle = None
        self._note_dist = np.asarray([])
        self._note_colors: list = []
        self._incident_dist = np.asarray([])
        self._incident_pens: list = []
        self._cursor_distance = 0.0
        self._kinds = np.asarray([], dtype=np.int8)

        # connect="finite" so the NaN gap markers do not poison the item's
        # bounding rect (a NaN rect collapses the map's auto-range and the
        # track is then drawn outside the visible view)
        self.base = pg.PlotDataItem(
            pen=pg.mkPen(C["dim"], width=2.2), antialias=False, connect="finite")
        self.loss = pg.PlotDataItem(
            pen=pg.mkPen(C["red"], width=5.0), antialias=False, connect="finite")
        self.gain = pg.PlotDataItem(
            pen=pg.mkPen(C["green"], width=5.0), antialias=False, connect="finite")
        # the track never moves, so cache it: otherwise every cursor move
        # re-strokes the whole path (~10ms). The cache lives on the inner
        # PlotCurveItem, not the PlotDataItem wrapper.
        for item in (self.base, self.loss, self.gain):
            item.curve.setCacheMode(
                QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.notes = pg.ScatterPlotItem(pen=pg.mkPen(None), symbol="o", size=5)
        self.incidents = pg.ScatterPlotItem(
            pen=pg.mkPen(C["bg"], width=1), symbol="t", size=9
        )
        self.start_item = pg.TextItem("S", color=C["green"], anchor=(0.5, 0.5))
        self.finish_item = pg.TextItem("F", color=C["amber"], anchor=(0.5, 0.5))
        for item in (self.start_item, self.finish_item):
            font = QFont("Segoe UI", 9)
            font.setBold(True)
            item.setFont(font)
        self.cursor = pg.ScatterPlotItem(
            pen=pg.mkPen(C["text"], width=2), brush=pg.mkBrush(None),
            symbol="o", size=13,
        )
        self.cursor_label = pg.TextItem(
            "", color=C["text"], anchor=(0, 1.35),
            fill=pg.mkBrush(8, 13, 23, 215), border=pg.mkPen(C["border"]),
        )
        self.cursor_label.setFont(QFont("Consolas", 8))
        self.hint = pg.TextItem("", color=C["muted"], anchor=(0.5, 0.5))
        self.hint.setFont(QFont("Segoe UI", 9))

        for item in (self.base, self.gain, self.loss, self.notes,
                     self.incidents, self.start_item, self.finish_item,
                     self.cursor, self.cursor_label, self.hint):
            plot.addItem(item, ignoreBounds=item is self.hint)

        plot.scene().sigMouseClicked.connect(self._on_clicked)
        plot.scene().sigMouseMoved.connect(self._on_moved)

    def clear(self) -> None:
        self.path = None
        self._dx = self._dy = None
        for item in (self.base, self.gain, self.loss, self.notes,
                     self.incidents, self.cursor):
            item.setData([])
        for item in (self.start_item, self.finish_item, self.cursor_label):
            item.hide()

    def show_message(self, text: str) -> None:
        self.clear()
        self.hint.setText(text)
        self.hint.show()

    # --- geometry ---------------------------------------------------------
    def _reorient(self) -> None:
        """Lay the stage along whichever axis the panel actually has.

        A 10km stage is roughly 6.7km by 1.8km, so in a narrow tall panel a
        horizontal layout wastes almost all of the height.
        """
        if self.path is None:
            return
        wide = float(np.ptp(self.path.x)) / max(1.0, float(np.ptp(self.path.y)))
        portrait = self.height() > self.width() * 1.1 and wide > 1.6
        angle = np.pi / 2.0 if portrait else 0.0
        if self._angle is not None and abs(angle - self._angle) < 1e-6:
            return
        self._angle = angle
        x = self.path.x - float(self.path.x.mean())
        y = self.path.y - float(self.path.y.mean())
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        self._dx = x * cos_a - y * sin_a
        self._dy = x * sin_a + y * cos_a

    def _runs(self, mask) -> list:
        """Contiguous index groups, so gaps do not get joined by a line."""
        idx = np.flatnonzero(mask)
        if not len(idx):
            return []
        return np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)

    def _polyline(self, mask) -> tuple[list, list]:
        xs: list[float] = []
        ys: list[float] = []
        for group in self._runs(mask):
            if len(group) < 2:
                continue
            xs.extend(self._dx[group])
            ys.extend(self._dy[group])
            xs.append(np.nan)
            ys.append(np.nan)
        return xs, ys

    def _render(self) -> None:
        if self.path is None or self._dx is None:
            return
        self.base.setData(self._dx, self._dy)
        self.loss.setData(*self._polyline(self._kinds > 0))
        self.gain.setData(*self._polyline(self._kinds < 0))
        self._render_points()
        self.start_item.setPos(float(self._dx[0]), float(self._dy[0]))
        self.start_item.show()
        self.finish_item.setPos(float(self._dx[-1]), float(self._dy[-1]))
        self.finish_item.show()
        self._render_cursor()

    def _render_points(self) -> None:
        if len(self._note_dist):
            index = self._indices(self._note_dist)
            self.notes.setData(
                self._dx[index], self._dy[index], brushes=list(self._note_colors)
            )
        else:
            self.notes.setData([])
        if len(self._incident_dist):
            index = self._indices(self._incident_dist)
            self.incidents.setData(self._dx[index], self._dy[index],
                                   pens=list(self._incident_pens))
        else:
            self.incidents.setData([])

    def _render_cursor(self) -> None:
        if not len(self._dx):
            return
        index = self.path.index_at_dist(self._cursor_distance)
        x = float(self._dx[index])
        y = float(self._dy[index])
        self.cursor.setData([x], [y])
        self.cursor_label.setText(f"{float(self.path.dist[index]):,.0f} m")
        self.cursor_label.setPos(x, y)
        self.cursor_label.show()

    def _indices(self, distances) -> np.ndarray:
        return np.clip(np.searchsorted(self.path.dist, np.asarray(distances)),
                       0, len(self._dx) - 1)

    def _apply_bounds(self) -> None:
        """Frame the track from its own extents.

        Auto-range is not usable here: while the panel is still empty the
        aspect-locked view collapses to a ~1e-155 range, and from then on the
        pixel padding math in every item's boundingRect returns NaN, so the map
        never recovers once data arrives.
        """
        if self._dx is None or not len(self._dx):
            return
        self.getPlotItem().vb.setRange(
            xRange=(float(self._dx.min()), float(self._dx.max())),
            yRange=(float(self._dy.min()), float(self._dy.max())),
            padding=0.08,
            disableAutoRange=True,
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # PlotWidget.__getattr__ traps unknown names, and Qt resizes us during
        # super().__init__() before our own fields exist.
        if getattr(self, "path", None) is not None:
            # only a width/height flip needs the path re-stroked; otherwise the
            # data is unchanged and re-setting it on every splitter move was the
            # heaviest part of dragging the replay panel
            angle = self._angle
            self._reorient()
            if angle != self._angle or self._dx is None:
                self._render()
            else:
                self._apply_bounds()

    # --- inputs -----------------------------------------------------------
    def set_path(self, path: acr_track.TrackPath | None) -> None:
        self.hint.hide()
        if path is None:
            self.show_message(tr("此 run 无赛道数据"))
            return
        self.path = path
        self._angle = None
        self._kinds = np.zeros(len(path.dist), dtype=np.int8)
        self._reorient()
        self._render()
        self._apply_bounds()

    def set_delta(self, grid, delta) -> None:
        if self.path is None:
            return
        self._kinds = acr_track.delta_kinds(self.path, grid, delta)
        self._render()

    def set_pacenotes(self, distances, colors) -> None:
        self._note_dist = np.asarray(distances, dtype=float)
        self._note_colors = list(colors)
        if self.path is not None:
            self._render_points()

    def set_incidents(self, distances, majors) -> None:
        self._incident_dist = np.asarray(distances, dtype=float)
        self._incident_pens = [QColor(C["red"]) if major else QColor(C["amber"])
                              for major in majors]
        if self.path is not None:
            self._render_points()

    def set_cursor(self, distance: float) -> None:
        self._cursor_distance = float(distance)
        if self.path is not None and self._dx is not None:
            self._render_cursor()

    def _nearest(self, event) -> int:
        if self.path is None or self._dx is None:
            return -1
        position = event.pos() if hasattr(event, "pos") else event
        view = self.getPlotItem().vb.mapSceneToView(position)
        d2 = (self._dx - view.x()) ** 2 + (self._dy - view.y()) ** 2
        return int(np.argmin(d2))

    def _on_clicked(self, event) -> None:
        if self.path is None:
            return
        index = self._nearest(event)
        if index >= 0:
            self.distance_clicked.emit(float(self.path.dist[index]))

    def _on_moved(self, position) -> None:
        if self.path is None:
            return
        index = self._nearest(position)
        if index < 0:
            return
        distance = float(self.path.dist[index])
        if abs(distance - self._hover_distance) > 1.0:
            self._hover_distance = distance
            self.distance_hovered.emit(distance)


class Loader(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, directory: Path):
        super().__init__()
        self.directory = directory

    def run(self) -> None:
        try:
            self.loaded.emit(acr_data.load_runs(self.directory))
        except Exception:
            self.failed.emit(traceback.format_exc())


class TelemetryWindow(QMainWindow):
    def __init__(
        self,
        runs=None,
        directory: Path = acr_data.TELEMETRY_DIR,
        auto_record: bool = True,
    ):
        super().__init__()
        self.directory = Path(directory)
        if _LANG_OVERRIDE:
            acr_i18n.set_language(_LANG_OVERRIDE)
        else:
            acr_i18n.set_language(str(self._load_ui_state().get("language", "zh")))
        self.runs = []
        self.current = None
        self.reference = None
        self.compare = None
        self.loader = None
        self.pending_indices = (None, None)
        self._updating = False
        self._cursor_x = 0.0
        self._cursor_index = 0
        self._cursor_lines = []
        self._incident_lines = []
        self._zone_items = []
        self._zone_labels = []
        self.pacenote_book = acr_pacenotes.load()
        self._pacenote_stage = None
        self._pacenote_notes = []
        self._pacenote_items = []
        self._pacenote_highlight = []
        self._pacenote_label = None
        self._pacenote_hover = None
        self._pacenote_follow_x = None
        self._chart_heights = []
        self._chart_widgets = []
        self._chart_handles = []
        self._chart_default_factors = []
        self._chart_viewports = {}
        self._mouse_proxies = []
        self._chart_heights_from_file = False
        self._chart_fitted = False
        self._chart_scale = {}
        self._scale_watched = set()
        self._applying_scale = False
        self._series = {}
        self._right_views = {}
        self.readout = {}
        self.readout_captions = []
        self.stat_values = {}
        self.tray = None
        self.tray_auto_action = None
        self.tray_video_action = None
        self._auto_recorder = None
        self._tray_icons = {}
        self._real_quit = False
        self._saved_until = 0.0
        self._saved_message = ""
        self._auto_select_newest = False
        self._reload_pending = False
        self._new_run_path = None
        self._auto_record = auto_record
        self.main_split = None
        self.replay_panel = None
        self.replay_panel_toggle = None
        self.video_view = None
        self.replay_state = None
        self.map_hint = None
        self.track_map = None
        self._map_path = None
        self._player = None
        self._manual_video = None
        self._video_sync_guard = False
        self._video_offset_override = {}
        self._map_run_id = None
        # cursor/axis updates are coalesced to ~30Hz: every mouse move otherwise
        # repaints all six plots and the map, which costs ~60ms per event
        self._video_resize_timer = QTimer(self)
        self._video_resize_timer.setSingleShot(True)
        self._video_resize_timer.setInterval(150)
        self._video_resize_timer.timeout.connect(self._paint_video_frame)
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setSingleShot(True)
        self._cursor_timer.setInterval(33)
        self._cursor_timer.timeout.connect(self._flush_cursor_update)
        self._pending_cursor = None
        self._axis_timer = QTimer(self)
        self._axis_timer.setSingleShot(True)
        self._axis_timer.setInterval(33)
        self._axis_timer.timeout.connect(self._flush_axis_sync)
        self._pending_axis = None
        # grid lines make range changes ~2.5x more expensive to repaint, so
        # they are hidden while the user pans/zooms and restored when idle
        self._grid_timer = QTimer(self)
        self._grid_timer.setSingleShot(True)
        self._grid_timer.setInterval(220)
        self._grid_timer.timeout.connect(self._restore_chart_grid)
        self._grid_hidden = False

        pg.setConfigOptions(background=C["bg"], foreground=C["muted"], antialias=True)
        self.setWindowTitle(f"ACR Telemetry Studio · v{APP_VERSION}")
        self.setMinimumSize(1280, 760)
        self.resize(1800, 1000)
        self.setStyleSheet(STYLE)
        self.setWindowIcon(self._make_tray_icon(C["green"]))

        self._build_ui()
        self._setup_player()
        if runs is not None:
            self.set_runs(runs)
        else:
            self.start_loader()
        if auto_record:
            self._setup_tray()
            self._setup_auto_recorder()
        else:
            self.auto_check.setChecked(False)
            self.auto_check.setEnabled(False)
            self._set_live("preview", tr("预览模式 · 自动录制未启动"))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_axis_width)
        if self._chart_fitted:
            return
        self._chart_fitted = True
        if not self._chart_heights_from_file:
            QTimer.singleShot(0, self._fit_chart_heights)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "chart_scroll"):
            QTimer.singleShot(0, self._sync_axis_width)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._build_live_bar())
        root.addWidget(self._build_readout())

        split = GripSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        split.addWidget(self._build_sidebar())
        chart_card = QFrame()
        chart_card.setObjectName("chartCard")
        chart_card.setMinimumWidth(320)
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(10, 8, 10, 8)
        chart_layout.setSpacing(2)
        self._build_charts()
        chart_layout.addWidget(self.chart_scroll, 1)
        axis_wrap = QWidget()
        axis_layout = QHBoxLayout(axis_wrap)
        axis_layout.setContentsMargins(8, 0, 8, 0)
        axis_layout.setSpacing(0)
        axis_layout.addWidget(self.axis_plot)
        chart_layout.addWidget(axis_wrap, 0)
        split.addWidget(chart_card)
        split.addWidget(self._build_replay_panel())
        split.setSizes([400, 1120, 420])
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        self.main_split = split
        # both dividers resize the six pyqtgraph plots; freeze the charts for
        # the duration of a drag and repaint them once on release
        for index in (1, 2):
            handle = split.handle(index)
            handle.drag_started.connect(self._begin_panel_drag)
            handle.drag_finished.connect(self._end_panel_drag)
        split.splitterMoved.connect(self._on_main_split_moved)
        self._apply_panel_state()
        root.addWidget(split, 1)

        self.status = self.statusBar()
        self.status.showMessage(tr("正在等待遥测数据…"))

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("header")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(10)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        brand = QLabel('ACR <span style="color:#22c55e">TELEMETRY</span> STUDIO')
        brand.setTextFormat(Qt.TextFormat.RichText)
        brand.setObjectName("brand")
        subtitle = QLabel("ASSETTO CORSA RALLY · STAGE ANALYSIS")
        subtitle.setObjectName("subtitle")
        titles.addWidget(brand)
        titles.addWidget(subtitle)
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setObjectName("cardHint")
        titles.addWidget(self.version_label)
        layout.addLayout(titles)
        layout.addStretch(1)

        layout.addWidget(self._selector_label(tr("当前")))
        self.current_combo = QComboBox()
        self.current_combo.setMinimumWidth(200)
        self.current_combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self.current_combo)

        layout.addSpacing(6)
        layout.addWidget(self._selector_label(tr("参考")))
        self.reference_combo = QComboBox()
        self.reference_combo.setMinimumWidth(200)
        self.reference_combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self.reference_combo)

        self.refresh_btn = QPushButton(tr("刷新"))
        self.refresh_btn.clicked.connect(self.start_loader)
        layout.addWidget(self.refresh_btn)
        self.reset_btn = QPushButton(tr("重置缩放"))
        self.reset_btn.clicked.connect(self.reset_zoom)
        layout.addWidget(self.reset_btn)
        self.reset_chart_btn = QPushButton(tr("重置图高"))
        self.reset_chart_btn.clicked.connect(self._on_reset_chart_heights)
        layout.addWidget(self.reset_chart_btn)
        self.replay_panel_toggle = QPushButton(tr("回放面板"))
        self.replay_panel_toggle.setCheckable(True)
        self.replay_panel_toggle.setChecked(True)
        self.replay_panel_toggle.clicked.connect(self._on_toggle_replay_panel)
        layout.addWidget(self.replay_panel_toggle)

        self.lang_combo = QComboBox()
        for code, name in acr_i18n.LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.setCurrentIndex(
            max(0, self.lang_combo.findData(acr_i18n.language())))
        self.lang_combo.setToolTip(tr("语言 · 立即生效"))
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        layout.addWidget(self.lang_combo)
        return frame

    def _selector_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("selectorLabel")
        return label

    def _build_live_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("liveBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 5, 18, 5)
        layout.setSpacing(8)
        self.live_dot = QLabel("●")
        self.live_dot.setObjectName("liveDot")
        self.live_state = QLabel("WAITING")
        self.live_state.setObjectName("liveState")
        self.live_detail = QLabel(tr("等待 AC Rally …"))
        self.live_detail.setObjectName("liveDetail")
        layout.addWidget(self.live_dot)
        layout.addWidget(self.live_state)
        layout.addWidget(self.live_detail)
        layout.addStretch(1)
        self.auto_check = QCheckBox(tr("自动录制"))
        self.auto_check.setChecked(True)
        self.auto_check.stateChanged.connect(self._on_auto_toggle)
        layout.addWidget(self.auto_check)
        self.video_check = QCheckBox(tr("自动录像"))
        self.video_check.setChecked(True)
        self.video_check.setToolTip(
            tr("跑赛段时同步录制画面+系统声音到 telemetry/videos，\n"
               "与遥测一一对应；赛段重置的片段会自动删除")
        )
        self.video_check.stateChanged.connect(self._on_video_toggle)
        layout.addWidget(self.video_check)
        self.video_info = QLabel("")
        self.video_info.setObjectName("videoInfo")
        self.video_info.setToolTip(tr("点击打开录像目录"))
        self.video_info.mousePressEvent = lambda _e: self._open_video_folder()
        layout.addWidget(self.video_info)
        return frame

    def _build_readout(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("readout")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 6, 18, 6)
        layout.setSpacing(26)
        fields = (
            ("distance", "距离", "m"),
            ("time", "时间", ""),
            ("speed", "速度", "km/h"),
            ("gas", "油门", "%"),
            ("brake", "刹车", "%"),
            ("gear", "挡位", ""),
            ("delta", "Δ 参考", "s"),
            ("ref_speed", "参考速度", "km/h"),
            ("pacenote", "路书", ""),
        )
        for key, caption, unit in fields:
            box = QVBoxLayout()
            box.setSpacing(0)
            caption_label = QLabel(f"{tr(caption)}  {unit}".strip())
            self.readout_captions.append((caption_label, caption, unit))
            caption_label.setObjectName("readoutCaption")
            value_label = QLabel("—")
            value_label.setObjectName("readoutValue")
            if key == "delta":
                value_label.setMinimumWidth(88)
            elif key == "pacenote":
                value_label.setMinimumWidth(270)
            box.addWidget(caption_label)
            box.addWidget(value_label)
            layout.addLayout(box)
            self.readout[key] = value_label
        layout.addStretch(1)
        return frame

    def _build_replay_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("replayPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        self.replay_split = GripSplitter(Qt.Orientation.Vertical)
        self.replay_split.setChildrenCollapsible(False)
        self._replay_split_save = QTimer(self)
        self._replay_split_save.setSingleShot(True)
        self._replay_split_save.setInterval(400)
        self._replay_split_save.timeout.connect(
            lambda: self._save_ui_state({
                "replay_split": self.replay_split.sizes()}))
        self.replay_split.splitterMoved.connect(self._on_replay_split_moved)
        video_block = QFrame()
        vbox = QVBoxLayout(video_block)
        vbox.setContentsMargins(6, 4, 6, 4)
        vbox.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(6)
        title = QLabel("REPLAY")
        title.setObjectName("cardTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.replay_state = QLabel(tr("无录像"))
        self.replay_state.setObjectName("cardHint")
        head.addWidget(self.replay_state)
        vbox.addLayout(head)

        target_row = QHBoxLayout()
        target_row.setSpacing(6)
        target_label = QLabel(tr("录像窗口"))
        target_label.setObjectName("cardHint")
        target_row.addWidget(target_label)
        self.video_target_combo = QComboBox()
        # window titles are long; without this the combo's size hint made the
        # whole replay panel unable to shrink below ~700px
        self.video_target_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.video_target_combo.setToolTip(
            tr("自动匹配会找 AC Rally 窗口；如果游戏窗口名不含这些字，\n"
               "从列表里选它。列表按打开面板时刷新。")
        )
        self.video_target_combo.currentIndexChanged.connect(
            self._on_video_target_changed
        )
        target_row.addWidget(self.video_target_combo, 1)
        refresh_target = QPushButton(tr("刷新"))
        refresh_target.clicked.connect(self._populate_video_targets)
        target_row.addWidget(refresh_target)
        vbox.addLayout(target_row)

        self.video_view = QLabel()
        self.video_view.setObjectName("videoView")
        self.video_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_view.setMinimumHeight(96)
        # Ignored, not Expanding: a QLabel reports the last painted pixmap size
        # as its minimum size hint, which ratcheted the pane (and the whole
        # replay panel) to the biggest size it had ever been, so neither could
        # be dragged smaller again once a video frame was on screen.
        self.video_view.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
        )
        self.video_view.setText(tr("尚无录像\n开启自动录像后按赛段生成"))
        self.video_view.installEventFilter(self)
        vbox.addWidget(self.video_view, 1)

        transport = QHBoxLayout()
        transport.setSpacing(4)
        self.play_btn = QPushButton(tr("播放"))
        self.play_btn.clicked.connect(self._on_play_toggle)
        transport.addWidget(self.play_btn)
        back_btn = QPushButton("−3s")
        back_btn.setToolTip(tr("后退 3 秒"))
        back_btn.clicked.connect(lambda: self._nudge_video(-3.0))
        transport.addWidget(back_btn)
        fwd_btn = QPushButton("+3s")
        fwd_btn.setToolTip(tr("前进 3 秒"))
        fwd_btn.clicked.connect(lambda: self._nudge_video(3.0))
        transport.addWidget(fwd_btn)
        self.video_time = QLabel("0:00.0 / —")
        self.video_time.setObjectName("cardHint")
        transport.addWidget(self.video_time)
        transport.addStretch(1)
        self.video_follow = QCheckBox(tr("跟随"))
        self.video_follow.setToolTip(tr("播放时图表光标和地图跟着视频走"))
        self.video_follow.setChecked(True)
        transport.addWidget(self.video_follow)
        vbox.addLayout(transport)

        levels = QHBoxLayout()
        levels.setSpacing(4)
        mute_btn = QPushButton(tr("静音"))
        mute_btn.setCheckable(True)
        mute_btn.toggled.connect(self._on_mute_toggled)
        levels.addWidget(mute_btn)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setToolTip(tr("音量"))
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        levels.addWidget(self.volume_slider, 1)
        self.video_align = QPushButton(tr("对齐到光标"))
        self.video_align.setToolTip(
            tr("把视频当前位置标成图表光标所在的赛段时刻。\n"
               "手动导入的录像用这个对齐一次即可。")
        )
        self.video_align.clicked.connect(self._on_align_video)
        levels.addWidget(self.video_align)
        open_btn = QPushButton(tr("打开…"))
        open_btn.setToolTip(tr("导入外部录像文件（录屏软件拍的也能用）"))
        open_btn.clicked.connect(self._on_open_external_video)
        levels.addWidget(open_btn)
        self.quality_combo = QComboBox()
        self._quality_labels = []
        for label, width, height, bitrate in (
            ("720p", 1280, 720, 5.0),
            ("1080p", 1920, 1080, 8.0),
            ("1440p", 2560, 1440, 14.0),
        ):
            self._quality_labels.append(label)
            self.quality_combo.addItem(
                tr("画质 {label}").format(label=label),
                {"width": width, "height": height, "bitrate_mbps": bitrate},
            )
        self.quality_combo.setToolTip(tr("录像分辨率与码率（下一段赛段生效）"))
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        levels.addWidget(self.quality_combo)
        vbox.addLayout(levels)

        map_block = QFrame()
        mbox = QVBoxLayout(map_block)
        mbox.setContentsMargins(6, 4, 6, 4)
        mbox.setSpacing(4)
        map_head = QHBoxLayout()
        map_head.setSpacing(6)
        map_title = QLabel(tr("赛道地图"))
        map_title.setObjectName("cardSubTitle")
        map_head.addWidget(map_title)
        map_head.addStretch(1)
        self.map_hint = QLabel(tr("红=比参考慢 绿=更快 · 每100m"))
        self.map_hint.setObjectName("cardHint")
        map_head.addWidget(self.map_hint)
        mbox.addLayout(map_head)

        self.track_map = TrackMap()
        # small enough that the video above it can still be dragged bigger
        self.track_map.setMinimumHeight(120)
        self.track_map.distance_clicked.connect(self._on_map_clicked)
        self.track_map.distance_hovered.connect(self._on_map_hovered)
        mbox.addWidget(self.track_map, 1)

        self.replay_split.addWidget(video_block)
        self.replay_split.addWidget(map_block)
        layout.addWidget(self.replay_split, 1)

        self.replay_panel = panel
        self._populate_video_targets()
        return panel

    def _apply_panel_state(self) -> None:
        state = self._load_ui_state()
        visible = bool(state.get("replay_panel", True))
        self.replay_panel.setVisible(visible)
        if self.replay_panel_toggle is not None:
            self.replay_panel_toggle.setChecked(visible)
        if visible:
            # the splitter has no geometry yet while the window is being built,
            # so restoring the panel width has to wait for the first show
            QTimer.singleShot(0, lambda: self._resize_panel(self._panel_width()))
            sizes = state.get("replay_split")
            if isinstance(sizes, list) and len(sizes) == 2:
                self.replay_split.setSizes([int(sizes[0]), int(sizes[1])])
            else:
                QTimer.singleShot(0, self._fit_replay_split)

    def _fit_replay_split(self) -> None:
        """First run: give the video the bigger half instead of the map."""
        total = sum(self.replay_split.sizes()) or self.replay_split.height()
        if total <= 0:
            return
        video = int(round(total * 0.62))
        self.replay_split.setSizes([video, total - video])

    def _begin_panel_drag(self) -> None:
        """Freeze the charts while the replay panel is dragged left/right.

        Six pyqtgraph plots cost ~80ms to repaint, so resizing them on every
        mouse move made the drag a slideshow. They keep the pixels they have
        and repaint once the handle is released.
        """
        if getattr(self, "_chart_drag_frozen", False):
            return
        self._chart_drag_frozen = True
        self.chart_scroll.setUpdatesEnabled(False)

    def _end_panel_drag(self) -> None:
        if not getattr(self, "_chart_drag_frozen", False):
            return
        self._chart_drag_frozen = False
        self.chart_scroll.setUpdatesEnabled(True)
        viewport = self.chart_scroll.viewport()
        if viewport is not None:
            viewport.update()
        QTimer.singleShot(0, self._sync_axis_width)

    def _on_replay_split_moved(self, _pos: int, _index: int) -> None:
        self._replay_split_save.start()

    def _on_main_split_moved(self, _pos: int, _index: int) -> None:
        self._replay_split_save.start()

    def _panel_width(self) -> int:
        return int(self._load_ui_state().get("replay_width") or 0) or 420

    def _resize_panel(self, width: int) -> None:
        if self.main_split is None:
            return
        sizes = self.main_split.sizes()
        if len(sizes) != 3:
            return
        total = sum(sizes) or self.width() or 1840
        charts = self.main_split.widget(1)
        # QSplitter silently redistributes when a pane is pushed under another
        # pane's minimum, which would shrink the panel back on every restore.
        chart_min = max(charts.minimumSizeHint().width(), charts.minimumWidth())
        room = total - sizes[0] - chart_min
        width = max(260, min(int(width), max(260, room)))
        if sizes[2] == width:
            return
        self.main_split.setSizes([sizes[0], total - sizes[0] - width, width])

    def _on_toggle_replay_panel(self, checked: bool) -> None:
        self.replay_panel.setVisible(checked)
        if checked:
            self._resize_panel(self._panel_width())
        self._save_ui_state()

    def _on_language_changed(self, _index: int) -> None:
        code = self.lang_combo.currentData()
        if not code or str(code) == acr_i18n.language():
            return
        previous = acr_i18n.language()
        acr_i18n.set_language(str(code))
        self._save_ui_state({"language": str(code)})
        self._retranslate(previous)
        self.status.showMessage(tr("语言已切换"))

    def _retranslate(self, previous: str) -> None:
        """Swap every visible string in place, then rebuild the dynamic parts."""
        def conv(text: str) -> str:
            return acr_i18n.translate_value(text, previous, acr_i18n.language())

        central = self.centralWidget()
        if central is not None:
            for widget in central.findChildren(QWidget):
                if isinstance(widget, (QLabel, QPushButton, QCheckBox, QRadioButton)):
                    widget.setText(conv(widget.text()))
                elif isinstance(widget, QGroupBox):
                    widget.setTitle(conv(widget.title()))
                elif isinstance(widget, QTabWidget):
                    for i in range(widget.count()):
                        widget.setTabText(i, conv(widget.tabText(i)))
                elif isinstance(widget, QComboBox):
                    for i in range(widget.count()):
                        widget.setItemText(i, conv(widget.itemText(i)))
                tip = widget.toolTip()
                if tip:
                    widget.setToolTip(conv(tip))
        for plot in getattr(self, "plots", ()):
            title = getattr(plot, "titleLabel", None)
            if title is not None and getattr(title, "text", ""):
                plot.setTitle(conv(title.text))
            legend = getattr(plot, "legend", None)
            for entry in (getattr(legend, "items", []) if legend is not None else []):
                try:
                    entry[1].setText(conv(entry[1].text))
                except Exception:
                    pass
            for side in ("left", "right"):
                try:
                    axis = plot.getAxis(side)
                    if getattr(axis, "labelText", ""):
                        axis.setLabel(conv(axis.labelText),
                                      color=C["muted"], size="8pt")
                except Exception:
                    pass
        for label, caption, unit in self.readout_captions:
            label.setText(f"{tr(caption)}  {unit}".strip())
        for index, name in enumerate(getattr(self, "_quality_labels", [])):
            self.quality_combo.setItemText(
                index, tr("画质 {label}").format(label=name))
        if self.current is not None:
            self._update_summary()
            self._update_analysis()
            self._update_splits()
            self._update_incidents()
            self._update_pace_notes()
        self._refresh_video_usage()
        message = self.status.currentMessage()
        if message:
            self.status.showMessage(conv(message))
        if self.tray is not None:
            menu = self.tray.contextMenu()
            for action in (menu.actions() if menu is not None else []):
                if action.text():
                    action.setText(conv(action.text()))

    def _load_ui_state(self) -> dict:
        if not hasattr(self, "_ui_state"):
            try:
                self._ui_state = json.loads(
                    self._layout_path().read_text(encoding="utf-8")
                )
            except Exception:
                self._ui_state = {}
        return self._ui_state

    def _save_ui_state(self, extra: dict | None = None) -> None:
        state = dict(self._load_ui_state())
        state["chart_heights"] = [round(h, 1) for h in self._chart_heights]
        state["replay_panel"] = bool(
            self.replay_panel is not None and self.replay_panel.isVisible()
        )
        if self.main_split is not None:
            sizes = self.main_split.sizes()
            # a hidden pane reports 0, which must not become the stored width
            if len(sizes) == 3 and sizes[2] > 0:
                state["replay_width"] = int(sizes[2])
        if extra:
            state.update(extra)
        self._ui_state = state
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._layout_path().write_text(
                json.dumps(state, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _rebuild_map(self) -> None:
        if self.track_map is None:
            return
        run = self.current
        if run is None:
            self.track_map.show_message(tr("没有数据"))
            return
        path = getattr(self, "_map_path", None)
        if getattr(self, "_map_run_id", None) != run.id:
            path = acr_track.build_path(run)
            self._map_path = path
            self._map_run_id = run.id
        if path is None:
            self.track_map.show_message(tr("此 run 无赛道数据"))
            self.map_hint.setText(tr("需要 velocity 列"))
            return
        self.map_hint.setText(tr("红=比参考慢 绿=更快 · 每100m"))
        self.track_map.set_path(path)
        compare = self.compare or {}
        self.track_map.set_delta(compare.get("distance"), compare.get("delta"))
        self._map_pacenotes()
        distances = [item["distance"] for item in run.incidents]
        majors = [bool(item.get("major")) for item in run.incidents]
        self.track_map.set_incidents(distances, majors)
        self.track_map.set_cursor(self._cursor_x)

    def _map_pacenotes(self) -> None:
        pairs = list(getattr(self, "_pacenote_notes", []) or [])
        if self.track_map.path is None or not pairs:
            self.track_map.set_pacenotes(np.asarray([]), [])
            return
        distances = np.asarray([rel for _note, rel in pairs], dtype=float)
        limit = float(self.track_map.path.dist[-1])
        keep = (np.isfinite(distances)
                & (distances >= 0.0) & (distances <= limit))
        colors = [
            QBrush(QColor(self._pacenote_color(note)))
            for (note, _rel), ok in zip(pairs, keep)
            if bool(ok)
        ]
        self.track_map.set_pacenotes(distances[keep], colors)

    def _on_map_clicked(self, distance: float) -> None:
        self._set_cursor_x(distance)
        self._follow_pacenote(distance)
        self._seek_video_to_distance(distance)

    def _on_map_hovered(self, distance: float) -> None:
        if self.track_map is None or self.track_map.path is None:
            return
        index = self.track_map.path.index_at_dist(distance)
        speed = float(self.track_map.path.speed[index])
        self.track_map.cursor_label.setText(
            f"{distance:,.0f} m · {speed:.0f} km/h"
        )

    def _build_sidebar(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(360)
        scroll.setMaximumWidth(460)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self._build_summary_card())
        layout.addWidget(self._build_analysis_card())
        layout.addWidget(self._build_incidents_card())
        layout.addStretch(1)
        scroll.setWidget(body)
        return scroll

    def _build_summary_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        top = QHBoxLayout()
        title = QLabel("STAGE TIME")
        title.setObjectName("cardTitle")
        top.addWidget(title)
        top.addStretch(1)
        self.clean_badge = QLabel("—")
        self.clean_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.clean_badge)
        layout.addLayout(top)

        self.time_label = QLabel("—")
        self.time_label.setObjectName("bigTime")
        layout.addWidget(self.time_label)
        self.delta_label = QLabel("—")
        self.delta_label.setObjectName("delta")
        layout.addWidget(self.delta_label)
        self.ref_label = QLabel(tr("等待数据…"))
        self.ref_label.setObjectName("muted")
        self.ref_label.setWordWrap(True)
        layout.addWidget(self.ref_label)

        track_row = QHBoxLayout()
        track_row.setSpacing(8)
        track_caption = QLabel(tr("赛道"))
        track_caption.setObjectName("statCaption")
        track_caption.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.track_label = QLabel("—")
        self.track_label.setObjectName("trackLabel")
        self.track_label.setWordWrap(True)
        self.track_label.setTextFormat(Qt.TextFormat.RichText)
        track_row.addWidget(track_caption, 0)
        track_row.addWidget(self.track_label, 1)
        layout.addLayout(track_row)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background:#1e293b;")
        layout.addWidget(divider)

        grid = QGridLayout()
        grid.setContentsMargins(0, 6, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        stats = (
            ("distance", tr("距离 km")),
            ("avg", tr("平均 km/h")),
            ("max", tr("最高 km/h")),
            ("full", tr("全油 %")),
            ("brake", tr("刹车 %")),
            ("coast", tr("滑行 %")),
            ("stationary", tr("静止 s")),
            ("incidents", tr("事件")),
        )
        for i, (key, caption) in enumerate(stats):
            box = QFrame()
            box.setObjectName("stat")
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(8, 5, 8, 5)
            box_layout.setSpacing(1)
            caption_label = QLabel(caption)
            caption_label.setObjectName("statCaption")
            value_label = QLabel("—")
            value_label.setObjectName("statValue")
            box_layout.addWidget(caption_label)
            box_layout.addWidget(value_label)
            grid.addWidget(box, i // 2, i % 2)
            self.stat_values[key] = value_label
        layout.addLayout(grid)
        return card

    def _build_analysis_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        title = QLabel("TIME ANALYSIS")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        top = QHBoxLayout()
        self.theoretical_label = QLabel(tr("理论最佳  —"))
        self.theoretical_label.setObjectName("muted")
        top.addWidget(self.theoretical_label)
        top.addStretch(1)
        self.potential_label = QLabel(tr("可提升  —"))
        self.potential_label.setObjectName("delta")
        top.addWidget(self.potential_label)
        layout.addLayout(top)

        self.analysis_note = QLabel(tr("100m 分段 · 已剔除参考事件区"))
        self.analysis_note.setObjectName("muted")
        self.analysis_note.setWordWrap(True)
        layout.addWidget(self.analysis_note)

        self.analysis_tabs = QTabWidget()
        self.analysis_tabs.setDocumentMode(True)
        self.analysis_tabs.setMinimumHeight(300)

        zone_wrap = QWidget()
        zone_layout = QVBoxLayout(zone_wrap)
        zone_layout.setContentsMargins(0, 4, 0, 0)
        zone_layout.setSpacing(2)
        self.zone_list = QListWidget()
        self.zone_list.itemClicked.connect(self._on_zone_clicked)
        zone_layout.addWidget(self.zone_list)
        self.analysis_tabs.addTab(zone_wrap, "Gains / Losses")

        brake_wrap = QWidget()
        brake_layout = QVBoxLayout(brake_wrap)
        brake_layout.setContentsMargins(0, 4, 0, 0)
        brake_layout.setSpacing(2)
        brake_note = QLabel(tr("刹车/弯区 · 入 / 弯心 / 出 · 当前 / 参考"))
        brake_note.setObjectName("muted")
        brake_layout.addWidget(brake_note)
        self.brake_list = QListWidget()
        self.brake_list.itemClicked.connect(self._on_zone_clicked)
        brake_layout.addWidget(self.brake_list)
        self.analysis_tabs.addTab(brake_wrap, "Brakes")

        split_wrap = QWidget()
        split_layout = QVBoxLayout(split_wrap)
        split_layout.setContentsMargins(0, 4, 0, 0)
        self.splits_table = QTableWidget(0, 4)
        self.splits_table.setHorizontalHeaderLabels([tr("距离"), tr("参考"), tr("当前"), "Δ"])
        self.splits_table.verticalHeader().setVisible(False)
        self.splits_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.splits_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.splits_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.splits_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.splits_table.setShowGrid(False)
        self.splits_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.splits_table.setFixedHeight(210)
        split_layout.addWidget(self.splits_table)
        self.analysis_tabs.addTab(split_wrap, "Splits")

        pace_wrap = QWidget()
        pace_layout = QVBoxLayout(pace_wrap)
        pace_layout.setContentsMargins(0, 4, 0, 0)
        pace_layout.setSpacing(4)
        pace_top = QHBoxLayout()
        pace_top.setSpacing(6)
        pace_top.addWidget(self._selector_label(tr("赛段")))
        self.pace_combo = QComboBox()
        self.pace_combo.currentIndexChanged.connect(self._on_pace_stage_changed)
        self.pace_combo.setEnabled(bool(self.pacenote_book.stages))
        pace_top.addWidget(self.pace_combo, 1)
        pace_layout.addLayout(pace_top)
        self._fill_pace_combo()
        self.pace_note = QLabel("—")
        self.pace_note.setObjectName("muted")
        self.pace_note.setWordWrap(True)
        pace_layout.addWidget(self.pace_note)
        self.pace_list = QListWidget()
        self.pace_list.itemClicked.connect(self._on_pacenote_clicked)
        pace_layout.addWidget(self.pace_list)
        self.analysis_tabs.addTab(pace_wrap, "Pace Notes")

        layout.addWidget(self.analysis_tabs)
        return card

    def _fill_pace_combo(self) -> None:
        self.pace_combo.blockSignals(True)
        self.pace_combo.clear()
        self.pace_combo.addItem(tr("自动匹配"), None)
        for key in sorted(self.pacenote_book.stages, key=acr_pacenotes.display_name):
            self.pace_combo.addItem(acr_pacenotes.display_name(key), key)
        self.pace_combo.blockSignals(False)

    def _on_pace_stage_changed(self, _index: int) -> None:
        if self._updating:
            return
        self._pacenote_stage = self.pace_combo.currentData()
        self._update_pace_notes()
        if self.track_map is not None and self.track_map.path is not None:
            self._map_pacenotes()

    def _update_track_label(self, stage=None) -> None:
        if not hasattr(self, "track_label"):
            return
        if self.current is None:
            self.track_label.setText("—")
            self.track_label.setToolTip("")
            return
        meta = self.current.meta or {}
        track = str(meta.get("track") or "").strip().replace("_", " ")
        config = str(meta.get("track_configuration") or "").strip()
        if config:
            config = acr_pacenotes.display_name(config.replace("_", " "))
        raw = " · ".join(part for part in (track, config) if part)
        lines = []
        tips = []
        if raw:
            lines.append(
                f"<span style='color:{C['blue']};font-weight:600'>"
                f"{html_escape(raw)}</span>"
                f" <span style='color:{C['muted']};font-weight:400'>"
                f"{tr('· 游戏数据')}</span>"
            )
            tips.append(tr("游戏赛道：{track}").format(track=raw))
        if stage is not None:
            source = tr("自动匹配") if raw else tr("按路书距离")
            prefix = (
                f"<span style='color:{C['muted']};font-weight:400'>"
                f"{tr('路书')}</span> "
                if raw
                else ""
            )
            lines.append(
                f"{prefix}<span style='color:{C['blue']};font-weight:600'>"
                f"{html_escape(stage.label)}</span>"
                f" <span style='color:{C['muted']};font-weight:400'>"
                f"· {source}</span>"
            )
            tips.append(tr("路书表：{table}（{source}）").format(
                table=stage.label, source=source))
        if not lines:
            self.track_label.setText("—")
            self.track_label.setToolTip("")
            return
        self.track_label.setText("<br>".join(lines))
        self.track_label.setToolTip("\n".join(tips))

    def _update_pace_notes(self) -> None:
        self._clear_pacenote_highlight()
        self._hide_pacenote_hover()
        self._clear_pacenote_readout()
        self._pacenote_follow_x = None
        self.pace_list.clear()
        self._pacenote_notes = []
        self._update_track_label(None)
        if self.pacenote_book.error:
            self.setWindowTitle(f"ACR Telemetry Studio · v{APP_VERSION}")
            self.pace_note.setText(tr("路书加载失败：{error}").format(
                error=self.pacenote_book.error))
            self._draw_pacenote_markers()
            return
        if self.current is None or not self.pacenote_book.stages:
            self.setWindowTitle(f"ACR Telemetry Studio · v{APP_VERSION}")
            self.pace_note.setText(tr("— 没有可用的赛段路书"))
            self._draw_pacenote_markers()
            return

        auto_key = acr_pacenotes.auto_stage(self.current, self.pacenote_book)
        auto_stage = self.pacenote_book.stages.get(auto_key or "")
        self._update_track_label(auto_stage)
        self.setWindowTitle(
            f"ACR Telemetry Studio · v{APP_VERSION} · {auto_stage.label}"
            if auto_stage is not None
            else f"ACR Telemetry Studio · v{APP_VERSION}"
        )
        self.pace_combo.setItemText(
            0,
            tr("自动匹配 · {stage}").format(stage=auto_stage.label)
            if auto_stage is not None
            else tr("自动匹配"),
        )
        key = self._pacenote_stage or auto_key
        stage = self.pacenote_book.stages.get(key or "")
        if stage is None:
            self.pace_note.setText(tr("— 没有匹配到赛段路书"))
            self._draw_pacenote_markers()
            return

        start = float(self.current.summary.get("start_distance", 0.0))
        max_x = float(self.current.traces["x"][-1]) if len(self.current.traces["x"]) else 0.0
        self._pacenote_notes = acr_pacenotes.relative_notes(stage, start)
        shown = 0
        for note, x in self._pacenote_notes:
            if x < -60.0 or x > max_x + 250.0:
                continue
            item = QListWidgetItem(
                f"{x:6.0f} m   {note.text}"
                + ("   ↔" if note.link else "")
            )
            color = self._pacenote_color(note)
            item.setForeground(QBrush(QColor(color)))
            item.setData(
                Qt.ItemDataRole.UserRole,
                {"x": x, "distance": note.distance, "text": note.text},
            )
            item.setToolTip(
                tr("路书距离 {dist:,.0f} m · 赛段相对 {rel:,.0f} m\n"
                   "参考长度 {length:,.0f} m").format(
                    dist=note.distance, rel=x, length=note.length)
                + ("\n" + tr("与下一条连贯") if note.link else "")
                + "\n" + tr("点击缩放到 {rel:,.0f} m").format(rel=x)
            )
            item.setSizeHint(QSize(0, 30))
            self.pace_list.addItem(item)
            shown += 1

        mode = tr("手动选择") if self._pacenote_stage else tr("自动匹配")
        text = tr("{mode} · {stage} · {n} 条").format(
            mode=mode, stage=stage.label, n=shown)
        meta = self.current.meta or {}
        if not self._pacenote_stage and not str(meta.get("track") or "").strip():
            text += tr(" · 按距离")
        if stage.start < start - 80.0 or stage.end > max_x + start + 300.0:
            text += tr(" · 与本次距离范围不完全匹配")
        self.pace_note.setText(text)
        self._draw_pacenote_markers()
        if self.current is not None:
            self._update_readout(self._cursor_index)
            self._follow_pacenote(self._cursor_x)

    def _draw_pacenote_markers(self) -> None:
        for plot, item in self._pacenote_items:
            plot.removeItem(item)
        self._pacenote_items = []
        if not self._pacenote_notes or self.current is None:
            return
        max_x = float(self.current.traces["x"][-1]) if len(self.current.traces["x"]) else 0.0
        groups: dict[str, list[float]] = {}
        for note, x in self._pacenote_notes:
            if x < 0.0 or x > max_x:
                continue
            groups.setdefault(self._pacenote_color(note), []).append(x)
        if not groups:
            return
        for plot in (self.delta_plot, self.speed_plot):
            lo, hi = plot.viewRange()[1]
            span = max(hi - lo, 1e-6)
            tick_lo = hi - span * 0.14
            tick_hi = hi - span * 0.02
            for color, xs in groups.items():
                x_data = []
                y_data = []
                for x in xs:
                    x_data.extend((x, x, np.nan))
                    y_data.extend((tick_lo, tick_hi, np.nan))
                item = pg.PlotCurveItem(
                    np.asarray(x_data),
                    np.asarray(y_data),
                    pen=pg.mkPen(color, width=1, style=Qt.PenStyle.DotLine),
                    connect="finite",
                )
                item.setZValue(30)
                plot.addItem(item, ignoreBounds=True)
                self._pacenote_items.append((plot, item))

    def _pacenote_color(self, note) -> str:
        return {
            "brake": C["amber"],
            "turn": C["blue"],
            "distance": C["dim"],
            "finish": C["green"],
            "other": C["muted"],
        }[note.category]

    def _nearest_pacenote(self, x: float):
        if not self._pacenote_notes:
            return None
        return min(self._pacenote_notes, key=lambda pair: abs(pair[1] - x))

    def _clear_pacenote_readout(self) -> None:
        label = self.readout.get("pacenote")
        if label is not None:
            label.setText("—")
            label.setStyleSheet("")
            label.setToolTip("")

    def _follow_pacenote(self, x: float) -> None:
        nearest = self._nearest_pacenote(x)
        if nearest is None:
            return
        _note, note_x = nearest
        if self._pacenote_follow_x is not None and abs(note_x - self._pacenote_follow_x) < 0.5:
            return
        self._pacenote_follow_x = note_x
        for index in range(self.pace_list.count()):
            item = self.pace_list.item(index)
            payload = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(payload, dict) and abs(float(payload.get("x", -1e9)) - note_x) < 0.5:
                self.pace_list.setCurrentItem(item)
                self.pace_list.scrollToItem(
                    item,
                    QAbstractItemView.ScrollHint.PositionAtCenter,
                )
                return

    def _ensure_pacenote_hover(self):
        if self._pacenote_hover is None:
            label = pg.TextItem(
                "",
                color=C["text"],
                anchor=(0.5, 0),
                fill=pg.mkBrush(15, 23, 42, 235),
                border=pg.mkPen(C["border"]),
            )
            label.setZValue(100)
            self.speed_plot.addItem(label, ignoreBounds=True)
            self._pacenote_hover = label
        return self._pacenote_hover

    def _hide_pacenote_hover(self) -> None:
        if self._pacenote_hover is not None:
            self._pacenote_hover.setVisible(False)

    def eventFilter(self, obj, event) -> bool:
        event_type = event.type()
        if event_type == QEvent.Type.Leave:
            scroll = getattr(self, "chart_scroll", None)
            if (
                (scroll is not None and obj is scroll.viewport())
                or obj in getattr(self, "_chart_widgets", ())
            ):
                self._hide_pacenote_hover()
        elif event_type == QEvent.Type.Wheel:
            if obj in getattr(self, "_chart_viewports", {}):
                self._handle_chart_wheel(obj, event)
                return True
        elif event_type == QEvent.Type.Resize:
            if obj is getattr(self, "video_view", None):
                # the picture is a scaled pixmap, so it keeps its old size
                # until the next decoded frame unless we repaint it here.
                # Rescaling a 1080p frame is not cheap, so coalesce a burst of
                # resize events (splitter drags) into one repaint.
                timer = getattr(self, "_video_resize_timer", None)
                if timer is not None:
                    timer.start()
            if obj in getattr(self, "_chart_widgets", ()):
                self._sync_axis_width_to(obj.width())
        return super().eventFilter(obj, event)

    def _handle_chart_wheel(self, viewport, event) -> None:
        delta = event.angleDelta().y()
        if not delta:
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            plot, widget = self._chart_viewports[viewport]
            x0, x1 = self.speed_plot.viewRange()[0]
            if x1 - x0 <= 1e-6:
                return
            scene_pos = widget.mapToScene(event.position().toPoint())
            center = float(plot.vb.mapSceneToView(scene_pos).x())
            center = min(max(center, x0), x1)
            scale = 0.8 if delta > 0 else 1.25
            max_x = 1.0
            if self.current is not None and len(self.current.traces["x"]):
                max_x = max(1.0, float(self.current.traces["x"][-1]))
            width = min(
                max(10.0, (x1 - x0) * scale),
                max(10.0, max_x * 1.05),
            )
            fraction = (center - x0) / (x1 - x0)
            low = center - width * fraction
            low = max(0.0, min(low, max(0.0, max_x - width)))
            self.speed_plot.setXRange(low, low + width, padding=0)
        else:
            bar = self.chart_scroll.verticalScrollBar()
            bar.setValue(bar.value() - delta)
        event.accept()

    def _update_pacenote_hover(self, plot, x: float) -> None:
        if self.current is None or not self._pacenote_notes:
            self._hide_pacenote_hover()
            return
        view = plot.viewRange()[0]
        width = float(plot.vb.width())
        if width <= 1.0 or view[1] <= view[0]:
            self._hide_pacenote_hover()
            return
        nearest = self._nearest_pacenote(x)
        if nearest is None:
            self._hide_pacenote_hover()
            return
        note, note_x = nearest
        threshold = max(0.5, 6.0 * (view[1] - view[0]) / width)
        if abs(note_x - x) > threshold:
            self._hide_pacenote_hover()
            return
        label = self._ensure_pacenote_hover()
        label.setColor(QColor(self._pacenote_color(note)))
        label.setText(f"{note_x:.0f} m  {note.text}")
        speed_view = self.speed_plot.viewRange()
        x0, x1 = speed_view[0]
        y0, y1 = speed_view[1]
        relative = (note_x - x0) / max(x1 - x0, 1e-6)
        anchor_x = 0.5
        if relative <= 0.15:
            anchor_x = 0.0
        elif relative >= 0.85:
            anchor_x = 1.0
        label.setAnchor((anchor_x, 0))
        label.setPos(note_x, y1 - (y1 - y0) * 0.2)
        label.setVisible(True)

    def _clear_pacenote_highlight(self) -> None:
        for plot, item in self._pacenote_highlight:
            plot.removeItem(item)
        self._pacenote_highlight = []
        if self._pacenote_label is not None:
            self.speed_plot.removeItem(self._pacenote_label)
            self._pacenote_label = None

    def _on_pacenote_clicked(self, item: QListWidgetItem) -> None:
        if self.current is None:
            return
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict):
            return
        x = float(payload["x"])
        max_x = float(self.current.traces["x"][-1]) if len(self.current.traces["x"]) else x
        lo = max(0.0, min(x - 120.0, max_x - 240.0))
        self.speed_plot.setXRange(lo, lo + 360.0, padding=0)
        self._set_cursor_x(x)
        self._seek_video_to_distance(x)
        self._clear_pacenote_highlight()
        for plot in (self.delta_plot, self.speed_plot):
            line = pg.InfiniteLine(
                pos=x,
                angle=90,
                movable=False,
                pen=pg.mkPen(C["yellow"], width=1.5),
            )
            line.setZValue(75)
            plot.addItem(line, ignoreBounds=True)
            self._pacenote_highlight.append((plot, line))
        lo_y, hi_y = self.speed_plot.viewRange()[1]
        label = pg.TextItem(
            f"{x:.0f} m  {payload['text']}",
            color=C["yellow"],
            anchor=(0.5, 1.0),
        )
        label.setPos(x, hi_y)
        label.setZValue(90)
        self.speed_plot.addItem(label, ignoreBounds=True)
        self._pacenote_label = label

    def _build_incidents_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        title = QLabel("INCIDENTS")
        title.setObjectName("cardTitle")
        layout.addWidget(title)
        self.incident_list = QListWidget()
        self.incident_list.setMinimumHeight(220)
        self.incident_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.incident_list.itemClicked.connect(self._on_incident_clicked)
        layout.addWidget(self.incident_list)
        return card

    def _build_charts(self) -> None:
        self.chart_scroll = QScrollArea()
        self.chart_scroll.setObjectName("chartScroll")
        self.chart_scroll.setWidgetResizable(True)
        self.chart_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chart_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.chart_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.chart_scroll.viewport().installEventFilter(self)

        self.chart_content = QWidget()
        self.chart_content.setObjectName("chartContent")
        self.chart_layout = QVBoxLayout(self.chart_content)
        self.chart_layout.setContentsMargins(8, 6, 8, 6)
        self.chart_layout.setSpacing(0)
        self.chart_scroll.setWidget(self.chart_content)

        self.delta_plot = self._new_plot(0.8, "DELTA · s")
        self.speed_plot = self._new_plot(1.45, "SPEED · km/h")
        self.input_plot = self._new_plot(1.15, "THROTTLE / BRAKE · %")
        self.gear_plot = self._new_plot(1.0, "GEAR / RPM")
        self.g_plot = self._new_plot(1.0, "STEERING / G")
        self.tire_plot = self._new_plot(1.25, "TYRES · °C / psi")
        self.plots = (
            self.delta_plot,
            self.speed_plot,
            self.input_plot,
            self.gear_plot,
            self.g_plot,
            self.tire_plot,
        )
        for plot in self.plots:
            if plot is not self.speed_plot:
                plot.setXLink(self.speed_plot)
            plot.getAxis("bottom").setStyle(showValues=False)
            right = plot.getAxis("right")
            plot.showAxis("right")
            right.setWidth(54)
            right.setStyle(showValues=False)
            right.setPen(pg.mkPen(None))
            right.setTextPen(pg.mkPen(None))
        for plot, label in (
            (self.delta_plot, "s"),
            (self.speed_plot, "km/h"),
            (self.input_plot, "%"),
            (self.gear_plot, tr("挡位")),
            (self.g_plot, tr("转向 %")),
            (self.tire_plot, "°C"),
        ):
            try:
                plot.getAxis("left").setLabel(label, color=C["muted"], size="8pt")
            except TypeError:
                plot.getAxis("left").setLabel(label)

        self.axis_plot = self._build_axis_plot()
        self.speed_plot.vb.sigXRangeChanged.connect(self._sync_fixed_axis)
        heights = self._load_chart_layout()
        if heights is None:
            heights = self._nominal_chart_heights()
        else:
            self._chart_heights_from_file = True
        self._set_chart_heights(heights, save=False)
        self.chart_scroll.verticalScrollBar().rangeChanged.connect(
            self._sync_axis_width
        )
        QTimer.singleShot(0, self._sync_axis_width)

        self.delta_plot.addItem(
            pg.InfiniteLine(
                pos=0,
                angle=0,
                movable=False,
                pen=pg.mkPen(C["border"], width=1),
            ),
            ignoreBounds=True,
        )

        delta_legend = self._make_legend(self.delta_plot)
        self._series["delta_pos"] = self._add_series(
            self.delta_plot,
            tr("更慢"),
            C["red"],
            width=1.4,
            fill=pg.mkBrush(239, 68, 68, 50),
            legend=delta_legend,
        )
        self._series["delta_neg"] = self._add_series(
            self.delta_plot,
            tr("更快"),
            C["green"],
            width=1.4,
            fill=pg.mkBrush(34, 197, 94, 50),
            legend=delta_legend,
        )

        speed_legend = self._make_legend(self.speed_plot)
        self._series["speed_cur"] = self._add_series(
            self.speed_plot, tr("当前"), C["green"], width=2.0, legend=speed_legend
        )
        self._series["speed_ref"] = self._add_series(
            self.speed_plot,
            tr("参考"),
            C["dim"],
            width=1.2,
            style=Qt.PenStyle.DashLine,
            legend=speed_legend,
        )

        input_legend = self._make_legend(self.input_plot)
        self._series["gas_cur"] = self._add_series(
            self.input_plot,
            tr("油门 当前"),
            C["green"],
            width=1.4,
            fill=pg.mkBrush(34, 197, 94, 32),
            legend=input_legend,
        )
        self._series["brake_cur"] = self._add_series(
            self.input_plot,
            tr("刹车 当前"),
            C["red"],
            width=1.4,
            fill=pg.mkBrush(239, 68, 68, 32),
            legend=input_legend,
        )
        # reference traces keep a colour the current traces never use, plus a
        # distinct pattern: yellow dashed for throttle, blue dash-dot for brake
        self._series["gas_ref"] = self._add_series(
            self.input_plot,
            tr("油门 参考"),
            C["yellow"],
            width=1.4,
            style=Qt.PenStyle.DashLine,
            legend=input_legend,
        )
        self._series["brake_ref"] = self._add_series(
            self.input_plot,
            tr("刹车 参考"),
            C["blue"],
            width=1.4,
            style=Qt.PenStyle.DashDotLine,
            legend=input_legend,
        )

        gear_legend = self._make_legend(self.gear_plot)
        self._series["gear"] = self._add_series(
            self.gear_plot, tr("挡位"), C["text"], width=1.5, legend=gear_legend
        )
        gear_right = self._right_axis(self.gear_plot, "RPM")
        self._right_views["rpm"] = gear_right
        self._series["rpm"] = self._add_series(
            self.gear_plot,
            "RPM",
            C["purple"],
            width=1.5,
            view=gear_right,
            legend=gear_legend,
        )

        g_legend = self._make_legend(self.g_plot)
        self._series["steer"] = self._add_series(
            self.g_plot, tr("转向 %"), C["blue"], width=1.5, legend=g_legend
        )
        g_right = self._right_axis(self.g_plot, "G")
        self._right_views["g"] = g_right
        self._series["glat"] = self._add_series(
            self.g_plot,
            tr("横向 G"),
            C["amber"],
            width=1.4,
            view=g_right,
            legend=g_legend,
        )
        self._series["glon"] = self._add_series(
            self.g_plot,
            tr("纵向 G"),
            C["yellow"],
            width=1.4,
            view=g_right,
            legend=g_legend,
        )

        tire_legend = self._make_legend(self.tire_plot)
        colors = (C["blue"], C["amber"], C["purple"], C["pink"])
        for i, wheel in enumerate(acr_data.WHEELS):
            self._series[f"tt_{i}"] = self._add_series(
                self.tire_plot,
                tr("{wheel} 温度").format(wheel=wheel),
                colors[i],
                width=1.6,
                legend=tire_legend,
            )
        tire_right = self._right_axis(self.tire_plot, "psi")
        self._right_views["psi"] = tire_right
        for i, wheel in enumerate(acr_data.WHEELS):
            self._series[f"press_{i}"] = self._add_series(
                self.tire_plot,
                tr("{wheel} 胎压").format(wheel=wheel),
                colors[i],
                width=1.0,
                style=Qt.PenStyle.DashLine,
                view=tire_right,
            )

        for plot in self.plots:
            line = pg.InfiniteLine(
                angle=90,
                movable=False,
                pen=pg.mkPen(C["cursor"], width=1),
            )
            line.setZValue(50)
            plot.addItem(line, ignoreBounds=True)
            self._cursor_lines.append((plot, line))

        self.speed_dot = pg.ScatterPlotItem(
            size=9,
            brush=pg.mkBrush(C["green"]),
            pen=pg.mkPen(C["bg"], width=2),
        )
        self.speed_dot.setZValue(60)
        self.speed_plot.addItem(self.speed_dot, ignoreBounds=True)
        self._mouse_proxies = [
            pg.SignalProxy(
                plot.scene().sigMouseMoved,
                rateLimit=60,
                slot=lambda event, p=plot: self._on_plot_mouse_moved(p, event),
            )
            for plot in self.plots
        ]

    def _new_plot(self, factor: float, title: str) -> pg.PlotItem:
        widget = pg.PlotWidget(background=C["bg"])
        widget.setFrameShape(QFrame.Shape.NoFrame)
        widget.setMinimumHeight(90)
        widget.setStyleSheet("background: transparent;")
        widget.installEventFilter(self)
        self.chart_layout.addWidget(widget)
        self._chart_widgets.append(widget)
        self._chart_heights.append(120.0)
        self._chart_default_factors.append(factor)

        plot = widget.getPlotItem()
        plot.hideButtons()
        plot.setMenuEnabled(False)
        plot.showGrid(x=True, y=True, alpha=0.16)
        plot.setTitle(title, color=C["muted"], size="8pt")
        for axis_name in ("left", "bottom", "right"):
            axis = plot.getAxis(axis_name)
            axis.setPen(pg.mkPen(C["border"]))
            axis.setTextPen(pg.mkPen(C["muted"]))
            try:
                axis.setStyle(tickFont=QFont("Consolas", 8))
            except TypeError:
                pass
        plot.getAxis("left").setWidth(54)
        plot.getAxis("left").setLabel(color=C["muted"], size="8pt")
        plot.getAxis("right").setWidth(54)

        widget.viewport().installEventFilter(self)
        self._chart_viewports[widget.viewport()] = (plot, widget)
        self._chart_handles.append(
            self._add_chart_handle(len(self._chart_widgets) - 1)
        )
        return plot

    def _add_chart_handle(self, index: int) -> ChartResizeHandle:
        handle = ChartResizeHandle(self, index)
        self.chart_layout.addWidget(handle)
        return handle

    def _build_axis_plot(self) -> pg.PlotWidget:
        axis = pg.PlotWidget(background=C["bg"])
        axis.setFixedHeight(34)
        axis.setFrameShape(QFrame.Shape.NoFrame)
        axis.setStyleSheet("background: transparent;")
        axis.hideButtons()
        axis.setMenuEnabled(False)
        item = axis.getPlotItem()
        item.setMouseEnabled(x=False, y=False)
        item.getViewBox().disableAutoRange()
        item.setXRange(0, 1, padding=0)
        for axis_name in ("left", "right"):
            spacer = item.getAxis(axis_name)
            item.showAxis(axis_name)
            spacer.setWidth(54)
            spacer.setStyle(showValues=False)
            spacer.setPen(pg.mkPen(None))
            spacer.setTextPen(pg.mkPen(None))
        item.showGrid(x=True, y=False, alpha=0.16)
        bottom = item.getAxis("bottom")
        bottom.setPen(pg.mkPen(C["border"]))
        bottom.setTextPen(pg.mkPen(C["muted"]))
        try:
            bottom.setStyle(tickFont=QFont("Consolas", 8))
        except TypeError:
            pass
        try:
            bottom.setLabel(tr("距离 (m)"), color=C["muted"], size="8pt")
        except TypeError:
            bottom.setLabel(tr("距离 (m)"))
        axis.viewport().installEventFilter(self)
        self._chart_viewports[axis.viewport()] = (self.speed_plot, axis)
        return axis

    def _set_chart_grid(self, visible: bool) -> None:
        for plot in getattr(self, "plots", ()):
            plot.showGrid(x=visible, y=visible, alpha=0.16)

    def _restore_chart_grid(self) -> None:
        if not self._grid_hidden:
            return
        self._grid_hidden = False
        self._set_chart_grid(True)

    def _sync_fixed_axis(self, _view, x_range) -> None:
        if not self._grid_hidden:
            self._grid_hidden = True
            self._set_chart_grid(False)
        self._grid_timer.start()
        self._pending_axis = (float(x_range[0]), float(x_range[1]))
        if not self._axis_timer.isActive():
            self._axis_timer.start()

    def _flush_axis_sync(self) -> None:
        pending = self._pending_axis
        self._pending_axis = None
        if pending is None:
            return
        self.axis_plot.setXRange(pending[0], pending[1], padding=0)

    def _sync_axis_width(self, *_args) -> None:
        if not self._chart_widgets:
            return
        self._sync_axis_width_to(self._chart_widgets[0].width())

    def _sync_axis_width_to(self, width: int) -> None:
        if not hasattr(self, "axis_plot"):
            return
        if width <= 120:
            return
        # keep the axis as wide as the chart above it, but only as a maximum:
        # setFixedWidth also pinned chart_card's minimum width, which stopped
        # the main splitter from shrinking the chart pane during a drag.
        if self.axis_plot.maximumWidth() != width:
            self.axis_plot.setMaximumWidth(width)
        if self.axis_plot.minimumWidth() != 0:
            self.axis_plot.setMinimumWidth(0)

    def _nominal_chart_heights(self) -> list[float]:
        available = 760.0
        total = sum(self._chart_default_factors) or 1.0
        return [
            float(int(max(90.0, available * factor / total)))
            for factor in self._chart_default_factors
        ]

    def _fit_chart_heights(self, save: bool = False) -> None:
        viewport = self.chart_scroll.viewport().height()
        if viewport <= 100:
            viewport = 760
        margins = self.chart_layout.contentsMargins()
        handles = len(self._chart_handles) * 8
        available = max(
            300.0,
            float(viewport - handles - margins.top() - margins.bottom()),
        )
        total = sum(self._chart_default_factors) or 1.0
        heights = [
            float(int(max(90.0, available * factor / total)))
            for factor in self._chart_default_factors
        ]
        self._set_chart_heights(heights, save=save)

    def _set_chart_height(self, index: int, height: float) -> None:
        heights = list(self._chart_heights)
        heights[index] = max(90.0, min(1600.0, float(height)))
        self._set_chart_heights(heights, save=False)

    def _set_chart_heights(self, heights: list[float], save: bool = False) -> None:
        if len(heights) != len(self._chart_widgets):
            return
        self._chart_heights = [float(value) for value in heights]
        for widget, height in zip(self._chart_widgets, self._chart_heights):
            widget.setFixedHeight(int(round(height)))
        margins = self.chart_layout.contentsMargins()
        total = (
            sum(int(round(height)) for height in self._chart_heights)
            + len(self._chart_handles) * 8
            + margins.top()
            + margins.bottom()
        )
        self.chart_content.setFixedHeight(total)
        QTimer.singleShot(0, self._sync_axis_width)
        QTimer.singleShot(0, self._apply_chart_scales)
        if save:
            self._save_chart_layout()

    # --- vertical scale ---------------------------------------------------
    def _scale_targets(self) -> list:
        """(key, view, widget) for every Y axis that keeps a fixed scale."""
        names = ("delta", "speed", "input", "gear", "steer", "tyre")
        targets = [(name, plot, plot.getViewWidget())
                   for name, plot in zip(names, self.plots)]
        owners = {"rpm": self.gear_plot, "g": self.g_plot, "psi": self.tire_plot}
        for key, view in self._right_views.items():
            owner = owners.get(key)
            if owner is not None:
                targets.append((f"{key}_right", view, owner.getViewWidget()))
        return targets

    def _remember_scales(self) -> None:
        """Record each axis' full extent and the units-per-pixel it was fit to.

        The chart then keeps that scale: shrinking a chart clips its bottom
        instead of squeezing the whole trace into fewer pixels.
        """
        for name, view, widget in self._scale_targets():
            lo, hi = view.viewRange()[1]
            height = max(1.0, float(widget.height()))
            self._chart_scale[name] = (float(lo), float(hi), (float(hi) - float(lo)) / height)
            self._watch_scale(name, view)

    def _watch_scale(self, name: str, view) -> None:
        """Follow a manual Y zoom: the user's own scale becomes the reference."""
        if name in self._scale_watched:
            return
        self._scale_watched.add(name)
        box = getattr(view, "vb", view)
        box.sigYRangeChanged.connect(
            lambda _box, span, key=name: self._on_user_y_range(key, span))

    def _on_user_y_range(self, name: str, span) -> None:
        if self._applying_scale or name not in self._chart_scale:
            return
        lo, _hi, _upp = self._chart_scale[name]
        widget = dict(
            (key, holder) for key, _view, holder in self._scale_targets()).get(name)
        extent = float(span[1]) - float(span[0])
        if widget is None or extent <= 1e-9:
            return
        # keep the data's full extent, but let their zoom set the scale
        self._chart_scale[name] = (lo, self._chart_scale[name][1],
                                   extent / max(1.0, float(widget.height())))

    def _apply_chart_scales(self) -> None:
        """Keep units-per-pixel constant, whatever the chart box is doing.

        Shrinking clips the trace (top and bottom equally around the current
        centre); growing keeps the same slope and shows blank space instead of
        stretching the curve to fill the box.
        """
        self._applying_scale = True
        try:
            for name, view, widget in self._scale_targets():
                saved = self._chart_scale.get(name)
                if saved is None:
                    continue
                lo, hi, upp = saved
                span = upp * max(1.0, float(widget.height()))
                current = view.viewRange()[1]
                centre = (float(current[0]) + float(current[1])) / 2.0
                if abs(centre - (lo + hi) / 2.0) > (hi - lo):
                    centre = (lo + hi) / 2.0
                view.setYRange(centre - span / 2.0, centre + span / 2.0, padding=0)
        finally:
            self._applying_scale = False

    def _layout_path(self) -> Path:
        return self.directory / "ui_layout.json"

    def _load_chart_layout(self) -> list[float] | None:
        try:
            data = json.loads(self._layout_path().read_text(encoding="utf-8"))
            heights = data.get("chart_heights")
            if not isinstance(heights, list) or len(heights) != len(self._chart_widgets):
                return None
            values = [float(value) for value in heights]
            if not all(90.0 <= value <= 1600.0 for value in values):
                return None
            return values
        except Exception:
            return None

    def _save_chart_layout(self) -> None:
        self._save_ui_state()

    def _on_reset_chart_heights(self) -> None:
        self._chart_heights_from_file = True
        self._fit_chart_heights(save=True)

    def _make_legend(self, plot: pg.PlotItem) -> pg.LegendItem:
        legend = plot.addLegend(
            offset=(10, 6),
            brush=pg.mkBrush(8, 13, 23, 210),
            pen=pg.mkPen(C["border"]),
        )
        legend.setLabelTextColor(C["muted"])
        try:
            legend.setLabelTextSize("8pt")
        except Exception:
            pass
        return legend

    def _add_series(
        self,
        plot: pg.PlotItem,
        name: str,
        color,
        width: float = 1.5,
        style: Qt.PenStyle = Qt.PenStyle.SolidLine,
        fill=None,
        view: pg.ViewBox | None = None,
        legend: pg.LegendItem | None = None,
    ) -> pg.PlotDataItem:
        pen = pg.mkPen(color, width=width, style=style)
        item = pg.PlotDataItem(
            [],
            [],
            pen=pen,
            antialias=False,
            fillLevel=0 if fill is not None else None,
            brush=fill,
            connect="finite",
        )
        if view is None:
            plot.addItem(item)
        else:
            view.addItem(item)
        # after addItem: PlotItem.addItem() overwrites these with its defaults
        item.setDownsampling(auto=True, method="peak")
        item.setClipToView(True)
        # lets a static view repaint the curve from a cached pixmap; big win
        # for cursor moves, which would otherwise re-stroke every curve
        item.curve.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        if legend is not None:
            legend.addItem(item, name)
        return item

    def _right_axis(self, plot: pg.PlotItem, label: str) -> pg.ViewBox:
        view = pg.ViewBox()
        view.setMouseEnabled(x=False, y=False)
        try:
            view.setBackgroundColor(pg.mkColor(0, 0, 0, 0))
        except AttributeError:
            pass
        plot.scene().addItem(view)
        plot.getAxis("right").linkToView(view)
        view.setXLink(plot)
        plot.showAxis("right")
        axis = plot.getAxis("right")
        axis.setWidth(54)
        try:
            axis.setStyle(showValues=True)
        except TypeError:
            pass
        try:
            axis.setLabel(label, color=C["muted"], size="8pt")
        except TypeError:
            axis.setLabel(label)
        axis.setPen(pg.mkPen(C["border"]))
        axis.setTextPen(pg.mkPen(C["muted"]))
        plot.vb.sigResized.connect(lambda: self._sync_right_view(view, plot))
        self._sync_right_view(view, plot)
        return view

    def _sync_right_view(self, view: pg.ViewBox, plot: pg.PlotItem) -> None:
        view.setGeometry(plot.vb.sceneBoundingRect())
        view.linkedViewChanged(plot.vb, view.XAxis)

    def _make_tray_icon(self, color: str) -> QIcon:
        if color in self._tray_icons:
            return self._tray_icons[color]
        pix = QPixmap(64, 64)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor("#0f172a")))
        painter.setPen(QPen(QColor("#334155"), 2))
        painter.drawEllipse(3, 3, 58, 58)
        painter.setPen(QPen(QColor("#e2e8f0")))
        font = QFont("Segoe UI", 22)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pix.rect(), int(Qt.AlignmentFlag.AlignCenter), "A")
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawEllipse(44, 44, 14, 14)
        painter.end()
        icon = QIcon(pix)
        self._tray_icons[color] = icon
        return icon

    def _set_live(self, state: str, detail: str) -> None:
        colors = {
            "recording": C["red"],
            "armed": C["blue"],
            "waiting": C["dim"],
            "saved": C["green"],
            "preview": C["muted"],
        }
        labels = {
            "recording": "REC",
            "armed": "ARMED",
            "waiting": "WAITING",
            "saved": "SAVED",
            "preview": "PREVIEW",
        }
        color = colors.get(state, C["dim"])
        self.live_dot.setStyleSheet(f"color:{color};")
        self.live_state.setText(labels.get(state, state.upper()))
        self.live_state.setStyleSheet(
            f"color:{color};font-size:8pt;font-weight:700;letter-spacing:1px;"
        )
        self.live_detail.setText(detail)
        self._update_tray(state, detail)

    def _update_tray(self, state: str, detail: str) -> None:
        if self.tray is None:
            return
        color = {
            "recording": C["red"],
            "armed": C["blue"],
            "waiting": C["dim"],
            "saved": C["green"],
            "preview": C["muted"],
        }.get(state, C["green"])
        self.tray.setIcon(self._make_tray_icon(color))
        self.tray.setToolTip(f"ACR Telemetry · {detail[:120]}")

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self._make_tray_icon(C["green"]), self)
        self.tray.setToolTip(tr("ACR Telemetry · 等待 AC Rally"))
        menu = QMenu(self)
        self._tray_menu = menu
        show_action = QAction(tr("显示分析"), self)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)
        self.tray_auto_action = QAction(tr("自动录制"), self)
        self.tray_auto_action.setCheckable(True)
        self.tray_auto_action.setChecked(True)
        self.tray_auto_action.toggled.connect(self._on_tray_auto_toggled)
        menu.addAction(self.tray_auto_action)
        self.tray_video_action = QAction(tr("自动录像"), self)
        self.tray_video_action.setCheckable(True)
        self.tray_video_action.setChecked(True)
        self.tray_video_action.toggled.connect(self._on_tray_video_toggled)
        menu.addAction(self.tray_video_action)
        open_action = QAction(tr("打开数据目录"), self)
        open_action.triggered.connect(self._open_data_dir)
        menu.addAction(open_action)
        menu.addSeparator()
        quit_action = QAction(tr("退出"), self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()
        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(False)

    def _setup_auto_recorder(self) -> None:
        self._set_live("waiting", tr("等待 AC Rally …"))
        self._auto_recorder = AutoRecorder(self.directory)
        self._auto_recorder.live.connect(self._on_live)
        self._auto_recorder.finished_run.connect(self._on_run_finished)
        self._auto_recorder.connection.connect(self._on_connection)
        self._auto_recorder.video_event.connect(self._on_video_event)
        self._apply_video_settings()
        self._auto_recorder.start()
        self._refresh_video_usage()

    def _on_connection(self, connected: bool) -> None:
        if connected:
            self.status.showMessage(tr("已连接共享内存 · 等待赛段"))
        else:
            self.status.showMessage(tr("等待 AC Rally …"))

    def _on_live(self, data: dict) -> None:
        state = str(data.get("state", "waiting"))
        if time.monotonic() < self._saved_until and state in ("waiting", "armed"):
            return
        if state == "recording":
            self._saved_until = 0.0
            detail = tr("{time} · {speed:.0f} km/h · {gear}挡 · "
                        "油门 {gas:.0f}% · 刹车 {brake:.0f}% · {rows} 行").format(
                time=acr_data.format_time(data.get("stage_time", 0.0)),
                speed=data.get("speed", 0.0),
                gear=int(data.get("gear", 0)),
                gas=data.get("gas", 0.0),
                brake=data.get("brake", 0.0),
                rows=data.get("rows", 0),
            )
            self._set_live("recording", detail)
        elif state == "saved":
            detail = str(data.get("message", tr("已保存")))
            self._saved_until = time.monotonic() + 8.0
            self._set_live("saved", detail)
        else:
            self._set_live(state, str(data.get("message", "")))

    def _on_run_finished(self, path: str, stage_time: float) -> None:
        self._new_run_path = path
        self._auto_select_newest = True
        self._saved_message = tr("已保存 {time} · 分析更新中…").format(
            time=acr_data.format_time(stage_time))
        self._saved_until = time.monotonic() + 20.0
        self._set_live("saved", self._saved_message)
        if self.loader is None:
            self.start_loader()
        else:
            self._reload_pending = True

    def _on_auto_toggle(self, _state: int) -> None:
        enabled = self.auto_check.isChecked()
        if self.tray_auto_action is not None:
            self.tray_auto_action.blockSignals(True)
            self.tray_auto_action.setChecked(enabled)
            self.tray_auto_action.blockSignals(False)
        if self._auto_recorder is not None:
            self._auto_recorder.set_auto(enabled)
        self._set_live(
            "armed" if enabled else "waiting",
            tr("自动录制已开启 · 等待赛段")
            if enabled
            else tr("自动录制已关闭"),
        )

    def _on_tray_auto_toggled(self, checked: bool) -> None:
        if self.auto_check.isChecked() == checked:
            return
        self.auto_check.blockSignals(True)
        self.auto_check.setChecked(checked)
        self.auto_check.blockSignals(False)
        self._on_auto_toggle(0)

    # --- auto video -------------------------------------------------------
    def _apply_video_settings(self) -> None:
        if self._auto_recorder is None:
            return
        state = self._load_ui_state()
        self._auto_recorder.set_video(
            enabled=bool(state.get("video_enabled", True)),
            window=str(state.get("video_window", "") or ""),
            fps=int(state.get("video_fps", 60)),
            width=int(state.get("video_width", 1920)),
            height=int(state.get("video_height", 1080)),
            bitrate_mbps=float(state.get("video_bitrate", 8.0)),
        )
        settings = self._auto_recorder.video_settings()
        for widget, key in (
            (self.video_check, "enabled"),
            (self.tray_video_action, "enabled"),
        ):
            if widget is None:
                continue
            widget.blockSignals(True)
            widget.setChecked(bool(settings[key]))
            widget.blockSignals(False)
        index = self.quality_combo.findData(
            {"width": int(state.get("video_width", 1920)),
             "height": int(state.get("video_height", 1080)),
             "bitrate_mbps": float(state.get("video_bitrate", 8.0))}
        ) if hasattr(self, "quality_combo") else -1
        if index >= 0 and hasattr(self, "quality_combo"):
            self.quality_combo.blockSignals(True)
            self.quality_combo.setCurrentIndex(index)
            self.quality_combo.blockSignals(False)
        self._populate_video_targets()

    def _populate_video_targets(self) -> None:
        combo = getattr(self, "video_target_combo", None)
        if combo is None:
            return
        wanted = str(self._load_ui_state().get("video_window", "") or "")
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tr("自动匹配 AC Rally"), "")
        try:
            import acr_video

            for _hwnd, title in acr_video.list_windows():
                combo.addItem(title[:44], title)
        except Exception:
            pass
        index = combo.findData(wanted)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _on_quality_changed(self, _index: int) -> None:
        if self._updating:
            return
        spec = self.quality_combo.currentData() or {}
        if self._auto_recorder is not None:
            self._auto_recorder.set_video(**spec)
        self._save_ui_state({
            "video_width": spec.get("width", 1920),
            "video_height": spec.get("height", 1080),
            "video_bitrate": spec.get("bitrate_mbps", 8.0),
        })

    def _on_video_target_changed(self, _index: int) -> None:
        if self._updating:
            return
        value = str(self.video_target_combo.currentData() or "")
        if self._auto_recorder is not None:
            self._auto_recorder.set_video(window=value)
        self._save_ui_state({"video_window": value})

    def _on_video_toggle(self, _state: int = 0) -> None:
        enabled = self.video_check.isChecked()
        if self.tray_video_action is not None:
            self.tray_video_action.blockSignals(True)
            self.tray_video_action.setChecked(enabled)
            self.tray_video_action.blockSignals(False)
        if self._auto_recorder is not None:
            self._auto_recorder.set_video(enabled=enabled)
        self._save_ui_state({"video_enabled": enabled})
        self.status.showMessage(
            tr("自动录像已开启 · 跑赛段时同步录制画面和声音")
            if enabled
            else tr("自动录像已关闭")
        )

    def _on_tray_video_toggled(self, checked: bool) -> None:
        if self.video_check.isChecked() == checked:
            return
        self.video_check.blockSignals(True)
        self.video_check.setChecked(checked)
        self.video_check.blockSignals(False)
        self._on_video_toggle()

    def _on_video_event(self, data: dict) -> None:
        state = str(data.get("state", "idle"))
        if state == "recording":
            target = data.get("target") or tr("自动匹配窗口")
            self._set_replay_state(tr("录像中 · {target}").format(target=target))
            if self.video_view is not None:
                self.video_view.setText(tr("录像中…\n回放面板在赛段结束后可播放"))
            self.status.showMessage(tr("正在录像 · {target}").format(target=target))
        elif state == "error":
            message = tr("录像失败：{error}").format(error=data.get("error"))
            self._set_replay_state(tr("录像失败"))
            self.status.showMessage(message)
            if self.tray is not None:
                self.tray.showMessage(
                    "ACR Telemetry", message + "\n" + tr("遥测照常录制"),
                    QSystemTrayIcon.MessageIcon.Warning, 6000,
                )
        else:
            if data.get("discarded"):
                self._set_replay_state(tr("赛段重置 · 录像已丢弃"))
            elif data.get("error"):
                self._set_replay_state(tr("录像中断"))
            else:
                self._set_replay_state(
                    tr("录像 {seconds:.0f}s · {mb:.0f}MB").format(
                        seconds=data.get("seconds", 0), mb=data.get("mb", 0)))

            self._refresh_video_usage()

    def _set_replay_state(self, text: str) -> None:
        if self.replay_state is not None:
            self.replay_state.setText(text)

    def _video_dir(self) -> Path:
        return self.directory / "videos"

    def _refresh_video_usage(self) -> None:
        folder = self._video_dir()
        files = sorted(folder.glob("*.mp4")) if folder.exists() else []
        total_mb = sum(f.stat().st_size for f in files) / 1048576.0
        if not files:
            self.video_info.setText(tr("无录像"))
            self.video_info.setToolTip(tr("跑完赛段后自动出现在这里 · 点击打开目录"))
            return
        self.video_info.setText(
            tr("录像 {n} · {gb:.2f}GB").format(n=len(files), gb=total_mb / 1024.0)
            if total_mb >= 1024
            else tr("录像 {n} · {mb:.0f}MB").format(n=len(files), mb=total_mb)
        )
        self.video_info.setToolTip(
            tr("{folder}\n共 {n} 段 · {mb:.0f}MB\n点击打开目录").format(
                folder=folder, n=len(files), mb=total_mb)
        )

    def _open_video_folder(self) -> None:
        folder = self._video_dir()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    # --- playback and three-way sync --------------------------------------
    def _setup_player(self) -> None:
        self._player = acr_play.VideoPlayer(self)
        self._player.frame_ready.connect(self._on_video_frame)
        self._player.position_changed.connect(self._on_video_position)
        self._player.state_changed.connect(self._on_video_state)
        self._player.error.connect(self._on_video_play_error)

    def _video_offset(self) -> float:
        override = getattr(self, "_video_offset_override", {})
        key = self.current.id if self.current else None
        if key in override:
            return float(override[key])
        meta = (self.current.meta if self.current else {}) or {}
        return float(meta.get("video_offset", 0.0) or 0.0)

    def _video_path_for(self, run) -> Path | None:
        name = (run.meta or {}).get("video") if run else None
        if not name:
            return None
        path = self._video_dir() / name
        return path if path.exists() else None

    def _stage_time_at(self, distance: float) -> float:
        traces = self.current.traces
        return float(np.interp(distance, traces["x"], traces["t"]))

    def _distance_at_time(self, stage_time: float) -> float:
        traces = self.current.traces
        return float(np.interp(stage_time, traces["t"], traces["x"]))

    def _load_run_video(self) -> None:
        """Attach the recording that belongs to the selected run, if any."""
        player = getattr(self, "_player", None)
        if player is None:
            return
        self._video_offset_override = getattr(self, "_video_offset_override", {})
        player.stop()
        run = self.current
        self._last_frame = None
        path = self._manual_video or self._video_path_for(run)
        if path is None:
            self.video_view.setText(
                tr("此 run 没有录像\n自动录像开启后按赛段生成")
                if run is not None else tr("尚无录像"))
            self._set_replay_state(tr("无录像"))
            self.video_time.setText("0:00.0 / —")
            self.play_btn.setEnabled(False)
            return
        if not player.load(path):
            self._set_replay_state(tr("录像打不开"))
            self.play_btn.setEnabled(False)
            return
        self.play_btn.setEnabled(True)
        label = tr("外部录像 · 需对齐") if self._manual_video else tr("录像就绪")
        self._set_replay_state(f"{label} {acr_data.format_time(player.duration)}")
        self.video_time.setText(
            f"0:00.0 / {acr_data.format_time(player.duration)}")

    def _seek_video_to_distance(self, distance: float, play: bool = True) -> None:
        player = getattr(self, "_player", None)
        if player is None or player._container is None or self.current is None:
            return
        seconds = self._stage_time_at(distance) - self._video_offset()
        if seconds < 0.0:
            seconds = 0.0
        self._video_sync_guard = True
        player.seek(seconds)
        if play and player.state_name != "playing":
            player.play(from_seconds=seconds)
        self._video_sync_guard = False

    def _nudge_video(self, seconds: float) -> None:
        player = getattr(self, "_player", None)
        if player is None or player._container is None:
            return
        player.seek((player._thread.playhead if player._thread else 0.0) + seconds)

    def _on_play_toggle(self) -> None:
        player = getattr(self, "_player", None)
        if player is None or player._container is None:
            return
        player.toggle()

    def _on_volume_changed(self, value: int) -> None:
        player = getattr(self, "_player", None)
        if player is not None:
            player.set_volume(value / 100.0)

    def _on_mute_toggled(self, checked: bool) -> None:
        player = getattr(self, "_player", None)
        if player is not None:
            player.set_muted(checked)

    def _on_video_frame(self, image, _when: float) -> None:
        if self.video_view is None or image.isNull():
            return
        self._last_frame = image
        self._paint_video_frame()

    def _paint_video_frame(self) -> None:
        """Keep the picture's aspect instead of stretching it to the pane."""
        image = getattr(self, "_last_frame", None)
        if self.video_view is None or image is None or image.isNull():
            return
        pixmap = QPixmap.fromImage(image).scaled(
            self.video_view.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_view.setText("")
        self.video_view.setPixmap(pixmap)

    def _on_video_position(self, seconds: float) -> None:
        player = getattr(self, "_player", None)
        if player is None or self.video_time is None:
            return
        self.video_time.setText(
            f"{acr_data.format_time(seconds)} / "
            f"{acr_data.format_time(player.duration)}"
        )
        if self._video_sync_guard or not self.video_follow.isChecked():
            return
        if self.current is None or player._thread is None:
            return
        distance = self._distance_at_time(seconds + self._video_offset())
        max_x = float(self.current.traces["x"][-1]) if len(self.current.traces["x"]) else 0.0
        if not 0.0 <= distance <= max_x:
            return
        self._video_sync_guard = True
        self._pending_cursor = (distance, None)
        if not self._cursor_timer.isActive():
            self._cursor_timer.start()
        self._video_sync_guard = False

    def _on_video_state(self, state: str) -> None:
        if self.play_btn is None:
            return
        self.play_btn.setText(tr("暂停") if state == "playing" else tr("播放"))

    def _on_video_play_error(self, message: str) -> None:
        self.status.showMessage(message)
        self._set_replay_state(tr("播放失败"))

    def _on_align_video(self) -> None:
        """Pin the video's current instant to the chart cursor's distance."""
        player = getattr(self, "_player", None)
        if player is None or player._container is None or self.current is None:
            self.status.showMessage(tr("先加载一段录像再对齐"))
            return
        position = player._thread.playhead if player._thread else 0.0
        key = self.current.id
        offset = self._stage_time_at(self._cursor_x) - position
        self._video_offset_override[key] = offset
        player.pause()
        self._set_replay_state(
            tr("已对齐 {dist:,.0f}m ↔ {time}").format(
                dist=self._cursor_x, time=acr_data.format_time(position)))
        self.status.showMessage(
            tr("录像已对齐：视频 {time} = {dist:,.0f} m").format(
                time=acr_data.format_time(position), dist=self._cursor_x))

    def _on_open_external_video(self) -> None:
        start = str(self._video_dir())
        path, _ = QFileDialog.getOpenFileName(
            self, tr("选择录像文件"), start, tr("视频 (*.mp4 *.mkv *.mov *.avi)"))
        if not path:
            return
        self._manual_video = Path(path)
        self._load_run_video()
        self.status.showMessage(
            tr("外部录像已载入 · 把光标放到已知点（如终点）后点“对齐到光标”"))

    def _on_tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show_window()

    def _show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _open_data_dir(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.directory)))

    def _quit_app(self) -> None:
        self._real_quit = True
        self.close()
        QApplication.quit()

    def closeEvent(self, event) -> None:
        if self.tray is not None and not self._real_quit:
            self.hide()
            self.tray.showMessage(
                "ACR Telemetry",
                tr("仍在托盘运行，赛段开始会自动录制"),
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
            event.ignore()
            return
        if self._auto_recorder is not None:
            self._auto_recorder.stop()
        if self.tray is not None:
            self.tray.hide()
        event.accept()

    def start_loader(self) -> None:
        if self.loader is not None:
            return
        self.current_combo.setEnabled(False)
        self.reference_combo.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.status.showMessage(tr("正在扫描 telemetry/*.csv …"))
        self._loading_text = tr("正在扫描 telemetry/*.csv …")
        self.loader = Loader(self.directory)
        self.loader.loaded.connect(self._on_loaded)
        self.loader.failed.connect(self._on_failed)
        self.loader.finished.connect(self._loader_finished)
        self.loader.start()

    def _loader_finished(self) -> None:
        self.loader = None
        if self._reload_pending:
            self._reload_pending = False
            self.start_loader()

    def _main_runs(self, runs):
        if not runs:
            return []
        longest = max(float(run.summary.get("distance", 0.0)) for run in runs)
        if longest <= 0:
            return list(runs)
        return [
            run
            for run in runs
            if float(run.summary.get("distance", 0.0)) >= longest * 0.8
        ]

    def _on_loaded(self, runs) -> None:
        self.current_combo.setEnabled(True)
        self.reference_combo.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        current_id = self.current_combo.currentData()
        reference_id = self.reference_combo.currentData()

        if self._auto_select_newest:
            self._auto_select_newest = False
            new_name = Path(self._new_run_path).name if self._new_run_path else None
            new_run = next(
                (
                    run
                    for run in runs
                    if new_name is not None and new_name in run.source_files
                ),
                None,
            )
            if new_run is not None:
                current_id = new_run.id
                candidates = [
                    run for run in self._main_runs(runs) if run.id != current_id
                ]
                if not candidates:
                    candidates = [run for run in runs if run.id != current_id]
                reference_id = (
                    min(candidates, key=lambda run: run.summary["time"]).id
                    if candidates
                    else current_id
                )
                self.set_runs(runs, current_id, reference_id)
                self._saved_message = tr("已保存 {time} · 分析已更新").format(
                    time=acr_data.format_time(new_run.summary["time"]))
                self._saved_until = time.monotonic() + 12.0
                self._set_live("saved", self._saved_message)
                if self.tray is not None:
                    self.tray.showMessage(
                        "ACR Telemetry",
                        self._saved_message,
                        QSystemTrayIcon.MessageIcon.Information,
                        5000,
                    )
            else:
                self.set_runs(runs, current_id, reference_id)
                self._saved_message = (
                    tr("录制已保存，但数据不足 5 秒，未加入分析")
                )
                self._saved_until = time.monotonic() + 10.0
                self._set_live("saved", self._saved_message)
                if self.tray is not None:
                    self.tray.showMessage(
                        "ACR Telemetry",
                        self._saved_message,
                        QSystemTrayIcon.MessageIcon.Warning,
                        5000,
                    )
        else:
            self.set_runs(runs, current_id, reference_id)

        pending = self.pending_indices
        self.pending_indices = (None, None)
        _apply_indices(self, *pending)

    def _on_failed(self, error: str) -> None:
        self._auto_select_newest = False
        self.current_combo.setEnabled(True)
        self.reference_combo.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.status.showMessage(tr("加载失败"))
        print(error, file=sys.stderr)

    def set_runs(self, runs, current_id=None, reference_id=None) -> None:
        self.runs = list(runs)
        if not self.runs:
            self.current = None
            self.reference = None
            self.current_combo.clear()
            self.reference_combo.clear()
            self.time_label.setText("—")
            self.delta_label.setText("—")
            self.ref_label.setText(tr("telemetry/ 下没有可用 CSV"))
            self.status.showMessage(tr("telemetry/ 下没有可用 CSV"))
            self._update_pace_notes()
            return

        ids = [run.id for run in self.runs]
        main_runs = self._main_runs(self.runs)
        if current_id not in ids:
            current_id = (main_runs or self.runs)[-1].id
        if reference_id not in ids:
            candidates = [run for run in main_runs if run.id != current_id]
            if not candidates:
                candidates = [run for run in self.runs if run.id != current_id]
            reference_id = (
                min(candidates, key=lambda run: run.summary["time"]).id
                if candidates
                else current_id
            )

        self._updating = True
        self.current_combo.blockSignals(True)
        self.reference_combo.blockSignals(True)
        self.current_combo.clear()
        self.reference_combo.clear()
        for run in self.runs:
            self.current_combo.addItem(run.label, run.id)
            self.reference_combo.addItem(run.label, run.id)
        self.current_combo.setCurrentIndex(self.current_combo.findData(current_id))
        self.reference_combo.setCurrentIndex(self.reference_combo.findData(reference_id))
        self.current_combo.blockSignals(False)
        self.reference_combo.blockSignals(False)
        self._updating = False
        self._apply_selection()

    def _on_selection_changed(self, _index: int) -> None:
        if self._updating:
            return
        self._apply_selection()

    def _apply_selection(self) -> None:
        current_id = self.current_combo.currentData()
        reference_id = self.reference_combo.currentData()
        current = next((r for r in self.runs if r.id == current_id), None)
        reference = next((r for r in self.runs if r.id == reference_id), None)
        if current is None or reference is None:
            return
        self.current = current
        self.reference = reference
        self._cursor_timer.stop()
        self._axis_timer.stop()
        self._pending_cursor = None
        self._pending_axis = None
        self.compare = acr_data.compare_runs(current, reference)
        self._update_summary()
        self._update_analysis()
        self._update_splits()
        self._update_incidents()
        self._update_charts()
        self._update_pace_notes()
        self._rebuild_map()
        self._load_run_video()
        self.status.showMessage(
            tr("{n} runs · {rate:.0f} Hz · {cur}  /  参考 {ref}").format(
                n=len(self.runs), rate=current.summary["rate"],
                cur=current.label, ref=reference.label)
        )

    def _update_summary(self) -> None:
        current = self.current
        reference = self.reference
        summary = current.summary
        delta = summary["time"] - reference.summary["time"]
        self.time_label.setText(acr_data.format_time(summary["time"]))
        if abs(delta) < 0.0005:
            self.delta_label.setText(tr("Δ 参考  0.000s"))
            self.delta_label.setStyleSheet(f"color:{C['muted']};")
        else:
            self.delta_label.setText(
                tr("Δ 参考  {delta:+.3f}s").format(delta=delta))
            self.delta_label.setStyleSheet(
                f"color:{C['green'] if delta < 0 else C['red']};"
            )
        self.ref_label.setText(
            tr("参考 · {ref}").format(ref=reference.label))
        if summary["clean"]:
            self.clean_badge.setText("CLEAN")
            self.clean_badge.setStyleSheet(
                "background:#052e1a;color:#6ee7b7;border:1px solid #065f46;"
                "border-radius:9px;padding:2px 8px;font-size:7.5pt;font-weight:700;"
            )
        else:
            self.clean_badge.setText(f"{summary['incidents']} EVENTS")
            self.clean_badge.setStyleSheet(
                "background:#2a1705;color:#fbbf24;border:1px solid #92400e;"
                "border-radius:9px;padding:2px 8px;font-size:7.5pt;font-weight:700;"
            )
        values = {
            "distance": f"{summary['distance']/1000:.2f}",
            "avg": f"{summary['avg_speed']:.1f}",
            "max": f"{summary['max_speed']:.1f}",
            "full": f"{summary['full_pct']:.1f}",
            "brake": f"{summary['brake_pct']:.1f}",
            "coast": f"{summary['coast_pct']:.1f}",
            "stationary": f"{summary['stationary_s']:.1f}",
            "incidents": str(summary["incidents"]),
        }
        for key, value in values.items():
            self.stat_values[key].setText(value)

    def _update_splits(self) -> None:
        splits = self.compare.get("splits", []) if self.compare else []
        self.splits_table.setRowCount(0)
        for split in splits:
            row = self.splits_table.rowCount()
            self.splits_table.insertRow(row)
            is_finish = split.get("finish", False)
            distance_text = tr("终点") if is_finish else f"{split['distance']/1000:.0f} km"
            delta = split["delta"]
            items = [
                (distance_text, C["muted"]),
                (acr_data.format_time(split["reference"]), C["dim"]),
                (acr_data.format_time(split["current"]), C["text"]),
                (f"{delta:+.2f}", C["green"] if delta < 0 else C["red"]),
            ]
            for col, (text, color) in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                item.setForeground(QBrush(QColor(color)))
                self.splits_table.setItem(row, col, item)
        self.splits_table.resizeRowsToContents()
        header_height = self.splits_table.horizontalHeader().height()
        row_height = sum(
            self.splits_table.rowHeight(i) for i in range(self.splits_table.rowCount())
        )
        self.splits_table.setFixedHeight(max(40, header_height + row_height + 4))

    def _add_zone_header(self, text: str, color: str) -> None:
        item = QListWidgetItem(text)
        item.setForeground(QBrush(QColor(color)))
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(0, 26))
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.zone_list.addItem(item)

    def _add_zone_item(self, zone: dict, color: str) -> None:
        text = (
            f"● {zone['start']/1000:.1f}–{zone['end']/1000:.1f} km    "
            f"{zone['delta']:+.2f}s"
        )
        item = QListWidgetItem(text)
        item.setForeground(QBrush(QColor(color)))
        item.setData(Qt.ItemDataRole.UserRole, zone)
        item.setToolTip(tr("点击缩放到 {start:.0f}–{end:.0f} m").format(
            start=zone["start"], end=zone["end"]))
        item.setSizeHint(QSize(0, 30))
        self.zone_list.addItem(item)

    def _update_analysis(self) -> None:
        analysis = self.compare.get("analysis", {}) if self.compare else {}
        theoretical = float(analysis.get("theoretical_time", 0.0))
        potential = float(analysis.get("potential_gain", 0.0))
        self.theoretical_label.setText(
            tr("两跑理论最佳  {time}").format(
                time=acr_data.format_time(theoretical))
            if theoretical > 0
            else tr("两跑理论最佳  —")
        )
        self.potential_label.setText(
            tr("可提升  +{gain:.2f}s").format(gain=potential))
        self.potential_label.setStyleSheet(
            f"color:{C['amber'] if potential > 0.05 else C['muted']};"
        )
        if self.reference is None or self.reference.id == self.current.id:
            self.analysis_note.setText(tr("100m 分段 · 同一 run 对比"))
        else:
            self.analysis_note.setText(
                tr("100m 分段 · 已剔除参考事件 {n} 个（灰色虚线）").format(
                    n=len(self.reference.incidents))
            )

        self.zone_list.clear()
        gains = analysis.get("top_gains", [])
        losses = analysis.get("top_losses", [])
        if not gains and not losses:
            item = QListWidgetItem(tr("— 暂无可分析的干净分段"))
            item.setForeground(QBrush(QColor(C["muted"])))
            self.zone_list.addItem(item)
        else:
            self._add_zone_header(tr("可提升 · 当前更慢"), C["red"])
            for zone in losses[:4]:
                self._add_zone_item(zone, C["red"])
            self._add_zone_header(tr("已获得 · 当前更快"), C["green"])
            for zone in gains[:4]:
                self._add_zone_item(zone, C["green"])

        self.brake_list.clear()
        brakes = analysis.get("braking_zones", [])
        if not brakes:
            item = QListWidgetItem(tr("— 没有检测到刹车区"))
            item.setForeground(QBrush(QColor(C["muted"])))
            self.brake_list.addItem(item)
        for zone in brakes:
            delta = float(zone["delta"])
            color = C["red"] if delta > 0 else C["green"]
            if zone.get("reference_incident"):
                color = C["dim"]
            text = tr("● {start:.2f} km   Δ{delta:+.2f}s   "
                      "入 {ce:.0f}/{re:.0f}  心 {cm:.0f}/{rm:.0f}  "
                      "出 {cx:.0f}/{rx:.0f}").format(
                start=zone["start"] / 1000, delta=delta,
                ce=zone["current_entry"], re=zone["reference_entry"],
                cm=zone["current_min"], rm=zone["reference_min"],
                cx=zone["current_exit"], rx=zone["reference_exit"])
            if zone.get("reference_incident"):
                text += tr("  · 参考事件附近")
            item = QListWidgetItem(text)
            item.setForeground(QBrush(QColor(color)))
            item.setData(Qt.ItemDataRole.UserRole, zone)
            item.setToolTip(tr(
                "点击缩放到 {start:.0f}–{end:.0f} m\n时间差 {delta:+.3f}s（当前 - 参考）"
            ).format(start=zone["start"], end=zone["end"], delta=delta))
            item.setSizeHint(QSize(0, 30))
            self.brake_list.addItem(item)

    def _on_zone_clicked(self, item: QListWidgetItem) -> None:
        zone = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(zone, dict):
            return
        start = float(zone["start"])
        end = float(zone["end"])
        pad = max(60.0, (end - start) * 0.4)
        lo = max(0.0, start - pad)
        hi = end + pad
        self.speed_plot.setXRange(lo, hi, padding=0)
        self._set_cursor_x((start + end) * 0.5)
        self._seek_video_to_distance(start)

    def _update_incidents(self) -> None:
        self.incident_list.clear()
        incidents = self.current.incidents if self.current else []
        if not incidents:
            item = QListWidgetItem(tr("CLEAN · 无停车 / 撞击 / 重生"))
            item.setForeground(QBrush(QColor(C["green"])))
            item.setSizeHint(QSize(0, 34))
            self.incident_list.addItem(item)
            return
        kind_labels = {"impact": tr("撞击"), "stop": tr("停车"), "respawn": tr("重生")}
        kind_colors = {"impact": C["red"], "stop": C["amber"], "respawn": C["purple"]}
        for incident in incidents:
            kind = incident["kind"]
            text = (
                f"● {acr_data.format_time(incident['t'])}   "
                f"{incident['distance']:.0f}m   "
                f"{kind_labels.get(kind, kind)}   {incident['detail']}"
            )
            item = QListWidgetItem(text)
            item.setForeground(QBrush(QColor(kind_colors.get(kind, C["text"]))))
            item.setData(Qt.ItemDataRole.UserRole, incident)
            item.setToolTip(tr("点击缩放到 {dist:.0f}m").format(
                dist=incident["distance"]))
            if incident.get("major"):
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            item.setSizeHint(QSize(0, 34))
            self.incident_list.addItem(item)

    def _update_charts(self) -> None:
        current = self.current
        reference = self.reference
        ct = current.traces
        rt = reference.traces
        comp = self.compare
        x = comp["distance"] if comp else np.asarray([])
        delta = comp["delta"] if comp else np.asarray([])
        if len(delta):
            pos = np.where(delta > 0, delta, np.nan)
            neg = np.where(delta < 0, delta, np.nan)
        else:
            pos = delta = np.asarray([])
            neg = np.asarray([])
        self._series["delta_pos"].setData(x, pos)
        self._series["delta_neg"].setData(x, neg)
        self._series["speed_cur"].setData(ct["x"], ct["speed"])
        self._series["speed_ref"].setData(rt["x"], rt["speed"])
        self._series["gas_cur"].setData(ct["x"], ct["gas"])
        self._series["brake_cur"].setData(ct["x"], ct["brake"])
        self._series["gas_ref"].setData(rt["x"], rt["gas"])
        self._series["brake_ref"].setData(rt["x"], rt["brake"])
        self._series["gear"].setData(ct["x"], ct["gear"])
        self._series["rpm"].setData(ct["x"], ct["rpm"])
        self._series["steer"].setData(ct["x"], ct["steer"])
        self._series["glat"].setData(ct["x"], ct["agx"])
        self._series["glon"].setData(ct["x"], ct["agz"])
        for i in range(4):
            self._series[f"tt_{i}"].setData(ct["x"], ct["tt"][i])
            self._series[f"press_{i}"].setData(ct["x"], ct["press"][i])

        max_x = max(float(ct["x"][-1]), float(rt["x"][-1])) if len(ct["x"]) and len(rt["x"]) else 1.0
        max_x = max(max_x, 1.0)
        self.speed_plot.setXRange(0, max_x, padding=0.01)

        if len(delta):
            limit = max(0.5, float(np.nanmax(np.abs(delta))) * 1.1)
        else:
            limit = 1.0
        self.delta_plot.setYRange(-limit, limit, padding=0)
        speed_lo, speed_hi = self._limits(ct["speed"], rt["speed"], fallback=(0, 200), pad=0.06)
        self.speed_plot.setYRange(max(0, speed_lo), speed_hi, padding=0)
        self.input_plot.setYRange(0, 100, padding=0)
        gear_hi = max(6.0, float(np.nanmax(ct["gear"])) + 0.5) if len(ct["gear"]) else 6.0
        self.gear_plot.setYRange(0, gear_hi, padding=0)
        rpm_hi = max(1000.0, float(np.nanmax(ct["rpm"])) * 1.05) if len(ct["rpm"]) else 8000.0
        self._right_views["rpm"].setYRange(0, rpm_hi, padding=0)
        steer_lim = max(20.0, float(np.nanmax(np.abs(ct["steer"]))) * 1.1 if len(ct["steer"]) else 20.0)
        self.g_plot.setYRange(-steer_lim, steer_lim, padding=0)
        g_abs = np.concatenate((np.abs(ct["agx"]), np.abs(ct["agz"]))) if len(ct["agx"]) else np.asarray([])
        g_lim = max(0.5, float(np.nanmax(g_abs)) * 1.1) if len(g_abs) else 0.5
        self._right_views["g"].setYRange(-g_lim, g_lim, padding=0)
        temp_arrays = [ct["tt"][i] for i in range(4)]
        temp_lo, temp_hi = self._limits(*temp_arrays, fallback=(0, 100), pad=0.08)
        self.tire_plot.setYRange(temp_lo, temp_hi, padding=0)
        press_arrays = [ct["press"][i] for i in range(4)]
        press_lo, press_hi = self._limits(*press_arrays, fallback=(20, 40), pad=0.08)
        self._right_views["psi"].setYRange(press_lo, press_hi, padding=0)
        self._remember_scales()

        for plot, line in self._incident_lines:
            plot.removeItem(line)
        self._incident_lines = []
        for incident in self._marker_incidents():
            color = {
                "impact": C["red"],
                "stop": C["amber"],
                "respawn": C["purple"],
            }.get(incident["kind"], C["dim"])
            for plot in (self.delta_plot, self.speed_plot):
                line = pg.InfiniteLine(
                    pos=incident["distance"],
                    angle=90,
                    movable=False,
                    pen=pg.mkPen(color, width=1, style=Qt.PenStyle.DashLine),
                )
                line.setZValue(40)
                plot.addItem(line, ignoreBounds=True)
                self._incident_lines.append((plot, line))

        if self.reference is not None and self.reference.id != self.current.id:
            for incident in self.reference.incidents:
                if incident["kind"] == "respawn":
                    show = True
                elif incident["kind"] == "impact":
                    show = incident.get("peak", 0.0) >= 80.0
                elif incident["kind"] == "stop":
                    show = incident.get("duration", 0.0) >= 2.5
                else:
                    show = False
                if not show:
                    continue
                for plot in (self.delta_plot, self.speed_plot):
                    line = pg.InfiniteLine(
                        pos=incident["distance"],
                        angle=90,
                        movable=False,
                        pen=pg.mkPen(
                            C["dim"], width=1, style=Qt.PenStyle.DotLine
                        ),
                    )
                    line.setZValue(35)
                    plot.addItem(line, ignoreBounds=True)
                    self._incident_lines.append((plot, line))

        for plot, item in self._zone_items:
            plot.removeItem(item)
        self._zone_items = []
        for label in self._zone_labels:
            self.delta_plot.removeItem(label)
        self._zone_labels = []
        analysis = self.compare.get("analysis", {}) if self.compare else {}
        zone_sets = (
            ("gain", analysis.get("top_gains", [])[:2], C["green"], pg.mkBrush(34, 197, 94, 25)),
            ("loss", analysis.get("top_losses", [])[:2], C["red"], pg.mkBrush(239, 68, 68, 25)),
        )
        for kind, zones, color, brush in zone_sets:
            for zone in zones:
                for plot in (self.delta_plot, self.speed_plot):
                    region = pg.LinearRegionItem(
                        values=(zone["start"], zone["end"]),
                        movable=False,
                        brush=brush,
                        pen=pg.mkPen(color, width=1, style=Qt.PenStyle.DashLine),
                    )
                    region.setZValue(-5)
                    region.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                    plot.addItem(region, ignoreBounds=True)
                    self._zone_items.append((plot, region))
                center = (zone["start"] + zone["end"]) * 0.5
                horizontal = 0.5
                if center > max_x * 0.85:
                    horizontal = 1.0
                elif center < max_x * 0.15:
                    horizontal = 0.0
                label = pg.TextItem(
                    f"{zone['start']/1000:.1f}–{zone['end']/1000:.1f}km "
                    f"{zone['delta']:+.1f}s",
                    color=color,
                    anchor=(horizontal, 1.0 if kind == "gain" else 0.0),
                )
                label.setPos(
                    center,
                    -limit * 0.85 if kind == "gain" else limit * 0.85,
                )
                label.setZValue(80)
                self.delta_plot.addItem(label, ignoreBounds=True)
                self._zone_labels.append(label)

        self._cursor_x = min(max_x * 0.35, max_x)
        self._set_cursor_x(self._cursor_x)

    def _limits(self, *arrays, fallback=(0.0, 1.0), pad=0.05):
        valid = []
        for array in arrays:
            if array is None or len(array) == 0:
                continue
            values = np.asarray(array)
            values = values[np.isfinite(values)]
            if values.size:
                valid.append(values)
        if not valid:
            return fallback
        lo = min(float(v.min()) for v in valid)
        hi = max(float(v.max()) for v in valid)
        if hi - lo < 1e-6:
            hi = lo + 1.0
        span = hi - lo
        return lo - span * pad, hi + span * pad

    def _marker_incidents(self):
        if self.current is None:
            return []
        result = []
        for incident in self.current.incidents:
            if incident["kind"] == "respawn":
                result.append(incident)
            elif incident["kind"] == "impact" and incident.get("peak", 0.0) >= 80.0:
                result.append(incident)
            elif incident["kind"] == "stop" and incident.get("duration", 0.0) >= 2.0:
                result.append(incident)
        return result

    def _on_plot_mouse_moved(self, plot, event) -> None:
        if self.current is None:
            return
        position = event[0] if isinstance(event, (tuple, list)) else event
        x = float(plot.vb.mapSceneToView(position).x())
        max_x = float(self.current.traces["x"][-1]) if len(self.current.traces["x"]) else 0.0
        self._pending_cursor = (min(max(x, 0.0), max_x), plot)
        if not self._cursor_timer.isActive():
            self._cursor_timer.start()

    def _flush_cursor_update(self) -> None:
        pending = self._pending_cursor
        self._pending_cursor = None
        if pending is None or self.current is None:
            return
        x, plot = pending
        self._set_cursor_x(x)
        if plot is None:
            return
        self._follow_pacenote(x)
        self._update_pacenote_hover(plot, x)

    def _set_cursor_x(self, x: float) -> None:
        if self.current is None:
            return
        traces = self.current.traces
        xs = traces["x"]
        if not len(xs):
            return
        index = int(np.searchsorted(xs, x))
        index = max(0, min(index, len(xs) - 1))
        if index > 0 and abs(float(xs[index - 1]) - x) < abs(float(xs[index]) - x):
            index -= 1
        self._cursor_x = float(xs[index])
        self._cursor_index = index
        for _plot, line in self._cursor_lines:
            line.setPos(self._cursor_x)
        self.speed_dot.setData([self._cursor_x], [float(traces["speed"][index])])
        self._update_readout(index)
        if self._video_follows_cursor():
            self._ensure_cursor_visible()
        if self.track_map is not None:
            self.track_map.set_cursor(self._cursor_x)

    def _video_follows_cursor(self) -> bool:
        player = self._player
        return bool(
            player is not None
            and player.state_name == "playing"
            and self.video_follow is not None
            and self.video_follow.isChecked()
        )

    def _ensure_cursor_visible(self) -> None:
        """Pan the charts with the cursor while the replay is playing.

        Without this the cursor walks out of a zoomed window and the chart
        shows nothing that matches what is playing.
        """
        if self.current is None:
            return
        x0, x1 = self.speed_plot.viewRange()[0]
        width = float(x1 - x0)
        if width <= 1.0:
            return
        x = float(self._cursor_x)
        if x0 + width * 0.12 <= x <= x1 - width * 0.12:
            return
        max_x = float(self.current.traces["x"][-1])
        low = x - width * 0.25
        low = max(0.0, min(low, max(0.0, max_x - width * 0.5)))
        self.speed_plot.setXRange(low, low + width, padding=0)

    def _update_readout(self, index: int) -> None:
        traces = self.current.traces
        summary = self.current.summary
        distance = float(traces["x"][index])
        stage_time = float(traces["t"][index])
        speed = float(traces["speed"][index])
        gas = float(traces["gas"][index])
        brake = float(traces["brake"][index])
        gear = int(round(float(traces["gear"][index])))
        delta = 0.0
        ref_speed = speed
        if self.compare is not None and len(self.compare.get("distance", [])):
            delta = float(
                np.interp(
                    distance,
                    self.compare["distance"],
                    self.compare["delta"],
                )
            )
        if self.reference is not None and len(self.reference.traces["x"]):
            ref_speed = float(
                np.interp(
                    distance,
                    self.reference.traces["x"],
                    self.reference.traces["speed"],
                )
            )
        self.readout["distance"].setText(f"{distance:,.0f} m")
        self.readout["time"].setText(acr_data.format_time(stage_time))
        self.readout["speed"].setText(f"{speed:.1f}")
        self.readout["gas"].setText(f"{gas:.0f}")
        self.readout["brake"].setText(f"{brake:.0f}")
        self.readout["gear"].setText(str(gear))
        self.readout["ref_speed"].setText(f"{ref_speed:.1f}")
        note_label = self.readout.get("pacenote")
        if note_label is not None:
            nearest = self._nearest_pacenote(distance)
            if nearest is None:
                self._clear_pacenote_readout()
            else:
                note, note_x = nearest
                note_label.setText(f"{note_x:.0f}m · {note.text}")
                note_label.setStyleSheet(
                    f"color:{self._pacenote_color(note)};"
                )
                note_label.setToolTip(
                    tr("路书距离 {dist:,.0f} m · 赛段相对 {rel:,.0f} m\n"
                       "参考长度 {length:,.0f} m").format(
                        dist=note.distance, rel=note_x, length=note.length)
                    + ("\n" + tr("与下一条连贯") if note.link else "")
                )
        delta_label = self.readout["delta"]
        if abs(delta) < 0.0005:
            delta_label.setText("0.000")
            delta_label.setStyleSheet(f"color:{C['muted']};")
        else:
            delta_label.setText(f"{delta:+.3f}")
            delta_label.setStyleSheet(
                f"color:{C['green'] if delta < 0 else C['red']};"
            )

    def _on_incident_clicked(self, item: QListWidgetItem) -> None:
        incident = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(incident, dict):
            return
        x = float(incident["distance"])
        window = max(120.0, min(500.0, float(self.current.summary["distance"]) * 0.06))
        lo = max(0.0, x - window)
        hi = x + window
        self.speed_plot.setXRange(lo, hi, padding=0)
        self._set_cursor_x(x)
        self._seek_video_to_distance(x)

    def reset_zoom(self) -> None:
        if self.current is None:
            return
        max_x = max(
            float(self.current.traces["x"][-1]) if len(self.current.traces["x"]) else 1.0,
            float(self.reference.traces["x"][-1]) if self.reference and len(self.reference.traces["x"]) else 0.0,
        )
        self.speed_plot.setXRange(0, max(max_x, 1.0), padding=0.01)


def _record_selftest(seconds: int, window: str | None, telemetry_dir: Path) -> int:
    import acr_video

    if window:
        target = acr_video.find_window((window,))
    else:
        target = acr_video.find_window()
    if target is None:
        print("record-test: FAIL no matching window")
        for hwnd, title in acr_video.list_windows()[:30]:
            print(f"  - {hwnd:08x}  {title}")
        return 2
    hwnd, title = target
    out_dir = Path(telemetry_dir) / "videos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "selftest.mp4"
    recorder = acr_video.VideoRecorder()
    if not recorder.start(out_path, hwnd=hwnd):
        print(f"record-test: FAIL start error={recorder.last_result.get('error')}")
        return 2
    print(f"record-test: recording '{title}' for {seconds}s -> {out_path}")
    time.sleep(max(2, int(seconds)))
    result = recorder.stop()
    if result.get("error"):
        print(f"record-test: FAIL error={result['error']}")
        return 2
    frames = result.get("frames", 0)
    print("record-test: PASS", json.dumps(result, ensure_ascii=False, default=str))
    if frames < 10:
        print("record-test: FAIL too few frames captured")
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ACR Telemetry Studio")
    parser.add_argument("--screenshot", type=Path, help="render a screenshot and exit")
    parser.add_argument("--telemetry-dir", type=Path, default=acr_data.TELEMETRY_DIR)
    parser.add_argument("--current", type=int, help="0-based current run index")
    parser.add_argument("--reference", type=int, help="0-based reference run index")
    parser.add_argument(
        "--tab",
        type=int,
        choices=range(4),
        help="analysis tab to show in screenshot mode",
    )
    parser.add_argument(
        "--cursor",
        type=float,
        help="cursor distance in meters for screenshot mode",
    )
    parser.add_argument(
        "--record-test",
        type=int,
        metavar="SECONDS",
        help="capture a window and report, to check recording works",
    )
    parser.add_argument(
        "--record-window",
        default=None,
        help="window title substring for --record-test (default: auto)",
    )
    parser.add_argument(
        "--lang",
        choices=tuple(acr_i18n.LANGUAGES),
        help="UI language for this launch (overrides the saved setting)",
    )
    args = parser.parse_args()

    if args.lang:
        global _LANG_OVERRIDE
        _LANG_OVERRIDE = args.lang
        acr_i18n.set_language(args.lang)

    if args.record_test:
        code = _record_selftest(args.record_test, args.record_window,
                                args.telemetry_dir)
        # native capture/av libs race Qt's atexit teardown outside the GUI
        # loop; skip interpreter shutdown entirely
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)

    if args.screenshot:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setApplicationName("ACR Telemetry Studio")

    lock = None
    if not args.screenshot:
        acr_data.ROOT.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(acr_data.ROOT / "acr_telemetry.lock"))
        lock.setStaleLockTime(30000)
        if not lock.tryLock(100):
            QMessageBox.information(
                None,
                "ACR Telemetry",
                tr("客户端已经在运行，请从系统托盘打开。"),
            )
            return 0

    if args.screenshot:
        runs = acr_data.load_runs(args.telemetry_dir)
        window = TelemetryWindow(
            runs=runs,
            directory=args.telemetry_dir,
            auto_record=False,
        )
        _apply_indices(window, args.current, args.reference)
        if args.tab is not None:
            window.analysis_tabs.setCurrentIndex(args.tab)
        window.resize(1840, 1120)
        window.show()
        app.processEvents()
        if args.cursor is not None:
            window._set_cursor_x(args.cursor)
            window._follow_pacenote(args.cursor)
            window._update_pacenote_hover(window.speed_plot, args.cursor)
            app.processEvents()

        def save() -> None:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            saved = window.grab().save(str(args.screenshot))
            print(f"saved={saved} path={args.screenshot}")
            app.quit()

        QTimer.singleShot(1500, save)
        return app.exec()

    window = TelemetryWindow(directory=args.telemetry_dir)
    window.pending_indices = (args.current, args.reference)
    window.show()
    return app.exec()


def _apply_indices(window: TelemetryWindow, current: int | None, reference: int | None) -> None:
    if current is not None and 0 <= current < window.current_combo.count():
        window.current_combo.setCurrentIndex(current)
    if reference is not None and 0 <= reference < window.reference_combo.count():
        window.reference_combo.setCurrentIndex(reference)


if __name__ == "__main__":
    raise SystemExit(main())
