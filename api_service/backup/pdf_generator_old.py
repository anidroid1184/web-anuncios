"""
Generador de reportes PDF usando ReportLab
Soporta múltiples formatos de estructura JSON
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT


def generar_reporte_pdf(
    json_data: dict,
    output_path: Path
) -> Path:
    """
    Genera un reporte PDF a partir del análisis JSON de OpenAI.

    Args:
        json_data: Diccionario con el análisis (debe seguir estructura esperada)
        output_path: Path donde guardar el PDF

    Returns:
        Path del archivo PDF generado
    """
    doc = SimpleDocTemplate(str(output_path), pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # --- Estilos Personalizados ---
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        textColor=colors.black
    )
    normal_style = styles['BodyText']
    normal_style.alignment = TA_JUSTIFY

    # 1. Título del Reporte
    campaign_name = json_data.get('campaign_name', 'Análisis de Campaña')
    elements.append(
        Paragraph(f"Análisis Forense de Video: {campaign_name}", title_style)
    )
    elements.append(Spacer(1, 20))

    # 2. Resumen Ejecutivo
    elements.append(Paragraph("Resumen Ejecutivo", subtitle_style))
    executive_summary = json_data.get('executive_summary', 'No disponible')
    elements.append(Paragraph(executive_summary, normal_style))
    elements.append(Spacer(1, 20))

    # 3. Análisis Comparativo (Iterar sobre Ganador/Perdedor)
    comparative_analysis = json_data.get('comparative_analysis', [])

    for video in comparative_analysis:
        # Color del encabezado según si es Ganador o Perdedor
        header_color = (
            colors.green if "Ganador" in video.get('status', '')
            else colors.red
        )
        status_text = f"{video.get('status', 'Video')} (ID: {video.get('ad_id', 'N/A')})"

        elements.append(
            Paragraph(
                status_text,
                ParagraphStyle(
                    'Status',
                    parent=styles['Heading3'],
                    textColor=header_color
                )
            )
        )

        # A. Tabla de Métricas Reales
        real_metrics = video.get('real_metrics', {})
        metrics_data = [
            ["Métrica", "Valor"],
            ["VTR (View Through Rate)", real_metrics.get('vtr', 'N/A')],
            ["CTR (Click Through Rate)", real_metrics.get('ctr', 'N/A')],
            ["Shares", real_metrics.get('shares', 'N/A')]
        ]
        t_metrics = Table(metrics_data, colWidths=[200, 200])
        t_metrics.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(t_metrics)
        elements.append(Spacer(1, 10))

        # B. Análisis Forense
        elements.append(Paragraph("<b>Detalle Forense:</b>", styles['Normal']))
        forensic = video.get('forensic_analysis', {})
        forensic_text = f"""
        <b>Hook (0-3s):</b> {forensic.get('hook_0_3s', 'N/A')}<br/>
        <b>Audio:</b> {forensic.get('audio', 'N/A')}<br/>
        <b>Ritmo Edición:</b> {forensic.get('editing_pace', 'N/A')}
        """
        elements.append(Paragraph(forensic_text, normal_style))
        elements.append(Spacer(1, 10))

        # C. Puntuaciones (Scores)
        scores = video.get('scores_qualitative', {})
        score_text = (
            f"<b>Puntuación Psicológica & Técnica:</b> "
            f"Composición Visual: {scores.get('visual_composition', 0)}/10 | "
            f"Psicología: {scores.get('target_psychology', 0)}/10 | "
            f"Potencial Conversión: {scores.get('conversion_potential', 0)}/10"
        )
        elements.append(Paragraph(score_text, normal_style))

        elements.append(Spacer(1, 10))
        justification = video.get('justification', 'N/A')
        elements.append(
            Paragraph(f"<b>Justificación:</b> {justification}", normal_style)
        )

        # Recomendaciones específicas del video
        recommendations = video.get('recommendations', '')
        if recommendations:
            elements.append(Spacer(1, 10))
            elements.append(
                Paragraph(
                    f"<b>Recomendaciones:</b> {recommendations}", normal_style)
            )

        elements.append(Spacer(1, 20))
        elements.append(
            Paragraph(
                "- - - - - - - - - - - - - - - - - - - - - - - - -",
                ParagraphStyle('Separator', parent=normal_style,
                               alignment=TA_CENTER)
            )
        )
        elements.append(Spacer(1, 20))

    # 4. Recomendaciones Generales
    general_recs = json_data.get('general_recommendations', [])
    if general_recs:
        elements.append(
            Paragraph("Recomendaciones Estratégicas Finales", subtitle_style)
        )
        for rec in general_recs:
            elements.append(Paragraph(f"• {rec}", normal_style))

    # Construir PDF
    doc.build(elements)
    return output_path
