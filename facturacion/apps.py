from django.apps import AppConfig


class FacturacionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "facturacion"
    verbose_name = "Facturación"

    # ── Datos para el menú y el tablero. Estos SÍ los cambias tú ──────────
    responsable = "Sin asignar"          # ← escribe tu nombre
    estado = "listo"           # ← cámbialo a "listo" al terminar
    icono = "bi-receipt"
    descripcion = "Emisión de facturas: cliente, productos, total y descuento de stock."
    url_inicio = "facturacion:inicio"
