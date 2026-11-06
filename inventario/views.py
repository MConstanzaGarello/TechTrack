from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import services
from .forms import FiltroDisponibilidadForm, MovimientoForm
from .models import ModeloRecurso, Operacion, Ubicacion

CONSULTA = "inventario.view_operacion"


def inicio(request):
    """Panel de inicio. Sin sesión, la raíz lleva directo al inicio de sesión."""
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.has_perm(CONSULTA):
        return acceso_denegado(request)

    cantidades = services.disponibilidad()
    tipo_de = dict(Ubicacion.objects.values_list("pk", "tipo"))
    por_tipo = {Ubicacion.Tipo.WAREHOUSE: 0, Ubicacion.Tipo.SECTOR: 0, Ubicacion.Tipo.PLANTA: 0}
    en_warehouse_por_modelo = {}
    for (modelo_id, ubicacion_id), cantidad in cantidades.items():
        tipo = tipo_de.get(ubicacion_id)
        if tipo in por_tipo:
            por_tipo[tipo] += cantidad
        if tipo == Ubicacion.Tipo.WAREHOUSE:
            en_warehouse_por_modelo[modelo_id] = en_warehouse_por_modelo.get(modelo_id, 0) + cantidad
    modelos = ModeloRecurso.objects.filter(activo=True)
    sin_stock = [m for m in modelos if en_warehouse_por_modelo.get(m.pk, 0) <= 0]

    movimientos = Operacion.objects.filter(tipo=Operacion.Tipo.MOVIMIENTO)
    contexto = {
        "total_modelos": modelos.count(),
        "en_uso": por_tipo[Ubicacion.Tipo.SECTOR],
        "en_warehouse": por_tipo[Ubicacion.Tipo.WAREHOUSE],
        "sin_stock": len(sin_stock),
        "sin_stock_lista": sin_stock[:6],
        "movimientos_hoy": movimientos.filter(fecha__date=timezone.localdate()).count(),
        "ultimas": Operacion.objects.select_related("modelo", "origen", "destino", "analista")[:7],
        "hoy": timezone.localtime(),
    }
    return render(request, "inventario/inicio.html", contexto)


@login_required
@permission_required(CONSULTA, raise_exception=True)
def disponibilidad(request):
    """HU-12 (versión básica): cantidades por modelo y ubicación, calculadas desde las operaciones."""
    filtro = FiltroDisponibilidadForm(request.GET or None)
    modelos = ModeloRecurso.objects.filter(activo=True)
    orden_tipo = Case(
        When(tipo=Ubicacion.Tipo.WAREHOUSE, then=Value(0)),
        When(tipo=Ubicacion.Tipo.SECTOR, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    ubicaciones = Ubicacion.objects.filter(activa=True).order_by(orden_tipo, "nombre")
    if filtro.is_valid():
        texto = filtro.cleaned_data.get("texto")
        if texto:
            modelos = modelos.filter(Q(nombre__icontains=texto) | Q(tipo__icontains=texto))
        if filtro.cleaned_data.get("ubicacion"):
            ubicaciones = ubicaciones.filter(pk=filtro.cleaned_data["ubicacion"].pk)

    cantidades = services.disponibilidad()
    ubicaciones = list(ubicaciones)
    # Encabezado agrupado como en la planilla Inventario: Warehouse / En uso / Plantas.
    nombres_grupo = {
        Ubicacion.Tipo.WAREHOUSE: ("Warehouse", ""),
        Ubicacion.Tipo.SECTOR: ("En uso", "grupo-uso"),
        Ubicacion.Tipo.PLANTA: ("Transferido a plantas", "grupo-planta"),
    }
    grupos, inicio_grupo = [], set()
    for i, u in enumerate(ubicaciones):
        if not grupos or grupos[-1]["tipo"] != u.tipo:
            nombre, clase = nombres_grupo.get(u.tipo, (u.get_tipo_display(), ""))
            grupos.append({"tipo": u.tipo, "nombre": nombre, "clase": clase, "columnas": 0})
            inicio_grupo.add(i)
        grupos[-1]["columnas"] += 1
    columnas = [{"ubicacion": u, "sep": i in inicio_grupo} for i, u in enumerate(ubicaciones)]
    filas = []
    for modelo in modelos:
        valores = [cantidades.get((modelo.pk, u.pk), 0) for u in ubicaciones]
        celdas = [{"valor": v, "sep": i in inicio_grupo} for i, v in enumerate(valores)]
        filas.append({"modelo": modelo, "celdas": celdas, "total": sum(valores)})

    contexto = {
        "filtro": filtro,
        "ubicaciones": ubicaciones,
        "columnas": columnas,
        "grupos": grupos,
        "filas": filas,
    }
    return render(request, "inventario/disponibilidad.html", contexto)


@login_required
@permission_required("inventario.registrar_movimiento", raise_exception=True)
def nuevo_movimiento(request):
    """HU-07 y HU-08: registrar un movimiento validado en el servidor."""
    form = MovimientoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        try:
            operacion = services.registrar_movimiento(
                analista=request.user,
                modelo=datos["modelo"],
                origen=datos["origen"],
                destino=datos["destino"],
                cantidad=datos["cantidad"],
            )
        except services.CantidadInsuficiente as error:
            form.add_error("cantidad", error.messages[0])
            messages.error(request, "El movimiento no se registró.")
        except ValidationError as error:
            form.add_error(None, error.messages[0])
            messages.error(request, "El movimiento no se registró.")
        else:
            messages.success(
                request,
                f"Movimiento registrado: {operacion.cantidad} × {operacion.modelo} "
                f"de {operacion.origen} a {operacion.destino}.",
            )
            return redirect("inventario:historial_modelo", modelo_id=operacion.modelo_id)
    elif request.method == "POST":
        messages.error(request, "Revisá los datos marcados en el formulario.")
    return render(request, "inventario/movimiento_form.html", {"form": form})


@login_required
@permission_required(CONSULTA, raise_exception=True)
def historial(request, modelo_id=None):
    """HU-14 (versión básica): historial de solo lectura, general o por modelo."""
    modelo = get_object_or_404(ModeloRecurso, pk=modelo_id) if modelo_id else None
    operaciones = Operacion.objects.select_related("modelo", "origen", "destino", "analista")
    if modelo:
        operaciones = operaciones.filter(modelo=modelo)
    pagina = Paginator(operaciones, 50).get_page(request.GET.get("pagina"))
    contexto = {"modelo": modelo, "pagina": pagina, "modelos": ModeloRecurso.objects.all()}
    return render(request, "inventario/historial.html", contexto)


def acceso_denegado(request, exception=None):
    return render(request, "403.html", status=403)


def no_encontrado(request, exception=None):
    return render(request, "404.html", status=404)
