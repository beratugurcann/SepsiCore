# -*- coding: utf-8 -*-
"""Sepsis erken uyarı analiz kuralları ve veri doğrulama yardımcıları."""

from __future__ import annotations

from dataclasses import dataclass
from math import isnan
from typing import Any, Mapping

from .i18n import analysis_t, normalize_language, validation_t


REQUIRED_COLUMNS = [
    "senaryo",
    "hasta_id",
    "hasta_adi",
    "yas",
    "servis",
    "zaman",
    "kalp_hizi",
    "ates",
    "oksijen",
    "sistolik_tansiyon",
    "solunum",
    "wbc",
    "laktat",
]

TEXT_COLUMNS = ["senaryo", "hasta_id", "hasta_adi", "servis"]
NUMERIC_COLUMNS = [
    "yas",
    "zaman",
    "kalp_hizi",
    "ates",
    "oksijen",
    "sistolik_tansiyon",
    "solunum",
    "wbc",
    "laktat",
]

RISK_RULE_COUNT = 7


@dataclass(frozen=True)
class AnalysisResult:
    """Tek hasta ölçümü için hesaplanan klinik risk çıktısı."""

    risk_score: int
    compatibility: int
    level: str
    color: str
    reasons: list[str]
    actions: list[str]


def safe_float(value: Any, default: float = 0.0) -> float:
    """CSV veya arayüzden gelen değeri güvenli şekilde sayıya çevirir."""

    try:
        if value is None or value == "":
            return default
        parsed = float(value)
        return default if isnan(parsed) else parsed
    except (TypeError, ValueError):
        return default


def analyze_row(row: Mapping[str, Any], language: str = "tr") -> AnalysisResult:
    """Bir hasta ölçüm satırını eşik kurallarına göre puanlar."""

    language = normalize_language(language)
    hr = safe_float(row.get("kalp_hizi"))
    temp = safe_float(row.get("ates"))
    o2 = safe_float(row.get("oksijen"))
    sys_bp = safe_float(row.get("sistolik_tansiyon"))
    resp = safe_float(row.get("solunum"))
    wbc = safe_float(row.get("wbc"))
    lactate = safe_float(row.get("laktat"))

    points = 0
    reasons: list[str] = []

    def add(condition: bool, score: int, text: str) -> None:
        nonlocal points
        if condition:
            points += score
            reasons.append(text)

    add(hr >= 110, 15, analysis_t(language, "hr_high"))
    add(temp >= 38.0 or temp <= 36.0, 14, analysis_t(language, "temp_out"))
    add(o2 <= 93, 16, analysis_t(language, "o2_low"))
    add(sys_bp <= 95, 12, analysis_t(language, "bp_low"))
    add(resp >= 24, 14, analysis_t(language, "resp_high"))
    add(wbc >= 12 or wbc <= 4, 15, analysis_t(language, "wbc_attention"))
    add(lactate >= 2.0, 14, analysis_t(language, "lactate_high"))

    risk_score = max(0, min(100, points))
    compatibility = min(100, int(round((len(reasons) / RISK_RULE_COUNT) * 85 + risk_score * 0.15)))

    if risk_score >= 76:
        level = analysis_t(language, "critical")
        color = "#E9354B"
        actions = [
            analysis_t(language, "act_critical_1"),
            analysis_t(language, "act_critical_2"),
            analysis_t(language, "act_critical_3"),
            analysis_t(language, "act_critical_4"),
        ]
    elif risk_score >= 55:
        level = analysis_t(language, "high")
        color = "#F08A24"
        actions = [
            analysis_t(language, "act_high_1"),
            analysis_t(language, "act_high_2"),
            analysis_t(language, "act_high_3"),
        ]
    elif risk_score >= 30:
        level = analysis_t(language, "medium")
        color = "#F4C542"
        actions = [
            analysis_t(language, "act_medium_1"),
            analysis_t(language, "act_medium_2"),
        ]
    else:
        level = analysis_t(language, "low")
        color = "#3DDC84"
        actions = [analysis_t(language, "act_low_1")]

    if not reasons:
        reasons = [analysis_t(language, "no_threshold")]

    return AnalysisResult(risk_score, compatibility, level, color, reasons, actions)


def validate_patient_rows(rows: list[dict[str, object]], language: str = "tr") -> list[str]:
    """CSV içeriğini gerekli kolonlar ve sayı alanları açısından doğrular."""

    language = normalize_language(language)
    errors: list[str] = []

    if not rows:
        return [validation_t(language, "empty")]

    columns = set(rows[0].keys())
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing:
        errors.append(validation_t(language, "missing", columns=", ".join(missing)))
        return errors

    for column in TEXT_COLUMNS:
        if any(str(row.get(column, "")).strip() == "" for row in rows):
            errors.append(validation_t(language, "empty_column", column=column))

    for column in NUMERIC_COLUMNS:
        invalid_count = sum(1 for row in rows if not _is_valid_number(row.get(column)))
        if invalid_count:
            errors.append(validation_t(language, "invalid_numeric", column=column, count=invalid_count))

    return errors


def normalize_patient_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Doğrulanmış CSV satırlarını uygulamanın beklediği tiplere dönüştürür."""

    normalized: list[dict[str, object]] = []

    for row in rows:
        clean_row = dict(row)
        for column in TEXT_COLUMNS:
            clean_row[column] = str(clean_row.get(column, "")).strip()
        for column in NUMERIC_COLUMNS:
            clean_row[column] = safe_float(clean_row.get(column))
        normalized.append(clean_row)

    return sorted(normalized, key=lambda item: (str(item["hasta_id"]), float(item["zaman"])))


def _is_valid_number(value: object) -> bool:
    """Boş, metin veya NaN olmayan sayısal hücreleri kabul eder."""

    if value is None or value == "":
        return False
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return False
    return not isnan(parsed)
