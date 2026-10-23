# ALVIÑA POS — 19.0.1.1.1

El ticket se sincroniza por el mecanismo existente de Odoo. En modo
**Boleta/Factura al final del ticket**, los medios de pago no fuerzan una factura
durante esa sincronización. Al elegir Boleta/Factura en la pantalla del recibo,
se consulta DNI/RUC, se confirma el cliente y se procesa el comprobante en Odoo.
El pedido facturado queda fuera del cron existente por tener `account_move`;
los tickets ordinarios quedan fuera por no tener `to_invoice`.

En **Ajustes → Usuarios y empresas → Empresas → compañía peruana → ALVIÑA POS**,
seleccionar ese modo y configurar JSON.PE con su token real. Es el valor inicial
en instalaciones nuevas; una actualización conserva el modo que ya estaba
guardado. **Pendiente** conserva la integración anterior y no ejecuta ningún cron.
No se cambia el método de sincronización ni se crea otra venta o pago.

La selección de diario respeta el método existente `_get_journal` de
`alvinha_point_of_sale` cuando está instalado; permite su diario específico de
boletas. Sin ese módulo utiliza el diario de facturas estándar del POS. Los
diarios deben pertenecer a la compañía real y admitir los documentos peruanos.
El diario de apuntes de pagos POS debe ser distinto de un diario de comprobantes
que exige tipo de documento, según la configuración contable real.

Dependencias: `point_of_sale`, `l10n_pe`, `requests`. Las consultas se hacen en el
servidor. El token tiene acceso restringido y no se exporta al navegador; se puede
usar la variable de entorno `ALVINA_JSONPE_TOKEN` o el campo de la compañía.

No incorpora un emisor electrónico independiente ni certifica aceptación
SUNAT/OSE. Conserva la integración EDI instalada. No se realiza ninguna consulta
real al proveedor ni envío SUNAT en las pruebas.

Ver [revisión y actualización](../ZIP_REVIEW_2026-10-23.md) para la aplicación,
las pruebas y los límites de compatibilidad con Enterprise.
