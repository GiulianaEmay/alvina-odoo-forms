# Validación actual — 16 de octubre de 2026 — 19.0.2.0.0

## Recuperación del 19 de octubre de 2026

Se aprobaron **9 pruebas Python**, compilación y comprobación de diferencias.
El preflight nuevo detectó el `commercial.py` sustituido en el ZIP operativo,
rechazándolo; pasó con el addon restaurado. La comparación de sus 41 archivos
contra `779f46d` fue idéntica. No cambió la lógica del addon ni se repitió la suite
Odoo durante este incidente; los 117 casos siguientes son evidencia anterior.
Véase [RECOVERY_2026-10-19.md](RECOVERY_2026-10-19.md).

Además, se reprodujo el arranque con Odoo 19 oficial y PostgreSQL local en una
base desechable nueva: el ZIP incorrecto terminó con código 255 por la relación
`sale_line_ids` cuyo inverso no existía en `sale.order.line`. Reemplazar únicamente
`commercial.py` y repetir sobre la misma base, sin borrarla, terminó con código
0 y registro/vistas/seguridad/reportes cargados. Es una prueba dirigida de
arranque/recuperación, separada de la suite completa histórica. Se verificaron
también login HTTP 200, autenticación local y backend `/odoo` autenticado HTTP
200. El servidor local se detuvo al terminar; no se generaron documentos y el
flujo central quedó desactivado.

Tras recibir el segundo error real (`UndefinedColumn`), se reprodujo también
con una base 19.0.1.2.0 de `d59eea3`, una venta previa y código nuevo sin aplicar
la actualización del addon. La lectura falló con la misma columna ausente.
Ejecutar únicamente `-u alvina_branch_requisition` en esa misma base terminó con
código 0, creó la columna y permitió leer la venta conservando sus datos y sin
documentos adicionales. No se desinstaló ni borró la base. Evidencia temporal:
`/tmp/alvina-incident-upgrade-result.json`. Esta comprobación no cubre Enterprise,
producción ni la variante alternativa `258a450`.

## Resultado comprobado

- **117 pruebas Odoo: 0 fallos, 0 errores, ninguna omitida** en la revisión final. Conserva los 76 casos anteriores y añade 18 de flujo comercial/migración, 15 de atención/Inventario y 8 de PDF. El conteo corresponde a `odoo.tests.result`, no al contador auxiliar que incluye preparación de clases.
- Instalación inicial limpia, sin demo: **116 casos aprobados** antes de añadir el último caso que bloquea la migración de la variante alternativa. La suite final de 117 se ejecutó con actualización de vistas/campos. Las comprobaciones posteriores solo cambiaron documentación.
- **6 pruebas Python y 5 de interfaz DOM: aprobadas**, además de compilación, validación XML y `git diff --check`.
- Chromium real: assets, categorías, cantidades y envío al servidor, sin omitir el caso.
- PDF binario real con wkhtmltopdf parcheado: generado en la suite y, aparte, desde HTTP autenticado como solicitante portal sin permisos de Ventas/Inventario. Muestra revisada visualmente: una página A4, datos sintéticos, 20 pedidos / 15 entregados / 5 faltantes, valores 70 / 52,50 / 17,50 en la moneda USD de la fixture, sin impuestos de prueba. La unidad muestra el nombre de la UoM configurada; la fixture usa idioma inglés para datos estándar, las etiquetas del informe son españolas.
- Dos POST HTTP concurrentes con el mismo token: exactamente un requerimiento, una OC y una OV, ambas en borrador. Sin añadir Industria a las compañías del usuario.
- Escenario real de Inventario: confirmación manual de la OV por el usuario de Industria, salida de 15 y backorder de 5; OC aún en borrador, recibido 0, ninguna factura automática.
- Actualización real **19.0.1.2.0 (`d59eea3`) → 19.0.2.0.0**: dos históricos preservados, incluido uno con cantidad atendida no nula (1). Sin OC/OV/movimientos nuevos ni activación de configuración central. Probe reproducible en `tools/check_intercompany_upgrade.py`.

Las pruebas cubren precios de lista en vez de precio público, descuentos, impuestos incluidos/excluidos, redondeo global, moneda, rollback atómico, idempotencia, suplantación RPC/defaults, asignaciones, contactos/compañías y recepción protegidos. El guardia nativo se prueba tanto en confirmar como en aprobar compras y confirmar ventas. Ese guardia se simula mediante mocking de presencia del módulo, **no constituye una prueba de Enterprise**.

Inventario distingue reservas, salidas netas y recepciones; cubre 20/15/5, backorders, devoluciones y devoluciones de devoluciones, sobreentrega real, operaciones canceladas, stock físico insuficiente y bienes no almacenables. El cierre de saldo exige motivo, usuario real y operaciones abiertas canceladas; no altera la demanda original. El consolidado reconoce reservas propias una sola vez y conserva indisponibles las de otros pedidos.

## Runtime y evidencia de esta máquina

Odoo oficial Community 19: `e1ed4fe077ba98ce7ac6802a43bb68242081dee9`. Python 3.12.14, PostgreSQL local mediante `pgserver`, rol de pruebas sin superusuario, Chromium real y wkhtmltopdf 0.12.6.1 con Qt parcheado. Dependencias oficiales; localmente se omitió python-ldap y se usó psycopg2-binary. La extensión pg_trgm no está en este PostgreSQL reducido; las pruebas no afirman cubrir índices trigram.

- Suite final: `/tmp/alvina-intercompany-accepted.log`, base `alvina_intercompany_test`.
- Instalación limpia: `/tmp/alvina-intercompany-install.log`, base `alvina_intercompany_install_test`.
- Actualización histórica: `/tmp/alvina-flow-upgrade.log`, baseline `/tmp/alvina-flow-upgrade-before.json`, base `alvina_supply_upgrade_test`.
- HTTP: `/tmp/alvina-flow-http-final.log`; fixture de entrega `/tmp/alvina-flow-smoke-delivery-final.log`, base `alvina_flow_smoke_test`.
- PDF de muestra: `/workspace/exports/alvina-despacho-ejemplo-pruebas.pdf` (datos de prueba, no documento real).

Estos logs/bases son evidencia temporal y no se suben a Git. El código y los probes reproducibles sí están en el repositorio. GitHub Actions remoto no se ha verificado.

## Reproducir las pruebas

Instalar las dependencias de pruebas siguiendo `.github/workflows/tests.yml` en un entorno aislado, con código Odoo fuera del addon. Para PDF en Linux amd64, `python tools/setup_test_pdf.py` descarga paquetes fijados por SHA256 y extrae solo en `/tmp/alvina-pdf-runtime`, sin instalación del sistema. Exportar:

```bash
export PATH=/tmp/alvina-pdf-runtime/usr/local/bin:$PATH
export LD_LIBRARY_PATH=/tmp/alvina-pdf-runtime/usr/lib/x86_64-linux-gnu
python -m unittest discover -s tools -v
NODE_PATH=/tmp/alvina-js-test/node_modules node --test tools/test_frontend.cjs
python /path/to/odoo/odoo-bin --addons-path=/path/to/odoo/addons,/path/to/repository \
  --db_host=/tmp/alvina-test-pg --db_user=alvina_test \
  -d alvina_intercompany_test -i alvina_branch_requisition --without-demo \
  --test-enable --test-tags=/alvina_branch_requisition --stop-after-init \
  --http-interface=127.0.0.1 --http-port=8093
```

Utilizar `-u` en vez de `-i` cuando la base desechable ya tenga el addon instalado. Se necesita un wkhtmltopdf funcional y Chromium para no omitir pruebas.

Para la migración: preparar los históricos con la revisión anterior en la base estrictamente local `alvina_supply_upgrade_test`, usando las fixtures documentadas en `tools/check_supply_upgrade.py`. Con 19.0.1.2.0 instalada, capturar el baseline con `python tools/check_intercompany_upgrade.py capture SNAPSHOT.json`; actualizar normalmente a la revisión actual; ejecutar `verify SNAPSHOT.json`. El probe solo lee la base local indicada. La prueba de esta sesión incluyó una cantidad atendida 1 insertada únicamente en su fixture SQL antes del baseline. Un subtotal histórico sin precio puede pasar de NULL a cero por recomputación de Odoo; se comprueba que siga sin precio capturado y no se interprete como valoración histórica.

Para HTTP concurrente: en una base local **nueva y desechable** `alvina_flow_smoke_test` con el addon instalado y socket `/tmp/alvina-test-pg`, ejecutar Odoo shell con `ALVINA_FLOW_SMOKE_PHASE=seed` y stdin `tools/flow_smoke_fixture.py`. Arrancar solo esa base en `127.0.0.1:8094` sin cron. Ejecutar `python tools/check_flow_http.py submit`; después Odoo shell con fase `deliver`; finalmente `python tools/check_flow_http.py pdf`. La fixture crea datos sintéticos y hace commit, rechaza bases/conexiones diferentes y no se debe ejecutar en datos operativos. El PDF se exporta a `/workspace/exports/`.

## Límites que las pruebas no resuelven

No se validaron Enterprise, automatizaciones privadas instaladas, rutas/datos fiscales/tema reales ni regresión ejecutable del formulario de producción privado. El guardia bloquea el automatismo Enterprise conocido y la fabricación privada por LdM; no prueba todos los addons desconocidos. La operación dentro de la misma compañía permanece bloqueada hasta aprobar y mapear su traslado.

La rama alternativa `feature/central-supply-multicompany` (`258a450`) tiene otro esquema aunque comparta número de versión con `d59eea3`. No se fusionó ni se migró su historial. El caso nuevo 117 verifica que su tabla de asignaciones provoca un bloqueo explícito en vez de perder datos. Confirmar el commit efectivamente instalado antes de actualizar.

No se hicieron pruebas ni cambios en producción, ni se concedieron permisos nuevos. Esta revisión no repitió la desinstalación destructiva de versiones anteriores.

## Evidencia histórica — versiones anteriores

# Evidencia de validación — 15 de octubre de 2026

## Resultado histórico: 19.0.1.2.0

- **76 pruebas Odoo: 0 fallos, 0 errores.** Las 46 de la entrega multiempresa, 22 de cotizaciones/precios/permisos y 8 de contexto web. Resultado del runner `odoo.tests.result`, sin omitir Chromium real.
- **6 pruebas Python y 5 pruebas DOM aprobadas.** Compilación Python, XML y `git diff --check` correctos.
- Instalación inicial y suite completa en `alvina_rfq_full_test`; repetición completa tras corregir los casos portal, con datos en `/tmp/alvina-rfq-full-data`. Registro final: `/tmp/alvina-rfq-full-tests-final.log`.
- Actualización real **19.0.1.1.0 → 19.0.1.2.0** en `alvina_supply_upgrade_test`: dos requerimientos históricos, empresas, usuarios, cantidades y vínculo archivado conservados. Cabeceras y líneas tienen sus monedas correctas. Precios históricos no inventados, importes marcados sin captura y ninguna cotización retroactiva. Logs: `/tmp/alvina-rfq-upgrade-update.log` y `/tmp/alvina-rfq-upgrade-verify-currency.log`. Probe reproducible en `tools/check_supply_upgrade.py`.

Las pruebas nuevas verifican una cotización en borrador por envío autorizado, en la empresa solicitante y con la abastecedora como proveedor, recepción de la solicitante y precio de venta registrado. Cubren precio cero, tarifa de proveedor distinta, cambios posteriores de precio, conversión monetaria, redondeo, productos privados/no comprables, duplicados, contexto `uom` manipulado, campos/defaults suplantados, identidad del documento y cancelación. Dos sucursales generan cotizaciones diferentes, mientras el consolidado suma la demanda antes de descontar una sola vez el stock del almacén abastecedor.

Se probó el POST HTTP con una empresa predeterminada distinta de la sucursal y un sitio web de Industria: crea la solicitud como el usuario real y la cotización en la sucursal correcta. La normalización de compañías se limita a estas rutas y a compañías permitidas del usuario; no altera la sesión ni el contexto estándar del backend/RPC. También se probó un usuario **portal**, sin roles internos de Compras/Inventario, con varios usuarios asignados al mismo vínculo: puede enviar, sin acceder a la operación de inventario ni a documentos privados.

El núcleo revisado no confirma, genera recepciones/movimientos, ventas, facturas ni correo al crear el borrador. La cotización conserva las reglas estándar de Compras: un almacenero solo de Industria no obtiene acceso general a las compras de las sucursales. El valor capturado corresponde a lo solicitado, no a una entrega acreditada. El ciclo de atención parcial/final sigue pendiente.

La creación de cotizaciones exige habilitación explícita por vínculo, una recepción compradora válida, productos compartidos habilitados para compras y un proveedor disponible en la compradora. No se modifican contactos, productos, membresías ni documentos anteriores para cumplir estos requisitos. Los impuestos del borrador requieren revisión según la configuración real.

Plataforma: el mismo Odoo 19 Community y runtime descritos más abajo. No se validaron Enterprise, automatizaciones privadas, tema desplegado ni producción. La evidencia de desinstalación de la sección histórica corresponde a la versión anterior; no se repitió para esta continuación. La ejecución remota de GitHub Actions de esta revisión no se verificó. El CI actual utiliza `pgserver==0.1.4` mediante socket local, sin servicio Docker.

## Entrega multiempresa anterior: 19.0.1.1.0

Se aprobaron 46 pruebas Odoo, además de las 6 Python y 5 DOM, y la migración real desde `bf19163` (`19.0.1.0.1`). La continuación actual conserva esa cobertura y añade las 30 pruebas descritas arriba.

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

Se instalaron los requisitos oficiales aplicables a Python 3.12 con dos ajustes solo para esta máquina: se omitió `python-ldap` (no se usa `auth_ldap`) y se utilizó `psycopg2-binary==2.9.9` en vez de compilar `psycopg2==2.9.9`. GCC para rjsmin y `websocket-client==1.8.0` para controlar Chromium. No se desactivaron TLS ni verificaciones de artefactos. El PostgreSQL reducido no incluye `pg_trgm`; Odoo advirtió que no podía crear esa extensión, pero completó la instalación y la suite. No se validan búsquedas trigram. El CI actual utiliza también PostgreSQL de `pgserver` y los requisitos oficiales completos de Odoo.

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
