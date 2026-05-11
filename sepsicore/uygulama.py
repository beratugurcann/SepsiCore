# -*- coding: utf-8 -*-
"""SepsiCore ana pencere ve kullanıcı akışları."""

from __future__ import annotations

import csv
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .analiz import AnalysisResult, analyze_row, normalize_patient_rows, safe_float, validate_patient_rows
from .ayarlar import (
    ALERT_SOUND_FILES,
    DEMO_DATA_PATH,
    NOTES_DIR,
    REAL_DATA_PATH,
    RECORDS_DIR,
    REPORTS_DIR,
    ensure_runtime_directories,
)
from .bilesenler import APP_STYLE, ECGWidget, PlotCanvas, VitalCard
from .i18n import DEFAULT_LANGUAGE, t
from .raporlar import ReportGenerationError, build_text_report, create_pdf_report, safe_file_token


@dataclass(frozen=True)
class ModeCardRefs:
    """Ana ekrandaki mod kartlarını çeviri güncellemesi için tutar."""

    heading: QLabel
    description: QLabel
    button: QPushButton
    title_key: str
    description_key: str
    button_key: str


class SepsiCore(QMainWindow):
    """Ana pencere: mod seçimi, canlı izlem ve raporlama akışlarını yönetir."""

    def __init__(self):
        super().__init__()
        ensure_runtime_directories()

        self.setWindowTitle("SepsiCore - Klinik Erken Uyarı Sistemi")
        self.resize(1440, 900)
        self.setStyleSheet(APP_STYLE)

        self.language = DEFAULT_LANGUAGE
        self.status_key = "status_standby"
        self.status_background = "#123A51"
        self.status_font_size = 24
        self.mode: str | None = None
        self.rows: list[dict[str, object]] = []
        self.current_patient: str | None = None
        self.current_rows: list[dict[str, object]] = []
        self.idx = 0
        self.running = False
        self.sound_enabled = True
        self.last_result: AnalysisResult | None = None
        self.mode_cards: list[ModeCardRefs] = []

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)

        self.sounds: dict[str, QSoundEffect] = {}
        self.load_sounds()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.build_home()
        self.build_monitor()
        self.stack.setCurrentWidget(self.home)
        self.apply_language()

    def load_sounds(self) -> None:
        for name, wav_path in ALERT_SOUND_FILES.items():
            effect = QSoundEffect(self)
            if wav_path.exists():
                effect.setSource(QUrl.fromLocalFile(str(wav_path)))
            effect.setLoopCount(1)
            effect.setVolume(0.85 if name == "critical" else 0.55)
            self.sounds[name] = effect

    def play_sound_for(self, score: int) -> None:
        if not self.sound_enabled or not self.running:
            return

        if score >= 76:
            sound = self.sounds.get("critical")
        elif score >= 55:
            sound = self.sounds.get("high")
        elif score >= 30:
            sound = self.sounds.get("medium")
        else:
            sound = None

        if sound is not None:
            sound.play()

    def stop_sounds(self) -> None:
        for sound in self.sounds.values():
            try:
                sound.stop()
            except RuntimeError:
                continue

    def build_home(self) -> None:
        self.home = QWidget()
        root = QVBoxLayout(self.home)
        root.setContentsMargins(45, 45, 45, 45)
        self.mode_cards.clear()

        top = QFrame()
        top.setObjectName("Card")
        top_layout = QVBoxLayout(top)
        title = QLabel("SepsiCore")
        title.setObjectName("Title")
        self.home_language_btn = QPushButton()
        self.home_language_btn.setFixedWidth(64)
        self.home_language_btn.clicked.connect(self.toggle_language)
        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.home_language_btn)
        self.home_subtitle = QLabel()
        self.home_subtitle.setObjectName("Subtitle")
        top_layout.addLayout(title_row)
        top_layout.addWidget(self.home_subtitle)
        root.addWidget(top)

        cards = QHBoxLayout()
        demo = self.mode_card(
            "demo_mode",
            "demo_desc",
            "open_demo",
            self.open_demo,
        )
        real = self.mode_card(
            "real_mode",
            "real_desc",
            "open_real",
            self.open_real,
        )
        cards.addWidget(demo)
        cards.addWidget(real)
        root.addLayout(cards)

        self.home_info = QLabel()
        self.home_info.setObjectName("Subtitle")
        self.home_info.setWordWrap(True)
        root.addWidget(self.home_info)
        self.stack.addWidget(self.home)

    def mode_card(self, title_key: str, desc_key: str, btn_key: str, callback: Callable[[], None]) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)

        heading = QLabel(t(self.language, title_key))
        heading.setObjectName("Title")
        heading.setStyleSheet("font-size:22px;font-weight:800;")
        text = QLabel(t(self.language, desc_key))
        text.setObjectName("Subtitle")
        text.setWordWrap(True)
        button = QPushButton(t(self.language, btn_key))
        button.setObjectName("Primary")
        button.clicked.connect(callback)

        self.mode_cards.append(
            ModeCardRefs(
                heading=heading,
                description=text,
                button=button,
                title_key=title_key,
                description_key=desc_key,
                button_key=btn_key,
            )
        )
        layout.addWidget(heading)
        layout.addWidget(text)
        layout.addStretch()
        layout.addWidget(button)
        card.setMinimumHeight(260)
        return card

    def toggle_language(self) -> None:
        self.language = "en" if self.language == "tr" else "tr"
        selected_scenario = self.current_scenario_key()
        if self.mode == "demo":
            self.set_combo_items(self.scenario_entries(), selected_scenario)
        elif self.mode == "real":
            self.set_combo_items([("csv", t(self.language, "csv_records"))], "csv")
        self.apply_language()
        if self.current_rows:
            self.update_frame()

    def apply_language(self) -> None:
        self.setWindowTitle(t(self.language, "window_title"))
        self.home_subtitle.setText(t(self.language, "home_subtitle"))
        self.home_info.setText(t(self.language, "disclaimer"))

        for button in [self.home_language_btn, self.monitor_language_btn]:
            button.setText(t(self.language, "lang_button"))
            button.setToolTip(t(self.language, "lang_tooltip"))

        for card in self.mode_cards:
            card.heading.setText(t(self.language, card.title_key))
            card.description.setText(t(self.language, card.description_key))
            card.button.setText(t(self.language, card.button_key))

        if self.mode == "demo":
            self.mode_label.setText(t(self.language, "demo_mode"))
        elif self.mode == "real":
            self.mode_label.setText(t(self.language, "real_mode"))
        else:
            self.mode_label.setText(t(self.language, "standby"))

        self.back_btn.setText(t(self.language, "home"))
        self.patient_selection_label.setText(t(self.language, "patient_selection"))
        self.btn_start.setText(t(self.language, "start"))
        self.btn_pause.setText(t(self.language, "pause"))
        self.btn_reset.setText(t(self.language, "reset"))
        mute_key = "unmute_alarm" if not self.sound_enabled else "mute_alarm"
        self.btn_mute.setText(t(self.language, mute_key))

        self.right_title.setText(t(self.language, "clinical_evaluation"))
        self.findings_label.setText(t(self.language, "findings_title"))
        self.actions_label.setText(t(self.language, "actions_title"))
        self.note_label.setText(t(self.language, "doctor_note"))
        self.note.setPlaceholderText(t(self.language, "note_placeholder"))
        self.btn_note.setText(t(self.language, "save_note"))
        self.btn_record.setText(t(self.language, "create_record"))
        self.btn_pdf.setText(t(self.language, "save_pdf"))

        self.cards["kalp_hizi"].set_caption(t(self.language, "vital_heart_rate"), "bpm")
        self.cards["ates"].set_caption(t(self.language, "vital_temperature"), "°C")
        self.cards["oksijen"].set_caption(t(self.language, "vital_oxygen"), "%")
        self.cards["sistolik_tansiyon"].set_caption(t(self.language, "vital_blood_pressure"), "mmHg")
        self.cards["solunum"].set_caption(t(self.language, "vital_respiration"), "/dk")
        self.cards["wbc"].set_caption("WBC", "10³/µL")
        self.cards["laktat"].set_caption(t(self.language, "vital_lactate"), "mmol/L")

        self.ecg.set_label(t(self.language, "ecg_live"))
        self.plot.set_labels(
            t(self.language, "chart_title"),
            t(self.language, "chart_heart_rate"),
            t(self.language, "chart_temperature"),
            t(self.language, "chart_oxygen"),
        )
        self.set_status(self.status_key, self.status_background, self.status_font_size)

        if not self.current_rows:
            self.patient_info.setText(t(self.language, "no_patient"))
            self.risk_label.setText(t(self.language, "risk_score_empty"))
            self.compat_label.setText(t(self.language, "compatibility_empty"))
            self.reasons.setText(t(self.language, "risk_reasons_placeholder"))
            self.actions.setText(t(self.language, "actions_placeholder"))

    def build_monitor(self) -> None:
        self.monitor = QWidget()
        root = QVBoxLayout(self.monitor)
        root.setContentsMargins(16, 16, 16, 16)

        header = QFrame()
        header.setObjectName("Card")
        header_layout = QHBoxLayout(header)
        self.app_title = QLabel("SepsiCore")
        self.app_title.setObjectName("Title")
        self.mode_label = QLabel(t(self.language, "standby"))
        self.mode_label.setObjectName("Subtitle")
        self.back_btn = QPushButton(t(self.language, "home"))
        self.back_btn.clicked.connect(self.go_home)
        self.monitor_language_btn = QPushButton()
        self.monitor_language_btn.setFixedWidth(64)
        self.monitor_language_btn.clicked.connect(self.toggle_language)

        header_layout.addWidget(self.app_title)
        header_layout.addWidget(self.mode_label)
        header_layout.addStretch()
        header_layout.addWidget(self.monitor_language_btn)
        header_layout.addWidget(self.back_btn)
        root.addWidget(header)

        content = QHBoxLayout()

        left = QFrame()
        left.setObjectName("Card")
        left.setFixedWidth(300)
        left_layout = QVBoxLayout(left)
        self.patient_selection_label = QLabel()
        self.patient_selection_label.setObjectName("Section")
        self.scenario_combo = QComboBox()
        self.scenario_combo.currentTextChanged.connect(self.scenario_changed)
        self.patient_list = QListWidget()
        self.patient_list.itemClicked.connect(self.patient_clicked)

        left_layout.addWidget(self.patient_selection_label)
        left_layout.addWidget(self.scenario_combo)
        left_layout.addWidget(self.patient_list, 1)

        self.btn_start = QPushButton()
        self.btn_start.setObjectName("Success")
        self.btn_start.clicked.connect(self.start_monitoring)
        self.btn_pause = QPushButton()
        self.btn_pause.clicked.connect(self.pause_monitoring)
        self.btn_reset = QPushButton()
        self.btn_reset.clicked.connect(self.reset_monitoring)
        self.btn_mute = QPushButton()
        self.btn_mute.clicked.connect(self.toggle_sound)

        for button in [self.btn_start, self.btn_pause, self.btn_reset, self.btn_mute]:
            left_layout.addWidget(button)

        content.addWidget(left)

        center = QFrame()
        center.setObjectName("Card")
        center_layout = QVBoxLayout(center)
        self.status_banner = QLabel()
        self.status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status("status_standby", "#123A51", 24)
        center_layout.addWidget(self.status_banner)

        grid = QGridLayout()
        self.cards = {
            "kalp_hizi": VitalCard(t(self.language, "vital_heart_rate"), "bpm"),
            "ates": VitalCard(t(self.language, "vital_temperature"), "°C"),
            "oksijen": VitalCard(t(self.language, "vital_oxygen"), "%"),
            "sistolik_tansiyon": VitalCard(t(self.language, "vital_blood_pressure"), "mmHg"),
            "solunum": VitalCard(t(self.language, "vital_respiration"), "/dk"),
            "wbc": VitalCard("WBC", "10³/µL"),
            "laktat": VitalCard(t(self.language, "vital_lactate"), "mmol/L"),
        }
        for index, card in enumerate(self.cards.values()):
            grid.addWidget(card, index // 4, index % 4)
        center_layout.addLayout(grid)

        self.ecg = ECGWidget()
        center_layout.addWidget(self.ecg)
        self.plot = PlotCanvas()
        center_layout.addWidget(self.plot)
        content.addWidget(center, 1)

        right = QFrame()
        right.setObjectName("Card")
        right.setFixedWidth(440)
        right_layout = QVBoxLayout(right)
        self.right_title = QLabel()
        self.right_title.setObjectName("Section")
        self.patient_info = QLabel()
        self.patient_info.setObjectName("Subtitle")
        self.patient_info.setWordWrap(True)
        self.risk_label = QLabel()
        self.risk_label.setObjectName("Title")
        self.risk_bar = QProgressBar()
        self.risk_bar.setRange(0, 100)
        self.compat_label = QLabel()
        self.compat_label.setObjectName("Section")
        self.compat_bar = QProgressBar()
        self.compat_bar.setRange(0, 100)
        self.reasons = QLabel()
        self.reasons.setWordWrap(True)
        self.actions = QLabel()
        self.actions.setWordWrap(True)
        self.note = QTextEdit()
        self.note.setMinimumHeight(100)

        self.btn_note = QPushButton()
        self.btn_note.clicked.connect(self.save_note)
        self.btn_record = QPushButton()
        self.btn_record.clicked.connect(self.save_record)
        self.btn_pdf = QPushButton()
        self.btn_pdf.setObjectName("Primary")
        self.btn_pdf.clicked.connect(self.save_pdf)

        for widget in [
            self.right_title,
            self.patient_info,
            self.risk_label,
            self.risk_bar,
            self.compat_label,
            self.compat_bar,
        ]:
            right_layout.addWidget(widget)

        self.findings_label = QLabel()
        self.actions_label = QLabel()
        self.note_label = QLabel()
        right_layout.addWidget(self.findings_label)
        right_layout.addWidget(self.reasons)
        right_layout.addWidget(self.actions_label)
        right_layout.addWidget(self.actions)
        right_layout.addWidget(self.note_label)
        right_layout.addWidget(self.note)
        for button in [self.btn_note, self.btn_record, self.btn_pdf]:
            right_layout.addWidget(button)

        content.addWidget(right)
        root.addLayout(content, 1)
        self.stack.addWidget(self.monitor)

    def set_status(self, status_key: str, background: str, font_size: int = 23) -> None:
        self.status_key = status_key
        self.status_background = background
        self.status_font_size = font_size
        self.status_banner.setText(t(self.language, status_key))
        self.status_banner.setStyleSheet(
            f"font-size:{font_size}px;"
            "font-weight:900;"
            "border-radius:8px;"
            "padding:12px;"
            f"background:{background};"
            "color:#FFFFFF;"
        )

    def go_home(self) -> None:
        self.pause_monitoring()
        self.stack.setCurrentWidget(self.home)

    def open_demo(self) -> None:
        self.mode = "demo"
        self.mode_label.setText(t(self.language, "demo_mode"))
        self.set_combo_items(self.scenario_entries())
        if self.load_data(DEMO_DATA_PATH):
            self.stack.setCurrentWidget(self.monitor)

    def open_real(self) -> None:
        self.mode = "real"
        self.mode_label.setText(t(self.language, "real_mode"))
        self.set_combo_items([("csv", t(self.language, "csv_records"))])
        if self.load_data(REAL_DATA_PATH):
            self.stack.setCurrentWidget(self.monitor)

    def set_combo_items(self, items: list[tuple[str, str]], selected_key: str | None = None) -> None:
        previous_state = self.scenario_combo.blockSignals(True)
        try:
            self.scenario_combo.clear()
            for key, label in items:
                self.scenario_combo.addItem(label, key)
            if selected_key is not None:
                index = self.scenario_combo.findData(selected_key)
                if index >= 0:
                    self.scenario_combo.setCurrentIndex(index)
        finally:
            self.scenario_combo.blockSignals(previous_state)

    def scenario_entries(self) -> list[tuple[str, str]]:
        return [
            ("stabil", t(self.language, "scenario_stable")),
            ("orta", t(self.language, "scenario_medium")),
            ("kritik", t(self.language, "scenario_critical")),
        ]

    def load_data(self, path: Path) -> bool:
        self.pause_monitoring()

        try:
            with open(path, newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
        except FileNotFoundError:
            self.rows = []
            self.clear_patient_context(t(self.language, "data_missing_context"))
            QMessageBox.critical(
                self,
                t(self.language, "data_file_missing_title"),
                t(self.language, "data_file_missing_body").format(path=path),
            )
            return False
        except Exception as exc:
            self.rows = []
            self.clear_patient_context(t(self.language, "data_read_context"))
            QMessageBox.critical(
                self,
                t(self.language, "data_file_read_title"),
                t(self.language, "data_file_read_body").format(error=exc),
            )
            return False

        errors = validate_patient_rows(rows, self.language)
        if errors:
            self.rows = []
            self.clear_patient_context(t(self.language, "data_invalid_context"))
            QMessageBox.critical(self, t(self.language, "data_file_invalid_title"), "\n".join(errors))
            return False

        self.rows = normalize_patient_rows(rows)
        self.populate_patients()
        self.reset_monitoring()
        return True

    def scenario_changed(self, _text: str) -> None:
        if self.mode != "demo" or not self.rows:
            return
        self.populate_patients()

    def populate_patients(self) -> None:
        self.patient_list.clear()
        data = self.rows

        if self.mode == "demo":
            scenario = self.current_scenario_key()
            data = [row for row in data if row["senaryo"] == scenario]

        if not data:
            self.clear_patient_context(t(self.language, "empty_selection"))
            return

        seen_patient_ids: set[str] = set()
        for row in data:
            patient_id = str(row["hasta_id"])
            if patient_id in seen_patient_ids:
                continue
            seen_patient_ids.add(patient_id)
            item = QListWidgetItem(f"{row['hasta_adi']}  |  {patient_id}")
            item.setData(Qt.ItemDataRole.UserRole, patient_id)
            self.patient_list.addItem(item)

        self.patient_list.setCurrentRow(0)
        current_item = self.patient_list.currentItem()
        if current_item is not None:
            self.select_patient(current_item.data(Qt.ItemDataRole.UserRole))

    def current_scenario_key(self) -> str:
        return self.scenario_combo.currentData() or "stabil"

    def patient_clicked(self, item: QListWidgetItem) -> None:
        self.select_patient(item.data(Qt.ItemDataRole.UserRole))

    def select_patient(self, patient_id: str) -> None:
        self.pause_monitoring()
        filtered = sorted(
            [row for row in self.rows if row["hasta_id"] == patient_id],
            key=lambda row: float(row["zaman"]),
        )
        if not filtered:
            self.clear_patient_context(t(self.language, "patient_missing"))
            return

        self.current_patient = patient_id
        self.current_rows = filtered
        self.idx = 0
        self.update_frame()
        self.set_status("status_standby", "#123A51", 24)

    def clear_patient_context(self, message: str | None = None) -> None:
        self.current_patient = None
        self.current_rows = []
        self.idx = 0
        self.last_result = None

        if not hasattr(self, "patient_info"):
            return

        self.patient_info.setText(message or t(self.language, "no_patient"))
        self.risk_label.setText(t(self.language, "risk_score_empty"))
        self.risk_label.setStyleSheet("font-size:21px;font-weight:900;color:#EAF7FF;")
        self.risk_bar.setValue(0)
        self.risk_bar.setStyleSheet("")
        self.compat_label.setText(t(self.language, "compatibility_empty"))
        self.compat_bar.setValue(0)
        self.reasons.setText(t(self.language, "risk_reasons_placeholder"))
        self.actions.setText(t(self.language, "actions_placeholder"))
        self.note.clear()
        for card in self.cards.values():
            card.clear()
        self.plot.clear()
        self.set_status("status_standby", "#123A51", 24)

    def start_monitoring(self) -> None:
        if not self.current_rows:
            QMessageBox.warning(self, t(self.language, "warning"), t(self.language, "select_patient_first"))
            return

        self.running = True
        self.set_status("status_active", "#0B7A57", 24)
        self.timer.start(900)

    def pause_monitoring(self) -> None:
        self.running = False
        self.timer.stop()
        self.stop_sounds()
        if hasattr(self, "status_banner"):
            self.set_status("status_paused", "#123A51", 24)

    def reset_monitoring(self) -> None:
        self.running = False
        self.timer.stop()
        self.stop_sounds()

        if not self.current_rows:
            self.clear_patient_context()
            return

        self.idx = 0
        self.update_frame()
        self.set_status("status_standby", "#123A51", 24)

    def toggle_sound(self) -> None:
        self.sound_enabled = not self.sound_enabled
        if not self.sound_enabled:
            self.stop_sounds()
        mute_key = "unmute_alarm" if not self.sound_enabled else "mute_alarm"
        self.btn_mute.setText(t(self.language, mute_key))

    def next_frame(self) -> None:
        if not self.current_rows:
            return

        self.idx += 1
        if self.idx >= len(self.current_rows):
            self.idx = len(self.current_rows) - 1
            self.pause_monitoring()

        self.update_frame(play_alert=True)

    def update_frame(self, play_alert: bool = False) -> None:
        if not self.current_rows:
            return

        row = self.current_rows[self.idx]
        self.last_result = analyze_row(row, self.language)
        age = int(row["yas"])
        minute = int(row["zaman"])
        self.patient_info.setText(
            f"{row['hasta_adi']} | {row['hasta_id']} | "
            f"{t(self.language, 'age')}: {age} | "
            f"{t(self.language, 'service')}: {row['servis']} | "
            f"{t(self.language, 'time')}: {minute}{t(self.language, 'minute_suffix')}"
        )

        limits = {
            "kalp_hizi": lambda value: value >= 110,
            "ates": lambda value: value >= 38 or value <= 36,
            "oksijen": lambda value: value <= 93,
            "sistolik_tansiyon": lambda value: value <= 95,
            "solunum": lambda value: value >= 24,
            "wbc": lambda value: value >= 12 or value <= 4,
            "laktat": lambda value: value >= 2,
        }
        for key, card in self.cards.items():
            value = safe_float(row.get(key))
            color = "#FF5B6D" if limits[key](value) else "#EAF7FF"
            card.set_value(value, color)

        result = self.last_result
        self.risk_label.setText(f"{t(self.language, 'risk_score')}: %{result.risk_score} - {result.level}")
        self.risk_label.setStyleSheet(f"font-size:21px;font-weight:900;color:{result.color};")
        self.risk_bar.setValue(result.risk_score)
        self.risk_bar.setStyleSheet(f"QProgressBar::chunk{{background:{result.color};border-radius:8px;}}")
        self.compat_label.setText(f"{t(self.language, 'compatibility_score')}: %{result.compatibility}")
        self.compat_bar.setValue(result.compatibility)
        self.reasons.setText("\n".join(f"• {reason}" for reason in result.reasons))
        self.actions.setText("\n".join(f"• {action}" for action in result.actions))
        self.plot.plot_data(self.current_rows, self.idx)

        if self.running:
            if play_alert:
                self.play_sound_for(result.risk_score)
            self.update_running_status(result.risk_score)

    def update_running_status(self, score: int) -> None:
        if score >= 76:
            self.set_status("status_critical", "#B51E33", 23)
        elif score >= 55:
            self.set_status("status_high", "#A85D18", 23)
        elif score >= 30:
            self.set_status("status_medium", "#8D7116", 23)
        else:
            self.set_status("status_active", "#0B7A57", 24)

    def current_summary(self) -> tuple[dict[str, object], AnalysisResult] | None:
        if not self.current_rows or self.last_result is None:
            return None
        return self.current_rows[self.idx], self.last_result

    def save_note(self) -> None:
        data = self.current_summary()
        if not data:
            QMessageBox.warning(self, t(self.language, "warning"), t(self.language, "record_missing"))
            return

        row, result = data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patient_token = safe_file_token(row["hasta_id"])
        path = NOTES_DIR / f"doktor_notu_{patient_token}_{timestamp}.txt"
        content = build_text_report(row, result, self.note.toPlainText(), only_note=True, language=self.language)
        path.write_text(content, encoding="utf-8")
        QMessageBox.information(self, t(self.language, "saved"), t(self.language, "note_saved").format(path=path))

    def save_record(self) -> None:
        data = self.current_summary()
        if not data:
            QMessageBox.warning(self, t(self.language, "warning"), t(self.language, "record_missing"))
            return

        row, result = data
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        patient_token = safe_file_token(row["hasta_id"])
        csv_path = RECORDS_DIR / "hasta_kayitlari.csv"
        txt_path = RECORDS_DIR / f"hasta_kaydi_{patient_token}_{timestamp}.txt"
        csv_exists = csv_path.exists()
        note_text = self.note.toPlainText().strip()

        with open(csv_path, "a", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            if not csv_exists:
                writer.writerow(
                    [
                        "tarih",
                        "mod",
                        "hasta_id",
                        "hasta_adi",
                        "yas",
                        "servis",
                        "risk_skoru",
                        "klinik_uyum",
                        "risk_seviyesi",
                        "kalp_hizi",
                        "ates",
                        "oksijen",
                        "sistolik_tansiyon",
                        "solunum",
                        "wbc",
                        "laktat",
                        "doktor_notu",
                    ]
                )
            writer.writerow(
                [
                    now.isoformat(timespec="seconds"),
                    self.mode_label.text(),
                    row["hasta_id"],
                    row["hasta_adi"],
                    int(row["yas"]),
                    row["servis"],
                    result.risk_score,
                    result.compatibility,
                    result.level,
                    row["kalp_hizi"],
                    row["ates"],
                    row["oksijen"],
                    row["sistolik_tansiyon"],
                    row["solunum"],
                    row["wbc"],
                    row["laktat"],
                    note_text,
                ]
            )

        txt_path.write_text(build_text_report(row, result, note_text, language=self.language), encoding="utf-8")
        QMessageBox.information(
            self,
            t(self.language, "record_created_title"),
            t(self.language, "record_created_body").format(csv_path=csv_path, txt_path=txt_path),
        )

    def save_pdf(self) -> None:
        data = self.current_summary()
        if not data:
            QMessageBox.warning(self, t(self.language, "warning"), t(self.language, "report_missing"))
            return

        row, result = data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patient_token = safe_file_token(row["hasta_id"])
        pdf_path = REPORTS_DIR / f"hasta_raporu_{patient_token}_{timestamp}.pdf"
        note_text = self.note.toPlainText()

        try:
            create_pdf_report(pdf_path, row, result, note_text, language=self.language)
        except ReportGenerationError as exc:
            txt_path = REPORTS_DIR / f"hasta_raporu_{patient_token}_{timestamp}.txt"
            txt_path.write_text(build_text_report(row, result, note_text, language=self.language), encoding="utf-8")
            QMessageBox.warning(
                self,
                t(self.language, "pdf_failed_title"),
                t(self.language, "pdf_failed_body").format(error=exc, path=txt_path),
            )
            return

        QMessageBox.information(self, t(self.language, "saved"), t(self.language, "pdf_saved").format(path=pdf_path))


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("SepsiCore")
    app.setApplicationDisplayName("SepsiCore")
    window = SepsiCore()
    window.show()
    sys.exit(app.exec())
