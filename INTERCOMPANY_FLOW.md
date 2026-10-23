# Flujo de abastecimiento — 19.0.3.1.0

## Procedimiento único

Todas las sucursales abastecidas por Industria siguen la misma secuencia:

**Sucursal solicita → Odoo crea y confirma OC/OV → Logística despacha →
guía interna valorizada → sucursal confirma recepción real.**

La sucursal compra en su compañía operativa real; Industria vende en su propia
compañía. La identificación del local permanece separada de esas compañías. No
se decide el flujo por condición jurídica ni se inventan compañías. Cuando
ambos extremos pertenecen a la misma compañía, esta implementación se detiene
hasta aprobar su operación interna real.

El usuario no necesita confirmar OC u OV manualmente. El servicio crea los dos
documentos, los vincula al requerimiento y utiliza las acciones estándar de Odoo
para confirmarlos y preparar sus operaciones de Inventario. La aprobación
técnica de una OC vinculada, si corresponde, se limita a esa OC dentro del
servicio; no cambia políticas de compra ni permisos generales del usuario.

El envío es atómico: si falla la configuración, creación, confirmación o algún
control de integración, se revierte el conjunto. El servicio rechaza efectos
de otras extensiones que creen facturas o validen existencias en esta fase.
Confirmar documentos **no acredita cantidades físicas**.

## Solicitud y fecha

La ruta autenticada `/branch/requisition/new` se abre desde
**Compras → Órdenes → Formulario Web**. Con una sucursal asignada aparece
bloqueada; con varias, el usuario solo elige entre sus autorizadas. No permite
escoger libremente otra empresa ni Industria. Se mantiene el usuario real del envío.

La fecha requerida se propone y limita a **hoy en `America/Lima` + dos días
calendario**. Si hoy en Perú es 21, el valor inicial es 23 y se admite 23 o una
fecha posterior. No son días hábiles. El servidor vuelve a comprobarlo al
enviar, incluyendo POST y creación por RPC; cambiar el reloj o la zona horaria
del navegador/usuario no reduce el plazo. Un formulario abierto antes de cambiar
el día puede necesitar una fecha posterior al enviarse. No se reescriben fechas históricas.

Las categorías admitidas son Comerciales, Útiles de escritorio, Útiles de limpieza
y Envases y embalajes. No se crean categorías ni se incluyen sus hijas
automáticamente. Solo se ofrecen productos habilitados explícitamente, activos,
compartidos, comprables y vendibles para este flujo. Se ordenan por referencia
interna. La solicitud no requiere stock disponible para existir.

Se conservan cantidades al cambiar categoría. Cambiar sucursal limpia las
cantidades para no mezclar compañías. Se validan productos, cantidades finitas,
redondeo de unidades y duplicados. El token del formulario y las restricciones
de unicidad impiden generar pares duplicados por reenvío.

## Precios y relaciones comerciales

Industria utiliza la **lista de precios configurada**, con los mecanismos
estándar de moneda, descuentos, impuestos, posición fiscal y redondeo. No se
sustituye silenciosamente por costo de inventario ni tarifa de proveedor.
La OC toma el precio neto efectivo de venta convertido a su moneda y adaptado
a los impuestos de compra. No se fija una tasa de IGV en el código.

El cliente de la OV es el contacto comercial de la compañía compradora y el
proveedor de la OC es el contacto comercial de Industria. El contacto operativo
de la sucursal se identifica aparte. No se comparten, duplican ni modifican
contactos o productos automáticamente. Deben existir país fiscal real, moneda,
tipos de cambio, impuestos y contactos disponibles en las compañías correspondientes.

Los precios e importes solicitados se capturan al crear la solicitud. No se
revalorizan los históricos con precios actuales. No hay una sincronización
general de ediciones posteriores entre ambos documentos. No se envían facturas
ni se crean automáticamente por este addon.

## Logística y cantidades físicas

**Ventas → Órdenes → Pedidos de sucursales** muestra las ventas vinculadas a
abastecimientos. Logística prepara la salida de Inventario de la OV, introduce
las cantidades realmente enviadas y valida el despacho. Si despacha menos,
debe conservar el faltante como operación pendiente; una operación configurada
para cancelar siempre el saldo se rechaza para este caso parcial.

La salida real genera una guía por picking, sin emitir dos guías para el mismo
despacho. Las siguientes salidas parciales tienen sus propias guías. La reserva
no se presenta como entrega ni la entrega como recepción. Los movimientos
reales y sus devoluciones determinan las cantidades físicas netas.

La sucursal abre **Compras → Órdenes → Guías internas y recepción**, revisa su
guía e introduce lo realmente recibido en **Confirmar recepción real**. La misma
acción valida la recepción pendiente existente de la OC y registra usuario,
fecha y conformidad. No exige un segundo trámite manual de Inventario ni da
al solicitante acceso genérico al Inventario de otras compañías.

Se permite una recepción menor que lo despachado con motivo obligatorio; no se
permite recibir más de lo documentado en esa guía. El asistente está limitado
a una recepción real pendiente de **un paso**, sin lotes ni números de serie.
Si la operación necesita datos o rutas adicionales se detiene; no inventa
lotes, movimientos o confirmaciones. Si no llegó ninguna unidad, se registra
una recepción con diferencias y motivo obligatorio, sin crear movimientos ni
validar una entrada vacía.

Ejemplo: pedido de 10, despacho de 8, recepción de 7. Quedan **2 pendientes de
despachar** y **1 de diferencia de recepción**. Esa diferencia no vuelve a
descontar stock de Industria ni se suma automáticamente al pendiente de
despacho. Si recibe las 8 enviadas, la recepción de esa guía es conforme aunque
queden 2 del pedido sin despachar. Resolver una diferencia no crea una factura
ni una reposición automática.

## Dos informes distintos

La nueva **Guía interna valorizada por despacho** conserva la identificación,
cantidades, precios, descuentos, impuestos y valores al emitirse. Modificar un
nombre o precio posterior no reescribe el despacho. Una confirmación de
recepción añade su propio registro inmutable con las cantidades recibidas y
diferencias. El PDF separa los productos de esa salida del saldo del pedido
capturado al emitir: solicitado, despachado neto acumulado y pendiente de
despachar. La guía es un PDF interno: no es una factura ni una guía SUNAT.

Se conserva el informe anterior **Orden de despacho valorizada — Industria**
desde la OV/requerimiento para consultar el resumen de pedido, reservas,
entregado neto, recibido y pendientes. Ese resumen refleja el estado consultado;
no sustituye la guía inmutable de una salida concreta.

## Seguridad y sustitución de personal

El grupo **Alviña: Logística de Industria** atiende todas las sucursales cuya
abastecedora sea una compañía ya permitida y seleccionada por ese usuario. No
exige añadirle cada vínculo de sucursal ni que sea el vendedor de origen.
Incluye los permisos estándar de ventas de documentos propios y los del
almacenero; las reglas del addon delimitan el ámbito comercial compartido.

Para este rol quedan fuera las ventas comunes, sus líneas y el análisis de
ventas, incluso si también pertenece a grupos comerciales de todos los
documentos o administrador de Ventas. Una URL directa, exportación o agregado
no sustituye esas comprobaciones. No puede crear o duplicar manualmente una
OV común. Los usuarios comerciales que no tienen este rol mantienen sus
permisos anteriores. El superusuario técnico conserva su capacidad administrativa.

Los solicitantes mantienen sus compañías actuales y su asignación explícita al
vínculo. El rol anterior **Alviña: Almacenero** mantiene sus reglas de asignación.
**Almacenero autorizado**, de otros desarrollos, no reemplaza al grupo nuevo.
Tener permisos administrativos de configuración no concede por sí solo acceso
a todos los requerimientos. Tampoco se eliminan otros permisos previos de
Contabilidad, Compras o Inventario al asignar el nuevo rol.

El responsable de ventas es un usuario existente configurado por el administrador.
Si está activo, debe ser interno, tener Industria autorizada y acceso a Ventas.
Si falta o está archivado, solo se resuelve automáticamente cuando existe
exactamente un usuario activo del nuevo rol con Industria ya autorizada. Con
cero o varios candidatos se exige una selección explícita. No hay nombres
personales codificados ni se modifican órdenes históricas al sustituir personal.

La elevación interna del puente y de la recepción está acotada al documento
validado tras comprobar actor, sucursal, compañía, guía y operaciones. El cliente
no puede asignarse precios, compañías, estados, vínculos o cantidades físicas
con campos o contextos manipulados.

## Consolidado e históricos

Se conserva **Compras → Órdenes → Consolidado de compras** para el rol de
almacenero. Agrupa demanda pendiente por producto, almacén y abastecedora,
manteniendo el desglose por sucursal. No crea compras externas ni mueve stock.
Reconoce las reservas propias una sola vez y conserva indisponibles las de
otros pedidos. No suma OC y movimientos entrantes por duplicado.

La sugerencia es `max(pendiente − reserva propia reconocida − max(stock libre,0)
− max(entradas,0),0)`. La reserva reconocida se limita por demanda y existencias
físicas/reservas del almacén. Es una consulta, no una asignación exclusiva de
entradas ni un motor de aprovisionamiento por ventanas de tiempo.

Se conserva la migración 19.0.2.0.0, que protege lo atendido anterior en
`legacy_qty_supplied`. La versión 19.0.3.1.0 no convierte requerimientos antiguos
en nuevas parejas OC/OV ni crea guías históricas, precios, compañías o
movimientos retroactivos. La configuración central no se crea ni activa sola.
Identificar el commit instalado antes de actualizar: la variante alternativa
con `keeper_ids` requiere su propio mapeo.

## Integración y límites

El automatismo Enterprise instalado se integra mediante la OC y su OV nativa;
requiere la dirección de generación y usuario correctos. Las pruebas locales
cubren su contrato ORM, no la instalación Enterprise real. La misma compañía en
ambos extremos y productos que disparen fabricación privada siguen bloqueados. La edición de
líneas del módulo privado de ventas requiere una integración comprobada.
Detalles y evidencia: [NATIVE_INTERCOMPANY.md](NATIVE_INTERCOMPANY.md) y
[TESTING.md](TESTING.md). No se ha autorizado ni ejecutado despliegue en producción.
