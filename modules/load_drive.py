import os
import requests
from mimetypes import guess_extension
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def load_drive(url_archivo, nombre_destino, carpeta_id, credenciales_json):
    """
    Descarga un archivo (imagen o video) desde una URL y lo sube a Google Drive con el nombre proporcionado.

    Parámetros:
    - url_archivo: str → URL directa al archivo
    - nombre_destino: str → Nombre deseado del archivo en Google Drive (sin extensión)
    - carpeta_id: str → ID de la carpeta en Google Drive
    - credenciales_json: str → Ruta al archivo JSON de credenciales del servicio

    Retorna:
    - ID del archivo subido a Google Drive
    """
    try:
        # 1. Obtener cabeceras para identificar el tipo MIME
        head = requests.head(url_archivo, allow_redirects=True)
        content_type = head.headers.get('Content-Type')
        print(f"Content-Type detectado: {content_type}")

        if not content_type:
            raise ValueError("No se pudo determinar el tipo de contenido del archivo.")

        # 2. Detectar extensión a partir del tipo MIME
        extension = guess_extension(content_type.split(';')[0])
        if not extension:
            raise ValueError("No se pudo determinar la extensión del archivo.")
        
        archivo_temporal = f"{nombre_destino}{extension}"

        # 3. Descargar el archivo
        print("Descargando archivo...")
        response = requests.get(url_archivo, stream=True)
        response.raise_for_status()

        with open(archivo_temporal, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # 4. Autenticarse con Google Drive
        scopes = ['https://www.googleapis.com/auth/drive']
        credentials = service_account.Credentials.from_service_account_file(
            credenciales_json, scopes=scopes
        )
        service = build('drive', 'v3', credentials=credentials)

        # 5. Subir a Drive
        file_metadata = {
            'name': f"{nombre_destino}{extension}",
            'parents': [carpeta_id]
        }
        media = MediaFileUpload(archivo_temporal, mimetype=content_type)
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            supportsAllDrives=True,
            fields='id'
        ).execute()

        print(f"✅ Archivo subido con ID: {uploaded_file.get('id')}")

        # 6. Eliminar archivo temporal
        os.remove(archivo_temporal)

        return uploaded_file.get('id')

    except Exception as e:
        print(f"❌ Error durante el proceso: {e}")
        return None

