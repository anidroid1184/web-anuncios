"""
AI Routes - OpenAI & Gemini
Endpoint simple para enviar prompts a IA
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from enum import Enum
import os

router = APIRouter()


class AIProvider(str, Enum):
    """Proveedores de IA disponibles"""
    openai = "openai"
    gemini = "gemini"


class SimplePromptRequest(BaseModel):
    """Request simple para enviar prompt a IA"""
    prompt: str = Field(..., description="Tu prompt o pregunta")
    provider: AIProvider = Field(
        AIProvider.openai,
        description="Proveedor de IA: 'openai' o 'gemini'"
    )


@router.post(
    '/generate',
    tags=["ai"],
    summary="Generar respuesta con IA (OpenAI o Gemini)"
)
def generate_with_ai(request: SimplePromptRequest) -> Dict[str, Any]:
    """
    Envía un prompt a OpenAI o Gemini y obtiene una respuesta

    **Uso simple**: Solo escribe tu prompt y elige el proveedor

    Args:
        request: {
            "prompt": "Tu pregunta aquí",
            "provider": "openai"  // o "gemini"
        }

    Returns:
        {
            "provider": "openai",
            "response": "Respuesta generada...",
            "model": "gpt-3.5-turbo"
        }

    Example:
        ```json
        {
            "prompt": "Explica qué es FastAPI",
            "provider": "openai"
        }
        ```
    """
    try:
        if request.provider == AIProvider.openai:
            # Usar OpenAI
            from openai import OpenAI

            api_key = os.getenv('OPEN_API_KEY')
            if not api_key:
                raise HTTPException(
                    status_code=503,
                    detail="OPEN_API_KEY no configurada en .env"
                )

            client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": request.prompt}
                ],
                temperature=0.6  # Prompts generales balanceados
            )

            return {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "response": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        else:  # Gemini
            from app.services.gemini_service import GeminiService

            gemini = GeminiService()
            result = gemini.generate_text(
                prompt=request.prompt,
                temperature=0.7
            )

            if result['status'] == 'error':
                raise HTTPException(
                    status_code=500,
                    detail=f"Gemini error: {result.get('error')}"
                )

            return {
                "provider": "gemini",
                "model": result['model'],
                "response": result['response'],
                "usage": result.get('usage', {})
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )


@router.post(
    '/analyze-file',
    tags=["ai"],
    summary="Analizar archivo con OpenAI"
)
async def analyze_file_with_ai(
    file: UploadFile = File(...,
                            description="Archivo a analizar (txt, csv, json, etc)"),
    prompt: str = Form(...,
                       description="¿Qué quieres que haga la IA con este archivo?"),
    provider: AIProvider = Form(
        AIProvider.openai, description="Proveedor de IA")
) -> Dict[str, Any]:
    """
    Sube un archivo y pídele a la IA que lo analice

    **Uso**:
    1. Selecciona un archivo de tu computadora
    2. Escribe qué quieres que haga la IA (ej: "resume este documento", "analiza estos datos")
    3. Elige el proveedor (OpenAI por defecto)

    **Tipos de archivo soportados**: txt, csv, json, md, py, js, etc (archivos de texto)

    Returns:
        {
            "provider": "openai",
            "filename": "datos.csv",
            "file_size": 1234,
            "response": "Análisis del archivo...",
            "model": "gpt-3.5-turbo"
        }
    """
    try:
        # Leer contenido del archivo
        content = await file.read()

        # Intentar decodificar como texto
        try:
            file_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="El archivo no es un archivo de texto válido. Usa archivos txt, csv, json, etc."
            )

        # Limitar tamaño para no exceder límites de tokens
        max_chars = 10000
        if len(file_content) > max_chars:
            file_content = file_content[:max_chars] + \
                f"\n\n[... archivo truncado, mostrando primeros {max_chars} caracteres]"

        # Construir prompt completo
        full_prompt = f"""{prompt}

--- CONTENIDO DEL ARCHIVO ({file.filename}) ---
{file_content}
--- FIN DEL ARCHIVO ---

Por favor analiza el contenido anterior según mi solicitud."""

        if provider == AIProvider.openai:
            # Usar OpenAI
            from openai import OpenAI

            api_key = os.getenv('OPEN_API_KEY')
            if not api_key:
                raise HTTPException(
                    status_code=503,
                    detail="OPEN_API_KEY no configurada en .env"
                )

            client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.5  # Análisis de archivos preciso
            )

            return {
                "provider": "openai",
                "filename": file.filename,
                "file_size": len(content),
                "model": "gpt-3.5-turbo",
                "response": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }
            }

        else:  # Gemini
            from app.services.gemini_service import GeminiService

            gemini = GeminiService()
            result = gemini.generate_text(
                prompt=full_prompt,
                temperature=0.7
            )

            if result['status'] == 'error':
                raise HTTPException(
                    status_code=500,
                    detail=f"Gemini error: {result.get('error')}"
                )

            return {
                "provider": "gemini",
                "filename": file.filename,
                "file_size": len(content),
                "model": result['model'],
                "response": result['response'],
                "usage": result.get('usage', {})
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando archivo: {str(e)}"
        )
