"""
PDF Generator Module
Genera PDFs profesionales directamente desde análisis JSON usando ReportLab
"""
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image as RLImage, KeepTogether
)
from reportlab.pdfgen import canvas
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import json


def parse_analysis_json(analysis_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parsea el campo 'analysis' si está en formato string con JSON embebido
    """
    if 'analysis' in analysis_json and isinstance(analysis_json['analysis'], str):
        try:
            analysis_str = analysis_json['analysis']
            # Remover markdown code blocks
            if '```json' in analysis_str:
                analysis_str = analysis_str.split('```json')[1].split('```')[0]
            elif '```' in analysis_str:
                analysis_str = analysis_str.split('```')[1].split('```')[0]

            analysis_str = analysis_str.strip()
            parsed = json.loads(analysis_str)
            return parsed
        except Exception:
            return {}
    return {}


def create_pdf_from_analysis(
    analysis_json: Dict[str, Any],
    output_path: Path,
    run_id: str
) -> Dict[str, Any]:
    """
    Genera un PDF profesional desde un análisis JSON

    Args:
        analysis_json: Datos del análisis en formato JSON
        output_path: Ruta donde guardar el PDF
        run_id: ID de la campaña

    Returns:
        Dict con success, pdf_path, y error (si hay)
    """
    try:
        # Crear documento
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"Análisis de Campaña - {run_id}"
        )

        # Contenedor de elementos
        story = []

        # Estilos
        styles = getSampleStyleSheet()

        # Estilos personalizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#283593'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )

        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#3949ab'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        )

        # ===== PORTADA =====
        story.append(Spacer(1, 2*inch))
        story.append(
            Paragraph("ANÁLISIS DE CAMPAÑA PUBLICITARIA", title_style))
        story.append(Spacer(1, 0.3*inch))

        info_data = [
            ["Run ID:", run_id],
            ["Fecha:", datetime.now().strftime("%d/%m/%Y %H:%M")],
            ["Modelo:", analysis_json.get('model', 'N/A')],
            ["Anuncios:", str(analysis_json.get('total_ads_analyzed', 0))],
            ["Imágenes:", str(analysis_json.get('total_images', 0))],
            ["Videos:", str(analysis_json.get('total_videos', 0))],
            ["Tokens:", f"{analysis_json.get('tokens_used', 0):,}"]
        ]

        info_table = Table(info_data, colWidths=[3*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#283593')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(info_table)
        story.append(PageBreak())

        # ===== PARSEAR ANÁLISIS =====
        parsed_analysis = parse_analysis_json(analysis_json)

        if not parsed_analysis:
            # Si no hay análisis parseado, mostrar mensaje
            story.append(Paragraph("RESUMEN EJECUTIVO", heading_style))
            story.append(Paragraph(
                "No se pudo parsear el análisis detallado. "
                "Revisa el archivo JSON para más información.",
                normal_style
            ))
            story.append(PageBreak())
        else:
            # ===== RESUMEN EJECUTIVO =====
            story.append(Paragraph("RESUMEN EJECUTIVO", heading_style))

            # Obtener nombre de campaña si existe
            campaign_name = parsed_analysis.get('campaign_name', '')
            if campaign_name:
                story.append(Paragraph(
                    f"<b>Campaña:</b> {campaign_name}",
                    normal_style
                ))
                story.append(Spacer(1, 0.1*inch))

            # Buscar en múltiples claves posibles
            executive_summary = (
                parsed_analysis.get('executive_summary') or
                parsed_analysis.get('conclusion') or
                "No se encontró resumen ejecutivo."
            )
            story.append(Paragraph(executive_summary, normal_style))

            # Insights de campaña si existen
            campaign_insights = parsed_analysis.get('campaign_insights', {})
            if campaign_insights:
                story.append(Spacer(1, 0.2*inch))
                story.append(
                    Paragraph("<b>Hallazgos Clave:</b>", normal_style))
                for finding in campaign_insights.get('key_findings', [])[:5]:
                    story.append(Paragraph(f"• {finding}", normal_style))

            story.append(Spacer(1, 0.3*inch))

            # ===== ANÁLISIS COMPARATIVO =====
            # Detectar estructura: comparative_analysis (nuevo) o ads (antiguo)
            comparative_analysis = parsed_analysis.get(
                'comparative_analysis', [])
            ads = parsed_analysis.get('ads', [])

            if comparative_analysis:
                # Nueva estructura: análisis comparativo de videos
                story.append(PageBreak())
                story.append(
                    Paragraph("ANÁLISIS COMPARATIVO DE VIDEOS", heading_style))

                for video in comparative_analysis:
                    status = video.get('status', 'Video')
                    ad_id = video.get('ad_id', 'N/A')

                    # Título del video
                    story.append(
                        Paragraph(f"{status}: {ad_id}", subheading_style))
                    story.append(Spacer(1, 0.1*inch))

                    # Métricas reales
                    real_metrics = video.get('real_metrics', {})
                    if real_metrics:
                        story.append(
                            Paragraph("<b>Métricas Reales:</b>", normal_style))
                        for metric, value in real_metrics.items():
                            metric_name = metric.upper()
                            story.append(
                                Paragraph(f"• {metric_name}: {value}", normal_style))
                        story.append(Spacer(1, 0.1*inch))

                    # Análisis forense
                    forensic = video.get('forensic_analysis', {})
                    if forensic:
                        story.append(
                            Paragraph("<b>Análisis Forense:</b>", normal_style))
                        for key, value in forensic.items():
                            label = key.replace('_', ' ').title()
                            story.append(
                                Paragraph(f"• <b>{label}:</b> {value}", normal_style))
                        story.append(Spacer(1, 0.1*inch))

                    # Scores cualitativos
                    scores = video.get('scores_qualitative', {})
                    if scores:
                        story.append(
                            Paragraph("<b>Puntuaciones:</b>", normal_style))
                        score_data = [['Métrica', 'Score']]
                        for metric, score in scores.items():
                            metric_name = metric.replace('_', ' ').title()
                            score_data.append([metric_name, str(score)])

                        score_table = Table(
                            score_data, colWidths=[3*inch, 1*inch])
                        score_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        story.append(score_table)
                        story.append(Spacer(1, 0.1*inch))

                    # Justificación
                    justification = video.get('justification', '')
                    if justification:
                        story.append(
                            Paragraph(f"<b>Justificación:</b> {justification}", normal_style))
                        story.append(Spacer(1, 0.1*inch))

                    # Recomendaciones
                    recommendations = video.get('recommendations', '')
                    if recommendations:
                        story.append(
                            Paragraph(f"<b>Recomendaciones:</b> {recommendations}", normal_style))

                    story.append(Spacer(1, 0.3*inch))

            elif ads:
                # Estructura antigua: análisis detallado por anuncio
                story.append(
                    Paragraph("ANÁLISIS DETALLADO POR ANUNCIO", heading_style))

            for i, ad in enumerate(ads, 1):
                # Título del anuncio
                ad_title = (
                    ad.get('ad_title') or
                    ad.get('image') or
                    ad.get('ad_id') or
                    f'Anuncio {i}'
                )
                story.append(Paragraph(f"{i}. {ad_title}", subheading_style))

                # Extraer scores de la nueva estructura
                scores = {}

                # Nueva estructura: cada métrica es un objeto con score, analysis, etc
                if 'visual_composition' in ad and isinstance(ad['visual_composition'], dict):
                    scores['Composición Visual'] = ad['visual_composition'].get(
                        'score', 'N/A')
                if 'message_copywriting' in ad and isinstance(ad['message_copywriting'], dict):
                    scores['Mensaje y Copywriting'] = ad['message_copywriting'].get(
                        'score', 'N/A')
                if 'target_psychology' in ad and isinstance(ad['target_psychology'], dict):
                    scores['Target y Psicología'] = ad['target_psychology'].get(
                        'score', 'N/A')
                if 'mobile_optimization' in ad and isinstance(ad['mobile_optimization'], dict):
                    scores['Optimización Mobile'] = ad['mobile_optimization'].get(
                        'score', 'N/A')
                if 'conversion_potential' in ad and isinstance(ad['conversion_potential'], dict):
                    scores['Potencial de Conversión'] = ad['conversion_potential'].get(
                        'score', 'N/A')

                # Estructura antigua (fallback)
                if not scores:
                    old_scores = ad.get('scores', {})
                    metric_names = {
                        'composicion_visual': 'Composición Visual',
                        'mensaje_y_copywriting': 'Mensaje y Copywriting',
                        'target_y_psicologia': 'Target y Psicología',
                        'optimizacion_mobile': 'Optimización Mobile',
                        'potencial_de_conversion': 'Potencial de Conversión',
                        'visual_composition': 'Composición Visual',
                        'message_copywriting': 'Mensaje y Copywriting',
                        'target_psychology': 'Target y Psicología',
                        'mobile_optimization': 'Optimización Mobile',
                        'conversion_potential': 'Potencial de Conversión'
                    }
                    for key, value in old_scores.items():
                        metric_name = metric_names.get(
                            key, key.replace('_', ' ').title())
                        if isinstance(value, dict):
                            scores[metric_name] = value.get('score', 'N/A')
                        else:
                            scores[metric_name] = value

                # Tabla de scores
                if scores:
                    score_data = [['Métrica', 'Puntuación']]

                    metric_names = {
                        'composicion_visual': 'Composición Visual',
                        'mensaje_y_copywriting': 'Mensaje y Copywriting',
                        'target_y_psicologia': 'Target y Psicología',
                        'optimizacion_mobile': 'Optimización Mobile',
                        'potencial_de_conversion': 'Potencial de Conversión',
                        'visual_composition': 'Composición Visual',
                        'message_copywriting': 'Mensaje y Copywriting',
                        'target_psychology': 'Target y Psicología',
                        'mobile_optimization': 'Optimización Mobile',
                        'conversion_potential': 'Potencial de Conversión'
                    }

                    for key, value in scores.items():
                        metric_name = metric_names.get(
                            key, key.replace('_', ' ').title())

                        # Extraer score si es dict
                        if isinstance(value, dict):
                            score = value.get('score', 'N/A')
                        else:
                            score = value

                        score_data.append([metric_name, str(score)])

                    score_table = Table(score_data, colWidths=[10*cm, 3*cm])
                    score_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0),
                         colors.HexColor('#3949ab')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                         [colors.white, colors.HexColor('#f5f5f5')]),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ]))

                    story.append(score_table)
                    story.append(Spacer(1, 0.1*inch))

                # Análisis textual
                analysis_text = ad.get('analysis', ad.get('justification', ''))
                if analysis_text:
                    story.append(
                        Paragraph(f"<b>Análisis:</b> {analysis_text}", normal_style))

                # Recomendaciones
                recommendations = ad.get('recommendations', '')
                if recommendations:
                    story.append(
                        Paragraph(f"<b>Recomendaciones:</b> {recommendations}", normal_style))

                story.append(Spacer(1, 0.2*inch))

                # Page break cada 3 anuncios
                if i % 3 == 0 and i < len(ads):
                    story.append(PageBreak())

            # ===== RECOMENDACIONES GENERALES =====
            general_recs = parsed_analysis.get('general_recommendations', [])
            if general_recs:
                story.append(PageBreak())
                story.append(
                    Paragraph("RECOMENDACIONES GENERALES", heading_style))

                for i, rec in enumerate(general_recs, 1):
                    story.append(
                        Paragraph(f"{i}. {rec}", normal_style))
                    story.append(Spacer(1, 0.1*inch))

            # ===== TOP PERFORMERS =====
            top_performers = parsed_analysis.get('top_performers', {})
            if top_performers and top_performers.get('ads'):
                story.append(PageBreak())
                story.append(Paragraph("TOP 3 ANUNCIOS", heading_style))

                story.append(Paragraph(
                    f"<b>IDs:</b> {', '.join(top_performers.get('ads', []))}",
                    normal_style
                ))
                story.append(Spacer(1, 0.1*inch))

                if top_performers.get('why_they_work'):
                    story.append(Paragraph(
                        f"<b>Por qué funcionan:</b> {top_performers['why_they_work']}",
                        normal_style
                    ))
                    story.append(Spacer(1, 0.1*inch))

                if top_performers.get('common_patterns'):
                    story.append(
                        Paragraph("<b>Patrones comunes:</b>", normal_style))
                    for pattern in top_performers['common_patterns']:
                        story.append(Paragraph(f"• {pattern}", normal_style))
                    story.append(Spacer(1, 0.2*inch))

            # ===== BOTTOM PERFORMERS =====
            bottom_performers = parsed_analysis.get('bottom_performers', {})
            if bottom_performers and bottom_performers.get('ads'):
                story.append(
                    Paragraph("ANUNCIOS CON OPORTUNIDAD DE MEJORA", heading_style))

                story.append(Paragraph(
                    f"<b>IDs:</b> {', '.join(bottom_performers.get('ads', []))}",
                    normal_style
                ))
                story.append(Spacer(1, 0.1*inch))

                if bottom_performers.get('why_they_fail'):
                    story.append(Paragraph(
                        f"<b>Áreas de mejora:</b> {bottom_performers['why_they_fail']}",
                        normal_style
                    ))
                    story.append(Spacer(1, 0.1*inch))

                if bottom_performers.get('common_issues'):
                    story.append(
                        Paragraph("<b>Problemas comunes:</b>", normal_style))
                    for issue in bottom_performers['common_issues']:
                        story.append(Paragraph(f"• {issue}", normal_style))
                    story.append(Spacer(1, 0.2*inch))

            # ===== RECOMENDACIONES ESTRATÉGICAS =====
            strategic_recs = parsed_analysis.get(
                'strategic_recommendations', {})
            if strategic_recs or 'recommendations' in parsed_analysis:
                story.append(PageBreak())
                story.append(
                    Paragraph("RECOMENDACIONES ESTRATÉGICAS", heading_style))

                # Nueva estructura
                if strategic_recs:
                    for section in ['visual_strategy', 'copy_strategy', 'targeting_strategy']:
                        if section in strategic_recs and strategic_recs[section]:
                            section_title = section.replace('_', ' ').title()
                            story.append(
                                Paragraph(f"<b>{section_title}:</b>", subheading_style))
                            for rec in strategic_recs[section]:
                                story.append(
                                    Paragraph(f"• {rec}", normal_style))
                            story.append(Spacer(1, 0.15*inch))

                    if 'budget_allocation' in strategic_recs:
                        story.append(
                            Paragraph("<b>Asignación de Presupuesto:</b>", subheading_style))
                        story.append(
                            Paragraph(strategic_recs['budget_allocation'], normal_style))
                        story.append(Spacer(1, 0.15*inch))

                    if 'next_steps' in strategic_recs:
                        story.append(
                            Paragraph("<b>Próximos Pasos:</b>", subheading_style))
                        for step in strategic_recs['next_steps']:
                            story.append(Paragraph(f"• {step}", normal_style))

                # Estructura antigua (fallback)
                elif 'recommendations' in parsed_analysis:
                    recs = parsed_analysis['recommendations']
                    if isinstance(recs, dict):
                        for key, value in recs.items():
                            rec_title = key.replace('_', ' ').title()
                            story.append(
                                Paragraph(f"<b>{rec_title}:</b> {value}", normal_style))
                            story.append(Spacer(1, 0.1*inch))
                    else:
                        story.append(Paragraph(str(recs), normal_style))

            # ===== CAMPAIGN INSIGHTS =====
            campaign_insights = parsed_analysis.get('campaign_insights', {})
            if campaign_insights:
                story.append(PageBreak())
                story.append(Paragraph("INSIGHTS DE CAMPAÑA", heading_style))

                if 'total_ads_analyzed' in campaign_insights:
                    story.append(Paragraph(
                        f"<b>Total de anuncios analizados:</b> {campaign_insights['total_ads_analyzed']}",
                        normal_style
                    ))
                    story.append(Spacer(1, 0.1*inch))

                avg_scores = campaign_insights.get('average_scores', {})
                if avg_scores:
                    story.append(
                        Paragraph("<b>Scores Promedio:</b>", subheading_style))
                    for metric, score in avg_scores.items():
                        metric_name = metric.replace('_', ' ').title()
                        story.append(
                            Paragraph(f"• {metric_name}: {score}", normal_style))
                    story.append(Spacer(1, 0.15*inch))

                if campaign_insights.get('key_findings'):
                    story.append(
                        Paragraph("<b>Hallazgos Clave:</b>", subheading_style))
                    for finding in campaign_insights['key_findings']:
                        story.append(Paragraph(f"• {finding}", normal_style))
                    story.append(Spacer(1, 0.15*inch))

                if campaign_insights.get('opportunities'):
                    story.append(
                        Paragraph("<b>Oportunidades:</b>", subheading_style))
                    for opp in campaign_insights['opportunities']:
                        story.append(Paragraph(f"• {opp}", normal_style))
                    story.append(Spacer(1, 0.15*inch))

                if campaign_insights.get('risks'):
                    story.append(
                        Paragraph("<b>Riesgos:</b>", subheading_style))
                    for risk in campaign_insights['risks']:
                        story.append(Paragraph(f"• {risk}", normal_style))

        # ===== PIE DE PÁGINA =====
        def add_page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 9)
            page_num = canvas.getPageNumber()
            text = f"Página {page_num}"
            canvas.drawRightString(A4[0] - 2*cm, 1.5*cm, text)
            canvas.drawString(2*cm, 1.5*cm, f"Run ID: {run_id}")
            canvas.restoreState()

        # Construir PDF
        doc.build(story, onFirstPage=add_page_number,
                  onLaterPages=add_page_number)

        return {
            'success': True,
            'pdf_path': str(output_path),
            'error': None
        }

    except Exception as e:
        return {
            'success': False,
            'pdf_path': None,
            'error': f"Error al generar PDF: {str(e)}"
        }
