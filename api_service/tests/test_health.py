# Test de salud para verificar que la API responde correctamente
import requests


def test_health_endpoint():
    response = requests.get("http://localhost:8001/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"
