"""
Dashboard views - Página principal del analizador de anuncios
"""
from django.shortcuts import render
from django.http import JsonResponse
from api_integration.services import APIService
import asyncio


def home(request):
    """
    Vista principal del dashboard
    """
    return render(request, 'dashboard/home.html')


async def dashboard_data(request):
    """
    Obtiene datos para el dashboard principal
    """
    try:
        api_service = APIService()
        metrics = await api_service.get_dashboard_metrics()
        trends = await api_service.get_trends(days=30)
        top_advertisers = await api_service.get_top_advertisers(limit=10)

        return JsonResponse({
            'status': 'success',
            'data': {
                'metrics': metrics,
                'trends': trends,
                'top_advertisers': top_advertisers
            }
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def dashboard_data_sync(request):
    """
    Wrapper síncrono para dashboard_data
    """
    return asyncio.run(dashboard_data(request))
