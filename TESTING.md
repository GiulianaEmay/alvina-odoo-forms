# Validación — 19.0.3.1.0

## Revisión conjunta con POS del ZIP operativo

El resultado conjunto actual de `main` es **256 pruebas Odoo correctas**: 191 de
sucursales, 23 de POS y 42 del QR recibido. Ver [el informe del ZIP](ZIP_REVIEW_2026-10-23.md)
para sus casos, la actualización del esquema POS y los límites de Enterprise.
El resultado de 233 que sigue corresponde a sucursales + QR antes de añadir POS.

## Alcance

Las comprobaciones utilizan Odoo **Community 19** oficial, revisión
`e1ed4fe077ba98ce7ac6802a43bb68242081dee9`, y PostgreSQL local en bases
**desechables**. No prueban ni modifican producción. No se dispone del runtime
Enterprise ni de la pila privada instalada de Alviña.

Resultado final de 19.0.3.1.0: **233 pruebas Odoo en una ejecución conjunta,
cero fallos, cero errores y ninguna omisión**: 191 de sucursales (incluidas 15 del
contrato nativo) y 42 del módulo QR facilitado. Además: **27 pruebas Python** de
validación/paquete y **5 DOM**, todas correctas. Chromium real y PDF binario.

La ejecución final está en `/tmp/alvina-combined-v31-final-tests.log`, base local
`alvina_native_qr_compat_test`, con `0 failed, 0 error(s) of 233 tests`. El primer
intento de integración local encontró dependencias gráficas de ReportLab ausentes;
se instaló `rl-renderPM` en el entorno de pruebas y se repitió la suite completa.
Una ejecución anterior de navegador encontró un filestore local incompleto;
se restauraron los archivos del fixture antes de la validación final.

Los conteos históricos de 176 pruebas corresponden a 19.0.3.0.0, y los de 117 a
19.0.2.0.0; no se suman ejecuciones parciales para presentar una suite completa.
No se ejecuta ni certifica el motor Enterprise real, que no viene en el ZIP.

## Evidencia específica de 19.0.3.1.0

- Adaptador: una sola OC y la OV observada del motor nativo; creación anidada o
  cabecera/líneas separadas; confirmación nativa o técnica; impuestos incluidos,
  precios y responsable conservados; aprobación técnica de dos pasos limitada
  a la OC del requerimiento. No amplía compañías ni permisos.
- Fallos: ausencia de OV, duplicado, empresa/cantidad/líneas incorrectas,
  facturación, compra inversa o precios alterados revierten todo el envío.
  Las creaciones ordinarias quedan fuera de la capacidad privada.
- Pendientes: el solicitante original puede enviar su requerimiento anterior
  una vez, sin cambiar referencias, fechas o demanda; se conservan intactos si
  falla la integración. Otro usuario no puede enviarlo.
- Inventario nativo: 10 pedidas, 8 despachadas en una guía valorizada en 28,
  7 recibidas, 2 pendientes de despacho y una diferencia de recepción;
  sin doble descuento de stock ni facturas. El precio del fixture es 3.5.
- Coexistencia QR: sus 42 pruebas originales ejecutan reservas, entrega real,
  lectura QR/Code128, cancelación, autorizaciones, cantidades y aislamiento,
  mientras sucursales está instalado. La suite de sucursales también se ejecutó
  completa con QR presente. El código de negocio QR no se modificó.
- Migración con historia: una solicitud QR se entregó realmente en una copia
  local (cinco unidades). Tras ejecutar `-u alvina_branch_requisition` desde una
  marca de versión predecesora se conservaron IDs, líneas, estado, cantidades
  y stock. Los dos campos ORM y sus claves foráneas apuntan a sus modelos
  respectivos. Ante una asociación producto/solicitud deliberadamente ambigua,
  el pre-migrador rechazó el caso sin borrar los movimientos.
- Instalación limpia: `alvina_native_clean_v31`, versión 19.0.3.1.0 instalada,
  registro cargado y columnas/claves verificadas. Log
  `/tmp/alvina-native-clean-install.log`.

Las evidencias de historia están en `/tmp/alvina-qr-history-before.json`,
`/tmp/alvina-qr-history-after.json`, `/tmp/alvina-qr-history-upgrade.log` y
`/tmp/alvina-qr-history-verify.log`. El fixture marcó explícitamente su versión
instalada como predecesora para ejercitar la migración sobre historia QR real;
no es una copia de la base de producción ni certifica todos sus datos históricos.

Para descubrir la suite QR del ZIP, se copió únicamente ese módulo a
`/tmp/alvina-qr-compat-addons`, se renombró su carpeta `test/` a `tests/` y se
importó desde su `__init__.py`. En su fixture se activó el tipo interno que
necesita el departamento de pruebas. Se conservaron sus 42 pruebas y todos sus
modelos originales. Esta adaptación es solo del runtime de pruebas; no debe
copiarse sobre el módulo operativo.

Comando conjunto, con el entorno PDF ya preparado:

```bash
/ruta/venv/bin/python /ruta/odoo/odoo-bin \
  --addons-path=/ruta/odoo/addons,/ruta/repositorio,/tmp/alvina-qr-compat-addons \
  --data-dir=/tmp/alvina-qr-compat-data \
  --db_host=/tmp/alvina-ci-pg --db_user=odoo_test \
  -d alvina_native_qr_compat_test \
  -u alvina_branch_requisition,alvina_stock_request \
  --test-enable --test-tags=/alvina_branch_requisition,/alvina_stock_request \
  --stop-after-init --http-interface=127.0.0.1 --http-port=8090
```

## Cobertura nueva

- Fechas: valor inicial y mínimo hoy de Lima + dos días calendario; límites al
  cambiar el día UTC/Lima; TZ manipulada; validación HTML, POST y creación RPC;
  conservación de fechas históricas. Navegador Chromium real.
- Comercial: una OC y una OV vinculadas, confirmadas automáticamente; ningún
  movimiento validado ni factura por el envío; aprobación técnica limitada al
  par real, políticas de compras ordinarias intactas, contextos falsificados y
  rollback si falla cualquier confirmación.
- Responsables: seleccionado activo válido, sustituto único con rol y compañía
  autorizada, rechazo de cero o varios candidatos y de una selección activa
  inválida. No se cambian membresías de compañías.
- Logística: todas las sucursales abastecidas por Industria, incluidas ventas
  del responsable anterior y sin asignación manual de cada vínculo; compañía
  permitida y seleccionada obligatoria.
- Aislamiento comercial: exclusión de ventas comunes, sus líneas y análisis,
  también con grupos Ventas de todos los documentos/administrador o permisos
  de Ajustes. Lectura directa, agregación, exportación, PDF y creación/copia
  manual. Los usuarios sin el nuevo rol conservan su ámbito comercial previo.
- Guías: una por salida física, emisión idempotente, instantánea inmutable,
  precios/impuestos reales, saldos del pedido al emitir y autorización del PDF.
  Cantidades reservadas, enviadas, recibidas y pendientes siguen separadas.
- Recepción: una acción de sucursal valida el picking real de su OC y registra
  conformidad/diferencias; acceso de otro local o de Logística rechazado;
  motivo obligatorio para diferencias, cero recibido sin entrada ficticia,
  cantidades mayores a la guía rechazadas, recepción parcial y concurrencia.
  Se bloquean rutas de varios pasos y productos que exigen lotes/series.
- Regresiones: catálogo, cantidades/unidades, formularios y CSRF, duplicados,
  migraciones, consolidación sin descontar reservas/stock dos veces, devoluciones,
  inmutabilidad e históricos. La confirmación comercial no activa facturación.

Las 15 pruebas del adaptador simulan la salida ORM del motor nativo sobre
Inventario/Compras/Ventas Community reales. **No ejecutan Enterprise**. La pila
privada completa requiere módulos Enterprise ausentes del ZIP; sus overrides
conocidos se revisaron estáticamente y los efectos de fabricación se bloquean.
Todavía debe verificarse una OC→OV con la regla/usuario de la copia real.

## Runtime y evidencias locales

Entorno de esta continuación: Python 3.12, Odoo en
`/tmp/alvina-incident-odoo19`, venv `/tmp/alvina-incident-venv`, PostgreSQL por
socket `/tmp/alvina-ci-pg` y rol `odoo_test` sin superusuario. Se utilizan Chromium
real y wkhtmltopdf con Qt parcheado. No se incluyen credenciales operativas en
Git; los probes contienen únicamente las credenciales sintéticas de su fixture.

La suite histórica de 19.0.3.0.0 ejecutada con `-u` está en
`/tmp/alvina-logistics-publication-tests.log`; su resumen es `0 failed, 0
error(s) of 176 tests`. Incluye Chromium real y los dos reportes PDF binarios,
incluida la guía por despacho con diferencias de recepción.

La instalación limpia en `alvina_logistics_clean_v3` y el reinicio sin `-i/-u`
cargaron la versión 19.0.3.0.0 y sus tablas/vistas. HTTP local devolvió 200 en
`/web/login` y 303 hacia login en `/odoo`, sin traceback. Logs:
`/tmp/alvina-logistics-clean-install.log` y
`/tmp/alvina-logistics-clean-http.log`.

Se instaló además el addon anterior `ecf9c6e` en otra base desechable y se
actualizó con el código nuevo. Los snapshots antes/después conservaron IDs,
fecha histórica 22/10/2026, precio registrado 13.75 aunque el catálogo ya tenía
99, demanda 7, suministrado 0, usuarios, grupos y compañías. No aparecieron OC,
OV, movimientos, guías ni facturas retroactivas. El reinicio/HTTP también pasó.
Evidencia temporal: `/tmp/alvina-logistics-upgrade-before.json`,
`/tmp/alvina-logistics-upgrade-after.json` y
`/tmp/alvina-logistics-upgrade-v3-update.log`.

El escenario HTTP autenticado envió dos POST simultáneos con el mismo token:
se creó un requerimiento, una OC confirmada y una OV confirmada. Logística,
sin asignación individual en el vínculo, despachó 15 de 20 unidades; el
solicitante, sin Inventario ni acceso a Industria, confirmó 13. Quedaron 5 por
despachar y 2 de diferencia de recepción. Stock de Industria: 15 → 0 al
despachar y 0 al recibir; stock comprador: 0 → 13. Sin facturas ni ampliación de
compañías. La descarga autenticada de la guía devolvió un PDF A4 de una página,
revisado visualmente, con precios conservados y esos saldos. La muestra local
`/workspace/exports/alvina-guia-interna-muestra.pdf` contiene solo datos
sintéticos; no forma parte del addon.

En esta máquina se usaron las dependencias oficiales de Odoo con ajustes locales
para `psycopg2-binary` y sin `python-ldap`, ya que no se usa `auth_ldap`. El
PostgreSQL reducido no incluye `pg_trgm`; no se afirma validar índices trigram.
No se desactivan TLS ni verificaciones de descarga.

## Reproducir

Seguir `.github/workflows/tests.yml`: Python 3.12, requisitos oficiales de Odoo,
`pgserver==0.1.4`, `psutil==5.9.8`, `websocket-client==1.8.0`, Node 22 y
`jsdom==26.1.0`. Chromium/Chrome y un wkhtmltopdf funcional son necesarios para
que las pruebas reales de navegador y PDF no queden omitidas.

Primero, comprobaciones locales desde la raíz del repositorio:

```bash
python tools/check_addon_package.py
python -m unittest discover -s tools -v
python -m compileall -q alvina_branch_requisition
npm install --prefix /tmp/alvina-js-test --no-package-lock --no-audit --no-fund jsdom@26.1.0
NODE_PATH=/tmp/alvina-js-test/node_modules node --test tools/test_frontend.cjs
```

Estas comprobaciones no validan por sí solas ACL, vistas ni ejecución del ORM.
Para PDF en Linux amd64, `python tools/setup_test_pdf.py` descarga paquetes
fijados por SHA256 y extrae el runtime en `/tmp/alvina-pdf-runtime`, sin instalar
paquetes del sistema. Antes de ejecutar Odoo:

```bash
export PATH=/tmp/alvina-pdf-runtime/usr/local/bin:$PATH
export LD_LIBRARY_PATH=/tmp/alvina-pdf-runtime/usr/lib/x86_64-linux-gnu
```

Preparar una base nueva desechable y una configuración **de pruebas**, con rutas
reales de Odoo/addons, datos fuera del repositorio, usuario PostgreSQL sin
superusuario y HTTP local. No usar las credenciales/base de producción.

```bash
/path/to/venv/bin/python /path/to/odoo/odoo-bin \
  -c /path/to/test.conf -d ALVINA_DISPOSABLE_TEST \
  -i alvina_branch_requisition --without-demo \
  --test-enable --test-tags=/alvina_branch_requisition --stop-after-init \
  --http-interface=127.0.0.1 --http-port=8079
```

Para una base desechable con el addon instalado, usar `-u` en lugar de `-i`.
Comprobar el resumen de `odoo.tests.result`: cero fallos, cero errores y ninguna
omisión de las pruebas requeridas; un proceso que termina sin traceback no
sustituye ese resumen. Repetir la aceptación con las tres cuentas de
[OPERATING_FLOW.md](OPERATING_FLOW.md) en una copia representativa.

El workflow prepara PostgreSQL/Odoo fuera del addon y ejecuta instalación limpia
con la suite. No se afirma una ejecución remota de GitHub Actions sin su
resultado verificable.

## Migración, recuperación y utilidades históricas

La actualización se realiza con carpeta completa, respaldo y `-u` dirigido;
no desinstalar para actualizar ni confiar solo en reiniciar el servicio.
El preflight detecta errores de empaquetado como la sustitución de
`models/commercial.py` por `branch.py` del incidente de octubre. Véase
[RECOVERY_2026-10-19.md](RECOVERY_2026-10-19.md).

El probe `tools/check_intercompany_upgrade.py` documenta específicamente la
migración **19.0.1.2.0 → 19.0.2.0.0** y comprueba esas versiones exactas.
No presentarlo como una prueba ejecutada de actualización a 19.0.3.0.0.
Se debe verificar el commit instalado, conservación de documentos/compañías,
cantidades y ausencia de conversiones comerciales retroactivas. La variante
`258a450` con `keeper_ids` sigue requiriendo mapeo específico.

`tools/check_flow_http.py` contiene la comprobación HTTP concurrente y PDF para
su fixture local dedicada. `tools/flow_smoke_fixture.py` crea datos sintéticos
y hace commit, únicamente en `alvina_logistics_http_test`, socket
`/tmp/alvina-ci-pg`, rol `odoo_test`. Ejecutar su fase `seed` desde Odoo shell;
con el servidor local en 127.0.0.1:8094 ejecutar `check_flow_http.py submit`;
después las fases shell `deliver` y `receive`, y finalmente
`check_flow_http.py pdf`. Las fases shell se seleccionan con
`ALVINA_FLOW_SMOKE_PHASE`. Nunca usar datos operativos. `tools/check_uninstall.py` es una prueba
**destructiva**, restringida a `alvina_requisition_test`; no es una instrucción
de actualización ni se requiere ejecutarla en una copia con información valiosa.

## Evidencia histórica, separada de esta entrega

| Versión | Resultado registrado | Alcance |
| --- | --- | --- |
| 19.0.2.0.0 | 117 casos Odoo, cero fallos/errores/omisiones; 6 Python y 5 DOM | Suite final con actualización; instalación limpia anterior de 116 casos antes del último caso de esquema alternativo |
| 19.0.1.2.0 | 76 casos Odoo; 6 Python y 5 DOM | Cotización compradora en borrador, precios y contexto web; aún no era el flujo comercial actual |
| 19.0.1.1.0 | 46 casos Odoo | Separación solicitante/abastecedora y migración desde 19.0.1.0.1 |
| 19.0.1.0.1 | 34 casos Odoo; 6 Python y 5 DOM | Auditoría inicial de seguridad, catálogo, cantidades, consolidación y navegador |

Para 19.0.2 se registraron instalación limpia, Chromium, PDF binario y HTTP
concurrente; una OC/OV en borrador por envío y una entrega parcial confirmada
manualmente. Ese comportamiento es histórico. La migración desde `d59eea3`
preservó dos requerimientos, incluido uno atendido parcialmente, sin crear OC,
OV, movimientos ni precios retroactivos. Los logs de aquella sesión incluyeron
`/tmp/alvina-intercompany-accepted.log`, `/tmp/alvina-intercompany-install.log`
y `/tmp/alvina-flow-upgrade.log`; son evidencia temporal, no parte del paquete.

La recuperación del 19 de octubre comprobó el fallo de arranque del ZIP
incorrecto y que una actualización dirigida resolvía el esquema pendiente.
No convierte la suite histórica en una certificación de esta continuación.

## Validaciones pendientes de la instalación real

Enterprise y automatismos privados, tema, datos fiscales, rutas/ubicaciones y
precios reales; operación interna cuando local e Industria comparten compañía;
trazabilidad con lotes/series y entradas de varios pasos; regresión del formulario
privado de producción y edición privada de líneas. Mantener los bloqueos
explicados en [NATIVE_INTERCOMPANY.md](NATIVE_INTERCOMPANY.md).

No hubo escritura en `SoyCalidad/alvinha`, ni conexión/despliegue a producción.
Publicar el repositorio de desarrollo no ejecuta esas acciones.
