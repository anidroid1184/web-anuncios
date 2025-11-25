"""
Django models para anuncios
Manejo de datos de anuncios desde BigQuery
"""
from django.db import models
from django.utils import timezone


class AdCampaign(models.Model):
    """Modelo para campañas de anuncios"""
    ad_archive_id = models.CharField(max_length=100, unique=True)
    page_id = models.CharField(max_length=100)
    page_name = models.CharField(max_length=200)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ads_campaign'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.page_name} - {self.ad_archive_id}"


class AdContent(models.Model):
    """Contenido de anuncios (texto, imágenes, videos)"""
    campaign = models.ForeignKey(
        AdCampaign, on_delete=models.CASCADE, related_name='content')
    body_text = models.TextField(blank=True)
    caption = models.CharField(max_length=500, blank=True)
    cta_text = models.CharField(max_length=100, blank=True)
    display_format = models.CharField(max_length=50, blank=True)

    # URLs de medios
    image_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)

    # IDs para Google Drive
    image_drive_id = models.CharField(max_length=100, blank=True)
    video_drive_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ads_content'

    def __str__(self):
        return f"Content for {self.campaign.ad_archive_id}"


class AdPlatform(models.Model):
    """Plataformas donde se publicó el anuncio"""
    PLATFORM_CHOICES = [
        ('FACEBOOK', 'Facebook'),
        ('INSTAGRAM', 'Instagram'),
        ('MESSENGER', 'Messenger'),
        ('AUDIENCE_NETWORK', 'Audience Network'),
        ('THREADS', 'Threads'),
    ]

    campaign = models.ForeignKey(
        AdCampaign, on_delete=models.CASCADE, related_name='platforms')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)

    class Meta:
        db_table = 'ads_platform'
        unique_together = ['campaign', 'platform']

    def __str__(self):
        return f"{self.campaign.ad_archive_id} - {self.platform}"


class AdCard(models.Model):
    """Tarjetas adicionales de anuncios (carrusel, etc.)"""
    campaign = models.ForeignKey(
        AdCampaign, on_delete=models.CASCADE, related_name='cards')
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    original_image_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)
    link_url = models.URLField(blank=True)
    link_description = models.TextField(blank=True)

    # Drive storage
    image_drive_id = models.CharField(max_length=100, blank=True)
    video_drive_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ads_card'

    def __str__(self):
        return f"Card for {self.campaign.ad_archive_id}"
