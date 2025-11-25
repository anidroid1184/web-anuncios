# Dashboard models - Para métricas y configuraciones
from django.db import models
from django.utils import timezone


class DashboardMetric(models.Model):
    """
    Modelo para almacenar métricas del dashboard
    """
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Métrica del Dashboard"
        verbose_name_plural = "Métricas del Dashboard"
        ordering = ['-last_updated']

    def __str__(self):
        return f"{self.name} - {self.last_updated}"


class SystemConfiguration(models.Model):
    """
    Configuraciones del sistema
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuraciones del Sistema"

    def __str__(self):
        return f"{self.key}: {self.value[:50]}"
