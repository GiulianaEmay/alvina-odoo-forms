# Entrega actual: flujo sucursales → Industria — 19.0.2.0.0

> Recuperación del incidente del 19/10/2026: rama `fix/requisition-startup-recovery`.
> El ZIP operativo tenía `models/commercial.py` sustituido por una copia de `branch.py`.
> Esta rama conserva el archivo correcto. Véase [diagnóstico y recuperación](RECOVERY_2026-10-19.md).
> Antes de transferir el addon, ejecutar `python tools/check_addon_package.py`.

Rama `feature/intercompany-purchase-sales-flow`. Addon técnico bajo **Compras → Órdenes**, sin aplicación ni menú raíz. Conserva formulario, requerimientos, consolidado e historia anteriores y añade OC/OV en borrador, entregas reales y PDF valorizado para compañías distintas.

**Estado: validado en Community; integración Enterprise pendiente.** No activar en producción. El automatismo nativo instalado sin adaptador auditado y las sucursales que comparten compañía con Industria quedan bloqueados expresamente. No se han creado compañías ficticias ni ampliado permisos. No se ha desplegado nada.

Antes de actualizar, identificar el **commit instalado**: también existe `feature/central-supply-multicompany`, con otro esquema y el mismo número de versión anterior. Se conserva intacta; migrar desde ella requiere un mapeo específico y la actualización se bloquea si detecta su tabla de asignaciones.

- [Configuración, comportamiento, seguridad, precios y límites actuales](INTERCOMPANY_FLOW.md).
- [Auditoría nativa/privada y datos necesarios para completar la integración](NATIVE_INTERCOMPANY.md).
- [Pruebas y evidencias](TESTING.md).
- [Traspaso a otra cuenta](TRANSFER.md).

Dependencias actuales: `purchase`, `stock`, `purchase_stock`, `sale_management`, `sale_stock`, `portal`, `website`. Copiar **solo la carpeta completa `alvina_branch_requisition/`** a la raíz de addons del repositorio operativo, al mismo nivel que sus otros addons; no anidar el repositorio entero dentro del addon. Usar primero una copia de pruebas respaldada. El código, documentación y herramientas de pruebas del repositorio de desarrollo se conservan para revisión.

En pruebas, con el servicio de esa base detenido, ejecutar con el Python y configuración reales de Odoo 19:

```bash
/path/to/odoo/odoo-bin -c /path/to/test.conf -d ALVINA_TEST \
  -u alvina_branch_requisition --stop-after-init
```

Para una instalación nueva usar `-i` en lugar de `-u`. Conservar todas las carpetas `migrations/`; reiniciar no actualiza campos/vistas/migraciones y desinstalar elimina datos propios. La configuración central nace desactivada y no genera documentos históricos. No activar el nuevo flujo hasta resolver los límites anteriores.

## Documentación histórica del modo anterior — 19.0.1.2.0

Las siguientes secciones describen el modo anterior, conservado mientras la configuración central nueva esté desactivada. Para el flujo actual prevalece `INTERCOMPANY_FLOW.md`; las afirmaciones históricas de que aún no existen ventas/entregas/PDF no describen la nueva implementación.

# Alviña — Requerimientos de sucursales

Addon técnico `alvina_branch_requisition`, versión histórica `19.0.1.2.0` para Odoo 19. No crea una aplicación: `application=False`, sin menú raíz ni icono. Depende de `purchase`, `stock`, `purchase_stock`, `portal`, `website` (y sus dependencias transitivas). No requiere bibliotecas frontend externas.

## Menús y aislamiento

Los tres accesos se agregan bajo `purchase.menu_procurement_management` (Compras → Órdenes): Formulario Web (`ir.actions.act_url`), Requerimientos (`ir.actions.act_window`) y Consolidado de compras (`ir.actions.act_window`). Identificador contrastado con el código oficial de Odoo 19:
https://github.com/odoo/odoo/blob/19.0/addons/purchase/views/purchase_views.xml

No se modifican los archivos originales de purchase ni Ventas, ni las acciones estándar de cotización o compra. La integración hereda `purchase.order` para vincular las cotizaciones creadas por el formulario; las compras ordinarias conservan su flujo. La vista estándar de productos heredada añade su habilitación para requerimientos; no altera el formulario de Ventas.

## Integración adaptable, pendiente de validar

`alvina.branch.binding` vincula un contacto de sucursal existente (`res.partner`), la empresa solicitante, la empresa abastecedora, su almacén y los usuarios autorizados. No crea contactos ni sucursales. El selector se limita a contactos; un adaptador explícito puede extender los modelos permitidos, nunca habilitar indiscriminadamente toda la base. Se impiden vínculos repetidos y cambios de identidad/almacén cuando existe historial; cambiar un almacén en ese caso requiere una migración controlada, no archivar y duplicar el contacto. El administrador asigna también los almaceneros a las sucursales bajo su responsabilidad. Las reglas globales restringen cabeceras y líneas por compañía y asignación; ser administrador no concede acceso a todas las solicitudes.

El ZIP `alvinha-cybe.zip` permitió localizar `/portal/production/new` en `alvinha_mrp` y la clasificación `res.partner.type_client = 'branch'` en `alvinha_base`. No contiene una relación personalizada de usuarios con varias sucursales. Véase [INTEGRATION.md](INTEGRATION.md) para referencias y dónde colocar la carpeta del addon. En la instalación real se deben seleccionar únicamente contactos de sucursales reales; el núcleo no instala ni simula los campos privados.

Pendientes: confirmar la revisión desplegada, asignaciones de usuarios en la base, configuración de almacenes, categorías homónimas/hijas, abastecimientos asignados y coexistencia con Enterprise y módulos privados. La presentación propia utiliza el mismo `website.layout`, color de título y patrones Bootstrap encontrados; la equivalencia exacta del tema requiere una base de pruebas con ese tema.

Las categorías se resuelven por sus cuatro nombres exactos, no por IDs: Comerciales, Útiles de escritorio, Útiles de limpieza, Envases y embalajes. No se crean categorías. Los productos deben estar activos y habilitados explícitamente mediante `alvina_requisition_enabled` en su ficha. No se consulta stock para permitir solicitudes. Orden natural por código, nombre e ID; conserva la representación y los ceros iniciales; sin código al final. No incluye subcategorías automáticamente.

## Abastecimiento central y compañías distintas

Industria puede abastecer a UPAO y otras sucursales sin añadir Industria a las compañías permitidas de los usuarios solicitantes. El vínculo separa **Empresa solicitante**, **Empresa abastecedora** y **Almacén abastecedor**. La solicitud pertenece a la primera; el stock y el consolidado se consultan en la segunda. Los almaceneros requieren asignación explícita a las sucursales; no se modifican los permisos estándar de otras compañías.

Consultar [SUPPLY_COMPANIES.md](SUPPLY_COMPANIES.md) para configurar el caso real confirmado por el usuario y actualizar desde `19.0.1.0.1`, incluidas las migraciones de datos. La nueva versión debe actualizarse primero en pruebas; el repositorio no modifica el servidor por sí solo.

## Solicitudes de cotización y precios

El administrador puede activar **Crear solicitud de cotización** en cada vínculo de sucursal. Está desactivado por defecto, también al actualizar: los requerimientos históricos no generan documentos nuevos. Cada envío posterior, con esta opción activada y configuración válida, crea una única solicitud de cotización estándar en borrador. Su empresa compradora es la sucursal solicitante, su proveedor es el contacto de la empresa abastecedora y su origen identifica el requerimiento. En Compras → Órdenes → Solicitudes de cotización, al agrupar por empresa, aparece bajo la sucursal que solicitó.

Debe configurarse una **Recepción de la sucursal** activa de la empresa compradora. Es distinta del almacén abastecedor de Industria. Para este flujo, el catálogo incluye únicamente productos compartidos, habilitados para compras y para requerimientos, dentro de las cuatro categorías. El contacto proveedor de Industria debe estar disponible para la empresa compradora; para atender varias compañías suele corresponder un contacto compartido, sujeto a revisión administrativa. El addon no comparte, duplica ni cambia automáticamente productos o contactos.

Los nuevos requerimientos guardan el precio de venta del producto, incluidos extras de variante, convertido desde la moneda real del producto a la moneda solicitante en la fecha de envío. Guardan también el importe por línea y el total solicitado. Los cambios posteriores de precio no revalorizan ese registro. No se usa el costo de inventario ni el precio de proveedor. Los históricos sin precio capturado se identifican como tales: no se inventa su valorización. El valor solicitado es cantidad por precio registrado; no acredita entregas. La cotización aplica los impuestos de compra configurados para la empresa compradora y requiere revisión fiscal antes de confirmarla.

La creación se limita a un documento en borrador: el núcleo revisado no confirma compras, envía correos, genera facturas ni mueve existencias. Los efectos de módulos Enterprise o automatizaciones privadas requieren validación en una base de pruebas representativa. Si falla la creación de la cotización, tampoco se guarda un requerimiento incompleto.

Los permisos estándar de Compras siguen vigentes. Para ver las cotizaciones de varias sucursales en la lista estándar, el comprador necesita acceso a esas compañías. Un almacenero con acceso solo a Industria puede seguir revisando sus requerimientos asignados y el consolidado, sin acceder por ello a las cotizaciones privadas de las sucursales. No es necesario añadir Industria a las compañías del usuario solicitante.

## Funcionalidad y límites actuales

- Formulario autenticado `/branch/requisition/new`, CSRF, sucursal automática bloqueada si es única y selección entre asignadas si son varias. La ruta recupera las compañías realmente permitidas al usuario para evitar que el contexto del sitio web oculte una sucursal asignada; no altera sus membresías ni las reglas de otras rutas. Sin asignación impide el envío.
- Cantidades conservadas entre categorías, distintas categorías por solicitud; cambiar sucursal limpia las cantidades para evitar mezclar compañías. No muestra selector de empresa ni contador.
- Validación de productos, compañía, habilitación, cantidades finitas y múltiplos de redondeo de UoM. No guarda ceros; rechaza duplicados y negativos. Token por formulario y restricción SQL contra doble envío. Ante error, vuelve a mostrar un formulario nuevo; las cantidades no se recuperan después de un error de servidor.
- Solicitudes enviadas inmutables, pendientes, con revisión/cancelación por almacenero. No permite borrar historial ni editar entregas por RPC. No incluye borradores editables de requerimientos. Si hay una cotización vinculada, debe cancelarse primero desde Compras para cancelar el requerimiento.
- Campos de cantidades atendidas/parcial/atendido preparados para una integración futura. NO hay procedimiento de entregas ni transición a atendido en esta fase: las entregas no deben inventarse. La cancelación solo admite solicitudes sin cantidades atendidas.
- Consolidación bajo permisos del usuario, por producto/almacén/empresa abastecedora, sumando primero las necesidades de las distintas compañías solicitantes, en la UoM base del producto, capturada al enviar. Si después cambia esa unidad, el consolidado se bloquea para evitar interpretar cantidades históricas en unidades diferentes. Las líneas de origen muestran el desglose por sucursal y solicitud. Recalcular obtiene datos actuales y excluye canceladas/atendidas.
- Consulta `free_qty` (existencias menos reservas) e `incoming_qty` del almacén: incluye movimientos entrantes confirmados de Odoo, NO suma órdenes de compra por separado. Sugerencia `max(pendiente - max(stock_libre,0) - max(entradas,0),0)`. No duplica compras y recepciones mediante sumas paralelas. No implementa asignaciones exclusivas de entradas, ventanas temporales ni compensación de inventario negativo: no es un motor de aprovisionamiento completo. Es informativa y puede requerir ajuste tras conocer el proceso real.
- Puede crear la solicitud de cotización en borrador descrita arriba, exclusivamente si se habilita en el vínculo. No crea compras confirmadas, ventas, facturas, transferencias, recepciones ni cambios en existencias al enviar el formulario.

## Instalación exclusivamente en pruebas

Se requiere un servidor Odoo **19** con el código Community y Enterprise autorizado, PostgreSQL y una base de pruebas aislada. No se incluyen Odoo ni Enterprise en este repositorio. Usar el checkout existente; las tareas cloud ya están aisladas, no crear worktrees salvo petición expresa.

1. Respaldar la base de pruebas y filestore si contienen información importante.
2. Añadir la ruta absoluta de este repositorio a `addons_path`, preservando todas las rutas existentes. Usar configuración local fuera del repositorio, sin subir credenciales.
3. Con el servicio de pruebas detenido (nunca producción), ejecutar con el Python y dependencias de su Odoo:

```bash
/path/to/odoo/odoo-bin -c /path/to/test.conf -d ALVINA_TEST \
  -i alvina_branch_requisition --without-demo --stop-after-init
```

4. Arrancar el servicio de pruebas con la misma configuración. Asignar el grupo «Alviña: Configuración» al administrador responsable; acceder a vínculos desde Compras → Configuración (requiere permisos de configuración de Compras), o desde el modelo mediante herramientas técnicas. Configurar únicamente sucursales reales. Asignar los grupos Solicitante/Almacenero según corresponda.
5. Verificar las cuatro categorías existentes y habilitar los productos deseados en su ficha. No importar duplicados. Para cotizaciones, comprobar además que los productos estén compartidos y habilitados para compras; revisar el contacto proveedor, seleccionar la recepción de la sucursal y activar la opción en el vínculo. Véase SUPPLY_COMPANIES.md.
6. Abrir Compras → Órdenes → Formulario Web. Para usuarios portal, abrir directamente la ruta web: el menú interno de Compras depende de los permisos estándar de Compras; no se amplían esos permisos a solicitantes automáticamente.
7. Comprobar envío, acceso de un segundo usuario y consolidado. La publicación cloud y los procesos de Odoo no están configurados por estos comandos.

Actualizar solo en pruebas y tras respaldo:

```bash
/path/to/odoo/odoo-bin -c /path/to/test.conf -d ALVINA_TEST \
  -u alvina_branch_requisition --stop-after-init
```

## Pruebas

Comprobaciones locales sin Odoo:

```bash
python -m unittest discover -s tools -v
python -m compileall -q alvina_branch_requisition
```

Suite de integración que exige Odoo/PostgreSQL y base aislada:

```bash
/path/to/odoo/odoo-bin -c /path/to/test.conf -d ALVINA_TEST \
  -i alvina_branch_requisition --test-enable \
  --test-tags /alvina_branch_requisition --stop-after-init --without-demo
```

La suite contiene pruebas de creación, acceso a cabeceras y líneas, inmutabilidad, productos deshabilitados, cantidades negativas, duplicados, compañía y consolidación/cancelación. Las pruebas Python sin Odoo no validan ACL, vistas ni ejecución de Odoo. La suite se ejecutó en una instancia temporal de Odoo 19 Community y PostgreSQL local. Véase TESTING.md para versiones, resultados y límites; no se validó Enterprise ni la instalación real de Alviña.

La suite incluye una prueba con Chromium real: carga de assets, orden de productos, persistencia entre categorías, borrado de cantidad y envío al servidor. Requiere Chromium/Chrome y `websocket-client==1.8.0`; comprobar que el runner no la marque como omitida. Antes de aceptar para despliegue faltan pruebas con Enterprise, tema y addons reales, doble envío concurrente, datos operativos y regresión del formulario de producción existente. Las comprobaciones locales se detallan en TESTING.md.

## Desinstalar y verificar

En la base de pruebas, respaldar base y filestore y desinstalar desde Aplicaciones mediante el mecanismo estándar. Se eliminarán registros y campos propios del addon; la copia de seguridad es necesaria para recuperarlos. Se comprobó la desinstalación estándar con registros de prueba en Community y se preservaron las entidades originales, existencias, documentos estándar y menús de Compras. Esto no garantiza reversibilidad en Enterprise ni recupera registros eliminados: restaurar un respaldo sigue siendo necesario. Verificar que desaparecen los tres menús y el campo añadido, que sucursales/productos/categorías originales permanecen y que Ventas/Compras/Inventario mantienen sus flujos, documentos y existencias. Restaurar el respaldo si se necesita recuperar las solicitudes.

## GitHub

La entrega multiempresa utiliza `feature/multi-company-supply`; `feature/branch-requisition-form` conserva la implementación anterior. Revisar el diff, ejecutar la suite Odoo y crear un PR contra la rama base cuando exista. El repositorio originalmente no tenía `main`: un PR necesita una rama base y un historial comparables. No se crea una rama principal ni se fusionan cambios automáticamente. Subir la rama a este repositorio de desarrollo no instala el addon en Odoo. En el repositorio operativo, confirmar antes si la rama elegida dispara despliegues automáticos. No desplegar ni fusionar sin autorización.

Pruebas de interacción DOM (jsdom, dependencia solo de pruebas):

```bash
npm install --cache /tmp/alvina-npm-cache --prefix /tmp/alvina-js-test --no-package-lock --no-audit --no-fund jsdom@26.1.0
NODE_PATH=/tmp/alvina-js-test/node_modules node --test tools/test_frontend.cjs
```

El workflow `.github/workflows/tests.yml` prepara PostgreSQL y Odoo Community fuera del addon, ejecuta las comprobaciones locales e instala/prueba el addon en una base desechable. Se ha preparado para GitHub; no se afirma que haya corrido en GitHub Actions.

`tools/check_uninstall.py` contiene la comprobación destructiva de desinstalación utilizada. Solo admite la base local desechable `alvina_requisition_test`; crea registros, hace commit y desinstala el addon. Ejecutarlo únicamente con Odoo shell en esa base de pruebas, nunca en una copia con información importante. Después reinstalar el addon con `-i` y repetir la suite.
