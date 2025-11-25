 """
Generador de reportes PDF usando ReportLab
Soporta estructura JSON forense detallada y legacy
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY


def generar_reporte_pdf(json_data: dict, output_path: Path) -> Path:
    """Genera PDF forense completo desde JSON de OpenAI"""
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=0.75*inch, rightMargin=0.75*inch
    )
    elements = []
    styles = getSampleStyleSheet()

    # Estilos
    title = ParagraphStyle(
        'Title', parent=styles['Heading1'], alignment=TA_CENTER,
        textColor=colors.HexColor('#1a1a2e'), fontSize=18, spaceAfter=20
    )
    h2 = ParagraphStyle(
        'H2', parent=styles['Heading2'],
        textColor=colors.HexColor('#16213e'), fontSize=14, spaceAfter=12
    )
    h3 = ParagraphStyle(
        'H3', parent=styles['Heading3'],
        textColor=colors.HexColor('#0f3460'), fontSize=12, spaceAfter=8
    )
    normal = ParagraphStyle(
        'Normal', parent=styles['BodyText'],
        alignment=TA_JUSTIFY, fontSize=10, leading=14
    )
    bullet = ParagraphStyle(
        'Bullet', parent=normal, leftIndent=20, bulletIndent=10
    )

    # Detectar estructura
    is_forensic = 'assets_analysis' in json_data
    is_legacy = 'comparative_analysis' in json_data

    # METADATA
    if is_forensic and 'metadata' in json_data:
        meta = json_data['metadata']
        elements.append(
            Paragraph(meta.get('report_title', 'Análisis Forense'), title)
        )
        meta_table = Table([
            ['Fecha:', meta.get('date', 'N/A')],
            ['Analista:', meta.get('analyst', 'N/A')],
            ['Assets:', str(meta.get('total_assets_analyzed', 'N/A'))],
            ['ID:', meta.get('campaign_id', 'N/A')]
        ], colWidths=[1.5*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(meta_table)
    else:
        elements.append(
            Paragraph(
                f"Análisis: {json_data.get('campaign_name', 'N/A')}", title
            )
        )
    elements.append(Spacer(1, 20))

    # RESUMEN EJECUTIVO
    elements.append(Paragraph("Resumen Ejecutivo", h2))
    if is_forensic and isinstance(json_data.get('executive_summary'), dict):
        for k in ['overview', 'key_patterns', 'critical_findings']:
            if k in json_data['executive_summary']:
                elements.append(
                    Paragraph(json_data['executive_summary'][k], normal)
                )
                elements.append(Spacer(1, 10))
    else:
        elements.append(
            Paragraph(
                json_data.get('executive_summary', 'No disponible'), normal
            )
        )
    elements.append(Spacer(1, 20))

    # ANÁLISIS DE ACTIVOS (FORENSIC)
    if is_forensic and 'assets_analysis' in json_data:
        elements.append(PageBreak())
        elements.append(Paragraph("Análisis Detallado de Activos", h2))

        for idx, asset in enumerate(json_data['assets_analysis'], 1):
            elements.append(
                Paragraph(
                    f"Activo #{idx}: {asset.get('file_name', 'N/A')}", h3
                )
            )

            # Info básica
            info = Table([
                ['ID:', asset.get('asset_id', 'N/A')],
                ['Tipo:', asset.get('asset_type', 'N/A')]
            ], colWidths=[1*inch, 4.5*inch])
            info.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(info)
            elements.append(Spacer(1, 12))

            # Visual Forensics
            if 'visual_forensics' in asset:
                elements.append(
                    Paragraph("<b>Análisis Visual:</b>", normal)
                )
                vf = asset['visual_forensics']
                for key, label in [
                    ('composition', 'Composición'),
                    ('lighting_color', 'Iluminación'),
                    ('subjects_elements', 'Sujetos')
                ]:
                    if key in vf:
                        elements.append(
                            Paragraph(f"• <b>{label}:</b> {vf[key]}", bullet)
                        )
                elements.append(Spacer(1, 10))

            # Semiótica
            if 'semiotic_analysis' in asset:
                elements.append(Paragraph("<b>Semiótica:</b>", normal))
                sa = asset['semiotic_analysis']
                for key in sa:
                    elements.append(
                        Paragraph(f"• <b>{key}:</b> {sa[key]}", bullet)
                    )
                elements.append(Spacer(1, 10))

            # Triggers
            if 'psychological_triggers' in asset:
                elements.append(Paragraph("<b>Triggers:</b>", normal))
                pt = asset['psychological_triggers']
                elements.append(
                    Paragraph(
                        f"• Principal: {pt.get('primary_trigger', 'N/A')}",
                        bullet
                    )
                )
                elements.append(
                    Paragraph(
                        f"• {pt.get('trigger_explanation', 'N/A')}", bullet
                    )
                )
                elements.append(Spacer(1, 10))

            # Scores
            if 'effectiveness_scores' in asset:
                elements.append(Paragraph("<b>Efectividad:</b>", normal))
                es = asset['effectiveness_scores']
                scores = Table([
                    ['Métrica', 'Score'],
                    ['Stopping Power', str(es.get('stopping_power', '-'))],
                    ['Claridad', str(es.get('message_clarity', '-'))],
                    ['Emoción', str(es.get('emotional_relevance', '-'))],
                    ['CTA', str(es.get('cta_strength', '-'))],
                    ['Recall', str(es.get('brand_recall', '-'))],
                    ['GENERAL', str(es.get('overall_score', '-'))]
                ], colWidths=[3*inch, 1.5*inch])
                scores.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3460')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ]))
                elements.append(scores)
                elements.append(Spacer(1, 10))

            # Optimización
            if 'optimization_roadmap' in asset:
                elements.append(Paragraph("<b>Optimización:</b>", normal))
                for o in asset['optimization_roadmap']:
                    pri = o.get('priority', 'MEDIA')
                    elements.append(
                        Paragraph(
                            f"<b>[{pri}]</b> {o.get('action', '')}", bullet)
                    )
                    elements.append(Spacer(1, 5))

            elements.append(Spacer(1, 20))

    # ANÁLISIS LEGACY
    elif is_legacy and 'comparative_analysis' in json_data:
        for video in json_data['comparative_analysis']:
            color = (
                colors.green if "Ganador" in video.get('status', '')
                else colors.red
            )
            elements.append(
                Paragraph(
                    f"{video.get('status', '')} (ID: {video.get('ad_id', '')})",
                    ParagraphStyle('S', parent=h3, textColor=color)
                )
            )

            # Métricas
            m = video.get('real_metrics', {})
            mt = Table([
                ['Métrica', 'Valor'],
                ['VTR', m.get('vtr', 'N/A')],
                ['CTR', m.get('ctr', 'N/A')],
                ['Shares', m.get('shares', 'N/A')]
            ])
            mt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(mt)
            elements.append(Spacer(1, 10))

            # Forense
            f = video.get('forensic_analysis', {})
            elements.append(
                Paragraph(
                    f"<b>Hook:</b> {f.get('hook_0_3s', 'N/A')}", normal
                )
            )
            elements.append(
                Paragraph(f"<b>Audio:</b> {f.get('audio', 'N/A')}", normal)
            )
            elements.append(Spacer(1, 15))

    # CONCLUSIONES
    elements.append(PageBreak())
    elements.append(Paragraph("Conclusiones", h2))

    if is_forensic and 'global_conclusions' in json_data:
        gc = json_data['global_conclusions']
        for key in gc:
            elements.append(Paragraph(f"<b>{key}:</b> {gc[key]}", normal))
            elements.append(Spacer(1, 10))

    # Recomendaciones
    if 'general_recommendations' in json_data:
        elements.append(Paragraph("Recomendaciones", h2))
        for rec in json_data['general_recommendations']:
            elements.append(Paragraph(f"• {rec}", bullet))

    # ROADMAP
    if is_forensic and 'strategic_roadmap' in json_data:
        elements.append(PageBreak())
        elements.append(Paragraph("Roadmap Estratégico", h2))
        sr = json_data['strategic_roadmap']

        if 'immediate_actions' in sr:
            elements.append(Paragraph("<b>Inmediato (48h):</b>", normal))
            for a in sr['immediate_actions']:
                elements.append(Paragraph(f"• {a}", bullet))
            elements.append(Spacer(1, 10))

        if 'short_term_plan' in sr:
            elements.append(Paragraph("<b>Corto Plazo:</b>", normal))
            elements.append(Paragraph(sr['short_term_plan'], normal))
            elements.append(Spacer(1, 10))

        if 'long_term_strategy' in sr:
            elements.append(Paragraph("<b>Largo Plazo:</b>", normal))
            elements.append(Paragraph(sr['long_term_strategy'], normal))

    doc.build(elements)
    return output_path
