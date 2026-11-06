from django import forms

from .models import ModeloRecurso, Ubicacion


class MovimientoForm(forms.Form):
    """Formulario de HU-07. Las reglas de negocio se validan en services.registrar_movimiento."""

    modelo = forms.ModelChoiceField(
        queryset=ModeloRecurso.objects.filter(activo=True), label="Modelo", empty_label="Elegí un modelo"
    )
    origen = forms.ModelChoiceField(
        queryset=Ubicacion.objects.filter(activa=True), label="Ubicación de origen", empty_label="Elegí el origen"
    )
    destino = forms.ModelChoiceField(
        queryset=Ubicacion.objects.filter(activa=True), label="Ubicación de destino", empty_label="Elegí el destino"
    )
    cantidad = forms.IntegerField(label="Cantidad", min_value=1, initial=1)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            clase = "form-select" if isinstance(campo, forms.ModelChoiceField) else "form-control"
            campo.widget.attrs["class"] = clase

    def clean(self):
        datos = super().clean()
        origen, destino = datos.get("origen"), datos.get("destino")
        if origen and destino and origen == destino:
            self.add_error("destino", "El destino debe ser distinto del origen.")
        return datos


class FiltroDisponibilidadForm(forms.Form):
    texto = forms.CharField(label="Modelo o tipo", required=False)
    ubicacion = forms.ModelChoiceField(
        queryset=Ubicacion.objects.filter(activa=True), label="Ubicación", required=False, empty_label="Todas"
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        self.fields["texto"].widget.attrs.update({"class": "form-control", "placeholder": "Ej.: Monitor"})
        self.fields["ubicacion"].widget.attrs["class"] = "form-select"
