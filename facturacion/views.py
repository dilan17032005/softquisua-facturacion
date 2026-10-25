"""Vistas del módulo Facturación."""
from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from productos.models import Producto

from .forms import DetalleFacturaFormSet, FacturaForm
from .models import DetalleFactura, Factura


def inicio(request):
    """Lista facturas con búsqueda por número, cliente o NIT."""
    busqueda = request.GET.get("q", "").strip()
    facturas = Factura.objects.select_related("cliente").all()
    if busqueda:
        filtros = Q(cliente__nombre__icontains=busqueda) | Q(cliente__nit__icontains=busqueda)
        if busqueda.isdigit():
            filtros |= Q(pk=int(busqueda))
        facturas = facturas.filter(filtros)

    paginator = Paginator(facturas, 15)
    pagina = paginator.get_page(request.GET.get("page"))
    total_historico = sum((f.total for f in facturas), Decimal("0.00"))
    return render(
        request,
        "facturacion/inicio.html",
        {
            "facturas": pagina,
            "busqueda": busqueda,
            "cantidad_facturas": facturas.count(),
            "total_historico": total_historico,
        },
    )


def detalle(request, pk):
    """Muestra el comprobante y sus líneas."""
    factura = get_object_or_404(
        Factura.objects.select_related("cliente").prefetch_related("detalles__producto"), pk=pk
    )
    return render(request, "facturacion/detalle.html", {"factura": factura})


def nueva(request):
    """Emite una factura y descuenta el stock en una única transacción."""
    if request.method == "POST":
        formulario = FacturaForm(request.POST)
        formulario_detalles = DetalleFacturaFormSet(request.POST, prefix="detalles")
        error_stock = None

        if formulario.is_valid() and formulario_detalles.is_valid():
            cantidades = defaultdict(int)
            for linea in formulario_detalles.cleaned_data:
                if linea.get("producto") and linea.get("cantidad") and not linea.get("DELETE", False):
                    cantidades[linea["producto"].pk] += linea["cantidad"]

            try:
                with transaction.atomic():
                    # Bloquear en orden estable reduce el riesgo de bloqueos cruzados.
                    productos_bloqueados = {
                        producto.pk: producto
                        for producto in Producto.objects.select_for_update()
                        .filter(pk__in=sorted(cantidades))
                        .order_by("pk")
                    }

                    for producto_id, cantidad in cantidades.items():
                        producto = productos_bloqueados.get(producto_id)
                        if producto is None:
                            raise ValueError("Uno de los productos seleccionados ya no existe.")
                        if cantidad > producto.stock:
                            raise ValueError(
                                f'Stock insuficiente para "{producto.nombre}". '
                                f"Disponible: {producto.stock}; solicitado: {cantidad}. No se guardó la factura."
                            )

                    factura = Factura.objects.create(cliente=formulario.cleaned_data["cliente"])
                    total = Decimal("0.00")
                    for producto_id, cantidad in cantidades.items():
                        producto = productos_bloqueados[producto_id]
                        precio = producto.precio
                        DetalleFactura.objects.create(
                            factura=factura,
                            producto=producto,
                            cantidad=cantidad,
                            precio_unitario=precio,
                        )
                        total += precio * cantidad
                        producto.stock -= cantidad
                        producto.save(update_fields=["stock"])

                    factura.total = total
                    factura.save(update_fields=["total"])

            except ValueError as error:
                error_stock = str(error)
            else:
                messages.success(request, f"Factura N.º {factura.pk} emitida correctamente.")
                return redirect(reverse("facturacion:detalle", kwargs={"pk": factura.pk}))
        return render(
            request,
            "facturacion/nueva.html",
            {
                "formulario": formulario,
                "formulario_detalles": formulario_detalles,
                "error_stock": error_stock,
                "productos_json": _catalogo_json(),
            },
        )

    return render(
        request,
        "facturacion/nueva.html",
        {
            "formulario": FacturaForm(),
            "formulario_detalles": DetalleFacturaFormSet(prefix="detalles"),
            "error_stock": None,
            "productos_json": _catalogo_json(),
        },
    )


def _catalogo_json():
    """Datos mínimos del catálogo para mostrar precios estimados en el formulario."""
    return list(Producto.objects.order_by("nombre").values("id", "nombre", "precio", "stock"))
