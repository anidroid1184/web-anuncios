# Test unitario para el servicio de OpenAI
from services.openai_service import OpenAIService


def test_openai_service_analyze_image(monkeypatch):
    class DummyResponse:
        class choices:
            class message:
                content = "Descripción de prueba"
            message = message()
        choices = [choices()]

    def dummy_create(*args, **kwargs):
        return DummyResponse()
    monkeypatch.setattr(OpenAIService, "analyze_image", dummy_create)
    service = OpenAIService(api_key="test")
    result = service.analyze_image(
        "http://test.com/image.jpg", "Describe la imagen")
    assert result == "Descripción de prueba"
