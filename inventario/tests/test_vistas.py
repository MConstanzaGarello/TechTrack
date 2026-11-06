"""Pruebas de las pantallas: autenticación, roles y flujo completo de un movimiento."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from inventario import services
from inventario.models import Operacion

from .test_reglas import BaseInventario


class AccesoTests(BaseInventario):
    def test_sin_sesion_la_raiz_lleva_al_login(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertRedirects(respuesta, reverse("login"))
        self.assertContains(self.client.get(reverse("login")), "Iniciar sesión")

    def test_panel_de_inicio_con_sesion(self):
        self.client.force_login(self.analista)
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "Panel de control")
        self.assertContains(respuesta, "Registrar movimiento")
        self.client.force_login(self.bp)
        self.assertNotContains(self.client.get(reverse("inicio")), reverse("inventario:nuevo_movimiento"))

    def test_sin_sesion_no_se_ven_datos(self):
        """RNF-14: las pantallas con datos redirigen al inicio de sesión."""
        for nombre in ("inventario:disponibilidad", "inventario:historial", "inventario:nuevo_movimiento"):
            with self.subTest(nombre=nombre):
                respuesta = self.client.get(reverse(nombre))
                self.assertEqual(respuesta.status_code, 302)
                self.assertIn(reverse("login"), respuesta["Location"])

    def test_bp_consulta_pero_no_registra(self):
        """RNF-15: el BP ve disponibilidad e historial; el formulario le devuelve 403 aun por URL directa."""
        self.client.force_login(self.bp)
        self.assertEqual(self.client.get(reverse("inventario:disponibilidad")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventario:historial")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventario:nuevo_movimiento")).status_code, 403)
        respuesta = self.client.post(
            reverse("inventario:nuevo_movimiento"),
            {"modelo": self.monitor.pk, "origen": self.externo.pk, "destino": self.interno.pk, "cantidad": 1},
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(Operacion.objects.filter(tipo=Operacion.Tipo.MOVIMIENTO).count(), 0)

    def test_bp_no_ve_el_enlace_para_registrar(self):
        self.client.force_login(self.bp)
        respuesta = self.client.get(reverse("inventario:disponibilidad"))
        self.assertNotContains(respuesta, reverse("inventario:nuevo_movimiento"))

    def test_usuario_sin_rol_no_ve_datos(self):
        from django.contrib.auth import get_user_model

        sin_rol = get_user_model().objects.create_user("sinrol", password="clave-de-prueba-123")
        self.client.force_login(sin_rol)
        self.assertEqual(self.client.get(reverse("inventario:disponibilidad")).status_code, 403)


class FlujoMovimientoTests(BaseInventario):
    def setUp(self):
        self.client.force_login(self.analista)

    def test_flujo_completo_de_un_movimiento(self):
        """De punta a punta: formulario → operación → historial → disponibilidad."""
        respuesta = self.client.post(
            reverse("inventario:nuevo_movimiento"),
            {"modelo": self.monitor.pk, "origen": self.externo.pk, "destino": self.interno.pk, "cantidad": 1},
            follow=True,
        )
        self.assertRedirects(respuesta, reverse("inventario:historial_modelo", args=[self.monitor.pk]))
        self.assertContains(respuesta, "Movimiento registrado")
        self.assertContains(respuesta, "analista")
        disponibilidad = self.client.get(reverse("inventario:disponibilidad"))
        filas = disponibilidad.context["filas"]
        ubicaciones = disponibilidad.context["ubicaciones"]
        celdas = dict(zip([u.pk for u in ubicaciones], [c["valor"] for c in filas[0]["celdas"]]))
        self.assertEqual(celdas[self.externo.pk], 6)
        self.assertEqual(celdas[self.interno.pk], 2)

    def test_formulario_muestra_error_si_no_alcanza(self):
        respuesta = self.client.post(
            reverse("inventario:nuevo_movimiento"),
            {"modelo": self.monitor.pk, "origen": self.interno.pk, "destino": self.externo.pk, "cantidad": 5},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "hay 1 registrada")
        self.assertContains(respuesta, "El movimiento no se registró")
        self.assertEqual(services.cantidad_en(self.monitor, self.interno), 1)

    def test_formulario_rechaza_origen_igual_destino(self):
        respuesta = self.client.post(
            reverse("inventario:nuevo_movimiento"),
            {"modelo": self.monitor.pk, "origen": self.interno.pk, "destino": self.interno.pk, "cantidad": 1},
        )
        self.assertContains(respuesta, "El destino debe ser distinto del origen")
        self.assertEqual(Operacion.objects.filter(tipo=Operacion.Tipo.MOVIMIENTO).count(), 0)

    def test_formulario_rechaza_cantidad_invalida(self):
        for cantidad in ("0", "-1", "abc"):
            with self.subTest(cantidad=cantidad):
                respuesta = self.client.post(
                    reverse("inventario:nuevo_movimiento"),
                    {"modelo": self.monitor.pk, "origen": self.externo.pk, "destino": self.interno.pk, "cantidad": cantidad},
                )
                self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Operacion.objects.filter(tipo=Operacion.Tipo.MOVIMIENTO).count(), 0)

    def test_historial_no_ofrece_editar_ni_borrar(self):
        self.client.post(
            reverse("inventario:nuevo_movimiento"),
            {"modelo": self.monitor.pk, "origen": self.externo.pk, "destino": self.interno.pk, "cantidad": 1},
        )
        respuesta = self.client.get(reverse("inventario:historial"))
        self.assertNotContains(respuesta, "Editar")
        self.assertNotContains(respuesta, "Eliminar")


class CargarDemoTests(TestCase):
    def test_carga_datos_iniciales_y_no_duplica(self):
        call_command("cargar_demo", password="Demo-TechTrack-2026", stdout=StringIO())
        cantidad = Operacion.objects.count()
        self.assertGreater(cantidad, 0)
        self.assertTrue(all(op.tipo == Operacion.Tipo.CARGA_INICIAL for op in Operacion.objects.all()))
        call_command("cargar_demo", password="Demo-TechTrack-2026", stdout=StringIO())
        self.assertEqual(Operacion.objects.count(), cantidad)

    def test_exige_contrasena(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("cargar_demo", stdout=StringIO())
