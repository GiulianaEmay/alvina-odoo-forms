# Traspaso del desarrollo multiempresa

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

La instrucción vigente del usuario es conservar y transferir lo existente.
No desarrollar nuevas funciones, fusionar ramas ni desplegar en producción.
