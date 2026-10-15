# Integración con los módulos existentes de Alviña

## Procedencia y alcance de la revisión

Se inspeccionó estáticamente el archivo aportado `alvinha-cybe.zip`, cuyo directorio
superior es `alvinha-cybe/`. La captura de GitHub muestra el repositorio privado
`SoyCalidad/alvinha` y la rama seleccionada `cybe`. Un ZIP de código y una captura
no demuestran qué revisión está instalada en el servidor ni si esa rama corresponde
a pruebas o a producción. Es necesario confirmarlo con su administrador.

No se ejecutó el código importado ni se utilizaron sus controladores, conexiones,
tareas programadas o servicios externos. Las instrucciones incluidas en los
documentos del ZIP son documentación de ese código, no autorización de despliegue.

Las rutas y líneas de las tablas siguientes son relativas a la raíz del ZIP y
corresponden a la copia inspeccionada. Las referencias al addon nuevo son relativas
a este repositorio.

Los nombres técnicos deben conservarse exactamente: los módulos privados usan
principalmente el prefijo **`alvinha_`**; `alvina_stock_request` y el nuevo
**`alvina_branch_requisition`** usan **`alvina_`**. No son nombres intercambiables.

## Formulario existente localizado

| Elemento | Evidencia en el ZIP | Consecuencia para la integración |
| --- | --- | --- |
| Entrada al formulario | `alvinha_mrp/controllers/main.py:35`, ruta `/portal/production/new` | El formulario pertenece a `alvinha_mrp`, no al addon nuevo. |
| Plantilla | `alvinha_mrp/views/portal_production_templates.xml:4`, identificador `alvinha_mrp.production_form` | Usa `website.layout`, contenedor Bootstrap, título `Registra tu pedido`, color `#681412`, selectores en una fila y tabla de cantidades. La revisión nueva usa esos patrones con plantilla y recursos propios, sin modificar la original; se probó en Chromium con el tema estándar y queda pendiente contrastar el tema privado. |
| Recursos frontend | `alvinha_mrp/static/src/js/public_widget.js:11`; declaración en `alvinha_mrp/__manifest__.py:31` | El widget se limita a `form#portal_production_form`. El nuevo formulario debe conservar su identificador y recursos propios para evitar interceptar esos eventos. |
| Carga de productos | `alvinha_mrp/controllers/main.py:66`; modelo `mrp.category.product` en `alvinha_mrp/models/mrp_category_product.py:8` | Los agrupadores de producción son un modelo propio. No equivalen automáticamente a las categorías de productos de requerimientos. |
| Envío | `alvinha_mrp/controllers/main.py:102`, ruta `/portal/production/create`; creación de venta en `:250` y `:255` | Es un flujo de producción que también crea ventas. El nuevo addon debe usar su controlador y modelos de requerimientos, sin llamar a ese envío. |
| Acción del menú existente | `alvinha_mrp/views/menu.xml:8`, `ir.actions.act_url`, destino `new` | Confirma el mecanismo de apertura en una pestaña nueva. En esta copia el menú está bajo `mrp.menu_mrp_manufacturing` (`:17`), no bajo Ventas. La ubicación observada en la instalación puede deberse a otra revisión o configuración de base de datos. |

La equivalencia de presentación puede verificarse contra esta plantilla. La
apariencia final también depende de `website.layout`, el tema, los recursos
instalados y las vistas heredadas de la base de pruebas. Inspeccionar el XML por sí
solo no prueba equivalencia visual en Enterprise.

## Sucursales y asignaciones

| Dato | Evidencia en el ZIP | Estado |
| --- | --- | --- |
| Entidad de sucursal | `alvinha_base/models/res_partner.py:30` | Es un contacto `res.partner` con `type_client == 'branch'`. Las otras opciones son `store` y `extra`; no deben tratarse como sucursales sin una decisión expresa. |
| Nombre alternativo | `alvinha_base/models/res_partner.py:16` | Campo `alias`, usado por la plantilla existente para mostrar el contacto. |
| Configuración en contacto | `alvinha_base/views/res_partner_view.xml:13` | La vista expone `type_client`. |
| Usuario interno sin rol de gestor de ventas | `alvinha_mrp/views/portal_production_templates.xml:50`; valores en `alvinha_mrp/controllers/main.py:58` | El formulario existente utiliza `user.company_id.partner_id`. No demuestra que cada compañía sea una sucursal ni que el contacto tenga `type_client == 'branch'`. |
| Usuario portal | `alvinha_mrp/views/portal_production_templates.xml:75`; valores en `alvinha_mrp/controllers/main.py:57` | Utiliza `user.partner_id`. Tampoco demuestra una asignación de varias sucursales. |
| Selector para gestor | `alvinha_base/controllers/main.py:17` y `:35`; llamada en `alvinha_mrp/static/src/js/public_widget.js:169` | Lista contactos clientes tipificados de una compañía o compartidos. No implementa autorización individual de sucursales. |
| Almacén en el flujo de venta | `alvinha_mrp/controllers/main.py:271` | Busca por compañía y nombre parecido a `Producto Terminado`. No es una relación sucursal-almacén abastecedor y no debe copiarse para requerimientos. |

No se encontró en los módulos Python aportados una extensión de `res.users` que
declare un conjunto autorizado de sucursales ni un campo de sucursal que determine
su almacén abastecedor. Esto no excluye campos de Studio u otros módulos no
incluidos en el ZIP.

El endpoint `/portal/get_partners` de `alvinha_base` declara `auth='public'` y utiliza
`sudo()` para buscar contactos (`controllers/main.py:17` y `:35`). No debe
reutilizarse para decidir las sucursales autorizadas del nuevo formulario. El
selector deshabilitado en una página tampoco reemplaza la validación del servidor.
Este hallazgo corresponde a código existente; su corrección requeriría un cambio
separado en ese módulo y no se realizó como parte de esta integración.

### Configuración recomendada para el addon nuevo

El vínculo `alvina.branch.binding` debe referenciar un contacto existente de la
sucursal y conservar una asignación explícita de usuarios y almacén. No se deben
crear nuevos contactos, compañías o almacenes por inferencia, ni copiar las
asignaciones inseguras del formulario de producción.

Para la instalación real, los contactos candidatos se deben contrastar con
`res.partner.type_client == 'branch'` y mostrar `alias` cuando corresponda. El selector del núcleo se limita a contactos existentes, comprueba acceso al configurar y vuelve a comprobar estado activo/compañía al enviar. Esta comprobación no sustituye validar la clasificación privada `type_client`. El núcleo
adaptable no debe declarar compatibilidad automática con `alvinha_base`: ese campo
solo existe cuando el módulo privado está instalado. Si se añade un adaptador
específico, debe declarar su dependencia de `alvinha_base`, validar tipo de contacto,
compañía y estado activo, y aportar pruebas propias. No basta con comprobar que un
campo de nombre coincidente existe.

Mientras no se identifique una relación de permisos ya mantenida en la base, la
asignación explícita en el vínculo es la fuente de autorización del nuevo addon.
Una sola asignación produce una sucursal automática bloqueada. Desde 19.0.1.2.0,
varias asignaciones bloquean el formulario y requieren corrección administrativa;
sin asignación tampoco se permite enviar. Los almaceneros también necesitan asignaciones
expresas. No convertir pertenencia a una compañía en acceso a todas sus sucursales.

## Relación con `alvina_stock_request`

Ese addon ya existe en el ZIP y es distinto del nuevo desarrollo:

| Aspecto | `alvina_stock_request` existente | `alvina_branch_requisition` nuevo |
| --- | --- | --- |
| Objeto principal | `alvina.stock.request`, `models/request.py:16` | `alvina.branch.request` |
| Destino | `alvina.stock.department`, `models/department.py:6` | Vínculo con la sucursal real |
| Función | Solicitudes de insumos, credenciales QR/Code128 y entrega autorizada mediante traslado interno | Formulario de sucursales y necesidades pendientes de compra; sin generar compras o traslados |
| Navegación | Aplicación raíz propia, `views/menus.xml:2`, `application=True` en `__manifest__.py:28` | Submenús de Compras, sin aplicación raíz |
| Almacén | Código `INS` y rutas específicas validadas en `models/department.py:21` | Almacén abastecedor configurado por vínculo, sin asumir un código global |

No reemplazar, renombrar ni eliminar `alvina_stock_request`. No sumar
automáticamente sus solicitudes al consolidado nuevo: una misma necesidad podría
contarse dos veces y sus estados representan procesos distintos. Una futura unión
requiere definir relaciones de origen, entrega parcial, cancelación, unidades de
medida y deduplicación, con pruebas. Sus departamentos no son evidencia de un
catálogo de sucursales.

## Dependencias y alcance de validación

| Componente | Dependencias declaradas relevantes | Qué puede validarse |
| --- | --- | --- |
| Addon nuevo | `purchase`, `stock`, `purchase_stock`, `portal`, `website` (`alvina_branch_requisition/__manifest__.py`) | El núcleo puede probarse con Odoo 19 Community. Eso no demuestra su funcionamiento con la pila Enterprise y módulos privados del servidor. |
| `alvinha_base` | Además de módulos Community de venta, compras, stock, fabricación, web, contactos y RR. HH., declara `mrp_workorder`, `mrp_account_enterprise` y localización peruana (`__manifest__.py:17`) | Requiere módulos Enterprise y verificar la disponibilidad y revisión de toda la localización. El ZIP no incluye esos módulos oficiales. No instalar esta pila en Community como si estuviese completa. |
| Localización declarada por `alvinha_base` | `l10n_pe`, `l10n_pe_edi`, `l10n_pe_edi_pos`, `l10n_pe_edi_stock`, `l10n_pe_pos`, `l10n_pe_reports`, `l10n_pe_reports_stock` (`__manifest__.py:24` y `:29`) | Confirmar estos nombres, su procedencia y versiones en los addons realmente desplegados. No se dispone de sus manifiestos en el ZIP para certificar la distribución de cada uno. |
| `alvinha_mrp` | `alvinha_base`, `mrp`, `website` (`__manifest__.py:10`) | Hereda los requisitos Enterprise de `alvinha_base`. Su versión `2.1` no identifica por sí sola una versión de Odoo. |
| `alvinha_purchase` | `purchase`, `alvinha_base` (`__manifest__.py:8`) | Personaliza `purchase.order`, cantidades y vistas; no es dependencia del nuevo núcleo. Verificar coexistencia en pruebas sin tocar sus archivos. |
| `alvinha_stock` / `alvinha_mrp_workorder` | `alvinha_base` (sus manifiestos, líneas `:8` y `:10`) | Deben incluirse si están instalados en la base de pruebas. No se ejecutaron sus integraciones de guías ni servicios. |
| `alvina_stock_request` | `stock`, `mail`, bibliotecas Python `qrcode`, `reportlab` (`__manifest__.py:9`) | Son requisitos de ese addon, no bibliotecas externas del formulario nuevo. Su generación gráfica requiere además el backend descrito en su README; no instalarlo solo para probar el núcleo nuevo. |

Que la revisión estática haya identificado modelos y rutas no certifica la
instalación completa del ZIP. Tampoco se debe añadir `alvinha_base` como dependencia
del núcleo únicamente para reproducir colores o maquetación: arrastraría una pila
amplia de fabricación, POS y localización fiscal sin necesidad funcional.

## Dónde colocar el addon

El repositorio de desarrollo `GiulianaEmay/alvina-odoo-forms` puede conservarse como
fuente del módulo. Si el administrador despliega los módulos personalizados desde
`SoyCalidad/alvinha`, el cambio que debe revisar en una **rama de pruebas
confirmada** consiste en añadir una sola carpeta como hermana de las existentes:

```text
alvinha/                         # raíz del repositorio de addons existentes
├── alvina_stock_request/        # existente, sin reemplazar
├── alvinha_base/                # existente
├── alvinha_mrp/                 # existente
├── alvinha_purchase/            # existente
├── alvinha_stock/               # existente
└── alvina_branch_requisition/   # copiar esta carpeta completa del repo nuevo
    ├── __init__.py
    ├── __manifest__.py
    ├── controllers/
    ├── data/
    ├── models/
    ├── security/
    ├── static/
    ├── tests/
    └── views/
```

No envolverla en `alvina-odoo-forms/alvina_branch_requisition/` dentro de ese
repositorio de addons, no copiar `.git`, no importar el ZIP entero y no editar el
código original de `purchase`. Odoo busca carpetas de módulos dentro de cada ruta
de `addons_path`. También es válido mantener los dos repositorios separados y
añadir la raíz de `alvina-odoo-forms` a `addons_path` de pruebas, si el mecanismo de
alojamiento lo permite.

Copiar o subir código a GitHub no instala el addon por sí solo, aunque ciertos
servicios sí construyen o despliegan automáticamente ramas vinculadas. Antes de
subirlo al repositorio operativo se debe confirmar qué entorno recibe esa rama.
La captura no permite clasificar `cybe` como pruebas. No fusionar ni colocar el
addon en una rama que actualice producción con esta autorización.

## Información que aún hace falta

1. Alojamiento, rama y commit realmente desplegados; identificar una base y una
   rama de pruebas que no publiquen cambios en producción.
2. Versión exacta de Community/Enterprise, rutas `addons_path`, manifiestos y lista
   de módulos instalados, incluidas personalizaciones Studio y vistas heredadas.
   Esto permite verificar dependencias y la diferencia del menú encontrado.
3. Contactos reales marcados como sucursal, sus identificadores externos, alias y
   compañía; confirmar los contactos compartidos y su compañía operativa. No
   hacen falta datos de clientes ajenos al alcance.
4. Usuarios solicitantes y almaceneros autorizados por sucursal; determinar si esa
   relación ya existe en módulos o campos no incluidos. No inferirla de un rol de
   ventas ni de `company_id`.
5. Almacén abastecedor y ubicaciones relevantes por sucursal y compañía; confirmar
   si la disponibilidad requerida es del almacén central o de la propia sucursal.
6. Categorías reales y productos habilitados, unidades de medida y política de
   entregas/cierre de pendientes. El ZIP no contiene los datos de la base para
   validar esos valores.
7. Acceso a una instancia de pruebas con los temas y módulos privados para probar
   apariencia, permisos, menús, consolidado y coexistencia. La certificación de
   Enterprise y de la instalación privada depende de esa validación.

Esta información completa la integración; no hace falta copiar todo Odoo al
repositorio ni compartir credenciales en documentos o chat.

## Límites de la entrega revisada

El formulario, permisos y consolidado están probados en Community; no se certifica la instalación privada mediante el ZIP. La atención parcial/final aún no tiene procedimiento de registro y no cambia `qty_supplied`: por ahora las solicitudes se revisan o cancelan, pero no se cierran por entrega. Es necesario definir ese procedimiento antes del uso operativo. La compra sugerida sigue siendo orientativa, sin asignación exclusiva de entradas.

El almacén de un vínculo con historial no se puede reasignar. La unicidad del contacto también impide archivar y crear un segundo vínculo del mismo contacto: un cambio de almacén con historial requiere diseñar una migración o versionado, no duplicar contactos ni borrar solicitudes.

La autorización actual permite subir las correcciones únicamente a `GiulianaEmay/alvina-odoo-forms`. El usuario trasladará después la carpeta del addon al repositorio compartido; no se realizó escritura en `SoyCalidad/alvinha` ni se confirmó el destino de despliegue de `cybe`.
