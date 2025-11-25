"""
Ejemplos de uso del paquete analysis
"""

# ============================================================================
# Ejemplo 1: Análisis completo desde URL
# ============================================================================


async def ejemplo_analisis_desde_url():
    """Análisis end-to-end desde Facebook Ads Library"""
    from app.api.routes.apify.facebook.analysis import (
        scrape_and_prepare_run,
        analyze_campaign_with_gemini,
        compile_latex_to_pdf
    )
    from app.api.routes.apify.facebook.analysis.prompts import DEFAULT_PROMPT
    from app.api.routes.apify.facebook.utils.config import (
        get_facebook_saved_base
    )
    from app.services.gemini_service import GeminiService
    from pathlib import Path

    # 1. Ejecutar workflow completo (scraping + preparación + upload)
    workflow_result = await scrape_and_prepare_run(
        url="https://facebook.com/ads/library/?id=123456",
        count=50,  # Scrapear hasta 50 anuncios
        top=5      # Procesar top 5 mejores
    )

    print(f"Run ID: {workflow_result['run_id']}")
    print(f"Archivos subidos: {workflow_result['uploaded_files']}")
    print(f"Top ads: {workflow_result['top_ads']}")

    # 2. Analizar con Gemini
    gemini_service = GeminiService()
    reports_dir = get_facebook_saved_base() / 'reports_json'

    analysis = analyze_campaign_with_gemini(
        run_id=workflow_result['run_id'],
        manifest_data=workflow_result['manifest'],
        analysis_prompt=DEFAULT_PROMPT,
        gemini_service=gemini_service,
        reports_dir=reports_dir,
        source="url"
    )

    print(f"Mejor anuncio: {analysis['campaign_summary']['best_performer']}")

    # 3. Compilar LaTeX a PDF
    latex_code = analysis.get('latex_code')
    if latex_code:
        tex_path = reports_dir / f"{workflow_result['run_id']}_report.tex"
        tex_path.write_text(latex_code)

        pdf_result = compile_latex_to_pdf(tex_path, reports_dir)

        if pdf_result['success']:
            print(f"PDF generado: {pdf_result['pdf_filename']}")
        else:
            print(f"Error PDF: {pdf_result['error']}")


# ============================================================================
# Ejemplo 2: Análisis desde archivos en GCS bucket
# ============================================================================

def ejemplo_analisis_desde_bucket():
    """Análisis rápido desde archivos ya subidos"""
    from app.api.routes.apify.facebook.analysis import (
        build_manifest_from_gcs,
        analyze_campaign_with_gemini,
        compile_latex_to_pdf
    )
    from app.api.routes.apify.facebook.analysis.prompts import DEFAULT_PROMPT
    from app.api.routes.apify.facebook.utils.config import (
        get_facebook_saved_base,
        get_gcs_service
    )
    from app.services.gemini_service import GeminiService

    run_id = "abc123def456"  # ID de run existente en GCS

    # 1. Construir manifest desde GCS
    gcs_service = get_gcs_service()
    manifest = build_manifest_from_gcs(run_id, gcs_service)

    print(f"Anuncios encontrados: {len(manifest['ads'])}")

    # 2. Analizar con Gemini
    gemini_service = GeminiService()
    reports_dir = get_facebook_saved_base() / 'reports_json'

    analysis = analyze_campaign_with_gemini(
        run_id=run_id,
        manifest_data=manifest,
        analysis_prompt=DEFAULT_PROMPT,
        gemini_service=gemini_service,
        reports_dir=reports_dir,
        source="gcs_bucket"
    )

    # 3. Guardar y compilar
    from app.api.routes.apify.facebook.analysis.gemini_analyzer import (
        save_analysis_results
    )

    saved_files = save_analysis_results(
        run_id=run_id,
        analysis_json=analysis,
        reports_dir=reports_dir,
        source="gcs_bucket"
    )

    if saved_files['latex_path']:
        pdf_result = compile_latex_to_pdf(
            saved_files['latex_path'],
            reports_dir
        )
        print(f"PDF: {pdf_result['pdf_filename']}")


# ============================================================================
# Ejemplo 3: Compilación standalone de LaTeX
# ============================================================================

def ejemplo_compilar_latex_standalone():
    """Compilar cualquier archivo LaTeX a PDF"""
    from app.api.routes.apify.facebook.analysis import compile_latex_to_pdf
    from pathlib import Path

    # Crear un LaTeX simple de prueba
    latex_content = r"""
\documentclass{article}
\usepackage[utf8]{inputenc}
\title{Análisis de Campaña}
\author{AI Analyzer}
\date{\today}

\begin{document}
\maketitle

\section{Resultados}
Este es un reporte de prueba.

\subsection{Score}
\begin{itemize}
    \item Visual: 8/10
    \item Copywriting: 9/10
    \item Target: 7/10
\end{itemize}

\end{document}
"""

    output_dir = Path('reports_json')
    output_dir.mkdir(exist_ok=True)

    tex_path = output_dir / 'test_report.tex'
    tex_path.write_text(latex_content)

    # Compilar
    result = compile_latex_to_pdf(tex_path, output_dir)

    if result['success']:
        print(f"✅ PDF creado: {result['pdf_filename']}")
    else:
        print(f"❌ Error: {result['error']}")


# ============================================================================
# Ejemplo 4: Prompt personalizado
# ============================================================================

async def ejemplo_prompt_personalizado():
    """Usar prompt customizado para análisis específico"""
    from app.api.routes.apify.facebook.analysis import (
        scrape_and_prepare_run,
        analyze_campaign_with_gemini
    )
    from app.services.gemini_service import GeminiService
    from pathlib import Path

    # Prompt especializado para e-commerce
    ECOMMERCE_PROMPT = """
Eres un experto en MARKETING DE E-COMMERCE.

Analiza estos anuncios enfocándote en:
1. Propuesta de valor del producto
2. Precio y ofertas visibles
3. Call-to-action para compra
4. Trust signals (reviews, garantías)
5. Mobile shopping experience

GENERA SCORES 0-10 y código LaTeX profesional.
Responde SOLO en JSON.
"""

    # Workflow
    workflow = await scrape_and_prepare_run(
        url="https://facebook.com/ads/library/?id=789",
        count=30,
        top=5
    )

    # Análisis con prompt custom
    gemini = GeminiService()

    analysis = analyze_campaign_with_gemini(
        run_id=workflow['run_id'],
        manifest_data=workflow['manifest'],
        analysis_prompt=ECOMMERCE_PROMPT,  # ← Prompt personalizado
        gemini_service=gemini,
        reports_dir=Path('reports_json'),
        source="url"
    )

    print("Análisis e-commerce completado")
    return analysis


# ============================================================================
# Ejemplo 5: Manejo de errores
# ============================================================================

async def ejemplo_manejo_errores():
    """Manejo robusto de errores en el flujo"""
    from app.api.routes.apify.facebook.analysis import (
        scrape_and_prepare_run,
        compile_latex_to_pdf
    )
    from fastapi import HTTPException
    from pathlib import Path

    try:
        # Intento de scraping
        result = await scrape_and_prepare_run(
            url="https://invalid-url.com",
            count=10,
            top=3
        )
    except HTTPException as e:
        print(f"Error HTTP {e.status_code}: {e.detail}")
        # Manejar según código:
        # 500: Error de scraper
        # 503: GCS no configurado
        # 504: Timeout
    except Exception as e:
        print(f"Error inesperado: {e}")

    # Compilación con manejo de pdflatex no instalado
    tex_path = Path('test.tex')
    result = compile_latex_to_pdf(tex_path, Path('.'))

    if not result['success']:
        if 'pdflatex not found' in result['error']:
            print("⚠️  Instalar TeX Live o MiKTeX para generar PDFs")
            print("Continuando sin PDF...")
        else:
            print(f"Error de compilación: {result['error']}")


# ============================================================================
# Ejemplo 6: Testing unitario
# ============================================================================

def ejemplo_testing():
    """Tests unitarios para cada módulo"""

    # Test de compilación
    def test_latex_compiler():
        from app.api.routes.apify.facebook.analysis import (
            compile_latex_to_pdf
        )
        from pathlib import Path

        tex = Path('test.tex')
        tex.write_text(
            r'\documentclass{article}\begin{document}Test\end{document}')

        result = compile_latex_to_pdf(tex, Path('.'))

        assert isinstance(result, dict)
        assert 'success' in result
        assert 'pdf_filename' in result or 'error' in result

        tex.unlink()
        print("✅ test_latex_compiler passed")

    # Test de manifest builder
    def test_manifest_builder():
        from app.api.routes.apify.facebook.analysis import (
            build_manifest_from_gcs
        )
        from app.api.routes.apify.facebook.utils.config import (
            get_gcs_service
        )

        gcs = get_gcs_service()
        if gcs:
            try:
                manifest = build_manifest_from_gcs('test_run_id', gcs)
                assert 'run_id' in manifest
                assert 'ads' in manifest
                print("✅ test_manifest_builder passed")
            except Exception as e:
                print(f"⚠️  test_manifest_builder skipped: {e}")

    # Ejecutar tests
    test_latex_compiler()
    test_manifest_builder()


# ============================================================================
# Main: Ejecutar ejemplos
# ============================================================================

if __name__ == "__main__":
    import asyncio

    print("=" * 60)
    print("EJEMPLOS DE USO - PAQUETE ANALYSIS")
    print("=" * 60)

    # Ejemplo 3: Compilación standalone (sin dependencias externas)
    print("\n[Ejemplo 3] Compilación LaTeX standalone")
    ejemplo_compilar_latex_standalone()

    # Ejemplo 6: Testing
    print("\n[Ejemplo 6] Testing unitario")
    ejemplo_testing()

    print("\n" + "=" * 60)
    print("Para ejecutar ejemplos con API:")
    print("  - Ejemplo 1: Análisis desde URL (requiere APIFY_TOKEN)")
    print("  - Ejemplo 2: Análisis desde bucket (requiere run_id en GCS)")
    print("  - Ejemplo 4: Prompt personalizado")
    print("  - Ejemplo 5: Manejo de errores")
    print("=" * 60)
