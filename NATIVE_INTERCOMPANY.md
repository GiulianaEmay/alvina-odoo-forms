# Compatibilidad nativa y privada — 19.0.3.0.0

## Estado

La implementación se contrasta con Odoo **Community 19**, revisión oficial
`e1ed4fe077ba98ce7ac6802a43bb68242081dee9`. No se dispone del checkout Enterprise
autorizado ni se ha ejecutado la pila privada real. La validación local no
certifica esa instalación. No se ha desplegado ni cambiado producción.

## Automatismo interempresa Enterprise

Community referencia `account_inter_company_rules` en `base_setup` como
mecanismo de generación de ventas/compras entre compañías. Su implementación
no está en el código disponible. No se ha verificado ningún hook, contexto de
omisión o método generador Enterprise.

Este addon crea **ambos** documentos y los confirma mediante acciones estándar.
Si otro automatismo genera la contraparte al confirmar, podría duplicarlos. Por
eso `_assert_supported()` bloquea habilitar/usar el flujo y confirmar/aprobar
sus órdenes cuando `account_inter_company_rules` está instalado, pendiente de
actualización o pendiente de eliminación. Las órdenes ordinarias no se someten
a este guardia específico del abastecimiento.

**El bloqueo sigue vigente.** No desinstalar el módulo Enterprise, falsear su
estado, quitar el guardia ni inventar flags para superarlo. Antes de habilitar
la instalación real, obtener en una copia de pruebas:

1. Revisión exacta y código completo de `account_inter_company_rules` y de los
   addons que lo heredan, con sus manifests y dependencias.
2. Configuración de generación/sincronización, usuarios y compañías utilizados,
   así como opciones de confirmación, aprobación y validación.
3. Extensiones y automatizaciones de Compras, Ventas e Inventario que creen,
   confirmen o sincronicen documentos y operaciones.
4. Mapa real de compañías, contactos comerciales, impuestos, monedas, almacenes,
   operaciones, rutas, ubicaciones y usuarios de sucursal/Logística.

Con esa evidencia se necesita un adaptador auditado y pruebas de unicidad al
confirmar/aprobar ambos documentos, reintentar, operar concurrentemente,
cancelar y registrar Inventario. Simular la presencia del módulo para comprobar
que el guardia bloquea **no es probar Enterprise**.

El servicio también revierte la operación si una extensión genera facturas o
valida cantidades físicas durante su confirmación comercial. Esos controles no
reemplazan la revisión de automatizaciones privadas ni garantizan ausencia de
efectos externos ajenos a la transacción de base de datos.

## Fabricación privada conocida

El ZIP facilitado de `alvinha_mrp` incluye un override de creación de líneas de
venta que puede llamar `_create_mrp_production` cuando el producto tiene una LdM,
incluso con una OV en borrador. Fabricar por ese efecto no corresponde a enviar
insumos a las sucursales.

El puente comprueba la presencia del módulo y las LdM del producto para Industria.
Si se dispararía fabricación, rechaza el envío con un mensaje de integración
pendiente. No falsifica `is_from_mrp`, no inventa contextos de omisión ni crea
órdenes de fabricación. Se debe revisar el código privado efectivamente instalado
y resolver su adaptación antes de usar esos productos.

La ruta privada `/portal/production/new` pertenece a `alvinha_mrp`; se conserva
sin modificar. El nuevo flujo de insumos usa `/branch/requisition/new`. Una
redirección hacia producción no demuestra que el menú de abastecimientos de
Ventas esté funcionando.

## Edición de ventas privada

`alvinha_sale_management` restringe la edición de líneas a su creador o a un
administrador de Ventas. Las líneas generadas automáticamente pueden conservar
como creador técnico al usuario de la sucursal. El nuevo rol de Logística
comparte el acceso a las ventas vinculadas, pero no certifica que ese override
privado permita todas las ediciones esperadas.

Revisar esa combinación con el código y la base representativa. No conceder
Ventas: Administrador como sustituto de un adaptador ni eliminar sus controles
sin una evaluación del ámbito. El flujo aprobado no exige que Logística cambie
los precios para confirmar lo físicamente enviado.

## Sucursal e Industria dentro de la misma compañía

El procedimiento funcional es uniforme, pero la compañía operativa sigue siendo
la real. Si la compradora es Industria, no corresponde generar una compra/venta
interempresa de la entidad consigo misma ni crear una empresa ficticia.

La variante interna mediante una orden y un traslado entre ubicaciones reales
requiere aprobación y mapa de destino. `_create_internal_dispatch()` permanece
bloqueado y no genera documentos. La presencia del campo de ubicación interna
no habilita esa variante en esta entrega.

## Rutas de recepción y trazabilidad

La confirmación guiada de sucursal admite una única recepción de compra pendiente
de un paso, con destino interno de la compradora. No valida automáticamente una
cadena de entrada, calidad o almacenamiento de varios pasos. Los productos con
lotes o números de serie requieren una integración de sus identificadores reales;
el asistente los bloquea y no los inventa. Conservar los saldos de entradas y
salidas parciales es requisito de configuración.

## Módulo de solicitudes internas con QR

El ZIP operativo recibido el 22/10/2026 incorpora `alvina_stock_request`, distinto
del addon de sucursales. Su `models/stock.py` declara
`stock.move.alvina_request_line_id` como relación a `alvina.stock.request.line`.
Este addon declara el mismo nombre de campo como relación a
`alvina.branch.request.line` en `models/fulfillment.py`.

Si ambos módulos están instalados, no se pueden tratar sus líneas como si fueran
el mismo modelo. Hay riesgo de sobrescritura de la definición por orden de carga,
relaciones/validaciones incompatibles y bloqueo de operaciones QR o de sucursales.
No se ha resuelto ni migrado esa coexistencia en 19.0.3.0.0. Se necesita separar
los nombres y revisar el esquema y datos reales antes de una migración; no
reasignar claves ni borrar movimientos para evitar el conflicto.

Este hallazgo no es la causa del `UndefinedColumn` de `stock.picking` reportado.
La recuperación del esquema de Ventas y la compatibilidad de ambos módulos son
comprobaciones diferentes. No habilitar ambos flujos como si esa integración
estuviera certificada.

## Variante anterior con esquema diferente

La revisión remota encontró `feature/central-supply-multicompany` en
`258a450923d1fe20317eb12cf7e0d98807c7dc4b`, basada en `bf19163`. La línea de esta
entrega conserva la implementación multiempresa de `d59eea3`. Ambas se
identificaban como **19.0.1.2.0**, pero no tenían el mismo esquema.

La alternativa utiliza `keeper_ids`/`alvina_binding_keeper_rel`, fija una sola
sucursal y consulta costo actual en el consolidado. No se ha fusionado ni
sobrescrito esa rama. La migración detecta su relación y exige un mapeo revisado;
no borra ni mezcla asignaciones para continuar. Identificar el commit instalado
antes de aplicar una actualización. La evidencia de migración histórica aquí
corresponde a `d59eea3` y sus antecedentes, no a esa alternativa.
