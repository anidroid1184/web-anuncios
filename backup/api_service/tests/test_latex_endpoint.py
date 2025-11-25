"""
Script para probar el endpoint de generación de LaTeX
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_generate_latex(run_id: str):
    """Prueba el endpoint de generación de LaTeX"""
    print(f"\n{'='*80}")
    print(f"🧪 PROBANDO GENERACIÓN DE LATEX PARA RUN_ID: {run_id}")
    print('='*80)

    url = f"{BASE_URL}/api/v1/apify/facebook/generate-latex-report"
    params = {"run_id": run_id}

    print(f"\n📡 POST {url}")
    print(f"📋 Params: {params}")

    try:
        response = requests.post(url, params=params)

        print(f"\n📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ ÉXITO")
            print(f"   📄 Archivo: {data.get('tex_filename')}")
            print(f"   💾 Ruta: {data.get('tex_file')}")
            print(f"   🪙 Tokens: {data.get('tokens_used')}")
            print(f"   🤖 Modelo: {data.get('model')}")
            print(f"\n   📝 Primeras 500 chars del LaTeX:")
            latex_preview = data.get('latex_code', '')[:500]
            print(f"   {latex_preview}...")

            print(f"\n   💡 Instrucciones de compilación:")
            for key, cmd in data.get('compile_instructions', {}).items():
                print(f"      {key}: {cmd}")

            return True
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ EXCEPCIÓN: {str(e)}")
        return False


def test_compile_pdf(run_id: str):
    """Prueba el endpoint de compilación de PDF con pdflatex"""
    print(f"\n{'='*80}")
    print(f"🔨 PROBANDO COMPILACIÓN DE PDF (pdflatex) PARA RUN_ID: {run_id}")
    print('='*80)

    url = f"{BASE_URL}/api/v1/apify/facebook/compile-latex-to-pdf"
    params = {"run_id": run_id}

    print(f"\n📡 POST {url}")
    print(f"📋 Params: {params}")

    try:
        response = requests.post(url, params=params)

        print(f"\n📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ PDF COMPILADO")
            print(f"   📄 Archivo: {data.get('pdf_filename')}")
            print(f"   💾 Ruta: {data.get('pdf_file')}")
            print(f"   📦 Tamaño: {data.get('pdf_size_bytes')} bytes")
            print(f"   📝 LaTeX usado: {data.get('tex_file')}")

            return True
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ EXCEPCIÓN: {str(e)}")
        return False


def test_generate_pdf_direct(run_id: str):
    """Prueba el endpoint de generación de PDF directo (ReportLab)"""
    print(f"\n{'='*80}")
    print(f"📄 PROBANDO GENERACIÓN PDF DIRECTO (ReportLab) PARA: {run_id}")
    print('='*80)

    url = f"{BASE_URL}/api/v1/apify/facebook/generate-pdf-report"
    params = {"run_id": run_id}

    print(f"\n📡 POST {url}")
    print(f"📋 Params: {params}")

    try:
        response = requests.post(url, params=params)

        print(f"\n📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ PDF GENERADO (ReportLab)")
            print(f"   📄 Archivo: {data.get('pdf_filename')}")
            print(f"   💾 Ruta: {data.get('pdf_file')}")
            print(f"   📦 Tamaño: {data.get('pdf_size_bytes')} bytes")
            print(f"   🔧 Generador: {data.get('generator')}")

            return True
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ EXCEPCIÓN: {str(e)}")
        return False

    print(f"\n📡 POST {url}")
    print(f"📋 Params: {params}")

    try:
        response = requests.post(url, params=params)

        print(f"\n📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ PDF COMPILADO")
            print(f"   📄 Archivo: {data.get('pdf_filename')}")
            print(f"   💾 Ruta: {data.get('pdf_file')}")
            print(f"   📦 Tamaño: {data.get('pdf_size_bytes')} bytes")
            print(f"   📝 LaTeX usado: {data.get('tex_file')}")

            return True
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ EXCEPCIÓN: {str(e)}")
        return False


if __name__ == "__main__":
    # Probar con los run_ids disponibles
    run_ids = [
        "yJeKF48KH4pPFspOY",
        "bfMXWLphPQcDmBsrz"
    ]

    print("\n" + "🧪 PRUEBA 1: GENERACIÓN DE LATEX ".center(80, "="))

    for run_id in run_ids:
        success = test_generate_latex(run_id)
        if success:
            print(f"\n✅ LaTeX generado para {run_id}")
        else:
            print(f"\n❌ LaTeX fallido para {run_id}")
        print("\n" + "="*80 + "\n")

    print("\n" + "🧪 PRUEBA 2: GENERACIÓN PDF DIRECTO (ReportLab) ".center(80, "="))

    for run_id in run_ids:
        success = test_generate_pdf_direct(run_id)
        if success:
            print(f"\n✅ PDF generado para {run_id}")
        else:
            print(f"\n❌ PDF fallido para {run_id}")
        print("\n" + "="*80 + "\n")

    print("\n" + "🧪 PRUEBA 3: COMPILACIÓN LATEX (Requiere pdflatex) ".center(80, "="))
    print("⚠️  Esta prueba solo funcionará si tienes pdflatex instalado\n")

    for run_id in run_ids:
        success = test_compile_pdf(run_id)
        if success:
            print(f"\n✅ PDF compilado para {run_id}")
        else:
            print(f"\n❌ PDF fallido para {run_id}")
            print("   ⚠️  Necesitas pdflatex (MiKTeX o TeX Live)")
        print("\n" + "="*80 + "\n")
