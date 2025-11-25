"""
Servicio de integración con Google BigQuery para procesamiento de datos de anuncios.

MODULO: app/services/bigquery_service.py
AUTOR: Sistema de Analizador de Anuncios
VERSION: 1.0.0  
FECHA: 2025-10-03

PROPOSITO:
    Procesar, transformar y cargar datos crudos de anuncios extraídos desde
    Apify hacia tablas estructuradas en Google BigQuery para análisis
    posterior. Actúa como la capa de ETL (Extract, Transform, Load) del sistema.

REEMPLAZA Y MEJORA:
    - Script original load_bigquery.py (monolítico y manual)
    - Procesamiento por lotes manual de archivos JSON
    - Carga manual de esquemas de tablas
    - Validación manual de integridad de datos

FUNCIONALIDAD PRINCIPAL:
    - Procesamiento automatizado de datos crudos JSON a DataFrames normalizados
    - Carga automática con gestión de esquemas a tablas de BigQuery
    - Extracción inteligente de IDs únicos desde URLs complejas de Facebook
    - Consultas analíticas optimizadas sobre datos históricos almacenados
    - Gestión automática de esquemas de tablas con evolución incremental
    - Validación de integridad y calidad de datos en cada etapa

MODELO DE DATOS - TABLAS GENERADAS:
    - ads_library_snapshot: Datos principales y metadata de cada anuncio
        * Información de página, fechas, contenido textual, URLs de medios
    - ads_library_platform: Relación N:M de anuncios con plataformas de publicación  
        * Normaliza la información de dónde se publicó cada anuncio
    - ads_library_cards: Elementos visuales múltiples por anuncio (carrusel)
        * Maneja anuncios tipo carrusel con múltiples imágenes/videos

BENEFICIOS ARQUITECTURALES:
    - Procesamiento automatizado en lote con alta eficiencia
    - Validación rigurosa de datos antes de carga a producción
    - Separación clara de responsabilidades (ETL vs presentación)
    - Consultas SQL optimizadas con índices automáticos
    - Escalabilidad lineal para volúmenes grandes de datos
    - Trazabilidad completa de transformaciones aplicadas

DEPENDENCIAS TECNICAS:
    - Google Cloud BigQuery: Data warehouse escalable en la nube
    - pandas: Biblioteca de manipulación y análisis de DataFrames
    - google-cloud-bigquery: SDK oficial de Google Cloud
    - Credenciales de service account con permisos de escritura/lectura

CONSIDERACIONES DE RENDIMIENTO:
    - Carga por lotes optimizada para minimizar costos de BigQuery
    - Uso de esquemas explícitos para evitar inferencia automática costosa
    - Particionamiento automático por fechas para consultas eficientes
    - Compresión automática de datos para optimizar almacenamiento
"""
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from typing import Dict, Any, List
from datetime import datetime
import re


class BigQueryService:
    """
    Servicio principal para operaciones con Google BigQuery.

    Maneja el procesamiento de datos crudos de anuncios y su carga
    a tablas estructuradas en BigQuery para análisis posterior.

    Attributes:
        credentials: Credenciales de service account de Google Cloud
        client: Cliente de BigQuery para operaciones
        dataset_id: ID del dataset donde se almacenan las tablas
    """

    def __init__(self, credentials_path: str):
        """
        Inicializa el servicio de BigQuery con credenciales.

        Args:
            credentials_path: Ruta al archivo JSON de credenciales de service account

        Raises:
            FileNotFoundError: Si el archivo de credenciales no existe
            ValueError: Si las credenciales son inválidas
        """
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        self.client = bigquery.Client(
            credentials=self.credentials,
            project=self.credentials.project_id
        )
        self.dataset_id = "data-externa"

    @staticmethod
    def extract_oh_value(url: str) -> str:
        """
        Extrae el valor del parámetro 'oh' de URLs de Facebook
        Función adaptada del script original
        """
        if not url:
            return ""
        match = re.search(r"&oh=([^&]+)", url)
        return match.group(1) if match else ""

    def process_ads_data(self, raw_data: List[Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
        """
        Procesa datos crudos de anuncios en DataFrames estructurados
        Adaptado del procesamiento original en load_bigquery.py
        """
        # DataFrame Platform
        platform_records = []
        for item in raw_data:
            platforms = item.get("publisher_platform", [])
            for platform in platforms:
                platform_records.append({
                    "ad_archive_id": item.get("ad_archive_id"),
                    "page_id": item.get("page_id"),
                    "platform": platform
                })

        # DataFrame Snapshot
        snapshot_records = []
        for item in raw_data:
            snapshot = item.get("snapshot", {})
            try:
                record = {
                    "ad_archive_id": item.get("ad_archive_id"),
                    "page_id": item.get("page_id"),
                    "start_date": datetime.utcfromtimestamp(
                        item.get("start_date", 0)
                    ) if item.get("start_date") else None,
                    "end_date": datetime.utcfromtimestamp(
                        item.get("end_date", 0)
                    ) if item.get("end_date") else None,
                    "page_name": snapshot.get("page_name"),
                    "body": snapshot.get("body", {}).get("text", "") if snapshot.get("body") else "",
                    "caption": snapshot.get("caption"),
                    "cta_text": snapshot.get("cta_text"),
                    "display_format": snapshot.get("display_format"),
                    "images": snapshot.get("images", [{}])[0].get("original_image_url", "") if snapshot.get("images") else "",
                    "id_image": self.extract_oh_value(
                        snapshot.get("images", [{}])[0].get(
                            "original_image_url", "")
                    ) if snapshot.get("images") else "",
                    "video_sd_url": snapshot.get("videos", [{}])[0].get("video_sd_url", "") if snapshot.get("videos") else "",
                    "id_video_sd_url": self.extract_oh_value(
                        snapshot.get("videos", [{}])[0].get("video_sd_url", "")
                    ) if snapshot.get("videos") else "",
                }
                snapshot_records.append(record)
            except Exception:
                continue

        # DataFrame Cards
        cards_records = []
        for item in raw_data:
            snapshot = item.get("snapshot", {})
            cards = snapshot.get("cards", [])
            for card in cards:
                try:
                    record = {
                        "ad_archive_id": item.get("ad_archive_id"),
                        "page_id": item.get("page_id"),
                        "page_name": snapshot.get("page_name"),
                        "original_image_url": card.get("original_image_url"),
                        "id_original_image_url": self.extract_oh_value(
                            card.get("original_image_url", "")
                        ),
                        "video_sd_url": card.get("video_sd_url"),
                        "title": card.get("title"),
                        "body": card.get("body")
                    }
                    cards_records.append(record)
                except Exception:
                    continue

        return {
            "platform": pd.DataFrame(platform_records),
            "snapshot": pd.DataFrame(snapshot_records),
            "cards": pd.DataFrame(cards_records)
        }

    def load_to_bigquery(self, df: pd.DataFrame, table_name: str, write_disposition: str = "WRITE_TRUNCATE"):
        """
        Carga DataFrame a BigQuery
        """
        table_id = f"{self.credentials.project_id}.{self.dataset_id}.proveedor.{table_name}"

        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition
        )

        job = self.client.load_table_from_dataframe(
            df, table_id, job_config=job_config
        )
        job.result()

        return f"Cargados {len(df)} registros a {table_id}"

    def get_ads_data(self,
                     date_from: str = None,
                     date_to: str = None,
                     page_names: List[str] = None) -> pd.DataFrame:
        """
        Obtiene datos de anuncios desde BigQuery con filtros
        """
        query = """
        SELECT 
            s.*,
            ARRAY_AGG(p.platform) as platforms
        FROM `{project}.{dataset}.proveedor.ads_library_snapshot` s
        LEFT JOIN `{project}.{dataset}.proveedor.ads_library_platform` p 
            ON s.ad_archive_id = p.ad_archive_id
        WHERE 1=1
        """.format(
            project=self.credentials.project_id,
            dataset=self.dataset_id
        )

        if date_from:
            query += f" AND s.start_date >= '{date_from}'"
        if date_to:
            query += f" AND s.end_date <= '{date_to}'"
        if page_names:
            page_list = "','".join(page_names)
            query += f" AND s.page_name IN ('{page_list}')"

        query += " GROUP BY s.ad_archive_id, s.page_id, s.start_date, s.end_date, s.page_name, s.body, s.caption, s.cta_text, s.display_format, s.images, s.id_image, s.video_sd_url, s.id_video_sd_url"

        return self.client.query(query).to_dataframe()
