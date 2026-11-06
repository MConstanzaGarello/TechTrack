"""
Modelo de datos de la iteración 1.

Regla central (Entregable 2, RNF-11): las cantidades NO se guardan en ninguna
tabla. Se calculan siempre a partir de las operaciones registradas, por eso no
existe un campo "cantidad" editable por ubicación.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Ubicacion(models.Model):
    class Tipo(models.TextChoices):
        WAREHOUSE = "warehouse", "Warehouse"
        SECTOR = "sector", "Sector en uso"
        PLANTA = "planta", "Otra planta"

    nombre = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo", "nombre"]
        verbose_name = "ubicación"
        verbose_name_plural = "ubicaciones"

    def __str__(self):
        return self.nombre


class ModeloRecurso(models.Model):
    """Modelo de accesorio que se controla por cantidad (monitor, headset, kit, etc.)."""

    nombre = models.CharField(max_length=120, unique=True)
    tipo = models.CharField(max_length=60, help_text="Por ejemplo: Monitor, Headset, Docking.")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo", "nombre"]
        verbose_name = "modelo de recurso"
        verbose_name_plural = "modelos de recurso"

    def __str__(self):
        return self.nombre


class OperacionNoModificable(Exception):
    """Se lanza al intentar editar o borrar una operación del historial."""


class Operacion(models.Model):
    """Registro inmutable de cada cambio en las cantidades (RNF-16)."""

    class Tipo(models.TextChoices):
        CARGA_INICIAL = "carga_inicial", "Carga inicial"
        MOVIMIENTO = "movimiento", "Movimiento"

    class Canal(models.TextChoices):
        WEB = "web", "Web"

    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    modelo = models.ForeignKey(ModeloRecurso, on_delete=models.PROTECT, related_name="operaciones")
    cantidad = models.PositiveIntegerField()
    origen = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, null=True, blank=True, related_name="salidas"
    )
    destino = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name="entradas")
    analista = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="operaciones"
    )
    canal = models.CharField(max_length=10, choices=Canal.choices, default=Canal.WEB)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "operación"
        verbose_name_plural = "operaciones"
        permissions = [("registrar_movimiento", "Puede registrar movimientos de recursos")]
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="operacion_cantidad_positiva"),
            models.CheckConstraint(
                condition=~models.Q(origen=models.F("destino")), name="operacion_origen_distinto_destino"
            ),
            models.CheckConstraint(
                condition=models.Q(tipo="carga_inicial", origen__isnull=True)
                | models.Q(tipo="movimiento", origen__isnull=False),
                name="operacion_origen_segun_tipo",
            ),
        ]

    def __str__(self):
        origen = self.origen or "—"
        return f"{self.get_tipo_display()}: {self.cantidad} × {self.modelo} ({origen} → {self.destino})"

    def clean(self):
        if self.tipo == self.Tipo.MOVIMIENTO and self.origen_id and self.origen_id == self.destino_id:
            raise ValidationError("El origen y el destino deben ser distintos.")

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise OperacionNoModificable(
                "Las operaciones no se modifican. Para corregir un error, registrá un movimiento inverso."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise OperacionNoModificable(
            "Las operaciones no se eliminan. Para corregir un error, registrá un movimiento inverso."
        )
