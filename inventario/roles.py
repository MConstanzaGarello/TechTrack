"""
Roles definidos en el Entregable 2 (sección 5.1):
- Analista de Soporte IT: acceso completo (en esta iteración, registrar movimientos y consultar).
- BP del área de IT: solo consulta.
"""
from django.contrib.auth.models import Group, Permission

ANALISTA = "Analista de Soporte IT"
BP = "BP del área de IT"

PERMISOS_CONSULTA = [
    "view_operacion",
    "view_ubicacion",
    "view_modelorecurso",
]
PERMISOS_ANALISTA = PERMISOS_CONSULTA + ["registrar_movimiento"]


def asegurar_roles(**kwargs):
    """Crea o actualiza los grupos y sus permisos. Se ejecuta después de cada migrate."""
    for nombre, codigos in ((ANALISTA, PERMISOS_ANALISTA), (BP, PERMISOS_CONSULTA)):
        grupo, _ = Group.objects.get_or_create(name=nombre)
        permisos = Permission.objects.filter(content_type__app_label="inventario", codename__in=codigos)
        grupo.permissions.set(permisos)


def es_analista(usuario):
    return usuario.is_authenticated and usuario.has_perm("inventario.registrar_movimiento")


def es_bp(usuario):
    return usuario.is_authenticated and usuario.groups.filter(name=BP).exists()
