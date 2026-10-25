"""Pruebas del mÃ³dulo FacturaciÃ³n. Ejecutar: python manage.py test facturacion"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente
from productos.models import Producto

from .models import DetalleFactura, Factura


class FacturacionTests(TestCase):
    def setUp(self):
        usuario = get_user_model().objects.create_user("prueba", password="x")
        self.client.force_login(usuario)
        self.cliente = Cliente.objects.create(nombre="Cliente Factura", nit="999")
        self.producto = Producto.objects.create(nombre="Cemento", precio=Decimal("48.50"), stock=10)

    def test_la_lista_muestra_las_facturas(self):
        Factura.objects.create(cliente=self.cliente, total=100)
        respuesta = self.client.get(reverse("facturacion:inicio"))
        self.assertContains(respuesta, "Cliente Factura")
        self.assertContains(respuesta, "Nueva factura")

    def test_detalle_muestra_datos_cliente_producto_y_total(self):
        factura = Factura.objects.create(cliente=self.cliente, total=Decimal("97.00"))
        DetalleFactura.objects.create(
            factura=factura, producto=self.producto, cantidad=2, precio_unitario=Decimal("48.50")
        )
        respuesta = self.client.get(reverse("facturacion:detalle", args=[factura.pk]))
        self.assertContains(respuesta, "Cliente Factura")
        self.assertContains(respuesta, "999")
        self.assertContains(respuesta, "Cemento")
        self.assertContains(respuesta, "97,00")

    def test_emitir_factura_calcula_total_y_descuenta_stock(self):
        respuesta = self.client.post(
            reverse("facturacion:nueva"),
            {
                "cliente": self.cliente.pk,
                "detalles-TOTAL_FORMS": "1",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "0",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": self.producto.pk,
                "detalles-0-cantidad": "3",
                "detalles-0-DELETE": "",
            },
        )
        factura = Factura.objects.get()
        self.producto.refresh_from_db()
        self.assertRedirects(respuesta, reverse("facturacion:detalle", args=[factura.pk]))
        self.assertEqual(factura.total, Decimal("145.50"))
        self.assertEqual(factura.detalles.count(), 1)
        self.assertEqual(factura.detalles.get().precio_unitario, Decimal("48.50"))
        self.assertEqual(self.producto.stock, 7)

    def test_no_permite_vender_mas_stock_y_no_guarda_nada(self):
        respuesta = self.client.post(
            reverse("facturacion:nueva"),
            {
                "cliente": self.cliente.pk,
                "detalles-TOTAL_FORMS": "1",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "0",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": self.producto.pk,
                "detalles-0-cantidad": "11",
                "detalles-0-DELETE": "",
            },
        )
        self.producto.refresh_from_db()
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Stock insuficiente")
        self.assertEqual(Factura.objects.count(), 0)
        self.assertEqual(DetalleFactura.objects.count(), 0)
        self.assertEqual(self.producto.stock, 10)

    def test_no_emite_factura_sin_productos(self):
        respuesta = self.client.post(
            reverse("facturacion:nueva"),
            {
                "cliente": self.cliente.pk,
                "detalles-TOTAL_FORMS": "1",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "0",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": "",
                "detalles-0-cantidad": "",
                "detalles-0-DELETE": "",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Agrega al menos un producto")
        self.assertEqual(Factura.objects.count(), 0)
