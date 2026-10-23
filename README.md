# Alviña — Abastecimiento de sucursales — 19.0.3.1.0

Addon Odoo 19 `alvina_branch_requisition`. La sucursal solicita desde **Compras**;
Industria atiende desde **Ventas**. Odoo vincula y confirma la OC y la OV para
preparar Inventario. Las únicas confirmaciones operativas son el despacho real
de Logística y la recepción real de la sucursal. No genera facturas.

Corrección publicada en `fix/native-supply-qr-compatibility`, sobre la entrega
de Logística anterior. Publicar esta rama en GitHub no instala ni actualiza Odoo.
**No se ha desplegado en producción.** La configuración nace desactivada.

## Documentación actual

- [Qué fallaba, qué se corrigió y cómo completar la puesta en marcha](RELEASE_2026-10-23.md).
- [Flujo y configuración para administrador, sucursal y Logística](OPERATING_FLOW.md).
- [Diseño funcional, precios, seguridad e históricos](INTERCOMPANY_FLOW.md).
- [Compatibilidad nativa, módulos privados y límites](NATIVE_INTERCOMPANY.md).
- [Validación y reproducción de pruebas](TESTING.md).
- [Recuperación del incidente del 19/10/2026](RECOVERY_2026-10-19.md).
- [Recuperación de Ventas y manifiesto incompleto del 22/10/2026](RECOVERY_2026-10-22.md).
- [Antecedentes del traspaso](TRANSFER.md).

Los documentos históricos `SUPPLY_COMPANIES.md`, `INTEGRATION.md` y `TRANSFER.md`
conservan antecedentes de entregas anteriores. Para el comportamiento de esta
versión prevalecen las cuatro primeras guías de esta lista. Las referencias
antiguas a OC/OV únicamente en borrador o a confirmaciones comerciales manuales
no describen el flujo central de 19.0.3.1.0.

## Qué cambia

- Fecha requerida inicial y mínima: **hoy en Perú + dos días calendario**.
  Se permite una fecha posterior; se rechazan fechas anteriores también en el servidor.
- Rol reutilizable **Alviña: Logística de Industria**: todas las sucursales
  abastecidas por Industria dentro de las compañías ya autorizadas al usuario.
  Excluye ventas comunes, sus líneas y su análisis; no depende del vendedor anterior.
- **Ventas → Órdenes → Pedidos de sucursales**, sin el filtro «Mis cotizaciones».
- Guía interna valorizada por salida real, con cantidades y precios conservados
  al emitirla. La sucursal confirma lo recibido y sus diferencias desde Compras.
- Confirmación comercial automática de los dos documentos; no supone entrega,
  recepción ni facturación. Se conservan los documentos y cantidades históricas.

El addon sigue siendo técnico (`application=False`), sin aplicación raíz propia.
Conserva el formulario anterior de producción `/portal/production/new` sin editarlo;
el formulario de insumos de este addon es `/branch/requisition/new`.

## Límites antes de activar

Se valida sobre Odoo 19 Community. **No equivale a certificar la instalación real
Enterprise de Alviña.** Con `account_inter_company_rules` instalado, el nuevo
adaptador enlaza la OV generada por Odoo al confirmar la OC. Hace falta configurar
en Industria esa dirección nativa y comprobarla en la copia real; las pruebas
locales de contrato no ejecutan Enterprise. Ver [revisión y puesta en marcha](RELEASE_2026-10-23.md).
También está bloqueada la operación cuando compradora e Industria son la misma
compañía. No se crean empresas ficticias para eludirlo.

La recepción guiada de esta entrega exige una operación real de entrada de
**un paso**, bienes sin lotes/números de serie y conservación de saldos. Las
integraciones privadas de fabricación y edición de líneas requieren la revisión
descrita en [NATIVE_INTERCOMPANY.md](NATIVE_INTERCOMPANY.md).

Identificar el **commit realmente instalado**, no solo la versión: la rama
alternativa `feature/central-supply-multicompany` tiene otro esquema con el mismo
número antiguo 19.0.1.2.0. Su tabla de asignaciones provoca un bloqueo explícito;
necesita un mapeo específico, sin fusionar ni descartar su historial.

## Preparar una actualización en pruebas

Dependencias: `purchase`, `stock`, `purchase_stock`, `sale_management`,
`sale_stock`, `portal`, `website`. Usar el checkout existente; no crear otro
worktree salvo petición expresa.

1. Respaldar la base de pruebas y su filestore. Conservar todas las rutas de
   addons originales, incluidos los privados y Enterprise autorizados.
2. Ejecutar `python tools/check_addon_package.py` en este repositorio.
3. Copiar **la carpeta completa `alvina_branch_requisition/`**, incluidas sus
   migraciones, al mismo nivel que los demás addons del repositorio operativo.
   No anidar el repositorio completo dentro de esa carpeta ni copiar archivos sueltos.
4. Con el servicio de esa base de pruebas detenido, usar su configuración y
   entorno Python reales:

```bash
/path/to/odoo/odoo-bin -c /path/to/test.conf -d ALVINA_TEST \
  -u alvina_branch_requisition --stop-after-init
```

Para una base que nunca tuvo el addon, usar `-i` en lugar de `-u`. Un reinicio
no actualiza campos, vistas ni migraciones. **No desinstalar para actualizar**:
se perderían los registros propios. El incidente de octubre incluyó un
`models/commercial.py` sustituido por una copia de `branch.py`; el preflight
comprueba ese tipo de paquete incompleto antes de transferirlo.

Después, seguir [OPERATING_FLOW.md](OPERATING_FLOW.md) en la copia de pruebas.
No activar producción hasta resolver los bloqueos y autorizar su despliegue.
