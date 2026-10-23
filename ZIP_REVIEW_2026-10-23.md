# Revisión del ZIP antes de actualizar — 23/10/2026

Archivo recibido: `alvinha-cybe (2).zip`, SHA-256
`2d27d1ad995e79c5410f88fc67e78ebb9d9b5d8a6eefc20402706f7f501e223d`.
Se analizaron 124 archivos Python, 57 XML y los manifests/imports/assets de los
módulos relevantes. No se detectaron errores de sintaxis Python/XML ni archivos
`data` ausentes. El ZIP original se conserva sin modificaciones.

## Resultado de Requerimientos de sucursales

Los 54 archivos requeridos coinciden byte a byte con `main`, versión
**19.0.3.1.0**. Las dependencias y el manifest están completos.

Solo sobra esta copia idéntica, anidada por error:

```
alvina_branch_requisition/migrations/19.0.2.0.0/19.0.3.1.0/pre-migration.py
```

Se retiró únicamente esa copia en el paquete revisado. Odoo no la ejecuta desde
esa ubicación anidada; no era un fallo de sintaxis ni la causa de una caída.
Se conserva la migración correcta:

```
alvina_branch_requisition/migrations/19.0.3.1.0/pre-migration.py
```

Conservar también las otras dos carpetas de versión y sus scripts originales.
No se modificó el código de negocio de sucursales en esta revisión.

## Resultado de POS Boleta/Factura

El ZIP contiene 19.0.1.1.0; la corrección es **19.0.1.1.1**.

- La selección/validación de diario ahora respeta `_get_journal` del
  `alvinha_point_of_sale` proporcionado. Su diario específico de boletas ya no se
  rechaza por ser distinto del diario general de facturas.
- En modo **Boleta/Factura al final del ticket**, sincronizar un ticket nuevo no
  genera automáticamente una factura por una marca del medio de pago. Se conserva
  el guardado y los pagos normales. Una factura ordinaria ya existente conserva
  sus marcas al resincronizarse.
- Al confirmar Boleta/Factura, el modo inmediato procesa el comprobante con el
  mismo pedido/pago. El cron existente exige `to_invoice=True` y ausencia de
  `account_move`: los tickets ordinarios sin esa marca y los pedidos ya facturados
  quedan fuera de esa selección.
- Se corrigió el test de vencimiento: Odoo 19 ignora escrituras a `create_date`.
  La prueba ahora avanza el reloj, sin dar acceso al modelo temporal al cajero.
- Se mantienen los contratos JSON.PE, la protección del token, la prevención de
  duplicados, el vínculo al pedido y los estados de fallo reales.

Los archivos del sincronizador, `alvinha_point_of_sale` y los otros módulos
privados se conservan byte a byte. En el archivo de validación del ZIP existe un
`await syncAllOrders`; no se añadió ni sustituyó un trabajador de sincronización.
La operación Boleta/Factura exige que ese pedido ya esté sincronizado.

## Validación ejecutada

**256 pruebas Odoo juntas: 191 sucursales + 23 POS + 42 QR; cero fallos, cero
errores y ninguna omisión.** Base local desechable `alvina_zip_preflight_20261023`.
Log: `/tmp/alvina-zip-release-final-256-tests.log`.

Las pruebas POS adicionales pagan una venta con sus líneas y pago reales,
contabilizan boleta/factura, verifican diario, importe y descarga, impiden otra
venta/pago al reintentar y prueban la exclusión del dominio nocturno y el respeto
a facturas anteriores. El transporte JSON.PE usa respuestas simuladas: no se
consultó ningún documento real ni se enviaron comprobantes a SUNAT.

Se compiló el bundle POS, incluidos JS, CSS y la extensión del recibo; el JS
resultante pasó la comprobación sintáctica de Node. No hubo errores CSS. Esto
no sustituye una prueba del navegador con todos los dispositivos de la tienda.

Se instaló el POS anterior 19.0.1.0.0 en otra base, se reprodujo la columna
faltante al arrancar Python nuevo sin actualizar y se aplicó `-u` dirigido.
La versión 19.0.1.1.1 arrancó conservando ID, nombre, modo, URL y token del fixture
(comparado mediante hash). Evidencias locales `/tmp/alvina-pos-schema-*.log` y
`/tmp/alvina-pos-schema-before.json`, `/tmp/alvina-pos-schema-after.json`.

El runtime es Odoo Community 19 oficial. Las pruebas nativas interempresa son
contratos ORM; no se ejecutó el motor Enterprise ausente del ZIP. Los diarios
privados se validaron por su contrato conocido, no instalando toda su dependencia
Enterprise. La configuración y la base reales no se han modificado.

## Orden de actualización

1. Comprobar que las cajas hayan sincronizado sus tickets pendientes. No borrar
   el almacenamiento local del navegador. Respaldar la base y el filestore, y
   comprobar la actualización en su copia.
2. Conservar los otros módulos y sincronizar las carpetas completas revisadas
   `alvina_branch_requisition` y `alvina_pos_comprobantes`, incluidas migraciones.
3. Con los procesos Odoo de esa base detenidos, ejecutar en su entorno real la
   actualización dirigida de **las dos apps**, con los nombres de base/configuración
   reales. La parte que debe incluir el comando de Odoo es:

   ```bash
   -u alvina_branch_requisition,alvina_pos_comprobantes --stop-after-init
   ```

   Después iniciar el servicio. Si POS todavía no estaba instalado, su instalación
   se hace expresamente al habilitarlo; `-u` no instala módulos nuevos. No desinstalar
   ninguno para actualizar. No basta un reinicio ni actualizar la lista de apps.
4. Como administrador, abrir **Ajustes → Usuarios y empresas → Empresas → compañía
   peruana → ALVIÑA POS** y guardar **Boleta/Factura al final del ticket**. La
   actualización conserva el modo anterior; si estaba en Pendiente, cambiarlo
   para este flujo. Configurar token JSON.PE y diarios reales.
5. Cerrar y reabrir las sesiones del navegador para cargar assets/grupos nuevos.
   Comprobar ticket normal, boleta y factura con las cuentas reales en la copia.
   Comprobar también un requerimiento UPAO→Industria y su despacho/recepción.

POS añade `res.company.alvina_jsonpe_profile`; Requerimientos añade, entre otros,
`stock.picking.alvina_dispatch_id`. Copiar Python y solo reiniciar sin aplicar el
esquema puede impedir abrir pantallas. Por eso el paso 3 es necesario antes de
volver a atender usuarios con el código nuevo.
