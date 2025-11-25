"""
Google Gemini AI Service
Servicio para interactuar con la API de Google Gemini
"""

import os
import json
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from typing import Optional, Dict, Any, List


class GeminiService:
    """Servicio para interactuar con Google Gemini AI"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el servicio de Gemini

        Args:
            api_key: API key de Google Gemini (si no se proporciona, 
                     se obtiene de GOOGLE_GEMINI_API)
        """
        self.api_key = api_key or os.getenv('GOOGLE_GEMINI_API')

        if not self.api_key:
            raise ValueError(
                "GOOGLE_GEMINI_API not found in environment variables"
            )

        # Configurar la API
        genai.configure(api_key=self.api_key)

        # Modelo por defecto
        self.default_model = "gemini-1.5-flash"

    def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con Gemini enviando un prompt simple

        Returns:
            Dict con status, mensaje de respuesta y metadata
        """
        try:
            model = genai.GenerativeModel(self.default_model)

            # Prompt de prueba simple
            test_prompt = "Di 'Hola' en una palabra"

            response = model.generate_content(test_prompt)

            return {
                'status': 'success',
                'connected': True,
                'model': self.default_model,
                'test_prompt': test_prompt,
                'response': response.text,
                'metadata': {
                    'candidates': len(response.candidates) if hasattr(
                        response, 'candidates'
                    ) else 0,
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'connected': False,
                'model': self.default_model,
                'error': str(e),
                'error_type': type(e).__name__
            }

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Genera texto usando Gemini

        Args:
            prompt: El prompt para generar texto
            model: Modelo a usar (por defecto: gemini-1.5-flash)
            temperature: Temperatura de generación (0-2)
            max_tokens: Máximo de tokens a generar

        Returns:
            Dict con la respuesta generada
        """
        try:
            model_name = model or self.default_model
            gemini_model = genai.GenerativeModel(model_name)

            # Configuración de generación
            generation_config = {
                'temperature': temperature,
            }
            if max_tokens:
                generation_config['max_output_tokens'] = max_tokens

            response = gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )

            return {
                'status': 'success',
                'model': model_name,
                'prompt': prompt,
                'response': response.text,
                'usage': {
                    'prompt_tokens': response.usage_metadata.prompt_token_count
                    if hasattr(response, 'usage_metadata') else None,
                    'completion_tokens': (
                        response.usage_metadata.candidates_token_count
                        if hasattr(response, 'usage_metadata') else None
                    ),
                    'total_tokens': response.usage_metadata.total_token_count
                    if hasattr(response, 'usage_metadata') else None,
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'model': model or self.default_model,
                'prompt': prompt,
                'error': str(e),
                'error_type': type(e).__name__
            }

    def list_models(self) -> List[str]:
        """
        Lista los modelos disponibles de Gemini

        Returns:
            Lista de nombres de modelos
        """
        try:
            models = []
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    models.append(model.name)
            return models
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    def analyze_ad(
        self,
        ad_text: str,
        ad_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analiza un anuncio usando Gemini

        Args:
            ad_text: Texto del anuncio
            ad_metadata: Metadata adicional del anuncio

        Returns:
            Análisis del anuncio
        """
        metadata_str = ""
        if ad_metadata:
            metadata_str = f"\n\nMetadata: {ad_metadata}"

        prompt = f"""Analiza el siguiente anuncio publicitario:

Texto del anuncio:
{ad_text}
{metadata_str}

Proporciona:
1. Sentimiento general (positivo/negativo/neutral)
2. Público objetivo probable
3. Principales mensajes/llamados a la acción
4. Puntos fuertes
5. Áreas de mejora

Responde en formato JSON."""

        return self.generate_text(prompt, temperature=0.3)

    def analyze_ad_campaign_from_manifest(
        self,
        manifest_data: Dict[str, Any],
        run_id: str
    ) -> Dict[str, Any]:
        """
        Analiza una campaña completa de anuncios desde un manifest JSON con URLs públicas.

        Actúa como un experto en marketing digital analizando cada anuncio en términos de:
        - Composición visual y uso de colores
        - Elementos destacados y objetos
        - Duración del video (si aplica)
        - Fuentes y tipografía
        - Música y audio (si aplica)
        - Engagement estimado
        - Efectividad del mensaje

        Args:
            manifest_data: Dict con estructura {"run_id": str, "ads": [{"ad_id": str, "files": [{"url": str, "type": str}]}]}
            run_id: ID del run para identificar el reporte

        Returns:
            Dict con análisis completo y path al archivo JSON guardado
        """

        # Preparar prompt como experto en marketing
        prompt = f"""
Eres un EXPERTO EN MARKETING DIGITAL y ANÁLISIS DE CAMPAÑAS PUBLICITARIAS con más de 15 años de experiencia.
Tu tarea es analizar una campaña de anuncios y determinar cuál fue el más efectivo y por qué.

CAMPAÑA ID: {run_id}
TOTAL DE ANUNCIOS: {len(manifest_data.get('ads', []))}

ANUNCIOS A ANALIZAR:
"""

        # Agregar información de cada anuncio
        for idx, ad in enumerate(manifest_data.get('ads', []), 1):
            ad_id = ad.get('ad_id', 'N/A')
            files = ad.get('files', [])

            prompt += f"\n--- ANUNCIO #{idx} (ID: {ad_id}) ---\n"
            prompt += f"Archivos multimedia: {len(files)}\n"

            for file_info in files:
                file_url = file_info.get('url', 'N/A')
                file_type = file_info.get('type', 'unknown')
                prompt += f"  - Tipo: {file_type}\n"
                prompt += f"    URL: {file_url}\n"

        # Instrucciones de análisis detallado
        prompt += """

ANALIZA CADA ANUNCIO CONSIDERANDO:

1. COMPOSICIÓN VISUAL:
   - Paleta de colores utilizada (cálidos, fríos, contrastes)
   - Balance y distribución de elementos
   - Jerarquía visual (qué capta la atención primero)
   - Uso de espacio negativo

2. ELEMENTOS Y OBJETOS:
   - Productos o servicios mostrados
   - Personas (edad, género, emociones)
   - Backgrounds y contextos
   - Props y elementos secundarios

3. TIPOGRAFÍA Y TEXTO:
   - Fuentes utilizadas (serif, sans-serif, script)
   - Tamaño y legibilidad
   - Cantidad de texto vs. espacio visual
   - Call-to-action (CTA) presente

4. CONTENIDO MULTIMEDIA (si aplica):
   - Duración del video (óptima: 6-15 segundos)
   - Ritmo y dinamismo
   - Transiciones y efectos
   - Audio/música (energética, emocional, neutral)

5. PSICOLOGÍA DEL MARKETING:
   - Emoción evocada (urgencia, alegría, curiosidad, FOMO)
   - Target demográfico implícito
   - Mensaje principal y secundario
   - Técnicas persuasivas empleadas

6. RENDIMIENTO ESTIMADO:
   - Probabilidad de engagement (CTR estimado)
   - Memorabilidad del anuncio
   - Viralidad potencial
   - Efectividad del mensaje

RESPONDE EN EL SIGUIENTE FORMATO JSON ESTRICTO:

{
  "campaign_summary": {
    "run_id": "...",
    "total_ads": 0,
    "analysis_date": "YYYY-MM-DD HH:MM:SS",
    "best_performer": {
      "ad_id": "...",
      "position": 1,
      "overall_score": 9.5
    }
  },
  "ads_analysis": [
    {
      "ad_id": "...",
      "rank": 1,
      "scores": {
        "visual_composition": 9.0,
        "color_effectiveness": 8.5,
        "typography": 9.5,
        "emotional_impact": 9.0,
        "cta_strength": 8.0,
        "overall": 8.8
      },
      "visual_analysis": {
        "color_palette": ["#FF5733", "#3498DB"],
        "dominant_colors": ["rojo vibrante", "azul confianza"],
        "composition_type": "regla de tercios",
        "focal_points": ["producto central", "CTA botón"]
      },
      "content_analysis": {
        "primary_objects": ["smartphone", "persona sonriente"],
        "background_type": "minimalista moderno",
        "text_elements": 3,
        "cta_text": "Compra Ahora"
      },
      "multimedia_analysis": {
        "duration_seconds": 10,
        "pacing": "rápido",
        "audio_type": "música energética",
        "transitions": "suaves y profesionales"
      },
      "marketing_analysis": {
        "target_demographic": "millennials urbanos 25-35 años",
        "emotional_trigger": "urgencia y exclusividad",
        "persuasion_techniques": ["escasez", "prueba social"],
        "brand_consistency": "alta"
      },
      "performance_prediction": {
        "estimated_ctr": "3.5-4.2%",
        "engagement_level": "alto",
        "memorability": "muy alta",
        "viral_potential": "medio-alto"
      },
      "strengths": [
        "Uso magistral de colores contrastantes que captan atención inmediata",
        "CTA claro y visible sin ser agresivo",
        "Balance perfecto entre información y estética"
      ],
      "weaknesses": [
        "Podría beneficiarse de más espacio negativo",
        "El texto secundario es ligeramente pequeño"
      ],
      "recommendations": [
        "Aumentar el tamaño del CTA en 15%",
        "Probar variantes con backgrounds más oscuros para mayor contraste"
      ]
    }
  ],
  "comparative_analysis": {
    "why_best_won": "El anuncio #1 superó a los demás por...",
    "common_success_patterns": ["uso de colores cálidos", "CTAs directos"],
    "common_failure_patterns": ["exceso de texto", "baja calidad de imagen"],
    "key_differentiators": ["calidad de producción", "claridad del mensaje"]
  },
  "recommendations": {
    "for_future_campaigns": [
      "Mantener duración de videos entre 8-12 segundos",
      "Priorizar paletas de colores cálidos"
    ],
    "best_practices_identified": [
      "Mostrar el producto en los primeros 3 segundos",
      "Incluir personas reales incrementa engagement"
    ],
    "avoid": [
      "Exceso de texto que compite con elementos visuales",
      "Música muy agresiva que distrae del mensaje"
    ]
  }
}

IMPORTANTE: 
- Sé ESPECÍFICO y TÉCNICO en tu análisis
- USA DATOS y MÉTRICAS cuando sea posible
- JUSTIFICA cada score con evidencia visual/textual
- Responde SOLO con el JSON, sin texto adicional
"""

        try:
            # Generar análisis con Gemini
            result = self.generate_text(
                prompt=prompt,
                temperature=0.4,  # Balance entre creatividad y consistencia
                max_tokens=8000  # Análisis extenso
            )

            if result['status'] == 'error':
                return {
                    'status': 'error',
                    'error': result.get('error'),
                    'error_type': result.get('error_type')
                }

            # Intentar parsear el JSON de la respuesta
            response_text = result.get('response', '')

            # Limpiar la respuesta para extraer solo el JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                return {
                    'status': 'error',
                    'error': 'No se pudo extraer JSON de la respuesta',
                    'raw_response': response_text[:500]
                }

            json_str = response_text[json_start:json_end]
            analysis_data = json.loads(json_str)

            # Guardar el reporte en reports_json
            reports_dir = Path('reports_json')
            reports_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"{run_id}_analysis_{timestamp}.json"
            report_path = reports_dir / report_filename

            # Agregar metadata al reporte
            final_report = {
                'metadata': {
                    'run_id': run_id,
                    'generated_at': datetime.now().isoformat(),
                    'model_used': self.default_model,
                    'total_ads_analyzed': len(manifest_data.get('ads', [])),
                    'report_version': '1.0'
                },
                'analysis': analysis_data,
                'raw_ai_response': {
                    'usage': result.get('usage', {}),
                    'model': result.get('model')
                }
            }

            # Guardar archivo JSON
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(final_report, f, indent=2, ensure_ascii=False)

            return {
                'status': 'success',
                'run_id': run_id,
                'report_path': str(report_path),
                'report_filename': report_filename,
                'analysis_summary': {
                    'total_ads': len(manifest_data.get('ads', [])),
                    'best_performer': analysis_data.get('campaign_summary', {}).get('best_performer'),
                    'generated_at': datetime.now().isoformat()
                },
                'full_analysis': analysis_data
            }

        except json.JSONDecodeError as e:
            return {
                'status': 'error',
                'error': f'Error parsing JSON: {str(e)}',
                'error_type': 'JSONDecodeError'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_type': type(e).__name__
            }
