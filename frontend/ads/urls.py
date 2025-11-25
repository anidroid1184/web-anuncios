"""
URLs para la app de anuncios
"""
from django.urls import path
from . import views

app_name = 'ads'

urlpatterns = [
    path('', views.ads_list, name='list'),
    path('<str:ad_archive_id>/', views.ad_detail, name='detail'),
    path('api/sync-bigquery/', views.sync_from_bigquery, name='sync_bigquery'),
    path('api/extract-new/', views.extract_new_ads, name='extract_new'),
]
