> Documentación del modo anterior 19.0.1.2.0. La nueva corrección funcional y configuración central 19.0.2.0.0 se documentan en [INTERCOMPANY_FLOW.md](INTERCOMPANY_FLOW.md). Con el flujo central activo todas las sucursales usan Industria; la opción heredada por vínculo deja de decidir la generación. Enterprise y las operaciones dentro de la misma compañía siguen pendientes según [NATIVE_INTERCOMPANY.md](NATIVE_INTERCOMPANY.md).

# Industria abastece a las sucursales — versión 19.0.1.2.0

## Flujo para el usuario

Industria puede centralizar la compra y el abastecimiento desde su almacén, mientras cada sucursal registra sus necesidades con su propio usuario y compañía. Con una sola sucursal asignada, el formulario la muestra bloqueada. Con varias, permite elegir entre las autorizadas. No muestra un selector de empresa.

Si el administrador activa **Crear solicitud de cotización** en el vínculo, cada nuevo envío registra el requerimiento y una cotización estándar en borrador, como en las capturas de Compras del usuario. La empresa compradora es la sucursal, el proveedor es Industria y el origen enlaza el requerimiento. Al agrupar Solicitudes de cotización por empresa, el documento aparece bajo la sucursal que lo pidió. La opción está desactivada por defecto y no genera cotizaciones para requerimientos históricos.

El almacenero de Industria ve las solicitudes de las sucursales que tenga asignadas y un consolidado por producto/almacén/empresa abastecedora. Si UPAO y otra sucursal pertenecen a compañías diferentes pero piden al mismo almacén de Industria, primero se suman las cantidades y después se descuenta una sola vez el stock libre y las entradas confirmadas. La compra sugerida sigue siendo informativa.

Los nuevos requerimientos capturan el precio de venta y el valor solicitado por sucursal. Este valor representa una necesidad, no una entrega realizada. Cuando corresponda confirmar, vender, facturar o entregar, debe utilizarse el proceso habitual de Alviña. El formulario crea únicamente la cotización en borrador si se habilita: no llama a confirmar/aprobar ni genera ventas, facturas o movimientos en el núcleo revisado. No envía correos de cotización. El registro de atención parcial/final y la valorización de entregas efectivas continúan pendientes de integración.

## Configuración en pruebas

Desde una cuenta administradora con `Alviña: Configuración`, abrir Compras → Configuración → Vínculos de sucursales Alviña. Utilizar registros existentes:

| Campo | Ejemplo de la configuración confirmada por el usuario |
| --- | --- |
| Sucursal existente | Contacto de sucursal existente → Sucursal UPAO |
| Empresa solicitante | La compañía Sucursal UPAO |
| Empresa abastecedora | INDUSTRIA PANIFICADORA ALVIÑA E.I.R.L. |
| Almacén abastecedor | Insumos de INDUSTRIA PANIFICADORA ALVIÑA E.I.R.L. |
| Crear solicitud de cotización | Activar después de comprobar proveedor, productos y recepción |
| Recepción de la sucursal | Operación de entrada activa de la compañía Sucursal UPAO |
| Usuarios autorizados | Sucursal UPAO - User y el almacenero de Industria responsable |
| Activo | Sí |

Los nombres anteriores son ejemplos basados en las capturas, nunca identificadores codificados ni instrucciones para crear duplicados. Confirmar los registros exactos en la base de pruebas. La empresa solicitante se configura explícitamente: el `company_id` de un contacto indica quién mantiene esa ficha comercial, y no identifica necesariamente a la compañía que solicita. El contacto puede estar compartido o pertenecer a la empresa solicitante o abastecedora; otra compañía es rechazada.

El usuario UPAO mantiene acceso a su compañía y el rol `Alviña: Solicitante`. **No necesita añadir Industria a sus compañías permitidas.** El almacenero mantiene Industria y el rol `Alviña: Almacenero`, además de la asignación explícita a las sucursales que atenderá. No necesita acceso general a la compañía de UPAO para revisar sus requerimientos asignados o su consolidado. La cuenta administradora debe tener los accesos apropiados para configurar las compañías y contactos existentes.

Las cotizaciones son documentos estándar de la empresa compradora. Para ver o gestionar las cotizaciones de varias sucursales en Compras → Órdenes → Solicitudes de cotización, el comprador necesita los permisos estándar y acceso a esas compañías. La asignación como almacenero de Industria no concede ese acceso. El addon no amplía las reglas estándar de Compras para mostrar documentos de otras empresas.

La recepción de la sucursal identifica dónde recibiría su compra una vez confirmada por el proceso habitual. **No seleccionar aquí el almacén Insumos de Industria:** ese es el origen abastecedor, no la recepción de UPAO. El formulario no crea ni confirma ninguna recepción.

El proveedor utilizado es el contacto comercial que ya tiene la compañía Industria (`supply_company_id.partner_id`), no el contacto de la sucursal. Debe estar activo y compartido o pertenecer a la empresa compradora. Para atender a varias compañías solicitantes, normalmente debe estar compartido. Esta decisión debe revisarla el administrador: el addon no cambia la compañía de ningún contacto.

Sin cotizaciones, el catálogo admite productos habilitados compartidos o privados de Industria. Con cotizaciones activadas, admite únicamente productos **compartidos**, habilitados para compras, activos y habilitados para requerimientos dentro de las cuatro categorías. Así se evita crear una compra de UPAO con un producto privado de otra compañía que después no pueda recibirse. No se comparten, duplican ni trasladan productos automáticamente. Si el catálogo queda vacío, revisar esa configuración, sin crear duplicados.

## Precio de venta y valor solicitado

Cada nueva línea registra el precio de venta del producto, incluidos los extras de variante, en su unidad base. Se convierte desde la moneda real del producto a la moneda de la empresa solicitante con la fecha del envío; no se presupone que la moneda del producto compartido sea la de Industria. El importe por línea es cantidad por precio, redondeado en la moneda solicitante. Un cambio posterior en el precio del producto no cambia el importe registrado.

No se utiliza el costo de inventario ni el precio de una tarifa de proveedor. Se conserva un precio cero válido. Las líneas históricas carecen de precio capturado y se señalan como tales; no se rellenan usando el precio actual ni se presentan como una valorización histórica comprobada.

El valor solicitado no acredita cuánto se entregó ni sustituye la valoración contable. La cotización estándar utiliza el precio capturado y los impuestos de compra configurados para la empresa compradora. El precio del catálogo y el tratamiento fiscal deben revisarse antes de confirmar, especialmente si se manejan precios con impuestos incluidos.

## Si el formulario dice «sin sucursal asignada»

Comprobar que el vínculo está guardado y activo, que el usuario exacto aparece en Usuarios autorizados, que tiene el rol Solicitante y que la empresa solicitante figura entre sus compañías permitidas. Pertenecer a una empresa no asigna automáticamente un vínculo de sucursal.

La versión `19.0.1.2.0` corrige también el contexto del sitio web: en estas rutas recupera exclusivamente las compañías realmente permitidas al usuario, para que la compañía del sitio web no oculte una sucursal autorizada. No añade compañías al usuario ni cambia la sesión o las reglas de otras rutas. Un simple reinicio con código antiguo no incorpora la corrección.

## Actualizar desde 19.0.1.0.1 o 19.0.1.1.0

La autorización actual permite preparar código y pruebas; no actualizar producción. El administrador debe validar primero esta actualización en una copia de pruebas con respaldo de base y filestore.

1. Colocar **la carpeta completa** `alvina_branch_requisition` de la nueva revisión en la ruta de addons de pruebas. Conservar todas las carpetas `migrations/`, incluida `19.0.1.1.0/`; no transferir únicamente los archivos Python modificados.
2. Con los procesos Odoo de esa base de pruebas detenidos, usar el Python y la configuración reales de pruebas:

```bash
/path/to/odoo/odoo-bin -c /path/to/test.conf -d ALVINA_TEST \
  -u alvina_branch_requisition --stop-after-init
```

3. Arrancar el servicio de pruebas con el mismo código. Reiniciar por sí solo no actualiza campos, vistas ni migraciones. No desinstalar para actualizar: se perderían registros propios del addon.
4. Verificar en Apps la versión `19.0.1.2.0` y la aparición de Empresa solicitante / Empresa abastecedora / Almacén abastecedor, Crear solicitud de cotización y Recepción de la sucursal en el vínculo.
5. Configurar UPAO como solicitante e Industria como abastecedora, sin ampliar las compañías permitidas del usuario UPAO. Si el intento anterior nunca se guardó, crear un vínculo nuevo; si ya hay uno sin solicitudes, puede corregirse. No crear otro contacto ni otro vínculo para la misma sucursal.
6. Revisar el proveedor de Industria, los productos compartidos habilitados para compras y la recepción de UPAO. Activar Crear solicitud de cotización solo para los vínculos que deban usar el nuevo flujo. No se generan documentos para solicitudes anteriores.
7. Probar el formulario como usuario UPAO y el consolidado como almacenero Industria. Comprobar que continúan denegados los documentos y existencias privados de Industria para el usuario UPAO. Con una cuenta compradora autorizada en UPAO, verificar la nueva cotización en borrador, su empresa, proveedor, precios y origen. No confirmar ni enviar documentos durante esa comprobación.

La migración conserva la compañía solicitante de todos los registros existentes y obtiene la abastecedora desde el almacén de cada vínculo. No convierte solicitudes históricas de una compañía a otra. Si un vínculo ya tiene historial y su empresa solicitante se configuró erróneamente antes, corregirlo requiere una migración específica revisada; no borrar solicitudes para eludir ese bloqueo.

## Validación técnica

Las reglas permiten al solicitante sus sucursales asignadas en sus compañías activas y al almacenero las sucursales asignadas abastecidas por sus compañías activas. Son permisos sobre los modelos de requerimientos; no se modifican las reglas estándar de compras, inventario, productos o compañías ni `res.users.company_ids`.

El catálogo utiliza lectura elevada limitada a productos habilitados y solo presenta ID, nombre/código, categoría y UoM. La cabecera y las líneas del requerimiento se crean con el usuario real, sin `sudo()`. Los campos de empresa, proveedor y almacén se derivan en el servidor del vínculo; el cliente no puede suplantarlos. Solo el puente privado que crea la cotización usa una escritura elevada acotada, después de autorizar el requerimiento. No concede ACL generales de compras ni modifica compañías del usuario. Si falla la cotización, se revierte también el requerimiento del mismo envío. El almacenero consulta las existencias con sus permisos normales y el contexto de su almacén abastecedor.

Si el requerimiento tiene una cotización, debe cancelarse primero desde Compras para cancelar el requerimiento. La cancelación del requerimiento no modifica automáticamente documentos estándar. Enterprise, las automatizaciones y los addons privados no están validados en esta máquina; deben comprobarse en una instalación de pruebas representativa. Consultar TESTING.md para la evidencia y los resultados de la versión actual.

La actualización real desde `bf19163` fue probada con dos compañías diferentes de la compañía del administrador, vínculos activos/archivados y solicitudes históricas. Las migraciones previas/posteriores preservan usuarios, compañías permitidas, compañías solicitantes, historia, cantidades, compras y movimientos. La fase posterior evita dejar vacíos los campos relacionados de las líneas por el orden de inicialización de Odoo 19; ambas fases se repitieron sin cambios adicionales.

Para reproducir la prueba de actualización, `tools/check_supply_upgrade.py` documenta las fases `prepare` con la versión antigua y `verify` con la nueva. El probe rechaza bases ajenas a `alvina_supply_upgrade_test` y conexiones remotas; crea fixtures y hace commit únicamente en esa base desechable. No ejecutar en una base con información importante.
