"""
Facebook Routes - Servicio de Storage (GCS)
Maneja operaciones con Google Cloud Storage
"""

from typing import Dict, List, Optional
from pathlib import Path
import json


class StorageService:
    """
    Servicio para operaciones con GCS.
    Requiere inyección de GCSService.
    """
    
    def __init__(self, gcs_service=None):
        """
        Inicializa con servicio de GCS opcional.
        
        Args:
            gcs_service: Instancia de GCSService (opcional)
        """
        self.gcs = gcs_service
    
    async def upload_dataset(
        self,
        run_id: str,
        local_path: Path,
        bucket_name: str,
        destination_prefix: Optional[str] = None
    ) -> Dict:
        """
        Sube un dataset completo a GCS.
        """
        if not self.gcs:
            return {
                "success": False,
                "message": "GCS service no disponible"
            }
        
        try:
            uploaded_files = []
            prefix = destination_prefix or f"facebook/{run_id}"
            
            # Subir todos los archivos del directorio
            for file_path in local_path.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(local_path)
                    blob_name = f"{prefix}/{relative_path}"
                    
                    await self.gcs.upload_file(
                        bucket_name,
                        str(file_path),
                        blob_name
                    )
                    uploaded_files.append(blob_name)
            
            return {
                "success": True,
                "uploaded_count": len(uploaded_files),
                "files": uploaded_files
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error en upload: {str(e)}"
            }
    
    async def get_public_urls(
        self,
        run_id: str,
        bucket_name: str,
        prefix: Optional[str] = None
    ) -> Dict:
        """
        Obtiene URLs públicas de archivos en GCS.
        """
        if not self.gcs:
            return {
                "success": False,
                "message": "GCS service no disponible"
            }
        
        try:
            search_prefix = prefix or f"facebook/{run_id}"
            blobs = await self.gcs.list_blobs(bucket_name, search_prefix)
            
            urls = []
            for blob in blobs:
                url = f"https://storage.googleapis.com/{bucket_name}/{blob}"
                urls.append({
                    "filename": blob.split('/')[-1],
                    "blob_name": blob,
                    "public_url": url
                })
            
            return {
                "success": True,
                "count": len(urls),
                "urls": urls
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error obteniendo URLs: {str(e)}"
            }
    
    async def list_run_files(
        self,
        run_id: str,
        bucket_name: str
    ) -> List[Dict]:
        """
        Lista todos los archivos de un run en GCS.
        """
        if not self.gcs:
            return []
        
        try:
            prefix = f"facebook/{run_id}"
            blobs = await self.gcs.list_blobs(bucket_name, prefix)
            
            files = []
            for blob in blobs:
                files.append({
                    "name": blob.split('/')[-1],
                    "blob_name": blob
                })
            
            return files
        except Exception:
            return []
