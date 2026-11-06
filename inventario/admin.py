"""
Panel de administración: solo para el usuario administrador del sistema.
Permite mantener el catálogo (ubicaciones y modelos). Las operaciones se ven
pero no se pueden crear, editar ni borrar desde aquí (RNF-16): se registran
únicamente mediante el servicio de operaciones.
"""
from django.contrib import admin

from .models import ModeloRecurso, Operacion, Ubicacion


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "activa")
    list_filter = ("tipo", "activa")
    search_fields = ("nombre",)


@admin.register(ModeloRecurso)
class ModeloRecursoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "activo")
    list_filter = ("tipo", "activo")
    search_fields = ("nombre", "tipo")


@admin.register(Operacion)
class OperacionAdmin(admin.ModelAdmin):
    list_display = ("fecha", "tipo", "modelo", "cantidad", "origen", "destino", "analista", "canal")
    list_filter = ("tipo", "canal")
    search_fields = ("modelo__nombre",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
