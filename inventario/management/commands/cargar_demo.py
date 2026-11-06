"""
Carga los datos iniciales de TechTrack (catálogo de equipamiento, ubicaciones y
cantidades de partida, ver inventario/datos_iniciales.py) y crea los usuarios de
prueba analista.demo y bp.demo.

Uso:
    python manage.py cargar_demo --password "<contraseña para los usuarios de prueba>"
o definiendo la variable de entorno TECHTRACK_DEMO_PASSWORD.

Es idempotente: si los modelos ya están cargados no los duplica (solo actualiza
los usuarios), por eso puede ejecutarse en cada despliegue.
"""
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventario import roles, services
from inventario.datos_iniciales import MODELOS, UBICACIONES
from inventario.models import ModeloRecurso, Ubicacion

USUARIOS = [
    ("analista.demo", "Analista", "IT", roles.ANALISTA),
    ("bp.demo", "BP", "IT", roles.BP),
]


class Command(BaseCommand):
    help = "Carga el catálogo, las ubicaciones y las cantidades iniciales, y los usuarios analista.demo y bp.demo."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Contraseña para los usuarios de prueba.")

    def handle(self, *args, **opciones):
        password = opciones.get("password") or os.environ.get("TECHTRACK_DEMO_PASSWORD")
        if not password:
            raise CommandError("Indicá la contraseña con --password o con TECHTRACK_DEMO_PASSWORD.")
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError("Contraseña no válida: " + " ".join(error.messages))

        roles.asegurar_roles()
        Usuario = get_user_model()

        with transaction.atomic():
            usuarios = {}
            for username, nombre, apellido, rol in USUARIOS:
                usuario, creado = Usuario.objects.get_or_create(
                    username=username, defaults={"first_name": nombre, "last_name": apellido}
                )
                usuario.first_name, usuario.last_name = nombre, apellido
                usuario.set_password(password)
                usuario.save()
                usuario.groups.set([Group.objects.get(name=rol)])
                usuarios[rol] = usuario
                self.stdout.write(f"Usuario {'creado' if creado else 'actualizado'}: {username} ({rol})")

            if ModeloRecurso.objects.exists():
                self.stdout.write(self.style.WARNING("Los datos iniciales ya estaban cargados; no se duplican."))
                return

            ubicaciones = {}
            for nombre, tipo in UBICACIONES:
                ubicaciones[nombre], _ = Ubicacion.objects.get_or_create(nombre=nombre, defaults={"tipo": tipo})
            for nombre, tipo, cargas in MODELOS:
                modelo = ModeloRecurso.objects.create(nombre=nombre, tipo=tipo)
                for ubicacion, cantidad in cargas.items():
                    services.registrar_carga_inicial(
                        analista=usuarios[roles.ANALISTA],
                        modelo=modelo,
                        destino=ubicaciones[ubicacion],
                        cantidad=cantidad,
                    )

        self.stdout.write(self.style.SUCCESS(f"Datos iniciales cargados: {len(MODELOS)} modelos."))
