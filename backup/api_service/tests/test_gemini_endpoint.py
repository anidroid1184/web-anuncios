"""
Script de prueba para endpoints de Gemini AI
Ejecutar: python test_gemini_endpoint.py
"""
import requests
import json

BASE_URL = "http://localhost:8001/api/v1/gemini"


def test_connection():
    """Prueba 1: Test de conexión"""
    print("\n" + "="*60)
    print("TEST 1: Probando conexión con Gemini")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/test")
        data = response.json()

        if response.status_code == 200:
            print("✅ Conexión exitosa!")
            print(f"   Modelo: {data['model']}")
            print(f"   Respuesta: {data['response']}")
        else:
            print(f"❌ Error {response.status_code}: {data}")

    except Exception as e:
        print(f"❌ Error de conexión: {e}")


def test_generate_simple():
    """Prueba 2: Generación de texto simple"""
    print("\n" + "="*60)
    print("TEST 2: Generación de texto simple")
    print("="*60)

    prompt = "Explica qué es FastAPI en 2 líneas"

    try:
        response = requests.post(
            f"{BASE_URL}/generate",
            json={"prompt": prompt, "temperature": 0.5}
        )
        data = response.json()

        if response.status_code == 200:
            print("✅ Generación exitosa!")
            print(f"\n   Prompt: {prompt}")
            print(f"\n   Respuesta:\n   {data['response']}")
            print(f"\n   Tokens usados: {data['usage']['total_tokens']}")
        else:
            print(f"❌ Error {response.status_code}: {data}")

    except Exception as e:
        print(f"❌ Error: {e}")


def test_generate_code():
    """Prueba 3: Generación de código"""
    print("\n" + "="*60)
    print("TEST 3: Generación de código")
    print("="*60)

    prompt = """
Genera una función Python que:
1. Reciba una lista de números
2. Retorne la suma de los números pares
3. Incluya docstring y type hints
"""

    try:
        response = requests.post(
            f"{BASE_URL}/generate",
            json={
                "prompt": prompt,
                "temperature": 0.3,
                "max_tokens": 500
            }
        )
        data = response.json()

        if response.status_code == 200:
            print("✅ Código generado!")
            print(f"\n{data['response']}")
        else:
            print(f"❌ Error {response.status_code}: {data}")

    except Exception as e:
        print(f"❌ Error: {e}")


def test_chat():
    """Prueba 4: Chat conversacional"""
    print("\n" + "="*60)
    print("TEST 4: Chat conversacional")
    print("="*60)

    messages = [
        {"role": "user", "content": "Hola, ¿qué es Python?"}
    ]

    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"messages": messages, "temperature": 0.7}
        )
        data = response.json()

        if response.status_code == 200:
            print("✅ Chat exitoso!")
            print(f"\n   Usuario: {messages[0]['content']}")
            print(f"\n   Gemini: {data['response'][:200]}...")

            # Segunda pregunta
            messages.append({"role": "model", "content": data['response']})
            messages.append({"role": "user", "content": "¿Y FastAPI?"})

            response2 = requests.post(
                f"{BASE_URL}/chat",
                json={"messages": messages}
            )
            data2 = response2.json()

            if response2.status_code == 200:
                print(f"\n   Usuario: {messages[2]['content']}")
                print(f"\n   Gemini: {data2['response'][:200]}...")
        else:
            print(f"❌ Error {response.status_code}: {data}")

    except Exception as e:
        print(f"❌ Error: {e}")


def test_list_models():
    """Prueba 5: Listar modelos"""
    print("\n" + "="*60)
    print("TEST 5: Listar modelos disponibles")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/models")
        data = response.json()

        if response.status_code == 200:
            print(f"✅ {data['total']} modelos disponibles:")
            for model in data['models']:
                print(f"   - {model}")
        else:
            print(f"❌ Error {response.status_code}: {data}")

    except Exception as e:
        print(f"❌ Error: {e}")


def test_different_temperatures():
    """Prueba 6: Diferentes valores de temperature"""
    print("\n" + "="*60)
    print("TEST 6: Efecto de temperature (creatividad)")
    print("="*60)

    prompt = "Describe una puesta de sol en 1 línea"
    temperatures = [0.2, 0.7, 1.5]

    for temp in temperatures:
        try:
            response = requests.post(
                f"{BASE_URL}/generate",
                json={"prompt": prompt, "temperature": temp}
            )
            data = response.json()

            if response.status_code == 200:
                print(f"\n   Temperature {temp}:")
                print(f"   {data['response']}")
            else:
                print(f"   ❌ Error con temperature {temp}")

        except Exception as e:
            print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRUEBAS DE ENDPOINTS GEMINI AI")
    print("="*60)
    print("\nAsegúrate de que:")
    print("1. El servidor está corriendo (python main.py)")
    print("2. GOOGLE_GEMINI_API está configurado en .env")
    print("\nPresiona Enter para continuar...")
    input()

    # Ejecutar todas las pruebas
    test_connection()
    test_generate_simple()
    test_generate_code()
    test_chat()
    test_list_models()
    test_different_temperatures()

    print("\n" + "="*60)
    print("PRUEBAS COMPLETADAS")
    print("="*60)
    print("\nPara más ejemplos, consulta: docs/GEMINI_API.md\n")
