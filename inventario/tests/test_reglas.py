"""Pruebas de las reglas de negocio de la iteración 1 (HU-07, HU-08, HU-12, HU-14, RNF-11, RNF-16)."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from inventario import roles, services
from inventario.models import ModeloRecurso, Operacion, OperacionNoModificable, Ubicacion


def crear_usuario(username, rol):
    usuario = get_user_model().objects.create_user(username=username, password="clave-de-prueba-123")
    usuario.groups.add(Group.objects.get(name=rol))
    return get_user_model().objects.get(pk=usuario.pk)  # recarga para limpiar la caché de permisos


class BaseInventario(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.analista = crear_usuario("analista", roles.ANALISTA)
        cls.bp = crear_usuario("bp", roles.BP)
        cls.interno = Ubicacion.objects.create(nombre="Interno prueba", tipo=Ubicacion.Tipo.WAREHOUSE)
        cls.externo = Ubicacion.objects.create(nombre="Externo prueba", tipo=Ubicacion.Tipo.WAREHOUSE)
        cls.monitor = ModeloRecurso.objects.create(nombre="Monitor prueba", tipo="Monitor")
        services.registrar_carga_inicial(
            analista=cls.analista, modelo=cls.monitor, destino=cls.externo, cantidad=7
        )
        services.registrar_carga_inicial(
            analista=cls.analista, modelo=cls.monitor, destino=cls.interno, cantidad=1
        )

    def mover(self, cantidad, origen=None, destino=None, usuario=None):
        return services.registrar_movimiento(
            analista=usuario or self.analista,
            modelo=self.monitor,
            origen=origen or self.externo,
            destino=destino or self.interno,
            cantidad=cantidad,
        )


class RolesTests(BaseInventario):
    def test_roles_creados_con_sus_permisos(self):
        self.assertTrue(self.analista.has_perm("inventario.registrar_movimiento"))
        self.assertTrue(self.analista.has_perm("inventario.view_operacion"))
        self.assertFalse(self.bp.has_perm("inventario.registrar_movimiento"))
        self.assertTrue(self.bp.has_perm("inventario.view_operacion"))


class MovimientoTests(BaseInventario):
    def test_movimiento_actualiza_origen_y_destino(self):
        """HU-07: el caso del Entregable 1 (7 en Externo y 1 en Interno; se mueve 1)."""
        self.mover(1)
        self.assertEqual(services.cantidad_en(self.monitor, self.externo), 6)
        self.assertEqual(services.cantidad_en(self.monitor, self.interno), 2)

    def test_movimiento_queda_registrado_con_todos_los_datos(self):
        """HU-07 criterio 02: recurso, cantidad, origen, destino, fecha, hora y analista."""
        op = self.mover(2)
        op.refresh_from_db()
        self.assertEqual(op.tipo, Operacion.Tipo.MOVIMIENTO)
        self.assertEqual((op.modelo, op.cantidad, op.origen, op.destino), (self.monitor, 2, self.externo, self.interno))
        self.assertEqual(op.analista, self.analista)
        self.assertIsNotNone(op.fecha)
        self.assertEqual(op.canal, Operacion.Canal.WEB)

    def test_cantidad_insuficiente_no_registra(self):
        """HU-08: si supera lo registrado en el origen, no se registra y se informa lo disponible."""
        antes = Operacion.objects.count()
        with self.assertRaises(services.CantidadInsuficiente) as ctx:
            self.mover(2, origen=self.interno, destino=self.externo)
        self.assertEqual(ctx.exception.disponible, 1)
        self.assertEqual(Operacion.objects.count(), antes)

    def test_se_puede_mover_exactamente_lo_disponible(self):
        self.mover(7)
        self.assertEqual(services.cantidad_en(self.monitor, self.externo), 0)

    def test_origen_igual_destino_se_rechaza(self):
        """HU-07 criterio 04."""
        with self.assertRaises(ValidationError):
            self.mover(1, origen=self.externo, destino=self.externo)

    def test_cantidad_cero_o_negativa_se_rechaza(self):
        for cantidad in (0, -3):
            with self.subTest(cantidad=cantidad), self.assertRaises(ValidationError):
                self.mover(cantidad)

    def test_bp_no_puede_registrar_movimientos(self):
        """RNF-15: el rol BP del área de IT solo consulta."""
        with self.assertRaises(PermissionDenied):
            self.mover(1, usuario=self.bp)

    def test_ubicacion_inactiva_se_rechaza(self):
        self.interno.activa = False
        self.interno.save()
        with self.assertRaises(ValidationError):
            self.mover(1)


class DisponibilidadTests(BaseInventario):
    def test_disponibilidad_se_calcula_desde_operaciones(self):
        """RNF-11: las cantidades coinciden siempre con la suma de las operaciones."""
        self.mover(3)
        self.mover(1, origen=self.interno, destino=self.externo)
        tabla = services.disponibilidad()
        self.assertEqual(tabla[(self.monitor.pk, self.externo.pk)], 5)
        self.assertEqual(tabla[(self.monitor.pk, self.interno.pk)], 3)
        total = sum(v for (m, _), v in tabla.items() if m == self.monitor.pk)
        self.assertEqual(total, 8)  # un movimiento no crea ni elimina unidades


class HistorialInmutableTests(BaseInventario):
    def test_operacion_no_se_puede_modificar(self):
        """RNF-16: el historial no se puede editar."""
        op = self.mover(1)
        op.cantidad = 5
        with self.assertRaises(OperacionNoModificable):
            op.save()

    def test_operacion_no_se_puede_eliminar(self):
        op = self.mover(1)
        with self.assertRaises(OperacionNoModificable):
            op.delete()

    def test_error_se_corrige_con_movimiento_inverso(self):
        self.mover(2)
        self.mover(2, origen=self.interno, destino=self.externo)
        self.assertEqual(services.cantidad_en(self.monitor, self.externo), 7)
        self.assertEqual(Operacion.objects.filter(tipo=Operacion.Tipo.MOVIMIENTO).count(), 2)

    def test_restricciones_de_base_de_datos(self):
        """La base de datos también rechaza cantidad cero y origen igual a destino."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Operacion.objects.create(
                tipo=Operacion.Tipo.MOVIMIENTO, modelo=self.monitor, cantidad=0,
                origen=self.externo, destino=self.interno, analista=self.analista,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Operacion.objects.create(
                tipo=Operacion.Tipo.MOVIMIENTO, modelo=self.monitor, cantidad=1,
                origen=self.externo, destino=self.externo, analista=self.analista,
            )
