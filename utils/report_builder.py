from __future__ import annotations

import os
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

# Switch to ReportLab for PDF rendering
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

import config


@dataclass
class LLMResult:
    executive_summary: str
    performance_analysis: str
    deliverability_assessment: str
    recommendations: str
    next_steps: str


def _safe_rate(numer: float, denom: float) -> float:
    return round((numer / denom * 100.0) if denom else 0.0, 2)


def _ensure_str_list(value: Any) -> list:
    """Coerce various input shapes into a list of strings.

    Handles: None, list[str], str (possibly JSON or newline-separated), dict -> flattened key:value lines.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    if isinstance(value, dict):
        items = []
        for k, v in value.items():
            if isinstance(v, (list, dict)):
                items.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
            else:
                items.append(f"{k}: {v}")
        return items
    if isinstance(value, str):
        s = value.strip()
        # Try JSON
        try:
            parsed = json.loads(s)
            return _ensure_str_list(parsed)
        except Exception:
            # Split on newlines, numbered lists, or semicolons
            lines = [ln.strip().lstrip('-•*0123456789. ') for ln in s.splitlines() if ln.strip()]
            if len(lines) > 1:
                return lines
            return [s]
    # Fallback
    return [str(value)]


def _join_as_bullets(value: Any) -> str:
    """Return a newline-joined bullet string for the given value."""
    parts = _ensure_str_list(value)
    if not parts:
        return ""
    return "\n".join(parts)


def _format_value_plain(value: Any, indent: int = 0) -> str:
    """Format dict/list/primitive into clean plain text with indentation.

    - dict -> lines of `key:` and indented values
    - list -> `- item` lines (recursively formatted if nested)
    - primitive -> string value
    """
    pad = "  " * indent
    lines = []

    if value is None:
        return ""

    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}:")
                sub = _format_value_plain(v, indent + 1)
                if sub:
                    lines.append(sub)
            else:
                lines.append(f"{pad}{k}: {v}")
        return "\n".join(lines)

    if isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                sub = _format_value_plain(item, indent + 1)
                if sub:
                    lines.append(sub)
            else:
                lines.append(f"{pad}- {item}")
        return "\n".join(lines)

    # Primitive
    return f"{pad}{value}"


escape_map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
}


def _escape_html(text: str) -> str:
    out = text or ""
    for k, v in escape_map.items():
        out = out.replace(k, v)
    return out


def _to_paragraph_text(text: str) -> str:
    """Escape HTML and convert newlines to <br/> for ReportLab Paragraph."""
    return _escape_html(text or "").replace("\n", "<br/>")


def _format_text_section(value: Any) -> str:
    """Return a clean plain-text section string from possibly JSON-like input.

    If `value` is a string containing JSON, parse and pretty-format it.
    If it's already a dict/list, format directly. Otherwise return the string.
    """
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return _format_value_plain(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return ""
        # Try to parse JSON and pretty-print if it works
        try:
            parsed = json.loads(s)
            return _format_value_plain(parsed)
        except Exception:
            return s
    return str(value)


def build_campaign_payload(campaign_state: Dict[str, Any], global_stats_df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    """
    Normalize data needed for the final report.
    """
    campaign_id = campaign_state.get("campaign_id")
    strategy = campaign_state.get("strategy", {})
    ab_results = campaign_state.get("ab_results", {})
    deliverability = campaign_state.get("deliverability_check", {})

    # Summaries
    totals = {
        "sent": sum(v.get("sent", 0) for v in ab_results.values()) if isinstance(ab_results, dict) else 0,
        "opened": sum(v.get("opened", 0) for v in ab_results.values()) if isinstance(ab_results, dict) else 0,
        "clicked": sum(v.get("clicked", 0) for v in ab_results.values()) if isinstance(ab_results, dict) else 0,
        "bounced": sum(v.get("bounced", 0) for v in ab_results.values()) if isinstance(ab_results, dict) else 0,
    }
    totals["open_rate"] = _safe_rate(totals["opened"], totals["sent"]) if totals else 0
    totals["click_rate"] = _safe_rate(totals["clicked"], totals["sent"]) if totals else 0
    totals["bounce_rate"] = _safe_rate(totals["bounced"], totals["sent"]) if totals else 0

    global_stats = None
    if global_stats_df is not None and not global_stats_df.empty:
        numeric_cols = [c for c in global_stats_df.columns if c != "date"]
        if numeric_cols:
            s = global_stats_df[numeric_cols].sum()
            global_stats = {k: int(s[k]) for k in numeric_cols if pd.notna(s[k])}

    payload = {
        "campaign_id": campaign_id,
        "campaign_name": campaign_state.get("campaign_name", "Unnamed Campaign"),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "strategy": {
            "goal": strategy.get("goal") or strategy.get("objective"),
            "audience": strategy.get("audience"),
            "value_proposition": strategy.get("value_proposition") or strategy.get("valueProp"),
            "kpis": strategy.get("kpis", {}),
            "subject_ideas": strategy.get("subject_suggestions") or strategy.get("subject_lines") or [],
            "ctas": strategy.get("ctas") or ([strategy.get("cta")] if isinstance(strategy.get("cta"), str) else []),
        },
        "ab_results": ab_results,
        "totals": totals,
        "deliverability": deliverability,
        "sendgrid_global": global_stats,
    }
    return payload


def _build_llm_prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are an expert email marketing analyst. Given the campaign data JSON below, "
        "produce a structured analysis with these sections: "
        "1) Executive Summary (<200 words)\n"
        "2) Performance Analysis (variant comparison, key drivers)\n"
        "3) Deliverability Assessment (risks, likely causes)\n"
        "4) Recommendations (prioritized, concrete actions)\n"
        "5) Next Steps (checklist for the next 7 days).\n\n"
        "Return a JSON object with these keys: executive_summary, performance_analysis, "
        "deliverability_assessment, recommendations, next_steps.\n\n"
        f"Campaign Data JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def call_llm_for_insights(payload: Dict[str, Any]) -> LLMResult:
    # Minimal OpenAI client without extra deps; assumes 'openai' package or HTTP call available.
    # To keep dependencies simple, we simulate a fallback if OPENAI_API_KEY is not set.
    api_key = getattr(config, "OPENAI_API_KEY", "")
    model = getattr(config, "OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        # Fallback deterministic text if no key configured
        return LLMResult(
            executive_summary="Executive summary unavailable (no LLM key configured). Overall performance summarized by totals.",
            performance_analysis="Variant comparison suggests opportunities to optimize subject lines and CTAs.",
            deliverability_assessment="Review sender reputation, authentication, and content signals.",
            recommendations=_join_as_bullets("1) Test subject lines\n2) Improve preheaders\n3) Tighten audience hygiene\n4) Iterate on CTA placement."),
            next_steps=_join_as_bullets("Day 1: Clean list\nDay 2-3: Create A/B subject tests\nDay 4: Template improvements\nDay 5-7: Send, monitor, iterate."),
        )

    try:
        import requests
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        prompt = _build_llm_prompt(payload)
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        try:
            parsed = json.loads(text)
        except Exception:
            # If the model returned text not JSON, use raw text as the executive summary
            parsed = {
                "executive_summary": text[:2000],
                "performance_analysis": "",
                "deliverability_assessment": "",
                "recommendations": "",
                "next_steps": "",
            }
        # Normalize fields into clean plain text (indent lists/dicts)
        exec_sum_raw = parsed.get("executive_summary", "")
        perf_raw = parsed.get("performance_analysis", "")
        deliver_raw = parsed.get("deliverability_assessment", "")
        recs = _join_as_bullets(parsed.get("recommendations", ""))
        steps = _join_as_bullets(parsed.get("next_steps", ""))

        return LLMResult(
            executive_summary=_format_text_section(exec_sum_raw),
            performance_analysis=_format_text_section(perf_raw),
            deliverability_assessment=_format_text_section(deliver_raw),
            recommendations=recs,
            next_steps=steps,
        )
    except Exception:
        return LLMResult(
            executive_summary="Executive summary unavailable due to LLM call failure.",
            performance_analysis="",
            deliverability_assessment="",
            recommendations="",
            next_steps="",
        )


# ReportLab rendering helpers

def _render_reportlab_pdf(payload: Dict[str, Any], llm: LLMResult, pdf_path: str, global_df: Optional[pd.DataFrame]) -> None:
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    title = f"Campaign Report: {payload.get('campaign_name')} ({payload.get('campaign_id')})"
    story.append(Paragraph(title, styles['Title']))
    story.append(Paragraph(f"Generated: {payload.get('generated_at')}", styles['Normal']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Executive Summary", styles['Heading2']))
    story.append(Paragraph(_to_paragraph_text(llm.executive_summary or 'N/A'), styles['BodyText']))
    story.append(Spacer(1, 12))

    totals = payload.get('totals', {}) or {}
    metrics_data = [
        ["Sent", str(totals.get('sent', 0))],
        ["Opened", str(totals.get('opened', 0))],
        ["Open Rate", f"{totals.get('open_rate', 0)}%"],
        ["Clicked", str(totals.get('clicked', 0))],
        ["Click Rate", f"{totals.get('click_rate', 0)}%"],
        ["Bounced", str(totals.get('bounced', 0))],
        ["Bounce Rate", f"{totals.get('bounce_rate', 0)}%"],
    ]
    t = Table(metrics_data, hAlign='LEFT', colWidths=[120, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
    ]))
    story.append(Paragraph("Key Metrics", styles['Heading2']))
    story.append(t)
    story.append(Spacer(1, 12))

    # Variant comparison table
    ab = payload.get('ab_results', {}) or {}
    table_data = [["Variant", "Sent", "Opened", "Clicked", "Open Rate", "Click Rate", "Bounced"]]
    for v, m in ab.items():
        table_data.append([
            v,
            str(m.get('sent', 0)),
            str(m.get('opened', 0)),
            str(m.get('clicked', 0)),
            f"{m.get('open_rate', 0)}%",
            f"{m.get('click_rate', 0)}%",
            str(m.get('bounced', 0)),
        ])
    vt = Table(table_data, hAlign='LEFT')
    vt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('ALIGN', (1,1), (-1,-1), 'LEFT'),
    ]))
    story.append(Paragraph("Variant Comparison", styles['Heading2']))
    story.append(vt)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Performance Analysis", styles['Heading2']))
    story.append(Paragraph(_to_paragraph_text(llm.performance_analysis or 'N/A'), styles['BodyText']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Deliverability Assessment", styles['Heading2']))
    story.append(Paragraph(_to_paragraph_text(llm.deliverability_assessment or 'N/A'), styles['BodyText']))
    story.append(Spacer(1, 12))

    # Provider global stats summary
    if global_df is not None and not global_df.empty:
        story.append(Paragraph("Provider Global Stats (Totals)", styles['Heading2']))
        numeric_cols = [c for c in global_df.columns if c != 'date']
        if numeric_cols:
            sums = global_df[numeric_cols].sum()
            gdata = [["Metric", "Total"]] + [[k.replace('_',' ').title(), str(int(sums[k]))] for k in numeric_cols]
            gt = Table(gdata, hAlign='LEFT', colWidths=[200, 100])
            gt.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('ALIGN', (1,1), (-1,-1), 'LEFT'),
            ]))
            story.append(gt)
            story.append(Spacer(1, 12))

    story.append(Paragraph("Recommendations", styles['Heading2']))
    if llm.recommendations:
        for line in llm.recommendations.splitlines():
            if line.strip():
                story.append(Paragraph(f"• {line.strip()}", styles['BodyText']))
    else:
        story.append(Paragraph('N/A', styles['BodyText']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Next Steps", styles['Heading2']))
    if llm.next_steps:
        for line in llm.next_steps.splitlines():
            if line.strip():
                story.append(Paragraph(f"• {line.strip()}", styles['BodyText']))
    else:
        story.append(Paragraph('N/A', styles['BodyText']))

    doc.build(story)


def generate_pdf_report(campaign_state: Dict[str, Any], results_dir: str, global_stats_df: Optional[pd.DataFrame] = None) -> str:
    """
    Build payload, call LLM for insights, and export a PDF using ReportLab.
    Returns the path to the generated PDF file. If ReportLab is unavailable,
    a .html fallback will be created with a plain text dump.
    """
    os.makedirs(results_dir, exist_ok=True)
    payload = build_campaign_payload(campaign_state, global_stats_df)
    llm = call_llm_for_insights(payload)

    # If LLM didn't return recommendations/next_steps, fall back to any existing report content
    report_section = campaign_state.get('campaign_report', {}) or {}
    if not llm.recommendations:
        if report_section.get('recommendations'):
            llm.recommendations = _join_as_bullets(report_section.get('recommendations'))
    if not llm.next_steps:
        if report_section.get('next_steps'):
            llm.next_steps = _join_as_bullets(report_section.get('next_steps'))

    # Output path
    campaign_id = campaign_state.get("campaign_id", "unknown")
    report_dir = os.path.join(results_dir, str(campaign_id))
    os.makedirs(report_dir, exist_ok=True)
    pdf_path = os.path.join(report_dir, f"final_report_{campaign_id}.pdf")

    if REPORTLAB_AVAILABLE:
        _render_reportlab_pdf(payload, llm, pdf_path, global_stats_df)
        return pdf_path

    # Fallback: create a minimal HTML if ReportLab is not available
    html_path = os.path.join(report_dir, f"final_report_{campaign_id}.html")

    def _build_plain_text_report(payload: Dict[str, Any], llm: LLMResult, global_df: Optional[pd.DataFrame]) -> str:
        lines = []
        lines.append(f"Campaign Report: {payload.get('campaign_name')} ({payload.get('campaign_id')})")
        lines.append(f"Generated: {payload.get('generated_at')}")
        lines.append("")
        lines.append("Executive Summary")
        lines.append("-------------------")
        lines.append(_format_text_section(llm.executive_summary) or "N/A")
        lines.append("")

        totals = payload.get('totals', {}) or {}
        lines.append("Key Metrics")
        lines.append("-----------")
        lines.append(f"Sent: {totals.get('sent', 0)}")
        lines.append(f"Opened: {totals.get('opened', 0)}")
        lines.append(f"Open Rate: {totals.get('open_rate', 0)}%")
        lines.append(f"Clicked: {totals.get('clicked', 0)}")
        lines.append(f"Click Rate: {totals.get('click_rate', 0)}%")
        lines.append(f"Bounced: {totals.get('bounced', 0)}")
        lines.append(f"Bounce Rate: {totals.get('bounce_rate', 0)}%")
        lines.append("")

        ab = payload.get('ab_results', {}) or {}
        if ab:
            lines.append("Variant Comparison")
            lines.append("-------------------")
            for v, m in ab.items():
                lines.append(f"{v}:")
                lines.append(f"  Sent: {m.get('sent', 0)}")
                lines.append(f"  Opened: {m.get('opened', 0)}")
                lines.append(f"  Clicked: {m.get('clicked', 0)}")
                lines.append(f"  Open Rate: {m.get('open_rate', 0)}%")
                lines.append(f"  Click Rate: {m.get('click_rate', 0)}%")
                lines.append(f"  Bounced: {m.get('bounced', 0)}")
            lines.append("")

        lines.append("Performance Analysis")
        lines.append("---------------------")
        lines.append(_format_text_section(llm.performance_analysis) or "N/A")
        lines.append("")

        lines.append("Deliverability Assessment")
        lines.append("--------------------------")
        lines.append(_format_text_section(llm.deliverability_assessment) or "N/A")
        lines.append("")

        lines.append("Recommendations")
        lines.append("----------------")
        if llm.recommendations:
            for line in llm.recommendations.splitlines():
                if line.strip():
                    lines.append(f"- {line.strip()}")
        else:
            lines.append("N/A")
        lines.append("")

        lines.append("Next Steps")
        lines.append("----------")
        if llm.next_steps:
            for line in llm.next_steps.splitlines():
                if line.strip():
                    lines.append(f"- {line.strip()}")
        else:
            lines.append("N/A")
        lines.append("")

        return "\n".join(lines)

    text_body = _build_plain_text_report(payload, llm, global_stats_df)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><body><pre>" + _escape_html(text_body) + "</pre></body></html>")
    return html_path
