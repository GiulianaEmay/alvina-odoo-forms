# Abastecimiento central entre compañías — 19.0.1.2.0

## Datos y permisos

`company_id` sigue siendo la **compañía solicitante** en el vínculo, la solicitud y sus líneas. El vínculo conserva `warehouse_id` como **almacén abastecedor**; `supply_company_id` se deriva de la compañía de ese almacén. El almacén ya no tiene que pertenecer a la solicitante.

Al enviar se capturan `warehouse_id` y `supply_company_id` en la cabecera; las líneas los almacenan mediante campos relacionados. Se toman del vínculo autorizado, nunca del navegador ni de valores RPC/contexto proporcionados por el solicitante. Cabeceras y líneas permanecen inmutables. Un vínculo con historial sigue sin permitir cambiar compañía, contacto o almacén.

Para UPAO → Industria:

1. Un administrador autorizado configura un contacto real de UPAO y su compañía solicitante en el vínculo. Selecciona el almacén existente de Industria; debe poder leer ese almacén y el contacto usando sus permisos normales.
2. En **Usuarios autorizados** asigna a los solicitantes de UPAO. Deben pertenecer a UPAO; no necesitan pertenecer a Industria ni recibir grupos de Compras/Inventario para enviar el formulario.
3. En **Almaceneros autorizados** asigna los responsables de Industria con el grupo `Alviña: Almacenero` y acceso a Industria. No necesitan pertenecer a UPAO.
4. Activa Industria al consultar el consolidado. Solo se consulta stock si la compañía abastecedora está entre las compañías activas autorizadas del almacenero. Se mantienen las ACL y reglas normales de stock, sin `sudo()` para calcular existencias.

Los almaceneros solo pueden leer/revisar/cancelar solicitudes y líneas de sus sucursales asignadas, con una compañía solicitante o abastecedora activa. Se mantiene la asignación anterior mediante `user_ids` para no romper los vínculos existentes de una sola compañía. `keeper_ids` añade la asignación expresa de responsables de la abastecedora. Tener el grupo de configuración no concede acceso general al historial.

Los grupos heredados existentes de `Alviña: Almacenero` (Compras e Inventario) se conservan; no se modifican reglas ni permisos de esos módulos. Esos permisos estándar se limitan a las compañías que ya tiene cada usuario. No se añade Industria a las compañías de UPAO. Para un solicitante sin permisos de Compras se usa la URL autenticada `/branch/requisition/new`; los menús internos siguen bajo Compras → Órdenes y conservan las restricciones estándar del menú padre.

Los productos usados **entre compañías deben ser compartidos** (`product.company_id = False`), estar habilitados para requerimientos y pertenecer a una de las cinco categorías admitidas (Comerciales, Útiles de escritorio, Útiles de limpieza, Envases y embalajes o Abarrotes). No se convierten productos privados ni se amplía el acceso al catálogo privado de Industria. En solicitudes dentro de una misma compañía sigue siendo válido su producto privado. El portal publica únicamente los datos mínimos del catálogo habilitado y aplica el mismo criterio que el modelo.

## Consolidado

Se buscan líneas pendientes con las reglas normales del usuario. Se agrupan por **producto + almacén abastecedor histórico + compañía abastecedora histórica**; la compañía solicitante no divide el grupo. Se suman primero las cantidades pendientes y luego se descuentan stock libre y entradas una sola vez por grupo:

`max(total_pendiente - max(stock_libre, 0) - max(entradas, 0), 0)`

Ejemplo: UPAO pide 12 y otra compañía pide 8 al mismo almacén. Con stock libre 8 y entradas 3 se obtiene una fila: pendiente 20, sugerencia 9. Almacenes distintos conservan filas distintas. El desglose mantiene las líneas de cada sucursal y compañía solicitante. Las canceladas no cuentan; recalcular sustituye los resultados anteriores. Cada consolidado y sus líneas solo son accesibles por su creador (salvo superusuario).

El total incluye exclusivamente las sucursales visibles para ese almacenero. Una consulta de alcance parcial no representa toda la demanda de Industria. La sugerencia sigue siendo informativa: no reserva stock entre consultas/almaceneros ni crea compras, ventas, movimientos o entregas. Se preserva el bloqueo si cambia la UoM histórica. Los filtros de ubicación y fecha recibidos por contexto no alteran la consulta actual del almacén configurado.

## Formulario de sucursal fija y compañía del sitio

Cada usuario del formulario debe tener exactamente un vínculo activo y válido en **Usuarios autorizados**. La sucursal aparece bloqueada y el servidor exige la misma asignación al recibir el POST. Con cero vínculos se indica que falta asignación; con varios se pide al administrador dejar uno solo. El backend conserva las autorizaciones existentes para otras herramientas; este requisito se aplica al formulario y su envío.

Odoo puede imponer la compañía del sitio en las rutas web. Por eso la búsqueda de sucursal del formulario usa únicamente las compañías que el usuario **ya tiene permitidas**, con sus reglas normales y su asignación de usuario. El envío se ejecuta en la compañía de su sucursal autorizada, y la confirmación conserva las reglas de lectura. No se usa `sudo()` para buscar o crear solicitudes, no se cambia la compañía del sitio ni se añaden empresas al usuario. El caso sitio Industria + usuario UPAO con ambas empresas permitidas está cubierto, también si Industria es su predeterminada.

## Valorización de insumos

El documento que recibe el almacenero es un **requerimiento interno**, no una orden de compra oficial. El consolidado muestra `Costo unitario actual` y `Valor estimado pendiente`: cantidad pendiente multiplicada por el `standard_price` existente del producto en la **compañía abastecedora**, en su moneda. El stock se descuenta para la compra orientativa, pero el valor pendiente corresponde a todo lo solicitado pendiente, no solo al faltante.

Cada fila abre un desglose por sucursal, solicitud y solicitante, con cantidad y valor pendiente al mismo costo actual. Solo el propietario del consolidado, con rol de almacenero, puede leer sus totales y detalles. El costo se consulta con sus permisos normales y exige la abastecedora activa. Los solicitantes no reciben costos privados en sus solicitudes ni en el formulario.

Recalcular obtiene costos y pendientes actuales; no cambia el costo original del producto ni escribe costos retrospectivos en solicitudes antiguas. Un costo cero se conserva como cero: el administrador debe comprobar que Industria tenga los costos configurados. Se mantiene el bloqueo ante cambios de UoM histórica para evitar mezclar cantidades y precios de unidades diferentes. Distintas monedas quedan en filas de abastecedoras distintas, sin un total combinado que las mezcle.

Estas cifras son estimaciones actuales, **no valorización de entregas realizadas ni contabilidad de inventario**. Registrar lo realmente enviado requiere un proceso de entrega aún pendiente; no se crean movimientos, compras o ventas automáticamente.

## Migración histórica

La migración introducida en `19.0.1.1.0` sigue aplicándose al actualizar desde `19.0.1.0.1`, también al saltar directamente a `19.0.1.2.0`. Odoo ejecuta `migrations/19.0.1.1.0/pre-migrate.py` antes de inicializar el nuevo esquema al actualizar el addon.

El script crea, si faltan, ambas columnas nuevas en cabeceras y líneas. Completa las cabeceras desde el almacén del vínculo y su compañía; completa explícitamente **todas las líneas históricas** desde su cabecera. Es idempotente, conserva snapshots existentes y, ante una actualización parcial, usa primero el almacén ya capturado en la cabecera. No depende exclusivamente de la recomputación de campos relacionados.

Si faltan referencias o hay snapshots contradictorios, aborta la actualización con un error explícito; no inventa un almacén. No cambia cantidades, estados, autores, fechas, tokens ni compañía solicitante. No crea documentos operativos ni hace commits por su cuenta: la transacción de actualización de Odoo conserva su atomicidad.

La versión anterior exigía que el almacén fuera de la compañía solicitante: ese es el significado que se conserva para el historial. **No se reasignan automáticamente solicitudes antiguas de UPAO a Industria.** Tal reasignación sería una migración operativa distinta que necesita validar almacenes, historial y datos reales.

Para validar en una copia aislada con respaldo y el servicio de esa copia detenido por su operador:

```bash
/path/to/python /path/to/odoo-bin -c /path/to/test.conf -d ALVINA_TEST \
  -u alvina_branch_requisition --stop-after-init --no-http
```

Comprobar que cabeceras y líneas tienen abastecedor/almacén, que concuerdan y que los campos anteriores mantienen sus valores. No ejecutar SQL manual para completar o reasignar producción. Este desarrollo no despliega ni reinicia ningún servidor real.

## Validación y dependencias pendientes

La suite del addon incluye casos multiempresa de creación, aislamiento de compras/stock de Industria, acceso del almacenero asignado, revocación, acciones no autorizadas, contexto falseado, snapshots inmutables, productos privados, consolidación entre compañías y separación de almacenes. Una prueba HTTP autentica un portal exclusivo de UPAO, comprueba el catálogo compartido y envía una solicitud real. Se mantiene la prueba Chromium del formulario existente.

Cuatro pruebas ejecutan el SQL real de migración en tablas temporales PostgreSQL: esquema antiguo, todas las líneas e idempotencia, recuperación parcial preservando snapshots y rechazos de referencias inválidas/inconsistentes. Véase TESTING.md para resultados y comandos de esta revisión.

Antes de producción falta validar en una copia autorizada de **Odoo 19 Enterprise** con sus módulos privados y tema: contactos reales, compañías y almacenes exactos, catálogo compartido, permisos efectivos de usuarios, reglas de stock personalizadas y migración sobre una copia representativa. No se dispone aquí de Enterprise, la base real, filestore o módulos privados. No se contactó el servidor real. Tampoco se implementa el procedimiento de atención parcial/final ni la creación automática de documentos.
