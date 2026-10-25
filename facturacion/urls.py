"""Rutas del módulo Facturación. Todas quedan bajo /facturacion/."""
from django.urls import path

from . import views

app_name = "facturacion"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("nueva/", views.nueva, name="nueva"),
    path("<int:pk>/", views.detalle, name="detalle"),
]
