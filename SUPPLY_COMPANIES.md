# Industria abastece a las sucursales — versión 19.0.1.1.0

## Flujo para el usuario

Industria puede centralizar la compra y el abastecimiento desde su almacén, mientras cada sucursal registra sus necesidades con su propio usuario y compañía. El requerimiento expresa una necesidad: no es una venta, compra, factura ni transferencia.

El almacenero de Industria ve las solicitudes de las sucursales que tenga asignadas y un consolidado por producto/almacén/empresa abastecedora. Si UPAO y otra sucursal pertenecen a compañías diferentes pero piden al mismo almacén de Industria, primero se suman las cantidades y después se descuenta una sola vez el stock libre y las entradas confirmadas. La compra sugerida sigue siendo informativa.

Cuando corresponda vender o entregar los productos, debe utilizarse el proceso habitual de Alviña. Esta versión no genera automáticamente ventas, compras, facturas ni movimientos. El registro de atención parcial/final continúa pendiente de integración.

## Configuración en pruebas

Desde una cuenta administradora con `Alviña: Configuración`, abrir Compras → Configuración → Vínculos de sucursales Alviña. Utilizar registros existentes:

| Campo | Ejemplo de la configuración confirmada por el usuario |
| --- | --- |
| Sucursal existente | Contacto de sucursal existente → Sucursal UPAO |
| Empresa solicitante | La compañía Sucursal UPAO |
| Empresa abastecedora | INDUSTRIA PANIFICADORA ALVIÑA E.I.R.L. |
| Almacén abastecedor | Insumos de INDUSTRIA PANIFICADORA ALVIÑA E.I.R.L. |
| Usuarios autorizados | Sucursal UPAO - User y el almacenero de Industria responsable |
| Activo | Sí |

Los nombres anteriores son ejemplos basados en las capturas, nunca identificadores codificados ni instrucciones para crear duplicados. Confirmar los registros exactos en la base de pruebas. La empresa solicitante se configura explícitamente: el `company_id` de un contacto indica quién mantiene esa ficha comercial, y no identifica necesariamente a la compañía que solicita. El contacto puede estar compartido o pertenecer a la empresa solicitante o abastecedora; otra compañía es rechazada.

El usuario UPAO mantiene acceso a su compañía y el rol `Alviña: Solicitante`. **No necesita añadir Industria a sus compañías permitidas.** El almacenero mantiene Industria y el rol `Alviña: Almacenero`, además de la asignación explícita a las sucursales que atenderá. No necesita acceso general a la compañía de UPAO para revisar sus requerimientos asignados. La cuenta administradora debe tener los accesos apropiados para configurar las compañías y contactos existentes.

El formulario sigue sin mostrar campos de empresa. La sucursal se selecciona automáticamente si existe una sola asignación; con varias, se permiten las autorizadas en las compañías solicitantes activas. Los productos proceden del catálogo habilitado de la empresa abastecedora o de productos compartidos, sin divulgar costes, proveedores ni existencias al solicitante mediante el formulario.

## Actualizar desde 19.0.1.0.1

La autorización actual permite preparar código y pruebas; no actualizar producción. El administrador debe validar primero esta actualización en una copia de pruebas con respaldo de base y filestore.

1. Colocar **la carpeta completa** `alvina_branch_requisition` de la nueva revisión en la ruta de addons de pruebas. Incluir `migrations/19.0.1.1.0/`; no transferir únicamente los archivos Python modificados.
2. Con los procesos Odoo de esa base de pruebas detenidos, usar el Python y la configuración reales de pruebas:

```bash
/path/to/odoo/odoo-bin -c /path/to/test.conf -d ALVINA_TEST \
  -u alvina_branch_requisition --stop-after-init
```

3. Arrancar el servicio de pruebas con el mismo código. Reiniciar por sí solo no actualiza campos, vistas ni migraciones. No desinstalar para actualizar: se perderían registros propios del addon.
4. Verificar en Apps la versión `19.0.1.1.0` y la aparición de Empresa solicitante / Empresa abastecedora / Almacén abastecedor en el vínculo.
5. Configurar UPAO como solicitante e Industria como abastecedora, sin ampliar las compañías permitidas del usuario UPAO. Si el intento anterior nunca se guardó, crear un vínculo nuevo; si ya hay uno sin solicitudes, puede corregirse. No crear otro contacto ni otro vínculo para la misma sucursal.
6. Probar el formulario como usuario UPAO y el consolidado como almacenero Industria. Comprobar que continúan denegados los documentos y existencias privados de Industria para el usuario UPAO.

La migración conserva la compañía solicitante de todos los registros existentes y obtiene la abastecedora desde el almacén de cada vínculo. No convierte solicitudes históricas de una compañía a otra. Si un vínculo ya tiene historial y su empresa solicitante se configuró erróneamente antes, corregirlo requiere una migración específica revisada; no borrar solicitudes para eludir ese bloqueo.

## Validación técnica

Las reglas permiten al solicitante sus sucursales asignadas en sus compañías activas y al almacenero las sucursales asignadas abastecidas por sus compañías activas. Son permisos sobre los modelos de requerimientos; no se modifican las reglas estándar de compras, inventario, productos o compañías ni `res.users.company_ids`.

El catálogo utiliza lectura elevada limitada a productos habilitados y solo presenta ID, nombre/código, categoría y UoM. La cabecera y las líneas se crean con el usuario real, sin `sudo()`. Los campos de empresa, proveedor y almacén se derivan en el servidor del vínculo; el cliente no puede suplantarlos. El almacenero consulta las existencias con sus permisos normales y el contexto de su almacén abastecedor.

La actualización real desde `bf19163` fue probada con dos compañías diferentes de la compañía del administrador, vínculos activos/archivados y solicitudes históricas. Las migraciones previas/posteriores preservan usuarios, compañías permitidas, compañías solicitantes, historia, cantidades, compras y movimientos. La fase posterior evita dejar vacíos los campos relacionados de las líneas por el orden de inicialización de Odoo 19; ambas fases se repitieron sin cambios adicionales.

Para reproducir la prueba de actualización, `tools/check_supply_upgrade.py` documenta las fases `prepare` con la versión antigua y `verify` con la nueva. El probe rechaza bases ajenas a `alvina_supply_upgrade_test` y conexiones remotas; crea fixtures y hace commit únicamente en esa base desechable. No ejecutar en una base con información importante.
