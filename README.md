# Alviña — Requerimientos de sucursales

Addon técnico `alvina_branch_requisition`, versión objetivo Odoo 19. No crea una aplicación: `application=False`, sin menú raíz ni icono. Depende de `purchase`, `stock`, `purchase_stock`, `portal` (y sus dependencias transitivas). No requiere bibliotecas frontend externas.

## Menús y aislamiento

Los tres accesos se agregan bajo `purchase.menu_procurement_management` (Compras → Órdenes): Formulario Web (`ir.actions.act_url`), Requerimientos (`ir.actions.act_window`) y Consolidado de compras (`ir.actions.act_window`). Identificador contrastado con el código oficial de Odoo 19:
https://github.com/odoo/odoo/blob/19.0/addons/purchase/views/purchase_views.xml

No se modifican los archivos de purchase ni Ventas, ni las acciones de cotización o compra. La única vista estándar heredada añade la habilitación de productos; no altera el formulario de Ventas.

## Integración adaptable, pendiente de validar

`alvina.branch.binding` es un vínculo de configuración, NO un catálogo paralelo de sucursales. Un administrador selecciona un registro real existente mediante `resource_ref`, su compañía, almacén abastecedor y usuarios autorizados. Se impiden vínculos repetidos y cambios de identidad/almacén cuando existe historial. No vincular entidades arbitrarias: primero confirmar cuál representa realmente la sucursal en la instalación. El administrador asigna también los almaceneros a las sucursales bajo su responsabilidad. Las reglas globales restringen cabeceras y líneas por compañía y asignación; ser administrador no concede acceso a todas las solicitudes.

Pendientes: modelo real y sincronización con asignaciones de usuarios existentes; reglas específicas del negocio; categorías homónimas o categorías hijas; política de almacenes; abastecimientos ya asignados; compatibilidad con addons privados; inspección de plantillas/controlador de `/portal/production/new`. El diseño granate es provisional y NO se afirma equivalencia visual con el formulario desconocido de Ventas.

Las categorías se resuelven por sus cuatro nombres exactos, no por IDs: Comerciales, Útiles de escritorio, Útiles de limpieza, Envases y embalajes. No se crean categorías. Los productos deben estar activos y habilitados explícitamente mediante `alvina_requisition_enabled` en su ficha. No se consulta stock para permitir solicitudes. Orden natural por código, nombre e ID; conserva la representación y los ceros iniciales; sin código al final. No incluye subcategorías automáticamente.

## Funcionalidad y límites de la primera entrega

- Formulario autenticado `/branch/requisition/new`, CSRF, sucursal automática bloqueada si es única y selección entre asignadas si son varias. Sin asignación impide el envío.
- Cantidades conservadas entre categorías, distintas categorías por solicitud; cambiar sucursal limpia las cantidades para evitar mezclar compañías. No muestra selector de empresa ni contador.
- Validación de productos, compañía, habilitación, cantidades finitas y múltiplos de redondeo de UoM. No guarda ceros; rechaza duplicados y negativos. Token por formulario y restricción SQL contra doble envío. Ante error, vuelve a mostrar un formulario nuevo; las cantidades no se recuperan después de un error de servidor.
- Solicitudes enviadas inmutables, pendientes, con revisión/cancelación por almacenero. No permite borrar historial ni editar entregas por RPC. No incluye borradores editables.
- Campos de cantidades atendidas/parcial/atendido preparados para una integración futura. NO hay procedimiento de entregas ni transición a atendido en esta fase: las entregas no deben inventarse. La cancelación solo admite solicitudes sin cantidades atendidas.
- Consolidación bajo permisos del usuario, por producto/almacén/compañía, en la UoM base del producto, capturada al enviar. Si después cambia esa unidad, el consolidado se bloquea para evitar interpretar cantidades históricas en unidades diferentes. Las líneas de origen muestran el desglose por sucursal y solicitud. Recalcular obtiene datos actuales y excluye canceladas/atendidas.
- Consulta `free_qty` (existencias menos reservas) e `incoming_qty` del almacén: incluye movimientos entrantes confirmados de Odoo, NO suma órdenes de compra por separado. Sugerencia `max(pendiente - max(stock_libre,0) - max(entradas,0),0)`. No duplica compras y recepciones mediante sumas paralelas. No implementa asignaciones exclusivas de entradas, ventanas temporales ni compensación de inventario negativo: no es un motor de aprovisionamiento completo. Es informativa y puede requerir ajuste tras conocer el proceso real.
- No crea órdenes, transferencias, recepciones ni cambios en existencias.

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
5. Verificar las cuatro categorías existentes y habilitar los productos deseados en su ficha. No importar duplicados.
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

Antes de aceptar para despliegue faltan pruebas con Enterprise y addons reales, navegador completo, doble envío concurrente, aislamiento multiempresa con datos operativos, reservas/recepciones reales y regresión del formulario de Ventas desconocido. Las comprobaciones HTTP y DOM locales se detallan en TESTING.md.

## Desinstalar y verificar

En la base de pruebas, respaldar base y filestore y desinstalar desde Aplicaciones mediante el mecanismo estándar. Se eliminarán registros y campos propios del addon; la copia de seguridad es necesaria para recuperarlos. Se comprobó la desinstalación estándar con registros de prueba en Community y se preservaron las entidades originales, existencias, documentos estándar y menús de Compras. Esto no garantiza reversibilidad en Enterprise ni recupera registros eliminados: restaurar un respaldo sigue siendo necesario. Verificar que desaparecen los tres menús y el campo añadido, que sucursales/productos/categorías originales permanecen y que Ventas/Compras/Inventario mantienen sus flujos, documentos y existencias. Restaurar el respaldo si se necesita recuperar las solicitudes.

## GitHub

Rama prevista: `feature/branch-requisition-form`. Revisar el diff, ejecutar la suite Odoo y crear un PR contra la rama base cuando exista. El repositorio originalmente no tenía `main`: un PR necesita una rama base y un historial comparables. No se crea una rama principal ni se fusionan cambios automáticamente. Subir la rama no instala el addon en Odoo. No desplegar ni fusionar sin autorización.

Pruebas de interacción DOM (jsdom, dependencia solo de pruebas):

```bash
npm install --cache /tmp/alvina-npm-cache --prefix /tmp/alvina-js-test --no-package-lock --no-audit --no-fund jsdom@26.1.0
NODE_PATH=/tmp/alvina-js-test/node_modules node --test tools/test_frontend.cjs
```

El workflow `.github/workflows/tests.yml` prepara PostgreSQL y Odoo Community fuera del addon, ejecuta las comprobaciones locales e instala/prueba el addon en una base desechable. Se ha preparado para GitHub; no se afirma que haya corrido en GitHub Actions.

`tools/check_uninstall.py` contiene la comprobación destructiva de desinstalación utilizada. Solo admite la base local desechable `alvina_requisition_test`; crea registros, hace commit y desinstala el addon. Ejecutarlo únicamente con Odoo shell en esa base de pruebas, nunca en una copia con información importante. Después reinstalar el addon con `-i` y repetir la suite.
