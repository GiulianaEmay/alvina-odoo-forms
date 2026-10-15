# Evidencia de validación — 15 de octubre de 2026

## Abastecimiento multiempresa — versión 19.0.1.1.0

Validado en este entorno cloud el 15 de octubre de 2026, partiendo de `bf19163`:

- **49 pruebas Odoo: 0 fallos, 0 errores, sin omisiones.** 17 de solicitudes, 11 de seguridad existente, 7 HTTP/navegador (incluida UPAO → Industria), 10 de abastecimiento multiempresa y 4 de migración PostgreSQL. El contador de `odoo.tests.result` es el resultado; las estadísticas auxiliares incluyen preparación de clases.
- **6 pruebas Python y 5 pruebas DOM: aprobadas.** Compilación Python y `git diff --check`: correctos.
- **Chromium real ejecutado** en la suite completa: assets, categorías, cantidades y envío con CSRF. No se sustituyó por jsdom ni se omitió.
- Instalación inicial del addon en Community y ejecución posterior de la suite completa tras actualizarlo: correctas.
- **Actualización histórica real comprobada:** se exportó el addon de `bf19163` fuera del checkout, se instaló en la base desechable `alvina_upgrade_history_test`, se crearon y confirmaron dos solicitudes con sus líneas y se actualizó a `19.0.1.1.0`. Se verificó que las dos cabeceras y las dos líneas tenían compañía/almacén abastecedores correctos, manteniendo compañía solicitante, autor, estado y cantidades. No se valida una actualización real con una base vacía como sustituto de esta comprobación.

La primera ejecución detectó acceso de un almacenero a un consolidado ajeno. Se añadieron reglas de propietario para cabeceras y líneas transitorias; la regresión ahora pasa. Las pruebas distinguen las ACL de modelo de Odoo (un usuario interno puede leer modelos de stock) del acceso real a registros de Industria, que queda denegado a UPAO. El consolidado respeta las reglas normales de stock sin elevar permisos.

Runtime: Odoo 19 Community `e1ed4fe077ba98ce7ac6802a43bb68242081dee9` en `/workspace/odoo-runtime`; Python 3.12.14, venv `/workspace/shared/alvina-venv`, Node 24.19.0, jsdom 26.1.0, PostgreSQL de `pgserver==0.1.4` y Chromium. Se omitió `python-ldap` por falta de cabeceras SASL (no se usa `auth_ldap`) y se usó `psycopg2-binary==2.9.9` en lugar de compilar la misma versión. No se desactivaron verificaciones TLS. PostgreSQL reducido no incluye `pg_trgm`: su instalación produjo la advertencia correspondiente; no se validan búsquedas trigram.

Comando de la suite completa en esta máquina (solo base desechable):

```bash
/workspace/shared/alvina-venv/bin/python /workspace/odoo-runtime/odoo-bin \
  --addons-path=/workspace/odoo-runtime/addons,/workspace/alvina-odoo-forms \
  --data-dir=/workspace/shared/alvina-data --db_host=/workspace/shared/alvina-pg \
  --db_user=alvina_test -d alvina_central_test -u alvina_branch_requisition \
  --test-enable --test-tags=/alvina_branch_requisition --stop-after-init \
  --without-demo --http-interface=127.0.0.1 --http-port=8079
```

Para la primera instalación en una base nueva usar `-i` en lugar de `-u`. El workflow existente de GitHub Actions usa ese camino y descubre también las pruebas nuevas; no se afirma haber ejecutado Actions remotamente.

Evidencia local de esta ejecución: `/tmp/alvina-central-tests-verified.log`, `/tmp/alvina-upgrade-history-install.log`, `/tmp/alvina-upgrade-history-seed.log`, `/tmp/alvina-upgrade-history-run.log` y `/tmp/alvina-upgrade-history-verify.log`. Son archivos del entorno, no resultados de la cuenta anterior.

Enterprise, módulos privados, tema y datos reales siguen pendientes; véase [MULTICOMPANY.md](MULTICOMPANY.md). No se reinició ni contactó el servidor real y no se desplegó en producción.

## Resultado de la auditoría 19.0.1.0.1

- **34 pruebas Odoo: 0 fallos, 0 errores.** Incluye 17 de modelos/configuración, 6 HTTP/navegador y 11 de seguridad. Conteo tomado de `odoo.tests.result`; el contador auxiliar de estadísticas incluye preparación de clases.
- **6 pruebas Python sin Odoo: aprobadas.** Cantidades, orden natural, pendientes, sugerencia y estructura XML/menús.
- **5 pruebas DOM con jsdom: aprobadas.** Persistencia entre categorías y envío conjunto; cambio de sucursal; cantidades negativas; borrado de una cantidad; conservación de un error numérico al ocultar su categoría.
- **Chromium real ejecutado, sin omitir la prueba:** carga de assets de Odoo, layout/título granate, sucursal bloqueada, cuatro categorías, orden natural 2 antes de 10, persistencia entre categorías, borrado de una cantidad y POST real con CSRF que crea una solicitud con el producto restante.
- Compilación Python, sintaxis JavaScript y carga de vistas/recursos de Odoo: correctas.
- Desinstalación estándar repetida con una solicitud persistida en la versión revisada: se conservaron contacto original de prueba, producto, categoría, existencias, cantidades de documentos de compra/movimientos y menús originales. Desaparecieron los tres accesos y el campo de habilitación del addon. No garantiza recuperación de solicitudes eliminadas ni reversibilidad en la pila privada.

La primera entrega `cb22c5f` tenía 21 pruebas Odoo, 6 Python y 3 DOM aprobadas. Esta auditoría amplió la cobertura y encontró defectos que aquellas pruebas no detectaban; los resultados anteriores no equivalían a certificar Enterprise ni todos los requisitos operativos.

## Correcciones comprobadas

1. **Cantidad borrada:** se enviaba una cadena vacía que el servidor rechazaba. Ahora borrar equivale a omitir esa cantidad; los números incompletos siguen bloqueados aunque se cambie de categoría. Regresiones DOM y navegador real.
2. **Precisión del consolidado:** sus columnas podían mostrar cero para una cantidad pequeña válida. Ahora usan la precisión `Product Unit`; una prueba cubre demanda 0.015, stock libre 0.005, entradas 0.003 y sugerencia 0.007 con tres decimales.
3. **Referencia de sucursal demasiado amplia:** permitía seleccionar registros de cualquier modelo y exponer su nombre mediante `sudo()`. Ahora el núcleo admite contactos existentes, exige acceso al configurar y evita revelar nombres de modelos no permitidos. Un adaptador explícito puede ampliar la selección para otro modelo verificado.
4. **Cambios posteriores del contacto:** se bloquea el envío si el contacto fue archivado o movido a otra compañía después de asignarlo. Esas sucursales tampoco aparecen como opciones activas del formulario.
5. **Presentación respecto al ZIP:** se inspeccionó la plantilla de `alvinha_mrp` y se alineó la plantilla propia con `website.layout`, título `#681412`, fila Bootstrap, tabla compacta y botón que hereda el tema. No se modificaron ni incorporaron módulos privados. El tema real aún no se ha probado.
6. **Mensaje de reasignación:** ya no recomienda archivar y duplicar un vínculo que la unicidad impide recrear. Reasignar almacén/identidad con historial requiere una migración controlada.

## Plataforma usada

Odoo 19 Community, commit `e1ed4fe077ba98ce7ac6802a43bb68242081dee9`, descargado del repositorio oficial a `/tmp/alvina-odoo19`, fuera del repositorio del addon. Python 3.12.14, entorno virtual `/tmp/alvina-venv`, Chromium del entorno, PostgreSQL local suministrado por `pgserver==0.1.4`. La auditoría utilizó la base desechable `alvina_audit_test` y datos en `/tmp/alvina-audit-data`. La prueba de desinstalación utiliza exclusivamente `alvina_requisition_test` y `/tmp/alvina-odoo-data`.

Se instalaron los requisitos oficiales aplicables a Python 3.12 con dos ajustes solo para esta máquina: se omitió `python-ldap` (no se usa `auth_ldap`) y se utilizó `psycopg2-binary==2.9.9` en vez de compilar `psycopg2==2.9.9`. GCC para rjsmin y `websocket-client==1.8.0` para controlar Chromium. No se desactivaron TLS ni verificaciones de artefactos. El PostgreSQL reducido no incluye `pg_trgm`; Odoo advirtió que no podía crear esa extensión, pero completó la instalación y la suite. No se validan búsquedas trigram. El CI preparado usa PostgreSQL estándar y los requisitos oficiales completos.

## Cobertura de seguridad y stock

Las pruebas cubren creación sin stock, stock negativo sin bloqueo ni modificación de existencias, exclusión de canceladas, duplicados de producto/token, cantidades inválidas, inmutabilidad de líneas/estados y prohibición de añadir líneas después de enviar. Verifican compañía, cabeceras y líneas, varios productos/categorías/sucursales, solicitud vacía y ubicación exacta de menús sin aplicación independiente.

Se verifica que el consolidado conserva la UoM histórica, bloquea cambios incompatibles y toma stock únicamente del almacén configurado. Con demanda 20, stock 10, reserva 4 y entrada confirmada 7 resulta una sugerencia de 7; el stock de otro almacén queda excluido y recalcular no crea compras ni movimientos.

Se probaron intentos de suplantación mediante contexto `default_*`, cantidades atendidas/pendientes, autor, referencia y fecha; acciones de almacenero desde un solicitante; almacenero sin sucursal asignada; compañía activa restringida para un usuario multicompañía; producto de otra compañía; referencia a un modelo privado; contacto archivado o movido de compañía. No se confirmó vulnerabilidad mediante `default_*`: las comprobaciones existentes y el ORM ya las impedían; se añadieron regresiones.

Las pruebas HTTP incluyen anonimato, CSRF, ausencia/una/varias sucursales, envío desde un usuario portal y reenvío secuencial sin duplicados. Las violaciones SQL intencionales de unicidad y el POST sin CSRF generan mensajes de error/advertencia esperados. El resultado final del runner es cero fallos y errores.

## Operación ejecutada

Instalación inicial con `-i alvina_branch_requisition`, actualizaciones y pruebas con:

```bash
/tmp/alvina-venv/bin/python /tmp/alvina-odoo19/odoo-bin \
  --addons-path=/tmp/alvina-odoo19/addons,/workspace/alvina-odoo-forms \
  --data-dir=/tmp/alvina-audit-data --db_host=/tmp/alvina-test-pg \
  --db_user=alvina_test -d alvina_audit_test \
  -u alvina_branch_requisition --test-enable \
  --test-tags=/alvina_branch_requisition --stop-after-init \
  --http-interface=127.0.0.1 --http-port=8080
```

Para otro entorno usar README.md y las rutas reales de su instalación. Logs locales: `/tmp/alvina-audit-final.log`, `/tmp/alvina-audit-uninstall.log`; los de la primera entrega permanecen en `/tmp/alvina-odoo-tests-final.log` y `/tmp/alvina-uninstall.log`. No son necesarios para instalar el addon.

## Validaciones e integraciones pendientes

- Enterprise, addons privados, temas, vistas y datos de la instalación real. El ZIP fue inspeccionado estáticamente; no se ejecutó su pila ni se contactaron sus servicios.
- Configurar contactos realmente marcados `type_client = 'branch'`, permisos por usuario y almacén abastecedor. El núcleo solo utiliza contactos estándar; no instala ni simula el campo privado. Véase INTEGRATION.md.
- **Atención parcial/final:** no existe aún un procedimiento para incrementar `qty_supplied` y cerrar solicitudes por entrega. Las solicitudes se revisan o cancelan, pero no se completan. Debe resolverse antes del uso operativo; no presentar el flujo como completo.
- **Compras sugeridas:** siguen siendo informativas, sin asignación exclusiva de entradas, ventanas temporales ni consideración de todas las salidas futuras sin reserva. Se requiere contrastar el cálculo con el proceso real de abastecimiento.
- Doble envío concurrente: se probó la unicidad SQL y el reenvío secuencial, pero no dos solicitudes HTTP simultáneas con sesiones concurrentes.
- Reasignar almacén con historial exige migración/versionado. La unicidad también impide recrear un vínculo archivado para el mismo contacto.
- Regresión operativa del formulario de producción existente y desinstalación sobre una copia representativa de Enterprise.
- GitHub Actions está preparado, pero no se afirma haber verificado una ejecución remota.

Solo se sube el resultado al repositorio de desarrollo autorizado. No se escribió en `SoyCalidad/alvinha`, no se clasificó `cybe` como pruebas y no hubo acceso ni cambios en producción.
