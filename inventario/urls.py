from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("disponibilidad/", views.disponibilidad, name="disponibilidad"),
    path("movimientos/nuevo/", views.nuevo_movimiento, name="nuevo_movimiento"),
    path("historial/", views.historial, name="historial"),
    path("historial/modelo/<int:modelo_id>/", views.historial, name="historial_modelo"),
]
