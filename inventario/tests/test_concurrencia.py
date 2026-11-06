"""
RNF-08: dos analistas que mueven el mismo modelo al mismo tiempo no pueden dejar
cantidades negativas. Esta prueba necesita PostgreSQL (el motor del entorno
desplegado); con SQLite se omite porque SQLite no admite escrituras simultáneas.
"""
import threading
import unittest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection, connections
from django.test import TransactionTestCase

from inventario import roles, services
from inventario.models import ModeloRecurso, Operacion, Ubicacion


@unittest.skipUnless(connection.vendor == "postgresql", "Requiere PostgreSQL")
class ConcurrenciaTests(TransactionTestCase):
    def setUp(self):
        roles.asegurar_roles()
        usuario = get_user_model().objects.create_user("analista_c", password="clave-de-prueba-123")
        usuario.groups.add(Group.objects.get(name=roles.ANALISTA))
        self.analista = get_user_model().objects.get(pk=usuario.pk)
        self.origen = Ubicacion.objects.create(nombre="Origen C", tipo=Ubicacion.Tipo.WAREHOUSE)
        self.destino = Ubicacion.objects.create(nombre="Destino C", tipo=Ubicacion.Tipo.WAREHOUSE)
        self.modelo = ModeloRecurso.objects.create(nombre="Modelo C", tipo="Monitor")
        services.registrar_carga_inicial(
            analista=self.analista, modelo=self.modelo, destino=self.origen, cantidad=5
        )

    def test_movimientos_simultaneos_no_dejan_negativos(self):
        barrera = threading.Barrier(4)
        resultados = []

        def intentar():
            try:
                barrera.wait()
                services.registrar_movimiento(
                    analista=self.analista, modelo=self.modelo, origen=self.origen, destino=self.destino, cantidad=2
                )
                resultados.append("ok")
            except services.CantidadInsuficiente:
                resultados.append("rechazado")
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=intentar) for _ in range(4)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        # Hay 5 unidades: solo dos movimientos de 2 pueden registrarse.
        self.assertEqual(resultados.count("ok"), 2)
        self.assertEqual(resultados.count("rechazado"), 2)
        self.assertEqual(services.cantidad_en(self.modelo, self.origen), 1)
        self.assertEqual(Operacion.objects.filter(tipo=Operacion.Tipo.MOVIMIENTO).count(), 2)
