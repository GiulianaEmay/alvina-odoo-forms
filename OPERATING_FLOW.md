# Guía de uso y configuración — 19.0.3.0.0

**La sucursal compra desde Compras. Logística de Industria atiende desde Ventas.**
Odoo genera y vincula ambos documentos y prepara las operaciones de Inventario.
Las personas confirman únicamente lo que salió y lo que llegó.

Esta guía sirve para una copia de pruebas después de actualizar la carpeta
completa del addon. No autoriza un despliegue en producción. Los bloqueos de
[compatibilidad](NATIVE_INTERCOMPANY.md) deben resolverse antes de activar el flujo
real; la configuración no viene creada ni activada.

## 1. Administrador: revisar las cuentas

En **Ajustes → Usuarios y empresas → Usuarios**, revisar las cuentas reales:

| Cuenta | Compañía que debe tener autorizada | Rol de este addon | Uso |
| --- | --- | --- | --- |
| Administrador de configuración | Industria y las compañías que ya le corresponda configurar | Alviña: Configuración | Configurar abastecimiento y vínculos; no implica ver todos los pedidos |
| Usuario de sucursal | Su compañía operativa real | Alviña: Solicitante | Enviar requerimientos y confirmar sus recepciones |
| Angelo o su sustituto | Industria, ya autorizada | Alviña: Logística de Industria | Atender las ventas de todas las sucursales abastecidas por Industria |

Para entrar al backend de Compras y confirmar recepción, el solicitante debe
ser usuario interno con **Compras: Usuario** además de **Alviña: Solicitante**.
El envío web también conserva el acceso de solicitantes portal autorizados;
esta entrega no convierte una cuenta portal en usuario interno ni le habilita
la confirmación de recepción del backend.

El nuevo rol de Logística incluye los permisos necesarios de almacenero,
Compras/Inventario y ventas de documentos propios. No hace falta poner Ventas
como «todos los documentos» o «administrador». La regla adicional limita sus
ventas a abastecimientos de sucursales incluso si conserva esos grupos amplios.
No elimina otros permisos administrativos, contables o de Inventario que el
usuario ya tuviera; revisarlos por separado si se requiere reducirlos.

**«Almacenero autorizado» no es el nuevo grupo.** Comprobar la pertenencia exacta
a **Alviña: Logística de Industria**, también desde **Ajustes → Usuarios y empresas
→ Grupos** con modo desarrollador si esa opción no aparece en el formulario de
usuario. No activar «Compartir grupo». El addon no añade Industria a ningún usuario.

Después de un cambio de grupos, cerrar y volver a iniciar sesión. En el selector
de compañías, Logística debe tener Industria seleccionada. El nombre de otra
compañía —por ejemplo Corporación Industrial— no sustituye a Industria Panificadora.

## 2. Administrador: abastecimiento central

Abrir **Compras → Configuración → Abastecimiento de Industria → Nuevo**.
Seleccionar registros reales; un nombre de lista de precios o de almacén
parecido no garantiza que pertenezca a la compañía correcta.

| Campo | Valor a revisar |
| --- | --- |
| Nombre | Descripción reconocible del abastecimiento |
| Industria Panificadora | `INDUSTRIA PANIFICADORA ALVIÑA E.I.R.L.`, la compañía real abastecedora |
| Responsable de ventas de Industria | Angelo, si es el responsable actual, activo y con Industria/Ventas autorizados |
| Lista de precios de Industria | Lista existente y activa, compartida o de Industria, con los precios acordados y moneda activa |
| Activar flujo de abastecimiento | Dejar desmarcado hasta completar y probar la configuración e integraciones |

Revisar país fiscal, monedas/tipos de cambio e impuestos de Industria y de cada
compradora. El precio empleado es el resultado de la lista seleccionada; si se
espera el precio de venta visible en Productos, la lista debe representar ese
acuerdo. El addon no elige otra lista ni usa costo como sustituto.

Si el responsable se retira, crear o usar su cuenta sustituta mediante el
procedimiento habitual, asignarle el mismo rol dentro de sus compañías
permitidas y seleccionarlo aquí. No cambiar los vendedores históricos para que
pueda ver pedidos anteriores: el nuevo rol ya comparte los abastecimientos.
Si se archiva el responsable anterior y existe exactamente un sustituto activo
con el rol e Industria autorizada, se resuelve ese usuario; con ninguno o varios,
la aplicación pide seleccionar un responsable explícitamente.

## 3. Administrador: vínculo de cada sucursal

Abrir **Compras → Configuración → Vínculos de sucursales Alviña**.
El ejemplo UPAO debe quedar así:

| Campo | Valor correcto |
| --- | --- |
| Sucursal existente | Contacto real **Sucursal UPAO**, no el contacto personal «Sucursal UPAO - User» |
| Identificación de sucursal | Código interno único del local, definido por la empresa; no dejar vacío |
| Empresa solicitante | Compañía operativa real **Sucursal UPAO** |
| Empresa abastecedora | **INDUSTRIA PANIFICADORA ALVIÑA E.I.R.L.** |
| Almacén abastecedor | Almacén real de insumos de Industria, perteneciente a Industria |
| Usuarios autorizados | Usuario solicitante **Sucursal UPAO - User** y demás solicitantes reales del local |
| Recepción de la sucursal | Operación de entrada existente de **Sucursal UPAO**, con destino interno de esa compradora y recepción de un paso |
| Activo | Marcado |

El contacto de la sucursal identifica el local; **Usuarios autorizados** indica
quién puede pedir y confirmar recepción por ese local. Con el rol nuevo no hace
falta incluir a Angelo en todos los vínculos: atiende todas las sucursales
abastecidas por su Industria autorizada. Si mantiene solo el rol antiguo de
almacenero, continúa necesitando su asignación explícita.

**Recepción de la sucursal** no es la recepción del almacén de Industria.
Si la operación compradora no existe, debe configurarse con el administrador de
Inventario y la estructura real del local, antes de continuar. No guardar el
formulario emergente con la compañía/almacén de Industria para simular la entrada
compradora. Las operaciones de entrada y salida deben conservar los faltantes
mediante operaciones pendientes; no configurarlas como «nunca» crear pendientes
si se van a manejar entregas parciales.

El campo heredado **Crear solicitud de cotización** no decide si una sucursal
participa cuando el flujo central está activo: todas siguen el mismo flujo.
La nueva configuración no crea OC/OV para requerimientos enviados anteriormente.

Si la compañía operativa del local es la misma Industria, detener la activación
y revisar la operación interna pendiente. No crear otra compañía para sortear
el bloqueo ni asignar una compañía ajena al local.

## 4. Administrador: catálogo y comprobación previa

En Productos, habilitar únicamente los insumos acordados para requerimientos.
Deben estar activos, compartidos entre compañías, comprables y vendibles, dentro
de una categoría admitida: Comerciales, Útiles de escritorio, Útiles de limpieza
o Envases y embalajes. No se incluyen automáticamente las categorías hijas.

Comprobar los contactos comerciales de Industria y de la compañía compradora,
los impuestos, la lista de precios, ubicaciones/rutas reales y stock del almacén.
Para la recepción guiada actual usar productos sin lotes ni números de serie.
Las integraciones Enterprise y privadas pendientes no se solucionan cambiando
roles o desinstalando módulos.

Activar y probar en una copia representativa solo cuando esos controles estén
resueltos. El número de versión de Aplicaciones muestra el código localizado;
por sí solo no demuestra que se hayan aplicado cambios de base. Seguir la
actualización dirigida de [README.md](README.md), sin desinstalar.

## 5. Sucursal: hacer el pedido

1. Entrar con el usuario real de UPAO a **Compras → Órdenes → Formulario Web**.
   La ruta es `/branch/requisition/new`.
2. Revisar la sucursal asignada. Si solo tiene UPAO no puede cambiarla.
3. La fecha aparece con dos días calendario de anticipación según Perú. Si hoy
   es 21, aparece 23; puede elegir 23 o después, nunca 21 ni 22.
4. Elegir productos y cantidades de las categorías habilitadas. Puede cambiar
   categoría conservando sus cantidades y añadir observaciones.
5. Enviar. Conservar la referencia `ALV/...` de confirmación.

Odoo crea el requerimiento en la compañía de UPAO, su OC a Industria y la OV de
Industria, los vincula y confirma los estados técnicos. Se pueden consultar la
OC y requerimiento desde Compras según los permisos de la sucursal. No hay un
segundo botón de aprobación comercial requerido al usuario y todavía no hay
unidades recibidas ni facturas por el solo envío.

## 6. Logística: preparar y despachar

1. Entrar con Angelo o el sustituto autorizado. Seleccionar Industria.
2. Abrir **Ventas → Órdenes → Pedidos de sucursales**. Ese acceso muestra los
   abastecimientos, incluidos los asignados al responsable anterior.
3. Abrir la OV correspondiente y su operación de entrega. Revisar sucursal,
   productos, fecha requerida y observaciones.
4. Registrar las cantidades físicas que realmente salen. Si son menores,
   indicar el motivo del faltante y conservar el saldo pendiente.
5. Validar el despacho. Odoo registra la salida real y emite su guía interna.
   Abrir la guía de la entrega e imprimir el PDF que acompaña los insumos.

No usar `/portal/production/new`: es el formulario anterior de producción.
No usar «Pruebe con un ejemplo» de una lista vacía para crear una venta de prueba
que reemplace al requerimiento. Si no hay pedidos, revisar configuración activa,
compañía seleccionada, fecha y referencia del envío. Los históricos sin OC/OV
no aparecen como nuevas ventas por actualizar el addon.

## 7. Sucursal: confirmar lo que llegó

1. Abrir **Compras → Órdenes → Guías internas y recepción** con el usuario del local.
2. Abrir la guía que llegó y pulsar **Confirmar recepción real**.
3. Introducir lo realmente recibido para cada producto; las cantidades no se
   dan por recibidas automáticamente. No copiar lo enviado si llegó menos.
4. Si existe diferencia, explicar el motivo. Confirmar recepción una sola vez.

La aplicación valida la recepción real de la OC y registra la conformidad en la
misma acción. Si recibió lo enviado, queda **Recepción conforme**; si recibió
menos, **Recepción con diferencias**. La guía conserva quién confirmó y cuándo.
No se puede recibir más que lo documentado ni reescribir una confirmación cerrada.

Si no llegó ninguna unidad, indicar cero y explicar el motivo. Se conserva la
recepción con diferencias sin inventar una entrada de Inventario vacía.

| Cantidad de ejemplo | Unidades | Significado |
| --- | ---: | --- |
| Pedido de UPAO | 10 | Demanda original |
| Despacho de Industria | 8 | Salida real que figura en la guía |
| Recepción de UPAO | 7 | Entrada real que confirma el local |
| Pendiente de despacho | 2 | Todavía no salió de Industria |
| Diferencia de recepción | 1 | Salió en esta guía, pero el local no lo recibió |

Si recibe las 8, la guía queda conforme aunque falten otras 2 del pedido.
Una diferencia no crea una reposición ni descuenta otra vez el stock de
Industria. Logística y sucursal deben revisar su causa con ese registro.
La guía es interna y valorizada; no se envía a SUNAT ni crea una factura.

## Comprobación de aceptación

En una copia de pruebas, verificar con las tres cuentas un pedido nuevo, entrega
completa, entrega parcial y recepción con diferencia. Confirmar que Logística
ve todas las sucursales abastecidas por su Industria y ninguna venta común;
que otra sucursal no ve esta guía; que OC/OV no generan facturas; y que las
cantidades físicas se registran solo mediante los dos pasos operativos descritos.
Consultar [TESTING.md](TESTING.md) para los casos automatizados y límites.
