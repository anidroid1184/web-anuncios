"""
Facebook Routes - Servicio de Upload
Maneja uploads a Drive y GCS con manifests
"""

from typing import Dict, Optional
from pathlib import Path
import json


class UploadService:
    """
    Servicio para manejar uploads a diferentes destinos.
    Usa inyección de dependencias para Drive y GCS services.
    """
    
    def __init__(self, drive_service=None, gcs_service=None):
        """
        Inicializa con servicios externos opcionales.
        
        Args:
            drive_service: Instancia de DriveService
            gcs_service: Instancia de GCSService
        """
        self.drive = drive_service
        self.gcs = gcs_service
    
    async def upload_to_drive(
        self,
        local_path: Path,
        folder_id: str,
        run_id: str
    ) -> Dict:
        """
        Sube archivos a Google Drive.
        """
        if not self.drive:
            return {
                "success": False,
                "message": "Drive service no disponible"
            }
        
        try:
            uploaded_files = []
            
            for file_path in local_path.rglob("*"):
                if file_path.is_file():
                    file_id = await self.drive.upload_file(
                        str(file_path),
                        folder_id
                    )
                    uploaded_files.append({
                        "filename": file_path.name,
                        "file_id": file_id
                    })
            
            return {
                "success": True,
                "run_id": run_id,
                "uploaded_count": len(uploaded_files),
                "files": uploaded_files
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error en upload a Drive: {str(e)}"
            }
    
    async def upload_to_gcs(
        self,
        local_path: Path,
        bucket_name: str,
        run_id: str,
        prefix: Optional[str] = None
    ) -> Dict:
        """
        Sube archivos a Google Cloud Storage.
        """
        if not self.gcs:
            return {
                "success": False,
                "message": "GCS service no disponible"
            }
        
        try:
            uploaded_files = []
            gcs_prefix = prefix or f"facebook/{run_id}"
            
            for file_path in local_path.rglob("*"):
                if file_path.is_file():
                    relative = file_path.relative_to(local_path)
                    blob_name = f"{gcs_prefix}/{relative}"
                    
                    await self.gcs.upload_file(
                        bucket_name,
                        str(file_path),
                        blob_name
                    )
                    uploaded_files.append(blob_name)
            
            return {
                "success": True,
                "run_id": run_id,
                "bucket": bucket_name,
                "uploaded_count": len(uploaded_files),
                "files": uploaded_files
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error en upload a GCS: {str(e)}"
            }
    
    async def create_manifest(
        self,
        run_id: str,
        metadata: Dict,
        local_path: Optional[Path] = None
    ) -> Dict:
        """
        Crea un manifest localmente.
        """
        try:
            manifest = {
                "run_id": run_id,
                "metadata": metadata,
                "files": []
            }
            
            if local_path:
                manifest_file = local_path / "manifest.json"
                manifest_file.write_text(
                    json.dumps(manifest, indent=2),
                    encoding='utf-8'
                )
                return {
                    "success": True,
                    "manifest_path": str(manifest_file)
                }
            
            return {"success": True, "manifest": manifest}
        except Exception as e:
            return {
                "success": False,
                "message": f"Error con manifest: {str(e)}"
            }
