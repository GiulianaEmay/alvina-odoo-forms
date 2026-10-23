# Compatibilidad nativa y privada — 19.0.3.1.0

## Estado

La implementación se contrasta con Odoo **Community 19**, revisión oficial
`e1ed4fe077ba98ce7ac6802a43bb68242081dee9`. No se dispone del checkout Enterprise
autorizado ni se ha ejecutado la pila privada real. La validación local no
certifica esa instalación. No se ha desplegado ni cambiado producción.

## Automatismo interempresa Enterprise

En 19.0.3.0.0 la presencia de `account_inter_company_rules` bloqueaba la
activación. Ese es el error de validación mostrado por el usuario; su configuración
central no llegaba a guardarse como activa. No era una falta de permisos de Angelo.

Desde 19.0.3.1.0 se admiten dos modos:

- Sin el módulo nativo instalado: el servicio crea una OC y una OV vinculadas.
- Con el módulo nativo instalado: el servicio crea **solo la OC** y deja que Odoo
  genere su OV al confirmarla. Un adaptador observa `sale.order.create` y
  `sale.order.line.create` durante esa transacción privada, valida compañía,
  cliente, productos, cantidades y precios y enlaza la única contraparte.
  Admite líneas anidadas y creación separada de cabecera y líneas.

Configurar el automatismo de **Industria** para generar ventas a partir de compras
de otras compañías, con su usuario interempresa existente autorizado. La dirección
contraria, una regla inactiva o permisos nativos insuficientes hacen fallar el envío.
No se cambian las opciones de las compañías, usuarios ni automatizaciones globales.
No se inventan hooks/flags privados ni se suprime el motor de Odoo.

Si no aparece una única OV válida, se revierte toda la operación y se informa del
error; no se registra un éxito con un pedido incompleto. Se rechazan otra OC, otra
OV, facturas automáticas, validaciones físicas anticipadas y términos comerciales
alterados. El adaptador no se activa mediante claves JSON-RPC del contexto.
Los módulos pendientes de actualización/eliminación siguen bloqueando el flujo.

**Límite de la evidencia:** las pruebas locales ejecutan Odoo Community real y un
contrato que simula la salida ORM del motor nativo. No ejecutan el módulo Enterprise
que no está incluido en el ZIP. Por ello aún hay que comprobar una transacción en
la copia real con sus reglas/usuario interempresa. El runtime valida el resultado;
si esa instalación produce una forma no admitida, se rechaza sin documentos
parciales. Esto no garantiza ausencia de efectos externos de otros automatismos.

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

El ZIP incorpora `alvina_stock_request`, distinto del addon de sucursales.
Ambos usaban antes `stock.move.alvina_request_line_id` para modelos diferentes.
Desde 19.0.3.1.0 sucursales usa `alvina_branch_request_line_id`; QR conserva su
campo y su modelo originales. Las relaciones de líneas de OC/OV conservan sus
nombres porque no colisionan con QR.

La migración conserva la columna anterior de QR cuando el módulo está instalado.
Solo acepta enlaces históricos identificables por producto y solicitud QR del
picking; ante una mezcla ambigua se detiene y conserva los registros para revisión.
Sin QR, renombra el campo anterior de sucursales y conserva sus valores. No borra
ni reasigna movimientos entre modelos por coincidencia de IDs.

La recuperación previa de `stock.picking.alvina_dispatch_id` es otra cuestión:
requiere aplicar el manifest completo y ejecutar la actualización de la app;
un reinicio por sí solo no crea su esquema. Esta entrega incluye ambos arreglos.

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
