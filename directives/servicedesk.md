# ServiceDesk (ERP de servicio técnico)

## Objetivo
ERP propio, escrito desde cero, para empresas de servicio técnico: clientes, partes de trabajo, firma digital, facturas y portal de cliente.

## Entradas
- API HTTP (FastAPI). Variable opcional `SERVICEDESK_DB` (por defecto `.tmp/servicedesk.db`).

## Herramientas
- `execution/servicedesk/app.py`. Arranque: `uvicorn execution.servicedesk.app:app`. Tests: `python -m pytest tests`.

## Flujo de un parte
abierto → en_curso → (firma obligatoria) terminado → facturado (genera factura `AAAA-NNNNN`, IVA 21 % por defecto).

## Salidas
- JSON por endpoint; factura imprimible en `/invoices/{id}/print`; portal en `/portal/{token}`.

## Casos extremos / pendiente
- Sin autenticación de operadores todavía (el portal usa token no adivinable por cliente).
- La numeración de facturas usa COUNT(*): no admite borrados; migrar a contador dedicado.
- Interfaz web en `/` (Jinja2 + formularios; firma con canvas). Rutas `/ui/*` solo redirigen a la API y devuelven errores por query `?error=`.
- Pendiente: PDF real, albaranes, auth, adjuntos.
