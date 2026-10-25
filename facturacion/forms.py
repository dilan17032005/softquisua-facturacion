"""Formularios del módulo de facturación."""
from django import forms
from django.forms import BaseFormSet, formset_factory

from clientes.models import Cliente
from productos.models import Producto


class FacturaForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        label="Cliente",
        empty_label="Selecciona un cliente",
        widget=forms.Select(attrs={"class": "form-select", "required": True}),
    )


class ProductoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.nombre} — Bs {obj.precio:.2f} — Stock: {obj.stock}"


class DetalleFacturaForm(forms.Form):
    producto = ProductoChoiceField(
        queryset=Producto.objects.all(),
        label="Producto",
        required=False,
        empty_label="Selecciona un producto",
        widget=forms.Select(attrs={"class": "form-select producto-select"}),
    )
    cantidad = forms.IntegerField(
        label="Cantidad",
        required=False,
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": "form-control cantidad-input", "min": "1", "step": "1", "placeholder": "1"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get("producto")
        cantidad = cleaned_data.get("cantidad")
        if producto and cantidad is None:
            self.add_error("cantidad", "Indica una cantidad válida para este producto.")
        elif cantidad is not None and not producto:
            self.add_error("producto", "Selecciona el producto correspondiente.")
        return cleaned_data


class BaseDetalleFacturaFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        hay_detalle = False
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            data = getattr(form, "cleaned_data", {})
            if data.get("producto") and data.get("cantidad"):
                hay_detalle = True
                break

        if not hay_detalle:
            raise forms.ValidationError("Agrega al menos un producto a la factura.")


DetalleFacturaFormSet = formset_factory(
    DetalleFacturaForm,
    formset=BaseDetalleFacturaFormSet,
    extra=1,
    can_delete=True,
)
