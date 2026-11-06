from django.apps import AppConfig
from django.db.models.signals import post_migrate


class InventarioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventario"
    verbose_name = "Inventario y trazabilidad"

    def ready(self):
        from .roles import asegurar_roles

        post_migrate.connect(asegurar_roles, sender=self)
