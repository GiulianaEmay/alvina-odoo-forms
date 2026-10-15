# Evidencia de validación — 15 de octubre de 2026

## Resultado

- **21 pruebas Odoo: 0 fallos, 0 errores.** Conteo tomado de `odoo.tests.result`, no del contador auxiliar de estadísticas que incluye preparación de clases.
- **6 pruebas Python sin Odoo: aprobadas.** Cantidades, orden natural, pendientes, sugerencia y estructura XML/menús.
- **3 pruebas DOM con jsdom: aprobadas.** Persistencia entre categorías y envío conjunto; cambio de sucursal; rechazo de cantidades negativas guardadas en otra categoría.
- Compilación Python, sintaxis JavaScript y carga de vistas/recursos de Odoo: correctas.
- Desinstalación estándar comprobada con una solicitud persistida: se conservaron sucursal original (contacto de prueba), producto, categoría, existencias, cantidades de documentos de compra/movimientos y menús originales. Desaparecieron los tres accesos y el campo de habilitación del addon. Se reinstaló y repitió la suite.

## Plataforma usada

Odoo 19 Community, commit `e1ed4fe077ba98ce7ac6802a43bb68242081dee9`, descargado del repositorio oficial a `/tmp/alvina-odoo19`, fuera del repositorio del addon. Python 3.12.14, entorno virtual `/tmp/alvina-venv`, PostgreSQL local suministrado por `pgserver==0.1.4`, base desechable `alvina_requisition_test`, datos y filestore en `/tmp/alvina-odoo-data`.

Se instalaron los requisitos oficiales aplicables a Python 3.12 con dos ajustes solo para la máquina de pruebas: se omitió `python-ldap` (no se usa `auth_ldap`), y se utilizó `psycopg2-binary==2.9.9` en vez de compilar `psycopg2==2.9.9`. Se utilizó GCC para rjsmin. No se desactivaron TLS ni verificaciones de artefactos. El PostgreSQL reducido no incluye `pg_trgm`; Odoo advirtió que no podía crear esa extensión, pero completó la instalación y la suite. No se validan búsquedas trigram ni funciones ajenas al addon. El CI preparado usa PostgreSQL estándar y los requisitos oficiales completos.

## Alcance de las 21 pruebas Odoo

16 pruebas de modelos/configuración: creación con stock cero; stock negativo sin bloqueo ni modificación de existencias; consolidación y exclusión por cancelación; productos deshabilitados; productos duplicados; token duplicado; inmutabilidad de líneas/estado y prohibición de añadir líneas posteriormente; varias sucursales y categorías; negativos; ausencia de asignación; compañía incompatible; reglas de cabecera y detalle; rechazo de solicitud vacía; ubicación exacta de los menús y `application=False`; conservación de la UoM histórica y bloqueo del consolidado si cambia la unidad base; stock libre tras reservas, entradas confirmadas, exclusión del stock de otro almacén y recálculo sin crear compras ni movimientos.

5 pruebas HTTP: acceso anónimo redirige al login; CSRF obligatorio; selector con varias sucursales; ausencia de sucursal impide formulario; sucursal única bloqueada, envío real autenticado desde usuario portal, confirmación y rechazo de reenvío sin crear duplicados.

Las violaciones SQL intencionales de unicidad generan mensajes ERROR en el log, esperados por sus pruebas. El resultado final del runner es cero fallos y errores.

## Operación ejecutada

Instalación inicial con `-i alvina_branch_requisition`, actualizaciones con `-u alvina_branch_requisition`, y pruebas con:

```bash
/tmp/alvina-venv/bin/python /tmp/alvina-odoo19/odoo-bin \
  --addons-path=/tmp/alvina-odoo19/addons,/workspace/alvina-odoo-forms \
  --data-dir=/tmp/alvina-odoo-data --db_host=/tmp/alvina-test-pg \
  --db_user=alvina_test -d alvina_requisition_test \
  -u alvina_branch_requisition --test-enable \
  --test-tags=/alvina_branch_requisition --stop-after-init \
  --http-interface=127.0.0.1 --http-port=8079
```

Esta ruta reproduce la instancia temporal actual; para otro entorno usar las instrucciones de README.md y sus rutas reales. Los logs de esta máquina están en `/tmp/alvina-odoo-tests-final.log`, `/tmp/alvina-odoo-tests-reinstall.log` y `/tmp/alvina-uninstall.log`; no se requieren para instalar el addon.

## Validaciones pendientes

Enterprise y los addons privados de Alviña; integración del modelo real de sucursales y sus asignaciones; equivalencia visual con Ventas; browser real y accesibilidad completa; carrera de envíos concurrentes (sí está probada la restricción SQL y el reenvío secuencial); cálculo con reservas/recepciones y asignaciones del negocio real; regresión operativa completa y desinstalación sobre una copia representativa de la instalación real. GitHub Actions está preparado, pero aún no se ha ejecutado allí.

La cantidad atendida permanece protegida y sin interfaz de modificación hasta integrar un procedimiento auditable de entregas. No se declara completo el flujo de atención parcial/final. No hubo conexión ni cambios en producción.
