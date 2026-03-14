import json
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table


def export_pdf(report_path: str, output_path: str | None = None) -> str:
    if not os.path.exists(report_path):
        raise FileNotFoundError(report_path)

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"compliance_report_{ts}.pdf"

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("AuditTrail Compliance Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Project: {report.get('project')}", styles["Normal"]))
    elements.append(Paragraph(f"Generated at: {report.get('generated_at')}", styles["Normal"]))
    elements.append(Paragraph(f"Risk level: {report.get('risk_level')}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    summary = report.get("summary", {})
    summary_data = [
        ["Total traces", summary.get("total_traces", 0)],
        ["Total events", summary.get("total_events", 0)],
        ["Violations found", summary.get("violations_found", 0)],
    ]
    elements.append(Table(summary_data))
    elements.append(Spacer(1, 12))

    doc.build(elements)
    return output_path


if __name__ == "__main__":
    # Example usage:
    # python pdf_exporter.py ./demo_output/fraud-detection-demo_compliance_report_XXXX.json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_exporter.py <compliance_report.json>")
        raise SystemExit(1)
    out = export_pdf(sys.argv[1])
    print(f"PDF exported to: {out}")
