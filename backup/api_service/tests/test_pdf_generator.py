"""
Script de prueba para verificar el PDF generator con la nueva estructura
"""
from app.api.routes.apify.facebook.analysis.pdf_generator import (
    parse_analysis_json,
    create_pdf_from_analysis
)
import json
import sys
from pathlib import Path

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent))


def test_parse_existing_json():
    """Probar parsing del JSON existente"""
    print("=" * 60)
    print("TEST: Parseo de JSON Existente")
    print("=" * 60)

    json_path = Path(__file__).parent / "app" / "processors" / "datasets" / "saved_datasets" / \
        "facebook" / "reports_json" / "bfMXWLphPQcDmBsrz_local_analysis.json"

    if not json_path.exists():
        print(f"❌ JSON no encontrado: {json_path}")
        return False

    print(f"✅ JSON encontrado: {json_path.name}")

    with open(json_path, 'r', encoding='utf-8') as f:
        analysis_json = json.load(f)

    print(f"\n📊 Contenido del JSON:")
    print(f"  - status: {analysis_json.get('status')}")
    print(f"  - run_id: {analysis_json.get('run_id')}")
    print(f"  - total_ads_analyzed: {analysis_json.get('total_ads_analyzed')}")
    print(f"  - model: {analysis_json.get('model')}")

    # Parsear análisis
    print(f"\n🔍 Parseando campo 'analysis'...")
    parsed = parse_analysis_json(analysis_json)

    if not parsed:
        print("❌ No se pudo parsear el análisis")
        return False

    print(f"✅ Análisis parseado correctamente")
    print(f"\n📋 Estructura encontrada:")
    for key in parsed.keys():
        print(f"  - {key}")

    # Verificar estructura esperada
    print(f"\n🎯 Verificando estructura del prompt nuevo:")
    expected_keys = ['campaign_name', 'executive_summary',
                     'comparative_analysis', 'general_recommendations']

    for key in expected_keys:
        if key in parsed:
            print(f"  ✅ {key}: encontrado")
            if key == 'comparative_analysis':
                videos = parsed.get(key, [])
                print(f"     - Videos analizados: {len(videos)}")
                for video in videos:
                    print(
                        f"       • {video.get('status', 'N/A')}: {video.get('ad_id', 'N/A')}")
            elif key == 'general_recommendations':
                recs = parsed.get(key, [])
                print(f"     - Recomendaciones: {len(recs)}")
        else:
            print(f"  ⚠️  {key}: NO encontrado")

    return True


def test_generate_pdf():
    """Probar generación de PDF"""
    print("\n" + "=" * 60)
    print("TEST: Generación de PDF")
    print("=" * 60)

    json_path = Path(__file__).parent / "app" / "processors" / "datasets" / "saved_datasets" / \
        "facebook" / "reports_json" / "bfMXWLphPQcDmBsrz_local_analysis.json"

    with open(json_path, 'r', encoding='utf-8') as f:
        analysis_json = json.load(f)

    output_path = Path(__file__).parent / "test_report.pdf"

    print(f"📄 Generando PDF en: {output_path}")

    try:
        result = create_pdf_from_analysis(
            analysis_json=analysis_json,
            output_path=output_path,
            run_id="bfMXWLphPQcDmBsrz"
        )

        if result['success']:
            print(f"✅ PDF generado exitosamente")
            print(f"   Path: {result['pdf_path']}")

            # Verificar tamaño
            if output_path.exists():
                size = output_path.stat().st_size
                print(f"   Tamaño: {size:,} bytes ({size/1024:.2f} KB)")
                return True
            else:
                print(f"❌ PDF no encontrado en {output_path}")
                return False
        else:
            print(f"❌ Error al generar PDF: {result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ Excepción al generar PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Iniciando tests del PDF generator...\n")

    test1 = test_parse_existing_json()
    test2 = test_generate_pdf() if test1 else False

    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    print(f"1. Parseo de JSON: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"2. Generación de PDF: {'✅ PASS' if test2 else '❌ FAIL'}")
    print("=" * 60)

    sys.exit(0 if (test1 and test2) else 1)
