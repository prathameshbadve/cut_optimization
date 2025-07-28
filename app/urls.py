from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('optimize/', views.optimize, name='optimize'),
    path('download-pdf/', views.download_cutting_pdf, name='download-pdf'),
]