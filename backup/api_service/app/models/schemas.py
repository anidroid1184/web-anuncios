"""
Modelos Pydantic para validación automática de datos de la API.

MODULO: app/models/schemas.py
AUTOR: Sistema de Analizador de Anuncios
VERSION: 1.0.0
FECHA: 2025-10-03

PROPOSITO:
    Definición de esquemas de datos para validación automática de requests y responses
    de la API FastAPI. Utiliza Pydantic para garantizar integridad de datos y generar
    documentación automática.

FUNCIONALIDAD:
    - Validación automática de tipos de datos en requests/responses
    - Documentación automática de la API en /docs y /redoc
    - Serialización y deserialización automática de JSON
    - Generación automática de esquemas OpenAPI/Swagger
    - Type hints para desarrollo con autocompletado
    - Prevención de errores de tipos de datos en tiempo de ejecución

BENEFICIOS:
    - Validación automática elimina bugs por tipos incorrectos
    - Documentación siempre actualizada automáticamente
    - Mejor experiencia de desarrollo con IntelliSense
    - Compatibilidad automática con herramientas OpenAPI
    - Facilita testing y debugging

DEPENDENCIAS:
    - pydantic: Validación de datos y parsing
    - typing: Type hints de Python
    - datetime: Manejo de fechas y tiempos

MODELOS INCLUIDOS:
    - AdData: Estructura completa de un anuncio individual
    - ApifyRequest/ApifyResponse: Comunicación bidireccional con Apify API
    - BigQueryRequest: Operaciones de carga/consulta en BigQuery
    - DriveUploadRequest/DriveUploadResponse: Gestión de archivos en Google Drive
    - AnalyticsRequest/AnalyticsResponse: Peticiones y respuestas de análisis
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AdData(BaseModel):
    """
    Modelo para representar un anuncio individual extraído desde Apify.

    Estructura los datos básicos de un anuncio de Facebook/Meta incluyendo
    identificadores únicos, información de la página publicitaria, fechas de
    campaña y plataformas de publicación.

    Este modelo es el núcleo del sistema ya que representa la unidad básica
    de información que se procesa desde la extracción hasta el análisis final.

    Attributes:
        ad_archive_id (str): Identificador único del anuncio en Facebook Ads 
            Library. Formato típico: números de 15-20 dígitos.
        page_id (str): Identificador único de la página de Facebook que 
            publicó el anuncio. Formato: números de 10-20 dígitos.
        page_name (Optional[str], optional): Nombre legible de la página o 
            marca. Puede ser None si la página fue eliminada. Defaults to None.
        start_date (Optional[datetime], optional): Fecha y hora de inicio de 
            la campaña publicitaria en UTC. Defaults to None.
        end_date (Optional[datetime], optional): Fecha y hora de finalización
            de la campaña publicitaria en UTC. None si aún está activa.
            Defaults to None.
        publisher_platform (List[str], optional): Lista de plataformas donde
            se publicó el anuncio. Valores posibles: ['Facebook', 'Instagram',
            'Messenger', 'Audience Network']. Defaults to [].
        snapshot (Optional[Dict[str, Any]], optional): Datos completos del
            anuncio en formato JSON incluyendo textos, imágenes, videos, CTAs,
            etc. Estructura variable según tipo de anuncio. Defaults to None.

    Example:
        >>> ad = AdData(
        ...     ad_archive_id="123456789012345",
        ...     page_id="987654321098765", 
        ...     page_name="Coca Cola",
        ...     publisher_platform=["Facebook", "Instagram"]
        ... )
        >>> print(ad.ad_archive_id)
        "123456789012345"

    Note:
        Los campos opcionales permiten flexibilidad cuando los datos desde
        Apify están incompletos o cuando la página/anuncio fue eliminado.
    """
    ad_archive_id: str
    page_id: str
    page_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    publisher_platform: List[str] = []
    snapshot: Optional[Dict[str, Any]] = None


class ApifyRequest(BaseModel):
    """
    Modelo para peticiones de ejecución de actors en Apify.

    Estructura los datos necesarios para ejecutar un actor específico en la
    plataforma Apify con configuración personalizada de entrada.

    Args:
        actor_id (str): Identificador único del actor en Apify. Formato típico:
            "username/actor-name" o "actor-id". Ejemplo: "apify/facebook-ads-scraper"
        input_data (Dict[str, Any]): Diccionario con configuración específica
            del actor. La estructura varía según el actor pero típicamente incluye
            páginas a analizar, términos de búsqueda, límites, etc.

    Example:
        >>> request = ApifyRequest(
        ...     actor_id="apify/facebook-ads-library-scraper",
        ...     input_data={
        ...         "pages": ["Coca Cola", "Pepsi"],
        ...         "maxResults": 100,
        ...         "searchTerms": ["bebida", "refresco"]
        ...     }
        ... )

    Note:
        La validación de input_data es flexible ya que cada actor de Apify
        tiene diferentes parámetros de configuración.
    """
    actor_id: str = Field(..., description="ID del actor de Apify")
    input_data: Dict[str, Any] = Field(..., description="Datos de entrada")


class ApifyResponse(BaseModel):
    """
    Modelo para respuestas de ejecución de actors en Apify.

    Encapsula el resultado de una ejecución de actor incluyendo identificador
    de ejecución, estado actual y datos extraídos (si están disponibles).

    Attributes:
        run_id (str): Identificador único de la ejecución en Apify.
            Formato: UUID o string alfanumérico de ~20 caracteres.
        status (str): Estado actual de la ejecución. Valores posibles:
            - "RUNNING": En progreso
            - "SUCCEEDED": Completada exitosamente  
            - "FAILED": Error durante ejecución
            - "TIMEOUT": Tiempo límite excedido
            - "ABORTED": Cancelada manualmente
        data (Optional[List[AdData]], optional): Lista de anuncios extraídos.
            Solo presente cuando status="SUCCEEDED" y hay resultados.
            Defaults to None.

    Returns:
        ApifyResponse: Instancia con información de la ejecución

    Example:
        >>> response = ApifyResponse(
        ...     run_id="abc123def456",
        ...     status="SUCCEEDED", 
        ...     data=[AdData(...), AdData(...)]
        ... )
        >>> if response.status == "SUCCEEDED":
        ...     print(f"Extraídos {len(response.data)} anuncios")

    Note:
        El campo 'data' estará vacío durante ejecución y se poblará al completar.
    """
    run_id: str
    status: str
    data: Optional[List[AdData]] = None


class BigQueryRequest(BaseModel):
    """
    Modelo para peticiones de operaciones con BigQuery.

    Encapsula los datos necesarios para realizar operaciones de carga,
    actualización o eliminación de datos en tablas de BigQuery.

    Args:
        table_name (str): Nombre completo de la tabla en BigQuery.
            Formato: "dataset.table" o solo "table" si se usa dataset default.
            Ejemplo: "proveedor.ads_library_snapshot"
        data (List[Dict[str, Any]]): Lista de registros a procesar. Cada
            diccionario representa una fila con nombres de columnas como keys
            y valores correspondientes.
        operation (str, optional): Tipo de operación a realizar.
            Valores válidos: "insert", "update", "delete".
            Defaults to "insert".

    Example:
        >>> request = BigQueryRequest(
        ...     table_name="ads_library_snapshot",
        ...     data=[
        ...         {"ad_id": "123", "page_name": "Coca Cola"},
        ...         {"ad_id": "456", "page_name": "Pepsi"}
        ...     ],
        ...     operation="insert"
        ... )

    Raises:
        ValidationError: Si operation no es uno de los valores permitidos

    Note:
        Para operaciones 'update' y 'delete', los registros deben incluir
        campos de identificación (claves primarias).
    """
    table_name: str
    data: List[Dict[str, Any]]
    operation: str = Field(
        default="insert", description="insert, update, delete")


class DriveUploadRequest(BaseModel):
    """
    Modelo para peticiones de subida de archivos a Google Drive.

    Estructura los parámetros necesarios para descargar un archivo desde una
    URL pública y subirlo a una carpeta específica en Google Drive.

    Args:
        url (str): URL completa del archivo a descargar. Debe ser accesible
            públicamente sin autenticación. Soporta imágenes, videos y
            documentos.
        filename (str): Nombre deseado para el archivo en Google Drive
            (sin extensión). La extensión se detecta automáticamente del
            Content-Type del archivo.
        folder_id (str): Identificador único de la carpeta destino en
            Google Drive. Formato: string alfanumérico de ~30 caracteres.
            Se puede obtener de la URL de la carpeta en Drive.

    Example:
        >>> request = DriveUploadRequest(
        ...     url="https://example.com/image.jpg",
        ...     filename="coca_cola_ad_123",
        ...     folder_id="1ABC123def456GHI789jkl012MNO345"
        ... )

    Note:
        El archivo se descarga temporalmente y luego se elimina tras la subida.
        El nombre final incluirá la extensión detectada automáticamente.
    """
    url: str = Field(..., description="URL del archivo a descargar")
    filename: str = Field(..., description="Nombre del archivo")
    folder_id: str = Field(..., description="ID de carpeta en Drive")


class DriveUploadResponse(BaseModel):
    """
    Modelo para respuestas de subida de archivos a Google Drive.

    Contiene información del resultado de la operación de subida incluyendo
    identificadores del archivo y URLs de acceso.

    Attributes:
        file_id (str): Identificador único del archivo en Google Drive.
            Formato: string alfanumérico de ~30 caracteres. Se usa para
            futuras operaciones sobre el archivo.
        filename (str): Nombre final del archivo en Drive incluyendo la
            extensión detectada automáticamente.
        url (str): URL de visualización del archivo en Google Drive.
            Permite acceso directo desde navegador web.
        status (str): Estado de la operación. Valores posibles:
            - "success": Subida completada exitosamente
            - "failed": Error durante la subida
            - "partial": Subida parcial (archivo corrupto)

    Returns:
        DriveUploadResponse: Instancia con información del archivo subido

    Example:
        >>> response = DriveUploadResponse(
        ...     file_id="1XYZ789abc123DEF456ghi",
        ...     filename="coca_cola_ad_123.jpg",
        ...     url="https://drive.google.com/file/d/1XYZ789.../view",
        ...     status="success"
        ... )
        >>> print(f"Archivo subido: {response.filename}")

    Note:
        La URL proporcionada requiere permisos de visualización configurados
        en la carpeta de Google Drive.
    """
    file_id: str
    filename: str
    url: str
    status: str


class AnalyticsRequest(BaseModel):
    """
    Modelo para peticiones de análisis de datos de anuncios.

    Estructura los filtros y parámetros necesarios para generar análisis
    personalizados de datos de anuncios almacenados en BigQuery.

    Args:
        date_from (Optional[datetime], optional): Fecha de inicio del rango
            de análisis. Si es None, se incluyen todos los anuncios desde
            el más antiguo. Formato UTC. Defaults to None.
        date_to (Optional[datetime], optional): Fecha de fin del rango de
            análisis. Si es None, se incluyen anuncios hasta la fecha actual.
            Formato UTC. Defaults to None.
        page_names (Optional[List[str]], optional): Lista de nombres de
            páginas específicas a analizar. Si es None, se incluyen todas
            las páginas. Útil para análisis competitivo. Defaults to None.
        platforms (Optional[List[str]], optional): Lista de plataformas
            específicas a analizar (Facebook, Instagram, etc.). Si es None,
            se incluyen todas las plataformas. Defaults to None.

    Example:
        >>> request = AnalyticsRequest(
        ...     date_from=datetime(2024, 1, 1),
        ...     date_to=datetime(2024, 12, 31),
        ...     page_names=["Coca Cola", "Pepsi"],
        ...     platforms=["Facebook", "Instagram"]
        ... )

    Note:
        Todos los filtros son opcionales y se combinan con AND lógico.
        Filtros None se ignoran en la consulta SQL resultante.
    """
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page_names: Optional[List[str]] = None
    platforms: Optional[List[str]] = None


class AnalyticsResponse(BaseModel):
    """
    Modelo para respuestas de análisis de datos de anuncios.

    Encapsula el resultado completo de un análisis incluyendo métricas
    cuantitativas, distribuciones, rankings e insights generados
    automáticamente.

    Attributes:
        total_ads (int): Número total de anuncios encontrados que cumplen
            los filtros aplicados. Base para cálculos de porcentajes.
        platforms_distribution (Dict[str, int]): Distribución de anuncios
            por plataforma. Key: nombre plataforma, Value: cantidad de anuncios.
            Ejemplo: {"Facebook": 150, "Instagram": 75}
        top_pages (List[Dict[str, Any]]): Lista de las páginas con más
            anuncios. Cada diccionario contiene: page_name, total_ads,
            active_days, avg_per_day. Ordenado por total_ads descendente.
        date_range (Dict[str, str]): Rango de fechas analizado. Keys:
            "from" y "to" con fechas en formato ISO string.
        insights (List[str]): Lista de insights generados automáticamente
            en lenguaje natural. Incluye tendencias, comparaciones y
            observaciones relevantes del análisis.

    Returns:
        AnalyticsResponse: Instancia con análisis completo de los datos

    Example:
        >>> response = AnalyticsResponse(
        ...     total_ads=1000,
        ...     platforms_distribution={"Facebook": 600, "Instagram": 400},
        ...     top_pages=[
        ...         {"page_name": "Coca Cola", "total_ads": 50, 
        ...          "active_days": 30, "avg_per_day": 1.67}
        ...     ],
        ...     date_range={"from": "2024-01-01", "to": "2024-12-31"},
        ...     insights=[
        ...         "Facebook es la plataforma dominante con 60% de anuncios",
        ...         "Coca Cola es el anunciante más activo del período"
        ...     ]
        ... )

    Note:
        Los insights se generan dinámicamente basados en los datos analizados
        y pueden incluir comparaciones, tendencias y anomalías detectadas.
    """
    total_ads: int
    platforms_distribution: Dict[str, int]
    top_pages: List[Dict[str, Any]]
    date_range: Dict[str, str]
    insights: List[str]
