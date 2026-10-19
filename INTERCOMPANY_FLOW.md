# Flujo uniforme de sucursales — 19.0.2.0.0

## Estado de esta entrega

Implementación y pruebas en Odoo 19 **Community**, en bases locales desechables.
No se ha instalado ni actualizado producción. Esta rama conserva la versión
anterior; no modifica las ramas publicadas previamente.

Hay integraciones pendientes antes de activar el flujo en la instalación real:

1. No se dispone del código Enterprise de `account_inter_company_rules`. El addon
   bloquea expresamente la activación y confirmación de sus documentos vinculados
   cuando ese automatismo está instalado, hasta contar con un adaptador auditado.
   No se adivinan métodos, flags ni compatibilidad. Véase [NATIVE_INTERCOMPANY.md](NATIVE_INTERCOMPANY.md).
2. Para una sucursal que comparte compañía con Industria se propuso una orden
   interna y un traslado entre ubicaciones existentes. Falta aprobar esa variante
   y confirmar su ubicación de destino. Este caso permanece bloqueado; no crea
   compras/ventas de la compañía a sí misma ni empresas ficticias.
3. Existe otra rama publicada, `feature/central-supply-multicompany`, con la misma
   versión 19.0.1.2.0 pero otro esquema. No se fusionó ni sobrescribió. Si la base
   instalada procede de ella, hace falta una migración específica de sus
   asignaciones. Esta actualización detecta su tabla de almaceneros y se detiene
   en lugar de descartarlos. Confirmar el commit instalado, no solo la versión.

No presentar estos límites como un flujo Enterprise completo o listo para producción.

## Qué hace el usuario

La sucursal abre **Compras → Órdenes → Formulario Web**, o directamente
`/branch/requisition/new`. Si solo tiene una sucursal asignada aparece bloqueada;
con varias solo puede elegir entre las autorizadas. No aparece Empresa ni un
contador. Puede solicitar insumos aunque no haya existencias.

Las categorías siguen siendo Comerciales, Útiles de escritorio, Útiles de
limpieza y Envases y embalajes. Los productos se ordenan por referencia interna.
El envío crea, en una sola transacción, un requerimiento, una **OC en borrador
en la compañía real de la sucursal** y una **OV en borrador en Industria**. En
Odoo esos borradores se muestran como solicitudes de cotización/cotizaciones.
Si falla cualquiera de los documentos, no queda una solicitud incompleta.

El responsable de ventas configurado —el usuario existente de Rolly— revisa la
OV desde Industria. Ve sucursal, compañía compradora, requerimiento, OC,
fecha requerida, observaciones, cantidades y términos comerciales estándar.
El addon no confirma las órdenes, no envía cotizaciones ni genera facturas.
Los operadores autorizados confirman por el procedimiento normal de Odoo.

Inventario prepara y valida las salidas reales. **Reservado, entregado y recibido
son cantidades distintas.** Pedir 20 y entregar 15 conserva la demanda original
de 20 y deja 5 pendientes con su backorder. Las devoluciones físicas reducen lo
entregado neto, incluso si no se marca la opción de ajuste de facturación.
La recepción de la compradora requiere su propia validación; no se valida desde
Industria ni se supone realizada por haber despachado.

## Configuración, exclusivamente en pruebas

Usar compañías, contactos, almacenes, operaciones y usuarios ya existentes.
No se deduce la compañía operativa de una condición jurídica ni del propietario
del contacto. No se crean empresas o sucursales para adaptar el flujo.

1. Instalar/actualizar la carpeta completa del addon, con todas sus migraciones,
   mediante `-i`/`-u alvina_branch_requisition` en una copia de pruebas respaldada.
   Un reinicio no ejecuta las migraciones. No desinstalar para actualizar.
2. Con el administrador autorizado, abrir **Compras → Configuración →
   Abastecimiento de Industria**. Hay una configuración central única, inicialmente
   desactivada: compañía Industria real, usuario de ventas existente y lista de
   precios del acuerdo con sucursales. No se elige automáticamente por nombre.
3. En **Vínculos de sucursales Alviña**, cada sucursal necesita un código único,
   su contacto existente, compañía solicitante real, Industria como abastecedora,
   almacén de Industria y operación de recepción de la compañía compradora.
   La recepción siempre está visible, aunque la opción heredada de cotización
   esté desmarcada. Con el flujo central activo esa opción heredada no decide
   qué sucursales participan: todas siguen la configuración central.
4. Asignar el usuario solicitante exacto y el responsable de ventas/almacenero
   de Industria a cada vínculo que deban atender. El solicitante mantiene sus
   compañías actuales; no añadir Industria para eludir la seguridad.
5. Habilitar los productos deseados. Para la operación entre compañías deben
   ser bienes físicos compartidos, activos, comprables y vendibles, habilitados
   para requerimientos y dentro de las categorías admitidas. No se comparten
   ni duplican automáticamente contactos o productos.
6. Revisar impuestos, posiciones fiscales, moneda/tipos de cambio, lista de
   precios, rutas de Inventario y ubicaciones intercompañía reales. Activar solo
   después de resolver las integraciones de la sección de estado.

El cliente comercial de la OV es el **contacto de la compañía compradora**, y el
proveedor de la OC es el **contacto de Industria**. La identidad operativa de la
sucursal se conserva separadamente en el vínculo, documentos, picking y PDF.
El contacto operativo de la sucursal puede seguir privado de su compañía. No
se fuerza a compartirlo. Los contactos de las compañías sí deben poder usarse
en sus respectivos documentos estándar.

Odoo configura propiedades de tránsito entre los contactos de compañías. Se
probó que el destino de la salida de Industria y el origen de la recepción de
la compradora coincidan. No se inventa ni escribe una ubicación de tránsito.
Dirección de entrega/facturación y recepción quedan protegidas en las órdenes
vinculadas. Cambiar una recepción con historial del nuevo flujo exige migración.

## Precios y PDF

El nuevo flujo calcula la OV con la lista configurada y los mecanismos estándar
de descuentos, impuestos, posición fiscal, moneda y redondeo. No usa el precio
público como sustituto silencioso, el costo ni una tarifa de proveedor.
La OC inicial toma el precio neto efectivo de venta, convertido a su moneda y
adaptado a los impuestos de compra de su compañía. No se codifica una tasa de
IGV. Las dos cotizaciones requieren revisión fiscal y comercial. Cambios
posteriores de precio en un borrador no se sincronizan automáticamente al otro.

El menú **Imprimir** de la OV y del requerimiento ofrece el PDF A4
**ORDEN DE DESPACHO VALORIZADA — INDUSTRIA**. Incluye referencias, sucursal,
compañías, fechas, códigos, unidades, solicitado, reservado, entregado neto,
recibido, pendiente, precios, impuestos e importes solicitados/entregados/pendientes.
Solo usa el logo real configurado, si existe. Puede imprimirse antes o después
de entregar; una reserva nunca se presenta como entrega. No acredita facturación.
El PDF refleja las condiciones actuales de la OV, no un comprobante fiscal ni
una copia legal inmutable de cada impresión.

Los faltantes pueden permanecer pendientes para otro despacho. Para cerrarlos,
un almacenero asignado cancela primero las operaciones abiertas del producto en
Inventario y usa **Cerrar saldo con motivo**. Registra cantidad, motivo, usuario
y fecha en un historial inmutable. No reduce la cantidad original ni crea una
entrega ficticia, y tampoco cancela movimientos automáticamente.

## Seguridad

La solicitud se crea con el usuario real. El puente privado valida su sucursal,
compañía permitida y configuración antes de crear exclusivamente las contrapartes
con elevación acotada. El navegador no puede elegir compañías, precios, estados
o vínculos comerciales. Token, bloqueo de fila y unicidad evitan duplicados.

Las reglas estándar de compañías y roles de Compras/Ventas/Inventario siguen
vigentes. Se añaden restricciones de asignación para las órdenes vinculadas;
los documentos ajenos al addon conservan su flujo. Rolly necesita sus permisos
de ventas ya existentes en Industria y asignación a las sucursales. El rol
Alviña: Almacenero se necesita además para el consolidado/cierre de saldos.
No se añaden compañías ni roles automáticamente a ningún usuario.

Un Rolly solo de Industria puede consultar su OV y su PDF autorizado sin obtener
acceso general a las OC de las compradoras. Los enlaces a documentos conservan
las ACL estándar. El PDF valida acceso y asignación, y entrega a QWeb únicamente
una proyección de datos autorizados, sin registros `sudo()` ni costos de inventario.

## Consolidado e históricos

Se conserva **Compras → Órdenes → Consolidado de compras**, para almaceneros.
Esta actualización lo vuelve a activar conforme a la última instrucción. No
crea una aplicación, menú raíz ni nuevas compras externas.

Agrupa primero la demanda pendiente por producto, almacén e Industria y conserva
el desglose de sucursales. Excluye requerimientos y OV cancelados. Usa stock libre,
entradas confirmadas y reservas reales de estas solicitudes dentro del almacén.
Las reservas propias se reconocen una sola vez: confirmar la OV no inventa una
nueva falta por haber reducido `free_qty`. Las reservas de otros pedidos siguen
indisponibles. No suma OC y movimientos entrantes por duplicado.

La sugerencia es `max(pendiente − reserva propia reconocida − max(stock libre,0)
− max(entradas,0),0)`. La reserva reconocida se limita por demanda y existencias
físicas/reservas del almacén. Es una consulta, no una asignación exclusiva de
entradas ni un motor de aprovisionamiento con ventanas de tiempo.

La migración `19.0.2.0.0` conserva lo atendido histórico en
`legacy_qty_supplied` antes de activar los cálculos de Inventario. No genera OC,
OV, movimientos ni precios retroactivos. Mantiene compañías, usuarios y documentos
anteriores. No convierte historial mal asignado a otra compañía. La configuración
central no se crea/activa automáticamente: el modo anterior sigue disponible
hasta que se revise y active expresamente el nuevo flujo.

## Aceptación pendiente

Antes de autorizar producción: probar la copia real con Enterprise, tema,
addons privados, rutas, valuación comercial, impuestos y permisos existentes;
resolver el adaptador nativo y la operación de sucursales dentro de Industria;
confirmar las direcciones operativas reales si varias sucursales comparten una
compañía compradora; probar la regresión de `/portal/production/new` sin editarlo.
Véase [TESTING.md](TESTING.md) para la evidencia reproducible actual.
