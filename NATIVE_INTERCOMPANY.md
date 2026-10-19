# Auditoría de integración nativa y privada

## Variante publicada por separado

La revisión remota encontró `feature/central-supply-multicompany` en
`258a450923d1fe20317eb12cf7e0d98807c7dc4b`, basada en `bf19163`, mientras esta
entrega parte de `feature/multi-company-supply` en `d59eea3`. Ambas versiones
anteriores se identifican como 19.0.1.2.0, pero su esquema no es idéntico.
La alternativa utiliza `keeper_ids`/`alvina_binding_keeper_rel`, fija una sola
sucursal y consulta costo actual en su consolidado. Esta rama no se ha fusionado
con ella ni la ha sobrescrito. La actualización detecta aquella relación y exige
un mapeo revisado; no elimina o mezcla sus asignaciones automáticamente.
Antes de actualizar una base existente se necesita el **commit del addon
efectivamente instalado**. La evidencia de migración actual corresponde a
`d59eea3` y sus migraciones anteriores, no a aquella alternativa.

## Código efectivamente disponible

Se verificó Odoo Community 19 en la revisión
`e1ed4fe077ba98ce7ac6802a43bb68242081dee9`. Su módulo `base_setup` referencia
`account_inter_company_rules` como automatismo de ventas/compras entre compañías:

- `addons/base_setup/models/res_config_settings.py`, campo de instalación.
- `addons/base_setup/views/res_config_settings_views.xml`, descripción del automatismo.
- `addons/stock/models/res_company.py`, propiedades de ubicaciones intercompañía
  de los contactos comerciales de las compañías.

No se dispone del checkout Enterprise autorizado. El intento de consultar
`odoo/enterprise`, rama `19.0`, devolvió «Repository not found». Por tanto **no
se ha verificado ningún hook, contexto de omisión, sincronización o método
generador nativo Enterprise**. No se ha desactivado ni alterado su configuración.

## Decisión implementada

El servicio de esta rama produce los dos borradores atómicamente en el runtime
Community probado. Un automatismo que generase la contraparte al confirmar uno
podría duplicarla. El guardia `_assert_supported()` rechaza el nuevo flujo si
`account_inter_company_rules` está instalado, pendiente de actualización o
eliminación. Se ejecuta al habilitar/usar el flujo y en las confirmaciones de
sus órdenes vinculadas, incluida la aprobación estándar de compras. Las órdenes
normales ajenas al addon no se modifican.

No se debe desinstalar el automatismo, editar su estado ni quitar este guardia
para hacer pasar la prueba. Tampoco afirmar que no está instalado basándose solo
en el código disponible aquí.

Para integrar la instalación real hace falta obtener **en pruebas**:

1. Revisión exacta y código completo de `account_inter_company_rules` y de
   cualquier addon que lo herede; dependencias/manifest de esos addons.
2. Configuración existente de generación/sincronización de OC/OV y sus usuarios,
   compañías, diarios si aplica y opciones de confirmación/validación.
3. Extensiones de Compras, Ventas, Inventario y automatizaciones de servidor que
   creen, confirmen o sincronicen estos documentos o sus entregas/recepciones.
4. Mapa real de compañías, contactos comerciales, almacenes, operaciones, rutas
   y ubicaciones; roles existentes de Rolly y de los usuarios de sucursal.

Con esa evidencia se podrá adaptar un mecanismo real y probar unicidad incluso
al confirmar/aprobar ambos documentos, concurrencia, cancelación y sincronización
de Inventario. No inventar nombres de campos/hook de Enterprise.

## Efecto privado conocido

El ZIP facilitado (`alvinha-cybe.zip`) contiene `alvinha_mrp/models/sale_order.py`:
su override de creación de líneas (aproximadamente líneas 218–242) puede llamar
`_create_mrp_production` (aproximadamente 247) cuando el producto tiene una LdM,
incluso con la OV en borrador. Esto no corresponde al despacho de insumos.

El nuevo puente comprueba ese módulo instalado y las LdM del producto para
Industria. Si se activaría fabricación, rechaza el envío con un mensaje de
integración pendiente. No falsifica `is_from_mrp`, no copia código privado ni
crea órdenes de fabricación para eludir el problema. La instalación representativa
debe verificar otras automatizaciones que no aparecen en el ZIP.

## Una misma compañía

El requisito funcional es uniforme por sucursal, con independencia de su
condición jurídica. La compañía operativa debe seguir siendo la realmente
configurada. Si es Industria, no corresponde generar compra/venta intercompañía
de la entidad consigo misma ni inventar otra empresa.

Se propuso conservar formulario, revisión, preparación y PDF mediante una orden
interna y un traslado a una ubicación existente. La confirmación de esa variante
y su destino siguen pendientes. `_create_internal_dispatch()` está bloqueado
expresamente y no produce documentos. Esta rama **todavía no cubre esa operación**.
