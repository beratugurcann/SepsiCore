# -*- coding: utf-8 -*-
"""SepsiCore arayüz bileşenleri."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


APP_STYLE = """
QMainWindow { background: #07131B; }
QWidget { color: #EAF7FF; font-family: Segoe UI, Arial; font-size: 12px; }
QFrame#Card { background: #0E2430; border: 1px solid #244D60; border-radius: 8px; }
QFrame#SoftCard { background: #102D3A; border: 1px solid #2A6075; border-radius: 8px; }
QLabel#Title { font-size: 27px; font-weight: 800; color: #F4FCFF; }
QLabel#Subtitle { font-size: 12px; color: #9CC7D5; }
QLabel#Section { font-size: 15px; font-weight: 700; color: #BDEFFF; }
QLabel#MetricName { color: #94C8DA; font-size: 11px; }
QLabel#MetricValue { color: #FFFFFF; font-size: 24px; font-weight: 800; }
QLabel#Tiny { color: #83B8CA; font-size: 10px; }
QPushButton { background: #14394C; color: #EAF7FF; border: 1px solid #2C86AA; border-radius: 8px; padding: 10px 14px; font-weight: 700; }
QPushButton:hover { background: #1A4C64; }
QPushButton:pressed { background: #0B2638; }
QPushButton#Primary { background: #00A6C8; color: #031218; border: 1px solid #35E6FF; }
QPushButton#Primary:hover { background: #16C1E5; }
QPushButton#Danger { background: #8A1F2A; color: #FFFFFF; border: 1px solid #FF5B6D; }
QPushButton#Danger:hover { background: #B92F3E; }
QPushButton#Success { background: #157A4E; border: 1px solid #3FE39E; }
QComboBox { background: #0B2536; color: #EAF7FF; border: 1px solid #2B7D9E; border-radius: 8px; padding: 8px; }
QComboBox QAbstractItemView { background: #0B2536; selection-background-color: #145B78; color: #EAF7FF; }
QTextEdit { background: #071E2C; color: #EAF7FF; border: 1px solid #236987; border-radius: 8px; padding: 8px; }
QListWidget { background: #071E2C; border: 1px solid #236987; border-radius: 8px; padding: 6px; }
QListWidget::item { padding: 9px; border-radius: 6px; }
QListWidget::item:selected { background: #145B78; color: white; }
QProgressBar { background: #06131C; border: 1px solid #2B6F8B; border-radius: 8px; height: 16px; text-align: center; color: white; }
QProgressBar::chunk { background: #00A6C8; border-radius: 8px; }
QToolTip { background: #102D3A; color: #EAF7FF; border: 1px solid #2A6075; padding: 6px; }
"""


class VitalCard(QFrame):
    """Tek vital bulguyu başlık, değer ve birim olarak gösterir."""

    def __init__(self, title: str, unit: str) -> None:
        super().__init__()
        self.setObjectName("SoftCard")
        self.title = QLabel(title)
        self.title.setObjectName("MetricName")
        self.value = QLabel("--")
        self.value.setObjectName("MetricValue")
        self.unit = QLabel(unit)
        self.unit.setObjectName("Tiny")

        layout = QVBoxLayout(self)
        layout.addWidget(self.title)

        row = QHBoxLayout()
        row.addWidget(self.value)
        row.addWidget(self.unit)
        row.addStretch()
        layout.addLayout(row)

    def set_value(self, value: object, color: str = "#FFFFFF") -> None:
        text = f"{value:.1f}" if isinstance(value, float) else str(value)
        self.value.setText(text)
        self.value.setStyleSheet(f"color:{color}; font-size:24px; font-weight:800;")

    def clear(self) -> None:
        self.value.setText("--")
        self.value.setStyleSheet("color:#FFFFFF; font-size:24px; font-weight:800;")

    def set_caption(self, title: str, unit: str) -> None:
        self.title.setText(title)
        self.unit.setText(unit)


class ECGWidget(QWidget):
    """Monitördeki canlı EKG hissini veren hafif çizim bileşeni."""

    def __init__(self) -> None:
        super().__init__()
        self.phase = 0
        self.label = "CANLI EKG AKIŞI"
        self.setMinimumHeight(150)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(45)

    def tick(self) -> None:
        self.phase = (self.phase + 1) % 120
        self.update()

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        gradient = QLinearGradient(0.0, 0.0, float(rect.width()), float(rect.height()))
        gradient.setColorAt(0, QColor("#061A25"))
        gradient.setColorAt(1, QColor("#0D344A"))
        painter.fillRect(rect, QBrush(gradient))

        painter.setPen(QPen(QColor(31, 91, 120, 90), 1))
        for x in range(0, rect.width(), 25):
            painter.drawLine(x, 0, x, rect.height())
        for y in range(0, rect.height(), 25):
            painter.drawLine(0, y, rect.width(), y)

        mid = rect.height() // 2
        points: list[QPointF] = []
        for x in range(rect.width()):
            t = (x + self.phase * 4) % 120
            y = mid + math.sin((x + self.phase) / 12) * 2
            if 18 < t < 24:
                y -= (t - 18) * 5
            elif 24 <= t < 30:
                y += (t - 24) * 13
            elif 30 <= t < 36:
                y -= (36 - t) * 10
            elif 62 < t < 80:
                y -= math.sin((t - 62) / 18 * math.pi) * 12
            y += random.uniform(-0.8, 0.8)
            points.append(QPointF(float(x), float(y)))

        painter.setPen(QPen(QColor("#39FFB6"), 2))
        for start, end in zip(points[:-1], points[1:]):
            painter.drawLine(start, end)

        painter.setPen(QPen(QColor("#9CEFD8"), 1))
        painter.drawText(12, 22, self.label)

    def set_label(self, label: str) -> None:
        self.label = label
        self.update()


class PlotCanvas(QWidget):
    """Seçili hastanın son vital trendlerini Qt ile çizen grafik bileşeni."""

    def __init__(self) -> None:
        super().__init__()
        self.title = "Vital Değer Trendleri"
        self.heart_rate_label = "Kalp hızı"
        self.temperature_label = "Ateş x3"
        self.oxygen_label = "Oksijen"
        self.view_rows: list[dict[str, object]] = []
        self.setMinimumHeight(250)

    def clear(self) -> None:
        self.view_rows = []
        self.update()

    def plot_data(self, rows: Sequence[dict[str, object]], idx: int) -> None:
        self.view_rows = list(rows[max(0, idx - 24) : idx + 1])
        self.update()

    def set_labels(self, title: str, heart_rate: str, temperature: str, oxygen: str) -> None:
        self.title = title
        self.heart_rate_label = heart_rate
        self.temperature_label = temperature
        self.oxygen_label = oxygen
        self.update()

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        painter.fillRect(rect, QColor("#071E2C"))
        chart = QRectF(rect.adjusted(44, 34, -18, -34))

        painter.setPen(QPen(QColor("#236987"), 1))
        painter.drawRoundedRect(chart, 6, 6)

        painter.setPen(QPen(QColor(35, 105, 135, 95), 1))
        for i in range(1, 4):
            y = chart.top() + chart.height() * i / 4
            painter.drawLine(int(chart.left()), int(y), int(chart.right()), int(y))
        for i in range(1, 6):
            x = chart.left() + chart.width() * i / 6
            painter.drawLine(int(x), int(chart.top()), int(x), int(chart.bottom()))

        painter.setPen(QColor("#EAF7FF"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(14, 22, self.title)

        if not self.view_rows:
            painter.setPen(QColor("#83B8CA"))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(chart, Qt.AlignmentFlag.AlignCenter, "--")
            return

        series: list[tuple[str, str, list[float]]] = [
            (self.heart_rate_label, "#66D9EF", [self._num(row.get("kalp_hizi")) for row in self.view_rows]),
            (self.temperature_label, "#F4C542", [self._num(row.get("ates")) * 3 for row in self.view_rows]),
            (self.oxygen_label, "#3DDC84", [self._num(row.get("oksijen")) for row in self.view_rows]),
        ]
        values = [value for _, _, data in series for value in data]
        min_value = min(values)
        max_value = max(values)
        if math.isclose(min_value, max_value):
            min_value -= 1
            max_value += 1
        padding = (max_value - min_value) * 0.12
        min_value -= padding
        max_value += padding

        for _label, color, data in series:
            self._draw_series(painter, chart, data, min_value, max_value, QColor(color))

        self._draw_legend(painter, chart, series)

    def _draw_series(
        self,
        painter: QPainter,
        chart: QRectF,
        data: Sequence[float],
        min_value: float,
        max_value: float,
        color: QColor,
    ) -> None:
        if len(data) == 1:
            x = chart.left()
            y = self._map_y(chart, data[0], min_value, max_value)
            painter.setBrush(color)
            painter.setPen(QPen(color, 2))
            painter.drawEllipse(QPointF(x, y), 3, 3)
            return

        points: list[QPointF] = []
        for index, value in enumerate(data):
            x = chart.left() + chart.width() * index / (len(data) - 1)
            y = self._map_y(chart, value, min_value, max_value)
            points.append(QPointF(x, y))

        painter.setPen(QPen(color, 2))
        for start, end in zip(points[:-1], points[1:]):
            painter.drawLine(start, end)

    def _draw_legend(
        self,
        painter: QPainter,
        chart: QRectF,
        series: Sequence[tuple[str, str, list[float]]],
    ) -> None:
        painter.setFont(QFont("Segoe UI", 8))
        x = chart.left()
        y = chart.bottom() + 22
        for label, color, _ in series:
            painter.setPen(QPen(QColor(color), 2))
            painter.drawLine(int(x), int(y - 4), int(x + 16), int(y - 4))
            painter.setPen(QColor("#BDEFFF"))
            painter.drawText(int(x + 22), int(y), label)
            x += max(92, len(label) * 7 + 38)

    @staticmethod
    def _num(value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _map_y(chart: QRectF, value: float, min_value: float, max_value: float) -> float:
        ratio = (value - min_value) / (max_value - min_value)
        return chart.bottom() - chart.height() * ratio
