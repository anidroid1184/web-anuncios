"""
Dashboard URLs
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/dashboard-data/', views.dashboard_data_sync, name='dashboard_data'),
]
