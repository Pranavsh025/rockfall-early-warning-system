"""PDF risk report generation (ReportLab)."""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BROWN = colors.HexColor("#5b3a1e")
SAND = colors.HexColor("#ead9c6")
RED = colors.HexColor("#d93a2f")
LEVEL_COLOR = {"LOW": "#2f8f4e", "MODERATE": "#d68a1a", "HIGH": "#d93a2f", "CRITICAL": "#8e1b14"}


def build_pdf(a: dict, name: str, location: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title=f"Rockfall Risk Report - {name}")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=BROWN, fontSize=20)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=BROWN, spaceBefore=10)
    body = ss["BodyText"]
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=colors.grey)

    lvl = a["risk_level"]
    story = [
        Paragraph("Rockfall Risk Assessment Report", h1),
        Paragraph(f"<b>{name}</b> — {location}", body),
        Paragraph(f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}", small),
        Spacer(1, 8),
        Paragraph(f"<font size=26 color='{LEVEL_COLOR[lvl]}'><b>{a['overall_score']:.1f}%</b></font>"
                  f"&nbsp;&nbsp;<font size=12 color='{LEVEL_COLOR[lvl]}'><b>{lvl} RISK</b></font>", body),
        Spacer(1, 14),
        Paragraph(f"ML ensemble probability (RF + XGBoost + Naive Bayes): <b>{a['ml_probability'] * 100:.1f}%</b>"
                  f" &nbsp;|&nbsp; Fuzzy AHP score: <b>{a['fahp_score']:.1f}</b>", body),
        Paragraph("Component scores", h2),
    ]

    comp = [["Criterion", "Fuzzy AHP weight", "Criterion risk", "Score contribution"]]
    for k, v in a["criteria"].items():
        comp.append([k.replace("_", " ").title(), f"{v['weight']:.3f}", f"{v['risk'] * 100:.0f}%", f"{a['components'][k]:.1f}"])
    story.append(_table(comp))

    story.append(Paragraph("Risk factors", h2))
    rf = [["Factor", "Level", "Fuzzy risk"]] + [[f["label"], f["level"], f"{f['risk'] * 100:.0f}%"] for f in a["risk_factors"]]
    story.append(_table(rf))

    e = a["environment"]
    story.append(Paragraph("Environmental conditions", h2))
    story.append(_table([
        ["Annual rainfall", f"{e['annual_rainfall']} mm", "Soil moisture", f"{e['soil_moisture']}%"],
        ["Soil type", str(e["soil_type"]), "Pore pressure", f"{e['pore_pressure']} kPa"],
        ["Last blasting", str(e.get("last_blasting") or "—"), "Days since blast", f"{e['days_since_blast']}"],
    ], header=False))

    story.append(Paragraph("Recommendations", h2))
    for r in a["recommendations"]:
        c = "#d93a2f" if r["severity"] == "critical" else "#b36b00" if r["severity"] == "warning" else "#5b3a1e"
        story.append(Paragraph(f"<font color='{c}'><b>• {r['title']}</b></font> — {r['detail']}", body))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Decision-support output. Field verification by a qualified geotechnical engineer is required "
                           "before operational decisions.", small))
    doc.build(story)
    return buf.getvalue()


def _table(rows, header=True):
    t = Table(rows, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8c4ad")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), SAND), ("TEXTCOLOR", (0, 0), (-1, 0), BROWN),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t
