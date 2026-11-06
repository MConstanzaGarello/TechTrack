"""
Servicio de operaciones: única vía para registrar cambios en las cantidades
(Entregable 3, sección 9). La web lo usa hoy; el audio de WhatsApp (Etapa 2)
y la importación inicial (HU-16) lo van a reutilizar.
"""
from collections import defaultdict

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum

from .models import ModeloRecurso, Operacion, Ubicacion


class CantidadInsuficiente(ValidationError):
    """HU-08: la cantidad a mover supera la registrada en el origen."""

    def __init__(self, disponible, solicitada, origen, modelo):
        self.disponible = disponible
        self.solicitada = solicitada
        super().__init__(
            f"No se puede mover {solicitada} unidad(es) de «{modelo}»: en {origen} hay "
            f"{disponible} registrada(s). Revisá el historial del modelo para investigar la diferencia."
        )


def cantidad_en(modelo, ubicacion):
    """Cantidad de un modelo en una ubicación, calculada desde las operaciones (RNF-11)."""
    entradas = (
        Operacion.objects.filter(modelo=modelo, destino=ubicacion).aggregate(t=Sum("cantidad"))["t"] or 0
    )
    salidas = (
        Operacion.objects.filter(modelo=modelo, origen=ubicacion).aggregate(t=Sum("cantidad"))["t"] or 0
    )
    return entradas - salidas


def disponibilidad():
    """Devuelve {(modelo_id, ubicacion_id): cantidad} para todos los pares con movimiento."""
    resultado = defaultdict(int)
    for fila in Operacion.objects.values("modelo_id", "destino_id").annotate(t=Sum("cantidad")):
        resultado[(fila["modelo_id"], fila["destino_id"])] += fila["t"]
    for fila in (
        Operacion.objects.filter(origen__isnull=False).values("modelo_id", "origen_id").annotate(t=Sum("cantidad"))
    ):
        resultado[(fila["modelo_id"], fila["origen_id"])] -= fila["t"]
    return dict(resultado)


def _validar_cantidad(cantidad):
    if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
        raise ValidationError("La cantidad debe ser un número entero mayor que cero.")


def registrar_movimiento(*, analista, modelo, origen, destino, cantidad, canal=Operacion.Canal.WEB):
    """
    HU-07 / CU-04: registra el traslado de `cantidad` unidades de `modelo` de
    `origen` a `destino`. Valida permisos y cantidades dentro de una transacción
    para que dos analistas no dejen cantidades negativas al operar a la vez.
    """
    if not analista.has_perm("inventario.registrar_movimiento"):
        raise PermissionDenied("Tu rol no permite registrar movimientos.")
    _validar_cantidad(cantidad)
    if origen.pk == destino.pk:
        raise ValidationError("El origen y el destino deben ser distintos.")
    if not (modelo.activo and origen.activa and destino.activa):
        raise ValidationError("El modelo y las ubicaciones deben estar activos.")

    with transaction.atomic():
        # Bloquea el modelo: los movimientos simultáneos del mismo modelo se procesan de a uno.
        ModeloRecurso.objects.select_for_update().get(pk=modelo.pk)
        disponible = cantidad_en(modelo, origen)
        if cantidad > disponible:
            raise CantidadInsuficiente(disponible, cantidad, origen, modelo)
        return Operacion.objects.create(
            tipo=Operacion.Tipo.MOVIMIENTO,
            modelo=modelo,
            cantidad=cantidad,
            origen=origen,
            destino=destino,
            analista=analista,
            canal=canal,
        )


def registrar_carga_inicial(*, analista, modelo, destino, cantidad):
    """
    Cantidad de partida de un modelo en una ubicación. La usa el comando de carga
    de datos iniciales y la va a reutilizar la importación de Máster, Inventario
    y Shop Floor (HU-16).
    """
    _validar_cantidad(cantidad)
    if not isinstance(destino, Ubicacion):
        raise ValidationError("Destino inválido.")
    return Operacion.objects.create(
        tipo=Operacion.Tipo.CARGA_INICIAL,
        modelo=modelo,
        cantidad=cantidad,
        origen=None,
        destino=destino,
        analista=analista,
    )
