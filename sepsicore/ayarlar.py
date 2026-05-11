# -*- coding: utf-8 -*-
"""Uygulamanın dosya yolları ve sabit ayarları."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
NOTES_DIR = BASE_DIR / "notes"
RECORDS_DIR = BASE_DIR / "records"
REPORTS_DIR = BASE_DIR / "reports"

SOUND_DIR = ASSETS_DIR / "sounds"
FONT_DIR = ASSETS_DIR / "fonts"
FONT_PATH = FONT_DIR / "DejaVuSans.ttf"

DEMO_DATA_PATH = DATA_DIR / "demo_patients.csv"
REAL_DATA_PATH = DATA_DIR / "real_patients.csv"

ALERT_SOUND_FILES = {
    "medium": SOUND_DIR / "alert_medium.wav",
    "high": SOUND_DIR / "alert_high.wav",
    "critical": SOUND_DIR / "alert_critical.wav",
}

RUNTIME_DIRS = (NOTES_DIR, RECORDS_DIR, REPORTS_DIR)


def ensure_runtime_directories() -> None:
    """Çalışma sırasında üretilen dosyalar için klasörleri hazırlar."""
    for path in RUNTIME_DIRS:
        path.mkdir(parents=True, exist_ok=True)
