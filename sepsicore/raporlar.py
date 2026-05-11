# -*- coding: utf-8 -*-
"""TXT ve PDF hasta raporu üretimi."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Mapping

from .analiz import AnalysisResult
from .ayarlar import FONT_PATH
from .i18n import normalize_language, report_t


# PDF bağımlılığı eksikse uygulama TXT rapor üretmeye devam eder.
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


class ReportGenerationError(RuntimeError):
    """Rapor üretimi kullanıcıya gösterilebilir bir nedenle tamamlanamadı."""


_FONT_REGISTERED = False


def safe_file_token(value: object) -> str:
    """Hasta kimliğini dosya adında güvenle kullanılacak hale getirir."""

    token = "".join(char if char.isalnum() or char in "-_." else "_" for char in str(value))
    return token.strip("._") or "hasta"


def build_text_report(
    row: Mapping[str, Any],
    result: AnalysisResult,
    note: str,
    *,
    only_note: bool = False,
    language: str = "tr",
) -> str:
    """Kayıt, doktor notu ve PDF yedeği için düz metin rapor hazırlar."""

    language = normalize_language(language)
    clean_note = note.strip() or report_t(language, "no_note")
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    if only_note:
        return (
            f"{report_t(language, 'doctor_note_title')}\n"
            f"{report_t(language, 'date')}: {now}\n"
            f"{report_t(language, 'patient')}: {row['hasta_adi']} ({row['hasta_id']})\n"
            f"{report_t(language, 'risk')}: {result.level} / %{result.risk_score}\n\n"
            f"{report_t(language, 'doctor_note')}:\n"
            f"{clean_note}\n"
        )

    reasons = "\n".join(f"- {reason}" for reason in result.reasons)
    actions = "\n".join(f"- {action}" for action in result.actions)

    return f"""{report_t(language, 'patient_report_title')}
{report_t(language, 'date')}: {now}
{report_t(language, 'patient')}: {row['hasta_adi']} ({row['hasta_id']})
{report_t(language, 'age')}: {int(row['yas'])}
{report_t(language, 'service')}: {row['servis']}

{report_t(language, 'risk_score')}: %{result.risk_score}
{report_t(language, 'compatibility')}: %{result.compatibility}
{report_t(language, 'risk_level')}: {result.level}

{report_t(language, 'vitals')}:
{report_t(language, 'heart_rate')}: {row['kalp_hizi']} bpm
{report_t(language, 'temperature')}: {row['ates']} °C
{report_t(language, 'oxygen')}: {row['oksijen']} %
{report_t(language, 'systolic_bp')}: {row['sistolik_tansiyon']} mmHg
{report_t(language, 'respiration')}: {row['solunum']} /dk
WBC: {row['wbc']}
{report_t(language, 'lactate')}: {row['laktat']}

{report_t(language, 'findings')}:
{reasons}

{report_t(language, 'actions')}:
{actions}

{report_t(language, 'doctor_note')}:
{clean_note}

{report_t(language, 'warning')}
"""


def create_pdf_report(
    path: Path,
    row: Mapping[str, Any],
    result: AnalysisResult,
    note: str,
    language: str = "tr",
) -> None:
    """Hasta değerlendirmesini ReportLab ile PDF dosyasına yazar."""

    language = normalize_language(language)
    if not REPORTLAB_AVAILABLE:
        raise ReportGenerationError(report_t(language, "reportlab_missing"))

    _register_font(language)

    clean_note = escape(note.strip() or report_t(language, "no_note")).replace("\n", "<br/>")
    path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TRTitle",
        parent=styles["Title"],
        fontName="DejaVu",
        textColor=colors.HexColor("#0B3A4A"),
        fontSize=20,
        leading=24,
    )
    normal = ParagraphStyle(
        "TRNormal",
        parent=styles["BodyText"],
        fontName="DejaVu",
        fontSize=11,
        leading=14,
    )
    heading = ParagraphStyle(
        "TRHeading",
        parent=styles["Heading2"],
        fontName="DejaVu",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0B3A4A"),
    )

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    story = [
        Paragraph(report_t(language, "pdf_title"), title),
        Spacer(1, 12),
        Paragraph(report_t(language, "pdf_notice"), normal),
        Spacer(1, 10),
    ]

    patient_rows = [
        [report_t(language, "patient"), f"{row['hasta_adi']} ({row['hasta_id']})"],
        [report_t(language, "age"), str(int(row["yas"]))],
        [report_t(language, "service"), str(row["servis"])],
        [report_t(language, "report_date"), datetime.now().strftime("%d.%m.%Y %H:%M")],
    ]
    story += [_build_table(patient_rows, "#D9EEF5"), Spacer(1, 12)]

    score_rows = [
        [report_t(language, "risk_score"), f"%{result.risk_score}"],
        [report_t(language, "compatibility"), f"%{result.compatibility}"],
        [report_t(language, "risk_level"), result.level],
    ]
    story += [_build_table(score_rows, "#FFE7E7"), Spacer(1, 12)]

    vital_rows = [
        [report_t(language, "heart_rate"), row["kalp_hizi"]],
        [report_t(language, "temperature"), row["ates"]],
        [report_t(language, "oxygen"), row["oksijen"]],
        [report_t(language, "systolic_bp"), row["sistolik_tansiyon"]],
        [report_t(language, "respiration"), row["solunum"]],
        ["WBC", row["wbc"]],
        [report_t(language, "lactate"), row["laktat"]],
    ]
    story += [Paragraph(report_t(language, "vitals"), heading), _build_table(vital_rows, "#EEF7FA"), Spacer(1, 12)]

    story.append(Paragraph(report_t(language, "findings"), heading))
    for reason in result.reasons:
        story.append(Paragraph(f"• {escape(reason)}", normal))

    story += [Spacer(1, 10), Paragraph(report_t(language, "actions"), heading)]
    for action in result.actions:
        story.append(Paragraph(f"• {escape(action)}", normal))

    story += [Spacer(1, 10), Paragraph(report_t(language, "doctor_note"), heading), Paragraph(clean_note, normal)]

    try:
        doc.build(story)
    except Exception as exc:
        raise ReportGenerationError(report_t(language, "pdf_build_failed", error=exc)) from exc


def _register_font(language: str) -> None:
    """Türkçe karakterleri destekleyen yazı tipini ReportLab'e tanıtır."""

    global _FONT_REGISTERED

    if _FONT_REGISTERED:
        return

    if not FONT_PATH.exists():
        raise ReportGenerationError(report_t(language, "font_missing", path=FONT_PATH))

    try:
        pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_PATH)))
    except Exception as exc:
        raise ReportGenerationError(report_t(language, "font_failed", error=exc)) from exc

    _FONT_REGISTERED = True


def _build_table(rows: list[list[object]], label_background: str) -> Table:
    """PDF içindeki iki sütunlu bilgi tabloları için ortak stil üretir."""

    table = Table(rows, colWidths=[150, 310])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(label_background)),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table
