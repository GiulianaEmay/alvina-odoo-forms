# Integrar el abastecimiento con la OV nativa y separar los movimientos QR

La presencia de `account_inter_company_rules` impedía guardar el abastecimiento
activo. Los requerimientos anteriores quedaban sin OC/OV y Logística no recibía
pedidos. El adaptador crea una sola OC y enlaza la OV generada por Odoo, validando
identidad, líneas, precios y responsable dentro de una transacción que se revierte
si no produce una única pareja válida. No cambia configuraciones globales.

Añade el envío explícito e idempotente de requerimientos anteriores pendientes,
separa el campo de movimientos de sucursales del campo QR con migración protectora
y conserva las dos confirmaciones operativas: despacho y recepción real.

Validación, límites y aplicación: TESTING.md y RELEASE_2026-10-23.md. El motor
Enterprise no viene en el ZIP: su contrato ORM se prueba sobre Community, pero la
regla y el usuario reales aún necesitan una comprobación en la copia instalada.
No se ha desplegado ni cambiado producción.
