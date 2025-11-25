import logging
from typing import Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, 
    TableStyle, KeepTogether, PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from datetime import datetime

# --- CONFIGURACIÓN DE PALETA DE COLORES PROFESIONAL ---
THEME_COLORS = {
    'primary': colors.HexColor('#1e3a8a'),
    'primary_light': colors.HexColor('#3b82f6'),
    'text_dark': colors.HexColor('#1e293b'),
    'text_body': colors.HexColor('#334155'),
    'text_light': colors.HexColor('#64748b'),
    'accent_success': colors.HexColor('#059669'),
    'bg_success': colors.HexColor('#ecfdf5'),
    'accent_warning': colors.HexColor('#d97706'),
    'bg_warning': colors.HexColor('#fef3c7'),
    'accent_danger': colors.HexColor('#b91c1c'),
    'bg_danger': colors.HexColor('#fef2f2'),
    'accent_info': colors.HexColor('#0891b2'),
    'bg_info': colors.HexColor('#cffafe'),
    'divider': colors.HexColor('#e2e8f0'),
    'white': colors.HexColor('#ffffff'),
    'bg_light': colors.HexColor('#f8fafc'),
}

class EnhancedPDFGenerator:
    """
    Generador de reportes PDF mejorado con gráficos, visualizaciones y diseño premium.
    """

    def __init__(self, output_path: str, data: Dict[str, Any]):
        self.output_path = output_path
        self.data = data
        self.styles = getSampleStyleSheet()
        
        # Configuración de color de marca
        if 'design_system_recommendation' in data:
            custom_hex = data['design_system_recommendation'].get('primary_hex_color')
            try:
                self.brand_color = colors.HexColor(custom_hex) if custom_hex else THEME_COLORS['primary']
            except:
                self.brand_color = THEME_COLORS['primary']
        else:
            self.brand_color = THEME_COLORS['primary']
        
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Define estilos tipográficos mejorados."""
        
        # Título del Documento
        self.styles.add(ParagraphStyle(
            name='DocTitle',
            fontName='Helvetica-Bold',
            fontSize=28,
            leading=34,
            textColor=THEME_COLORS['white'],
            alignment=TA_CENTER,
            spaceAfter=6
        ))
        
        # Subtítulo del Header
        self.styles.add(ParagraphStyle(
            name='DocSubtitle',
            fontName='Helvetica',
            fontSize=11,
            textColor=colors.Color(1, 1, 1, 0.9),
            alignment=TA_CENTER
        ))

        # Encabezados de Sección
        self.styles.add(ParagraphStyle(
            name='SectionHead',
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=self.brand_color,
            spaceBefore=24,
            spaceAfter=14,
            borderPadding=(0, 0, 6, 0)
        ))

        # Sub-encabezados
        self.styles.add(ParagraphStyle(
            name='SubHead',
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=THEME_COLORS['text_dark'],
            spaceBefore=12,
            spaceAfter=8
        ))

        # Cuerpo de texto
        self.styles.add(ParagraphStyle(
            name='DeepBody',
            fontName='Helvetica',
            fontSize=10,
            leading=16,
            textColor=THEME_COLORS['text_body'],
            alignment=TA_JUSTIFY,
            spaceAfter=10
        ))

        # Texto destacado
        self.styles.add(ParagraphStyle(
            name='Highlight',
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=self.brand_color,
            spaceAfter=8
        ))

        # Etiquetas
        self.styles.add(ParagraphStyle(
            name='LabelText',
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=THEME_COLORS['text_light'],
            alignment=TA_CENTER
        ))

        # Lista con bullets
        self.styles.add(ParagraphStyle(
            name='BulletList',
            fontName='Helvetica',
            fontSize=10,
            leading=15,
            textColor=THEME_COLORS['text_body'],
            leftIndent=20,
            spaceAfter=6
        ))

    def _create_progress_bar(self, value, max_value=10, width=3*inch, height=0.3*inch):
        """Crea una barra de progreso visual."""
        drawing = Drawing(width, height)
        
        # Fondo de la barra
        drawing.add(Rect(0, 0, width, height, 
                        fillColor=THEME_COLORS['bg_light'],
                        strokeColor=THEME_COLORS['divider'],
                        strokeWidth=1))
        
        # Barra de progreso
        progress_width = (value / max_value) * width
        if value >= 7:
            bar_color = THEME_COLORS['accent_success']
        elif value >= 5:
            bar_color = THEME_COLORS['accent_warning']
        else:
            bar_color = THEME_COLORS['accent_danger']
            
        drawing.add(Rect(0, 0, progress_width, height,
                        fillColor=bar_color,
                        strokeColor=None))
        
        return drawing

    def _create_metric_card(self, label, value, icon="●"):
        """Crea una tarjeta de métrica con icono."""
        card_html = f"""
        <para align="center" spaceBefore=10 spaceAfter=10>
            <font name="Helvetica-Bold" size=20 color="{self.brand_color.hexval()}">{icon}</font><br/>
            <font name="Helvetica" size=9 color="#64748b">{label.upper()}</font><br/>
            <font name="Helvetica-Bold" size=16 color="#1e293b">{value}</font>
        </para>
        """
        return Paragraph(card_html, self.styles['Normal'])

    def _create_card(self, content_elements, border_color=None, bg_color=THEME_COLORS['white'], title=None):
        """Crea un contenedor visual mejorado."""
        elements = []
        
        # Agregar título si existe
        if title:
            title_para = Paragraph(f'<b>{title}</b>', self.styles['SubHead'])
            elements.append([title_para])
        
        # Agregar contenido
        for el in content_elements:
            elements.append([el])
        
        t = Table(elements, colWidths=[6.5*inch])
        
        style_cmds = [
            ('BACKGROUND', (0,0), (-1,-1), bg_color),
            ('BOX', (0,0), (-1,-1), 1, THEME_COLORS['divider']),
            ('LEFTPADDING', (0,0), (-1,-1), 20),
            ('RIGHTPADDING', (0,0), (-1,-1), 20),
            ('TOPPADDING', (0,0), (-1,-1), 16),
            ('BOTTOMPADDING', (0,0), (-1,-1), 16),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]
        
        # Línea lateral de acento
        if border_color:
            style_cmds.append(('LINEBEFORE', (0,0), (0,-1), 5, border_color))
            
        t.setStyle(TableStyle(style_cmds))
        return t

    def _create_comparison_table(self, data_rows, headers):
        """Crea una tabla comparativa profesional."""
        table_data = [headers] + data_rows
        
        col_widths = [6.5*inch / len(headers)] * len(headers)
        t = Table(table_data, colWidths=col_widths)
        
        t.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0,0), (-1,0), self.brand_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            
            # Body
            ('BACKGROUND', (0,1), (-1,-1), THEME_COLORS['white']),
            ('TEXTCOLOR', (0,1), (-1,-1), THEME_COLORS['text_body']),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('ALIGN', (0,1), (-1,-1), 'LEFT'),
            ('TOPPADDING', (0,1), (-1,-1), 10),
            ('BOTTOMPADDING', (0,1), (-1,-1), 10),
            ('LEFTPADDING', (0,1), (-1,-1), 12),
            
            # Grid
            ('GRID', (0,0), (-1,-1), 0.5, THEME_COLORS['divider']),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [THEME_COLORS['white'], THEME_COLORS['bg_light']]),
        ]))
        
        return t

    def _add_footer(self, canvas, doc):
        """Agrega footer con número de página."""
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(THEME_COLORS['text_light'])
        
        page_num = canvas.getPageNumber()
        text = f"Página {page_num}"
        canvas.drawRightString(A4[0] - 0.75*inch, 0.5*inch, text)
        
        # Línea decorativa
        canvas.setStrokeColor(THEME_COLORS['divider'])
        canvas.setLineWidth(0.5)
        canvas.line(0.75*inch, 0.65*inch, A4[0] - 0.75*inch, 0.65*inch)
        
        canvas.restoreState()

    def render(self):
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.6*inch, bottomMargin=0.75*inch
        )
        story = []

        # --- 1. PORTADA MEJORADA ---
        meta = self.data.get('meta_info', {})
        title_text = meta.get('report_title', 'INFORME DE RENDIMIENTO')
        date_text = meta.get('generated_date', datetime.now().strftime('%Y-%m-%d'))
        tone_text = meta.get('brand_tone_detected', 'N/A')

        header_elements = [
            Paragraph(title_text.upper(), self.styles['DocTitle']),
            Spacer(1, 8),
            Paragraph(f"FECHA: {date_text}  |  TONO DETECTADO: {tone_text}", self.styles['DocSubtitle']),
            Spacer(1, 4),
            Paragraph("Análisis Profesional de Campaña Publicitaria", self.styles['DocSubtitle'])
        ]
        
        header_table = Table([[header_elements]], colWidths=[7.5*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), self.brand_color),
            ('TOPPADDING', (0,0), (-1,-1), 40),
            ('BOTTOMPADDING', (0,0), (-1,-1), 40),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.4*inch))

        # --- 2. RESUMEN EJECUTIVO MEJORADO ---
        story.append(Paragraph("📊 Resumen Ejecutivo & Diagnóstico", self.styles['SectionHead']))
        
        exec_sum = self.data.get('executive_summary', {})
        score = float(exec_sum.get('investment_efficiency_score', 0))
        overview = exec_sum.get('overview', '')

        # Score visual mejorado
        if score >= 7:
            score_color = THEME_COLORS['accent_success']
            score_bg = THEME_COLORS['bg_success']
            score_label = "EXCELENTE"
        elif score >= 5:
            score_color = THEME_COLORS['accent_warning']
            score_bg = THEME_COLORS['bg_warning']
            score_label = "BUENO"
        else:
            score_color = THEME_COLORS['accent_danger']
            score_bg = THEME_COLORS['bg_danger']
            score_label = "NECESITA MEJORA"

        # Layout mejorado con 3 columnas
        score_html = f"""
        <para align="center" spaceBefore=15 spaceAfter=15>
            <font name="Helvetica" size=10 color="#64748b">PUNTUACIÓN GLOBAL</font><br/>
            <font name="Helvetica-Bold" size=36 color="{score_color.hexval()}">{score}</font>
            <font name="Helvetica-Bold" size=18 color="{score_color.hexval()}">/10</font><br/>
            <font name="Helvetica-Bold" size=11 color="{score_color.hexval()}">{score_label}</font>
        </para>
        """
        
        left_col = [Paragraph(overview, self.styles['DeepBody'])]
        right_col = [
            Paragraph(score_html, self.styles['Normal']),
            Spacer(1, 10),
            self._create_progress_bar(score, 10, 2.5*inch, 0.25*inch)
        ]

        summary_table = Table([[left_col, right_col]], colWidths=[4.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (1,0), (1,0), score_bg),
            ('BOX', (1,0), (1,0), 1, score_color),
            ('LEFTPADDING', (0,0), (-1,-1), 15),
            ('RIGHTPADDING', (0,0), (-1,-1), 15),
            ('TOPPADDING', (0,0), (-1,-1), 20),
            ('BOTTOMPADDING', (0,0), (-1,-1), 20),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))

        # --- 3. MÉTRICAS CLAVE CON ICONOS ---
        stats = self.data.get('campaign_stats_highlight', {})
        if stats:
            story.append(Paragraph("📈 Indicadores Clave de Rendimiento (KPIs)", self.styles['SectionHead']))
            
            # Crear tarjetas de métricas
            metric_cards = []
            icons = ["📊", "🎯", "💰", "👥"]
            idx = 0
            
            for k, v in stats.items():
                label = k.replace('_', ' ').title()
                icon = icons[idx % len(icons)]
                metric_cards.append(self._create_metric_card(label, v, icon))
                idx += 1
            
            # Distribuir en filas de 3
            rows = []
            for i in range(0, len(metric_cards), 3):
                row = metric_cards[i:i+3]
                # Rellenar con celdas vacías si es necesario
                while len(row) < 3:
                    row.append(Paragraph("", self.styles['Normal']))
                rows.append(row)
            
            col_w = 7*inch / 3
            metrics_table = Table(rows, colWidths=[col_w]*3)
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), THEME_COLORS['bg_light']),
                ('BOX', (0,0), (-1,-1), 1, THEME_COLORS['divider']),
                ('INNERGRID', (0,0), (-1,-1), 0.5, THEME_COLORS['divider']),
                ('TOPPADDING', (0,0), (-1,-1), 20),
                ('BOTTOMPADDING', (0,0), (-1,-1), 20),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(metrics_table)
            story.append(Spacer(1, 0.3*inch))

        # --- 4. TOP PERFORMERS MEJORADO ---
        tops = self.data.get('top_performers', [])
        if tops:
            story.append(Paragraph("🏆 Mejores Resultados - Análisis Forense", self.styles['SectionHead']))
            
            story.append(Paragraph(
                "Los siguientes anuncios han demostrado un rendimiento excepcional basado en métricas clave como CTR, ROAS y engagement. "
                "A continuación se presenta un análisis detallado de los factores de éxito:",
                self.styles['DeepBody']
            ))
            story.append(Spacer(1, 0.15*inch))
            
            for idx, item in enumerate(tops, 1):
                ad_id = item.get('ad_id', 'N/A')
                content = item.get('analysis_content', '')
                
                # Título con número
                title_html = f'<font color="{THEME_COLORS["accent_success"].hexval()}">★</font> ANUNCIO #{idx}: {ad_id}'
                
                card_elements = [
                    Paragraph(title_html, self.styles['Highlight']),
                    Spacer(1, 8),
                    Paragraph("<b>Análisis de Rendimiento:</b>", self.styles['SubHead']),
                    Paragraph(content, self.styles['DeepBody']),
                    Spacer(1, 8),
                    Paragraph("<b>Factores Clave de Éxito:</b>", self.styles['SubHead']),
                    Paragraph("• Composición visual optimizada para captar atención", self.styles['BulletList']),
                    Paragraph("• Mensaje claro y directo al público objetivo", self.styles['BulletList']),
                    Paragraph("• Coherencia entre imagen y texto", self.styles['BulletList']),
                ]
                
                t_card = self._create_card(card_elements, border_color=THEME_COLORS['accent_success'])
                story.append(KeepTogether(t_card))
                story.append(Spacer(1, 0.2*inch))

        # --- 5. BOTTOM PERFORMERS MEJORADO ---
        bottoms = self.data.get('bottom_performers', [])
        if bottoms:
            story.append(Paragraph("⚠️ Áreas de Optimización Crítica", self.styles['SectionHead']))
            
            story.append(Paragraph(
                "Los siguientes anuncios requieren atención inmediata. Se han identificado problemas específicos "
                "que están afectando negativamente el rendimiento de la campaña:",
                self.styles['DeepBody']
            ))
            story.append(Spacer(1, 0.15*inch))
            
            for idx, item in enumerate(bottoms, 1):
                ad_id = item.get('ad_id', 'N/A')
                content = item.get('analysis_content', '')
                
                title_html = f'<font color="{THEME_COLORS["accent_danger"].hexval()}">⚡</font> ANUNCIO #{idx}: {ad_id}'
                
                card_elements = [
                    Paragraph(title_html, self.styles['Highlight']),
                    Spacer(1, 8),
                    Paragraph("<b>Diagnóstico del Problema:</b>", self.styles['SubHead']),
                    Paragraph(content, self.styles['DeepBody']),
                    Spacer(1, 8),
                    Paragraph("<b>Recomendaciones de Mejora:</b>", self.styles['SubHead']),
                    Paragraph("• Simplificar el diseño visual para mejorar la legibilidad", self.styles['BulletList']),
                    Paragraph("• Alinear el mensaje con la imagen presentada", self.styles['BulletList']),
                    Paragraph("• Mejorar el contraste y la jerarquía visual", self.styles['BulletList']),
                    Paragraph("• Realizar pruebas A/B con variaciones del diseño", self.styles['BulletList']),
                ]
                
                t_card = self._create_card(card_elements, border_color=THEME_COLORS['accent_danger'])
                story.append(KeepTogether(t_card))
                story.append(Spacer(1, 0.2*inch))

        # --- 6. PROFUNDIZACIÓN ESTRATÉGICA EXPANDIDA ---
        strat = self.data.get('strategic_deep_dive', {})
        if strat:
            story.append(PageBreak())
            story.append(Paragraph("🎯 Profundización Estratégica y Contexto Teórico", self.styles['SectionHead']))
            
            story.append(Paragraph(
                "Esta sección proporciona un análisis profundo de los aspectos estratégicos de la campaña, "
                "incluyendo recomendaciones basadas en teoría de marketing, psicología del consumidor y mejores prácticas de la industria.",
                self.styles['DeepBody']
            ))
            story.append(Spacer(1, 0.2*inch))
            
            strategy_icons = {
                'visual_strategy': '🎨',
                'copywriting_audit': '✍️',
                'audience_resonance': '👥',
                'competitive_analysis': '📊',
                'market_positioning': '🎯'
            }
            
            for key, text in strat.items():
                title = key.replace('_', ' ').title()
                icon = strategy_icons.get(key, '•')
                
                card_elements = [
                    Paragraph(f"{icon} <b>{title}</b>", self.styles['SubHead']),
                    Spacer(1, 6),
                    Paragraph(text, self.styles['DeepBody']),
                ]
                
                t_card = self._create_card(card_elements, bg_color=THEME_COLORS['bg_info'])
                story.append(t_card)
                story.append(Spacer(1, 0.15*inch))

        # --- 7. HOJA DE RUTA ACCIONABLE MEJORADA ---
        roadmap = self.data.get('actionable_roadmap', [])
        if roadmap:
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("🗺️ Hoja de Ruta Accionable - Plan de Implementación", self.styles['SectionHead']))
            
            story.append(Paragraph(
                "Plan de acción paso a paso para implementar las mejoras recomendadas. "
                "Cada acción incluye prioridad y impacto esperado:",
                self.styles['DeepBody']
            ))
            story.append(Spacer(1, 0.15*inch))
            
            # Crear tabla de roadmap mejorada
            roadmap_data = [['#', 'Acción', 'Prioridad', 'Impacto']]
            
            priorities = ['ALTA', 'ALTA', 'MEDIA']
            impacts = ['Alto', 'Medio', 'Alto']
            
            for idx, step in enumerate(roadmap, 1):
                priority = priorities[idx-1] if idx-1 < len(priorities) else 'MEDIA'
                impact = impacts[idx-1] if idx-1 < len(impacts) else 'Medio'
                
                priority_color = THEME_COLORS['accent_danger'] if priority == 'ALTA' else THEME_COLORS['accent_warning']
                
                num_para = Paragraph(f'<b>{idx}</b>', self.styles['Normal'])
                action_para = Paragraph(step, self.styles['DeepBody'])
                priority_para = Paragraph(f'<font color="{priority_color.hexval()}"><b>{priority}</b></font>', self.styles['Normal'])
                impact_para = Paragraph(impact, self.styles['Normal'])
                
                roadmap_data.append([num_para, action_para, priority_para, impact_para])
            
            roadmap_table = Table(roadmap_data, colWidths=[0.4*inch, 4.5*inch, 0.9*inch, 0.7*inch])
            roadmap_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0,0), (-1,0), self.brand_color),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('ALIGN', (0,0), (-1,0), 'CENTER'),
                
                # Body
                ('BACKGROUND', (0,1), (-1,-1), THEME_COLORS['white']),
                ('TEXTCOLOR', (0,1), (-1,-1), THEME_COLORS['text_body']),
                ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,1), (-1,-1), 9),
                ('ALIGN', (0,1), (0,-1), 'CENTER'),
                ('ALIGN', (1,1), (1,-1), 'LEFT'),
                ('ALIGN', (2,1), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                
                # Padding
                ('TOPPADDING', (0,0), (-1,-1), 12),
                ('BOTTOMPADDING', (0,0), (-1,-1), 12),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
                
                # Grid
                ('GRID', (0,0), (-1,-1), 0.5, THEME_COLORS['divider']),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [THEME_COLORS['white'], THEME_COLORS['bg_light']]),
            ]))
            story.append(roadmap_table)

        # --- 8. CONCLUSIONES Y PRÓXIMOS PASOS ---
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("💡 Conclusiones y Próximos Pasos", self.styles['SectionHead']))
        
        conclusion_text = f"""
        Basado en el análisis exhaustivo de la campaña, se ha identificado una puntuación de eficiencia de <b>{score}/10</b>. 
        Los anuncios de mejor rendimiento demuestran la importancia de la coherencia visual y mensajes claros. 
        Las áreas de mejora identificadas requieren atención inmediata para optimizar el ROI de la campaña.
        <br/><br/>
        <b>Recomendaciones Clave:</b><br/>
        • Implementar las acciones de la hoja de ruta en orden de prioridad<br/>
        • Realizar pruebas A/B continuas para validar mejoras<br/>
        • Monitorear métricas semanalmente y ajustar estrategia según resultados<br/>
        • Mantener la coherencia de marca en todos los creativos<br/>
        <br/>
        <b>Próxima Revisión:</b> Se recomienda realizar un seguimiento en 2-3 semanas para evaluar el impacto de las optimizaciones implementadas.
        """
        
        conclusion_card = self._create_card(
            [Paragraph(conclusion_text, self.styles['DeepBody'])],
            bg_color=THEME_COLORS['bg_light']
        )
        story.append(conclusion_card)

        # Construir PDF con footer
        try:
            doc.build(story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)
            print(f"✅ Reporte Profesional Mejorado generado: {self.output_path}")
            return self.output_path
        except Exception as e:
            print(f"❌ Error generando PDF: {e}")
            import traceback
            traceback.print_exc()
            raise
