# Traspaso del desarrollo multiempresa

Este documento conserva el estado de la entrega `19.0.1.1.0` y, al final, la continuación autorizada para `19.0.1.2.0`. Las restricciones y resultados de cada bloque corresponden a ese momento; la versión y las pruebas actuales se consultan en el bloque de continuación y en `TESTING.md`.

## Entrega histórica: 19.0.1.1.0

Estado recuperado el 15 de octubre de 2026. Rama de entrega:
`feature/multi-company-supply`, basada en `bf1916364624638308a57be5d7e3a16df9e4af70`
de `feature/branch-requisition-form`. No se fusionó ni sobrescribió la rama original.
Versión del addon: `19.0.1.1.0`.

## Implementación conservada

1. El vínculo y las solicitudes separan empresa solicitante, empresa abastecedora
   y almacén abastecedor. No se crean empresas ni sucursales reales.
2. UPAO puede solicitar con su propia compañía a un almacén de Industria. El catálogo
   admite productos compartidos o de la abastecedora, habilitados expresamente.
3. Las reglas exigen asignación de sucursal y la compañía activa correspondiente.
   El usuario UPAO no necesita acceso general a Industria; el almacenero de Industria
   puede revisar los requerimientos asignados sin acceso general a la empresa UPAO.
   No se alteran las reglas estándar de Compras, Inventario, productos o compañías.
4. `migrations/19.0.1.1.0/` conserva la compañía solicitante, obtiene la abastecedora
   del almacén y rellena los nuevos campos relacionados de cabeceras y líneas
   históricas, incluidos vínculos archivados.
5. El consolidado agrupa por producto, almacén y abastecedora: suma las necesidades
   de las sucursales antes de descontar una sola vez stock libre y entradas.

Se conservan también las pruebas nuevas, el probe de actualización, la documentación
y la corrección pendiente del CI para utilizar PostgreSQL local sin servicio Docker.

## Evidencia disponible al recuperar el trabajo

- Suite completa en Odoo 19 Community: **46 pruebas, 0 fallos y 0 errores**.
  Incluye pruebas multiempresa y Chromium real. Registro de esta máquina:
  `/tmp/alvina-supply-tests-final.log`.
- Actualización real desde `19.0.1.0.1` en la base desechable
  `alvina_supply_upgrade_test`: verificada, incluidas líneas históricas y repetición
  de las migraciones. Probe reproducible: `tools/check_supply_upgrade.py`.
- Las 6 pruebas Python y 5 pruebas DOM habían pasado en esta sesión.
- El helper de PostgreSQL del CI se comprobó localmente, incluida repetición
  idempotente y conexión con su rol sin superusuario. La nueva ejecución remota
  de GitHub Actions queda sin verificar.

Los archivos de `/tmp` y las bases de prueba no se transfieren mediante Git. El
código y las pruebas reproducibles sí están en este repositorio. `TESTING.md`
conserva además la evidencia de la auditoría anterior de 34 pruebas.

## Cómo retomar desde otra cuenta

Conectar esta cuenta de Codex al repositorio autorizado
`GiulianaEmay/alvina-odoo-forms` y seleccionar `feature/multi-company-supply`.
Leer primero `README.md`, `SUPPLY_COMPANIES.md`, `INTEGRATION.md` y este documento.
Usar el checkout aislado disponible; no es necesario crear un worktree.
Las instrucciones de preparación y ejecución de pruebas están en el README y
`.github/workflows/tests.yml`; Odoo oficial y Enterprise no se incluyen en Git.

## Límites y autorización

No se accedió, instaló, actualizó ni desplegó nada en producción ni se escribió
en `SoyCalidad/alvinha`. Publicar esta rama no cambia el Odoo instalado.
Una actualización del addon requiere primero una base de pruebas, respaldo y
la carpeta completa, incluidas las migraciones; reiniciar el servidor no basta.
No desinstalar el addon para actualizarlo.

Quedan por validar Enterprise, el tema y los addons privados en una copia
representativa de la instalación. La atención parcial/final de solicitudes
continúa pendiente; este módulo no genera ventas, compras, facturas ni movimientos
automáticos. No ampliar las compañías permitidas de UPAO para eludir el error de
la versión anterior. Un vínculo con historial y compañía solicitante incorrecta
requiere una migración específica; no cambiar ni borrar su historial.

La instrucción de esa etapa fue conservar y transferir lo existente, sin
desarrollar nuevas funciones, fusionar ramas ni desplegar en producción.
La continuación autorizada posteriormente se describe a continuación.

## Continuación autorizada: 19.0.1.2.0

Después del traspaso, el usuario precisó el flujo mediante capturas de Compras y productos y autorizó continuar la implementación y publicación en el repositorio de desarrollo. La prohibición de desplegar o modificar producción permanece vigente. No se fusiona ni sobrescribe la rama original `feature/branch-requisition-form`.

La versión `19.0.1.2.0` continúa en `feature/multi-company-supply` y añade:

1. Opción administrativa **Crear solicitud de cotización** en cada vínculo. Por defecto es falsa: solo nuevos envíos con la opción activa crean una cotización estándar en borrador, en la empresa solicitante y con el contacto de la empresa abastecedora como proveedor. Los históricos no generan cotizaciones. El documento identifica su requerimiento y no admite reasignar ese vínculo.
2. Configuración explícita de una **Recepción de la sucursal**, activa y perteneciente a la empresa compradora. Es diferente del almacén abastecedor Insumos de Industria. El proveedor debe estar activo y disponible para la empresa compradora; para varias compradoras normalmente corresponde un contacto compartido, sujeto a revisión administrativa.
3. Para vínculos con cotización, catálogo limitado a productos compartidos y habilitados para compras, además de las validaciones anteriores de actividad, habilitación y categorías. No se comparten, duplican ni modifican productos automáticamente. Los requerimientos sin cotización conservan el catálogo anterior, que permite productos privados de la abastecedora.
4. Captura del precio de venta por variante y del valor solicitado por línea y requerimiento. Se usa la moneda real del producto y conversión a la moneda solicitante con fecha de envío. No se usa el costo ni una tarifa de proveedor. Los históricos sin captura se identifican como tales, sin inventar importes retrospectivos. El importe solicitado no acredita entrega; los impuestos de la cotización requieren revisión fiscal antes de confirmar.
5. Corrección de las rutas del formulario para recuperar únicamente las compañías realmente permitidas al usuario, conservando la asignación explícita. Así la compañía del sitio web no oculta una sucursal autorizada. No cambia sus membresías, la sesión ni las reglas estándar.

La escritura elevada se limita al puente privado que crea la cotización después de la autorización del requerimiento. Cabecera y líneas del requerimiento continúan creándose como el usuario real. La creación de ambos documentos comparte la transacción: un fallo de cotización impide guardar un envío incompleto. No se conceden permisos generales de compras al solicitante. Para cancelar un requerimiento con cotización vinculada, primero debe cancelarse esa cotización desde Compras.

Las cotizaciones conservan las reglas estándar de Compras y pertenecen a las sucursales. El comprador necesita acceso a las compañías de esas sucursales para verlas agrupadas en la lista estándar. Un almacenero con acceso únicamente a Industria puede seguir consultando los requerimientos asignados y el consolidado; ese rol no concede acceso general a las cotizaciones de UPAO. No añadir Industria a las compañías del solicitante para solucionar la asignación.

En el núcleo estándar revisado, enviar el formulario no confirma compras, envía correos, genera ventas, facturas ni movimientos de inventario. Los addons Enterprise, las automatizaciones y el tema privados siguen pendientes de validación en una instalación de pruebas representativa. La atención parcial/final y la valorización de entregas efectivas también permanecen pendientes.

Leer `README.md` y `SUPPLY_COMPANIES.md` para configuración y actualización completa a `19.0.1.2.0`. Conservar todas las migraciones, actualizar primero en una base de pruebas con respaldo y ejecutar `-u alvina_branch_requisition`; reiniciar no basta y desinstalar elimina datos propios. Publicar código en GitHub no actualiza el servidor. Los resultados comprobados de esta continuación se registran en `TESTING.md`; las 46 pruebas indicadas arriba corresponden a la entrega anterior.
