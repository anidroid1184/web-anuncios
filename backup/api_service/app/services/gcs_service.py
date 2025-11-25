"""
Servicio para Google Cloud Storage (GCS).
Maneja la subida de archivos y gestión de blobs en buckets de GCS.
"""
import os
from typing import Optional, List
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError


class GCSService:
    """Servicio para interactuar con Google Cloud Storage."""

    def __init__(self, credentials_path: Optional[str] = None, bucket_name: Optional[str] = None):
        """
        Inicializa el servicio GCS.

        Args:
            credentials_path: Ruta al archivo de credenciales JSON. 
                            Si es None, usa GOOGLE_APPLICATION_CREDENTIALS del entorno.
            bucket_name: Nombre del bucket por defecto. 
                        Si es None, usa GOOGLE_BUCKET_NAME del entorno.
        """
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        self.client = storage.Client()
        self.default_bucket_name = bucket_name or os.getenv(
            "GOOGLE_BUCKET_NAME", "proveedor-1")

    def get_bucket(self, bucket_name: Optional[str] = None) -> storage.Bucket:
        """
        Obtiene un bucket de GCS.

        Args:
            bucket_name: Nombre del bucket. Si es None, usa el bucket por defecto.

        Returns:
            Objeto Bucket de GCS.
        """
        name = bucket_name or self.default_bucket_name
        return self.client.bucket(name)

    def upload_file(
        self,
        local_path: str,
        blob_name: str,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> dict:
        """
        Sube un archivo local a GCS.

        Args:
            local_path: Ruta local del archivo a subir.
            blob_name: Nombre/ruta del blob en GCS (ej: "runs/123/file.jpg").
            bucket_name: Nombre del bucket. Si es None, usa el bucket por defecto.
            content_type: Tipo de contenido MIME. Si es None, se detecta automáticamente.

        Returns:
            Diccionario con información del archivo subido:
            {
                "bucket": nombre del bucket,
                "blob_name": nombre del blob,
                "public_url": URL pública del archivo,
                "size": tamaño en bytes
            }

        Raises:
            FileNotFoundError: Si el archivo local no existe.
            GoogleCloudError: Si hay error al subir a GCS.
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Archivo no encontrado: {local_path}")

        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Configurar content_type si se proporciona
        if content_type:
            blob.content_type = content_type

        # Subir archivo
        blob.upload_from_filename(local_path)

        return {
            "bucket": bucket.name,
            "blob_name": blob.name,
            "public_url": blob.public_url,
            "media_link": blob.media_link,
            "size": blob.size
        }

    def upload_blob(
        self,
        data: bytes,
        blob_name: str,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> dict:
        """
        Sube datos binarios directamente a GCS.

        Args:
            data: Datos binarios a subir.
            blob_name: Nombre/ruta del blob en GCS.
            bucket_name: Nombre del bucket. Si es None, usa el bucket por defecto.
            content_type: Tipo de contenido MIME.

        Returns:
            Diccionario con información del archivo subido.
        """
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if content_type:
            blob.content_type = content_type

        blob.upload_from_string(data, content_type=content_type)

        return {
            "bucket": bucket.name,
            "blob_name": blob.name,
            "public_url": blob.public_url,
            "media_link": blob.media_link,
            "size": blob.size
        }

    def upload_string(
        self,
        content: str,
        blob_name: str,
        bucket_name: Optional[str] = None,
        content_type: str = "text/plain"
    ) -> dict:
        """
        Sube contenido de texto a GCS.

        Args:
            content: Contenido de texto a subir.
            blob_name: Nombre/ruta del blob en GCS.
            bucket_name: Nombre del bucket. Si es None, usa el bucket por defecto.
            content_type: Tipo de contenido MIME (por defecto text/plain).

        Returns:
            Diccionario con información del archivo subido.
        """
        return self.upload_blob(content.encode('utf-8'), blob_name, bucket_name, content_type)

    def list_blobs(
        self,
        prefix: Optional[str] = None,
        bucket_name: Optional[str] = None
    ) -> List[dict]:
        """
        Lista los blobs en un bucket o con un prefijo específico.

        Args:
            prefix: Prefijo para filtrar blobs (ej: "runs/123/").
            bucket_name: Nombre del bucket. Si es None, usa el bucket por defecto.

        Returns:
            Lista de diccionarios con información de cada blob.
        """
        bucket = self.get_bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)

        return [
            {
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "updated": blob.updated,
                "public_url": blob.public_url
            }
            for blob in blobs
        ]

    def delete_blob(self, blob_name: str, bucket_name: Optional[str] = None) -> bool:
        """
        Elimina un blob de GCS.

        Args:
            blob_name: Nombre del blob a eliminar.
            bucket_name: Nombre del bucket. Si es None, usa el bucket por defecto.

        Returns:
            True si se eliminó correctamente.
        """
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()
        return True

    def blob_exists(self, blob_name: str, bucket_name: Optional[str] = None) -> bool:
        """
        Verifica si un blob existe en GCS.

        Args:
            blob_name: Nombre del blob a verificar.
            bucket_name: Nombre del bucket. Si es None, usa el bucket por defecto.

        Returns:
            True si el blob existe, False en caso contrario.
        """
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()

    def get_signed_url(
        self,
        blob_name: str,
        expiration: int = 3600,
        bucket_name: Optional[str] = None
    ) -> str:
        """
        Genera una URL firmada temporal para acceder a un blob privado.

        Args:
            blob_name: Nombre del blob.
            expiration: Tiempo de expiración en segundos (por defecto 1 hora).
            bucket_name: Nombre del bucket. Si es None, usa el bucket por defecto.

        Returns:
            URL firmada temporal.
        """
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)

        url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method="GET"
        )

        return url
