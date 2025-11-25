"""
Views para la gestión de anuncios
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from .models import AdCampaign, AdContent, AdPlatform
from api_integration.services import APIService
import json


def ads_list(request):
    """Lista de anuncios con filtros"""
    campaigns = AdCampaign.objects.select_related().prefetch_related('platforms')

    # Filtros
    search = request.GET.get('search', '')
    platform = request.GET.get('platform', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if search:
        campaigns = campaigns.filter(
            Q(page_name__icontains=search) |
            Q(ad_archive_id__icontains=search)
        )

    if platform:
        campaigns = campaigns.filter(platforms__platform=platform).distinct()

    if date_from:
        campaigns = campaigns.filter(start_date__gte=date_from)

    if date_to:
        campaigns = campaigns.filter(end_date__lte=date_to)

    # Paginación
    paginator = Paginator(campaigns, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'platform': platform,
        'date_from': date_from,
        'date_to': date_to,
        'platforms': AdPlatform.PLATFORM_CHOICES,
    }

    return render(request, 'ads/list.html', context)


def ad_detail(request, ad_archive_id):
    """Detalle de un anuncio específico"""
    campaign = get_object_or_404(AdCampaign, ad_archive_id=ad_archive_id)
    content = AdContent.objects.filter(campaign=campaign).first()
    platforms = campaign.platforms.all()
    cards = campaign.cards.all()

    context = {
        'campaign': campaign,
        'content': content,
        'platforms': platforms,
        'cards': cards,
    }

    return render(request, 'ads/detail.html', context)


def sync_from_bigquery(request):
    """Sincroniza datos desde BigQuery via API Service"""
    if request.method == 'POST':
        try:
            api_service = APIService()

            # Obtener parámetros
            data = json.loads(request.body)
            date_from = data.get('date_from')
            date_to = data.get('date_to')
            page_names = data.get('page_names', [])

            # Llamar al API Service
            result = api_service.get_analytics(
                date_from=date_from,
                date_to=date_to,
                page_names=page_names
            )

            # Aquí podrías procesar y guardar los datos en la base local
            # Por ahora solo retornamos el resultado

            return JsonResponse({
                'status': 'success',
                'data': result
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


def extract_new_ads(request):
    """Extrae nuevos anuncios usando Apify"""
    if request.method == 'POST':
        try:
            api_service = APIService()

            data = json.loads(request.body)
            pages = data.get('pages', [])
            search_terms = data.get('search_terms', [])

            # Iniciar extracción
            result = api_service.extract_facebook_ads(pages, search_terms)

            return JsonResponse({
                'status': 'success',
                'run_id': result.get('run_id'),
                'message': 'Extracción iniciada exitosamente'
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
