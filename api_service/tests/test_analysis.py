# Test de integración para el endpoint de análisis
import requests


def test_analysis_endpoint():
    files = {'file': ('test.jpg', open(
        'storage/test.jpg', 'rb'), 'image/jpeg')}
    data = {'prompt': 'Describe la imagen'}
    response = requests.post(
        "http://localhost:8001/analyze", files=files, data=data)
    assert response.status_code == 200
    assert "result" in response.json()
    assert "public_url" in response.json()
