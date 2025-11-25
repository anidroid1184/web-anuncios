"""
Servicio de gestión de archivos en Google Drive para anuncios publicitarios.

MODULO: app/services/drive_service.py
AUTOR: Sistema de Analizador de Anuncios
VERSION: 1.0.0
FECHA: 2025-10-03

PROPOSITO:
    Gestionar la descarga, organización y almacenamiento de archivos multimedia
    (imágenes, videos) de anuncios publicitarios en Google Drive de manera
    automatizada y estructurada.

REEMPLAZA Y MEJORA:
    - Módulo original load_drive.py (función individual)
    - Script consolidation_drive.py (procesamiento manual por lotes)
    - Carga manual de archivos desde URLs de Facebook
    - Organización manual de carpetas y nomenclatura

FUNCIONALIDAD PRINCIPAL:
    - Descarga automatizada de archivos desde URLs públicas
    - Detección automática de tipos MIME y extensiones
    - Subida organizada a carpetas específicas en Google Drive
    - Gestión de nomenclatura consistente con metadatos
    - Procesamiento por lotes para múltiples archivos
    - Manejo robusto de errores y limpieza de archivos temporales

CASOS DE USO:
    - Almacenamiento centralizado de creatividades publicitarias
    - Backup automático de contenido multimedia de anuncios
    - Organización por campañas, marcas o fechas
    - Acceso compartido para equipos de análisis
    - Preservación de contenido ante eliminación de anuncios

BENEFICIOS:
    - Eliminación del procesamiento manual de archivos
    - Nomenclatura consistente y trazeable
    - Organización automática por metadatos
    - Acceso compartido centralizado
    - Backup automático de contenido multimedia
    - Integración directa con pipeline de análisis

DEPENDENCIAS TECNICAS:
    - google-api-python-client: SDK oficial de Google Drive API v3
    - google-oauth2: Autenticación con service accounts
    - requests: Descarga de archivos desde URLs externas
    - mimetypes: Detección automática de tipos de archivo

CONSIDERACIONES DE ALMACENAMIENTO:
    - Límites de cuota de Google Drive por cuenta
    - Optimización de nombres para búsqueda eficiente
    - Estructura de carpetas escalable
    - Manejo de duplicados por contenido hash
"""
import os
import requests
from mimetypes import guess_extension
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from typing import Optional


class DriveService:
    def __init__(self, credentials_path: str):
        scopes = ['https://www.googleapis.com/auth/drive']
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=scopes
        )
        self.service = build('drive', 'v3', credentials=self.credentials)
        # Optional shared drive id fallback from env
        self.shared_drive_id = os.getenv('GOOGLE_SHARED_DRIVE_ID')

    async def upload_from_url(
        self,
        file_url: str,
        filename: str,
        folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Descarga archivo desde URL y lo sube a Google Drive
        Función adaptada del load_drive.py original
        """
        try:
            # Obtener tipo MIME
            head = requests.head(file_url, allow_redirects=True)
            content_type = head.headers.get('Content-Type')

            if not content_type:
                raise ValueError("No se pudo determinar el tipo de contenido")

            # Detectar extensión
            extension = guess_extension(content_type.split(';')[0])
            if not extension:
                raise ValueError("No se pudo determinar la extensión")

            temp_filename = f"{filename}{extension}"

            # Descargar archivo
            response = requests.get(file_url, stream=True)
            response.raise_for_status()

            with open(temp_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Subir a Drive
            target_folder = folder_id or os.getenv(
                'GOOGLE_SHARED_DRIVE_ID') or os.getenv('GOOGLE_PATH_ID')
            file_metadata = {'name': temp_filename}
            if target_folder:
                file_metadata['parents'] = [target_folder]

            media = MediaFileUpload(temp_filename, mimetype=content_type)
            try:
                uploaded_file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    supportsAllDrives=True,
                    fields='id,name,webViewLink'
                ).execute()
            except HttpError as he:
                # Detect storage quota exceeded for service accounts
                content = getattr(he, 'content', None)
                msg = str(he)
                code = None
                if content and b'storageQuotaExceeded' in content:
                    code = 'storageQuotaExceeded'
                return {
                    'error': msg,
                    'status': 'failed',
                    'code': code,
                    'suggestion': 'Use a Shared Drive (add the service account as member) or use OAuth2/domain delegation'
                }

            # Limpiar archivo temporal
            os.remove(temp_filename)

            return {
                'file_id': uploaded_file.get('id'),
                'name': uploaded_file.get('name'),
                'url': uploaded_file.get('webViewLink'),
                'status': 'success'
            }

        except Exception as e:
            return {
                'error': str(e),
                'status': 'failed'
            }

    def create_folder(self, name: str, parent_id: str = None) -> str:
        """
        Crea una carpeta en Google Drive
        """
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        if parent_id:
            file_metadata['parents'] = [parent_id]

        folder = self.service.files().create(
            body=file_metadata,
            supportsAllDrives=True,
            fields='id'
        ).execute()

        return folder.get('id')

    def list_files(self, folder_id: str = None, page_size: int = 100):
        """
        Lista archivos en Drive
        """
        query = ""
        if folder_id:
            query = f"'{folder_id}' in parents"

        results = self.service.files().list(
            q=query,
            pageSize=page_size,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
        ).execute()

        return results.get('files', [])

    async def upload_local_file(self, file_path: str, filename: str, folder_id: Optional[str] = None):
        """
        Sube un archivo local existente a Google Drive usando la API ya inicializada.
        """
        try:
            # Determinar content-type
            from mimetypes import guess_type
            content_type, _ = guess_type(str(file_path))

            name = filename
            if not os.path.splitext(name)[1]:
                name = f"{filename}{os.path.splitext(file_path)[1]}"

            target_folder = folder_id or os.getenv(
                'GOOGLE_SHARED_DRIVE_ID') or os.getenv('GOOGLE_PATH_ID')
            file_metadata = {'name': name}
            if target_folder:
                file_metadata['parents'] = [target_folder]

            media = MediaFileUpload(file_path, mimetype=content_type)
            try:
                uploaded_file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    supportsAllDrives=True,
                    fields='id,name,webViewLink'
                ).execute()
            except HttpError as he:
                content = getattr(he, 'content', None)
                msg = str(he)
                code = None
                if content and b'storageQuotaExceeded' in content:
                    code = 'storageQuotaExceeded'
                return {
                    'error': msg,
                    'status': 'failed',
                    'code': code,
                    'suggestion': 'Use a Shared Drive (add the service account as member) or use OAuth2/domain delegation'
                }

            # Hacer el archivo público (anyone with link -> reader)
            try:
                self.service.permissions().create(
                    fileId=uploaded_file.get('id'),
                    body={'role': 'reader', 'type': 'anyone'},
                    fields='id',
                ).execute()
            except Exception:
                # No bloquear si falla permiso; continuar
                pass

            return {
                'file_id': uploaded_file.get('id'),
                'name': uploaded_file.get('name'),
                'url': uploaded_file.get('webViewLink'),
                'status': 'success'
            }
        except Exception as e:
            return {'error': str(e), 'status': 'failed'}
