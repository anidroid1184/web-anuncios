"""
Views para analytics y reportes
"""
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from api_integration.services import APIService
import json
import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder


def analytics_home(request):
    """Vista principal de analytics"""
    return render(request, 'analytics/home.html')


def generate_report(request):
    """Genera reportes personalizados"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            report_type = data.get('report_type', 'general')
            date_from = data.get('date_from')
            date_to = data.get('date_to')
            page_names = data.get('page_names', [])

            api_service = APIService()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Obtener datos según el tipo de reporte
            if report_type == 'trends':
                report_data = loop.run_until_complete(
                    api_service.get_trends(days=30)
                )
            elif report_type == 'advertisers':
                report_data = loop.run_until_complete(
                    api_service.get_top_advertisers(limit=20)
                )
            else:  # general
                report_data = loop.run_until_complete(
                    api_service.get_analytics(
                        date_from=date_from,
                        date_to=date_to,
                        page_names=page_names
                    )
                )

            loop.close()

            return JsonResponse({
                'status': 'success',
                'report_data': report_data
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return render(request, 'analytics/report_generator.html')


def create_charts(request):
    """Crea gráficos interactivos"""
    try:
        api_service = APIService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Obtener datos para gráficos
        metrics = loop.run_until_complete(api_service.get_dashboard_metrics())
        trends = loop.run_until_complete(api_service.get_trends())

        loop.close()

        # Crear gráfico de plataformas
        platforms_data = metrics.get('platforms', [])
        if platforms_data:
            df_platforms = pd.DataFrame(platforms_data)
            fig_platforms = px.pie(
                df_platforms,
                values='count',
                names='platform',
                title='Distribución por Plataformas'
            )
            platforms_chart = json.dumps(fig_platforms, cls=PlotlyJSONEncoder)
        else:
            platforms_chart = None

        # Crear gráfico de tendencias
        trends_data = trends.get('trends', [])
        if trends_data:
            df_trends = pd.DataFrame(trends_data)
            fig_trends = go.Figure()
            fig_trends.add_trace(go.Scatter(
                x=df_trends['date'],
                y=df_trends['ads_count'],
                mode='lines+markers',
                name='Anuncios por día'
            ))
            fig_trends.update_layout(
                title='Tendencia de Anuncios',
                xaxis_title='Fecha',
                yaxis_title='Número de Anuncios'
            )
            trends_chart = json.dumps(fig_trends, cls=PlotlyJSONEncoder)
        else:
            trends_chart = None

        return JsonResponse({
            'status': 'success',
            'charts': {
                'platforms': platforms_chart,
                'trends': trends_chart
            }
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def export_data(request):
    """Exporta datos a CSV"""
    try:
        format_type = request.GET.get('format', 'csv')
        report_type = request.GET.get('type', 'general')

        api_service = APIService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Obtener datos según el tipo
        if report_type == 'advertisers':
            data = loop.run_until_complete(
                api_service.get_top_advertisers(limit=100)
            )
            df = pd.DataFrame(data.get('top_advertisers', []))
        else:
            data = loop.run_until_complete(
                api_service.get_dashboard_metrics()
            )
            df = pd.DataFrame(data.get('platforms', []))

        loop.close()

        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
            df.to_csv(path_or_buf=response, index=False)
            return response

        return JsonResponse({
            'status': 'error',
            'message': 'Formato no soportado'
        }, status=400)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
