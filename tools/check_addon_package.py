"""Read-only preflight for this addon's model links before copying its files.

No Odoo/database is required and uploaded Python is parsed, never executed.
This catches the actual incident where commercial.py was replaced by branch.py;
it does not validate database migrations or Enterprise compatibility.
"""
import argparse
import ast
import csv
from pathlib import Path
import xml.etree.ElementTree as ET


DEFAULT_ADDON = Path(__file__).resolve().parents[1] / 'alvina_branch_requisition'
# These links are consumed by fulfillment, views, rules and the report. Missing
# either inverse field can prevent Odoo from building the entire registry.
REQUIRED_LINKS = {
    'alvina.branch.request': {'supply_flow', 'supply_config_id', 'operation_mode', 'sale_order_id'},
    'sale.order': {'alvina_branch_request_id'},
    'sale.order.line': {'alvina_request_line_id'},
    'purchase.order': {'alvina_sale_order_id'},
    'purchase.order.line': {'alvina_request_line_id'},
}
V3_FIELD_LINKS = {
    ('sale.report', 'alvina_sale_order_id'): ('Many2one', 'sale.order'),
    ('stock.picking', 'alvina_dispatch_id'): ('Many2one', 'alvina.branch.dispatch'),
    ('stock.picking', 'alvina_emitted_dispatch_ids'): ('One2many', 'alvina.branch.dispatch', 'picking_id'),
    ('alvina.branch.dispatch', 'picking_id'): ('Many2one', 'stock.picking'),
    ('alvina.branch.dispatch', 'request_id'): ('Many2one', 'alvina.branch.request'),
    ('alvina.branch.dispatch', 'line_ids'): ('One2many', 'alvina.branch.dispatch.line', 'dispatch_id'),
    ('alvina.branch.dispatch.line', 'dispatch_id'): ('Many2one', 'alvina.branch.dispatch'),
    ('alvina.branch.dispatch.line', 'request_line_id'): ('Many2one', 'alvina.branch.request.line'),
    ('alvina.branch.dispatch.receipt', 'dispatch_id'): ('Many2one', 'alvina.branch.dispatch'),
    ('alvina.branch.dispatch.receipt', 'line_ids'): ('One2many', 'alvina.branch.dispatch.receipt.line', 'wizard_id'),
    ('alvina.branch.dispatch.receipt.line', 'wizard_id'): ('Many2one', 'alvina.branch.dispatch.receipt'),
    ('alvina.branch.dispatch.receipt.line', 'dispatch_line_id'): ('Many2one', 'alvina.branch.dispatch.line'),
}
V3_REQUIRED_FIELDS = {
    'alvina.branch.dispatch': {'snapshot_json', 'receipt_state', 'receipt_confirmation_json'},
    'alvina.branch.dispatch.line': {'quantity', 'price_unit', 'amount_total'},
    'alvina.branch.dispatch.receipt.line': {'quantity'},
}
V3_REQUIRED_METHODS = {
    'alvina.branch.binding': {'_alvina_user_can_attend_supply'},
    'sale.report': {'_select_additional_fields'},
    'stock.picking': {'_alvina_emit_dispatch'},
    'alvina.branch.dispatch': {'action_open_receipt', 'action_print'},
    'alvina.branch.dispatch.receipt': {'action_confirm'},
    'report.alvina_branch_requisition.dispatch_note': {'_get_report_values'},
}
V3_ACCESS_LINKS = {
    'model_alvina_branch_dispatch', 'model_alvina_branch_dispatch_line',
    'model_alvina_branch_dispatch_receipt', 'model_alvina_branch_dispatch_receipt_line',
}
# Validate loaded XML identities and their actual model/action links. A stale
# file left on disk must not make an incomplete manifest appear publishable.
V3_XML_LINKS = {
    'security/groups.xml': {
        'group_industry_logistics': ('res.groups', {}),
    },
    'security/commercial_rules.xml': {
        'rule_industry_logistics_sales_report_scope': ('ir.rule', {'model_id': ('ref', 'sale.model_sale_report')}),
    },
    'security/dispatch_security.xml': {
        'sequence_dispatch_note': ('ir.sequence', {'code': ('text', 'alvina.branch.dispatch')}),
        'rule_dispatch_scope': ('ir.rule', {'model_id': ('ref', 'model_alvina_branch_dispatch')}),
        'rule_dispatch_line_scope': ('ir.rule', {'model_id': ('ref', 'model_alvina_branch_dispatch_line')}),
    },
    'views/logistics_views.xml': {
        'action_logistics_branch_sales': ('ir.actions.act_window', {'res_model': ('text', 'sale.order')}),
    },
    'views/dispatch_views.xml': {
        'action_dispatch_notes': ('ir.actions.act_window', {'res_model': ('text', 'alvina.branch.dispatch')}),
        'view_dispatch_receipt_form': ('ir.ui.view', {'model': ('text', 'alvina.branch.dispatch.receipt')}),
    },
    'report/dispatch_note_templates.xml': {
        'action_dispatch_note_report': ('ir.actions.report', {
            'model': ('text', 'alvina.branch.dispatch'),
            'report_name': ('text', 'alvina_branch_requisition.dispatch_note'),
        }),
    },
}


def check_package(addon):
    addon = Path(addon)
    errors = []
    try:
        manifest = ast.literal_eval((addon / '__manifest__.py').read_text(encoding='utf-8'))
    except (OSError, SyntaxError, ValueError) as error:
        return ['No se puede leer el manifest: ' + str(error)]
    for filename in manifest.get('data', []):
        if not (addon / filename).is_file():
            errors.append('Archivo declarado en el manifest ausente: ' + filename)
    for dependency in ('sale_management', 'sale_stock'):
        if dependency not in manifest.get('depends', []):
            errors.append('Dependencia necesaria ausente: ' + dependency)
    if not (addon / 'tests' / '__init__.py').is_file():
        errors.append('Falta tests/__init__.py: Odoo no descubrirá la suite en una carpeta llamada test/.')

    def parse(filename):
        try:
            return ast.parse(filename.read_text(encoding='utf-8'), filename=str(filename))
        except (OSError, SyntaxError) as error:
            errors.append(str(error))
            return ast.Module(body=[], type_ignores=[])

    root = parse(addon / '__init__.py')
    if not any(isinstance(node, ast.ImportFrom) and node.level == 1 and not node.module
               and any(alias.name == 'models' for alias in node.names) for node in root.body):
        errors.append('__init__.py no importa el paquete models.')
    imported = []
    for node in parse(addon / 'models' / '__init__.py').body:
        if isinstance(node, ast.ImportFrom) and node.level == 1 and not node.module:
            imported.extend(alias.name for alias in node.names)
    fields_by_model = {}
    field_calls = {}
    methods_by_model = {}
    for module in imported:
        for node in parse(addon / 'models' / (module + '.py')).body:
            if not isinstance(node, ast.ClassDef):
                continue
            names = {}
            field_names = set()
            for assignment in node.body:
                if not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1:
                    continue
                target = assignment.targets[0]
                if not isinstance(target, ast.Name):
                    continue
                if target.id in ('_name', '_inherit'):
                    try:
                        names[target.id] = ast.literal_eval(assignment.value)
                    except (ValueError, TypeError):
                        pass
                value = assignment.value
                if (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                        and isinstance(value.func.value, ast.Name) and value.func.value.id == 'fields'):
                    field_names.add(target.id)
            model = names.get('_name') or names.get('_inherit')
            if isinstance(model, str):
                fields_by_model.setdefault(model, set()).update(field_names)
                methods_by_model.setdefault(model, set()).update(
                    child.name for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)))
                for assignment in node.body:
                    if (isinstance(assignment, ast.Assign) and len(assignment.targets) == 1
                            and isinstance(assignment.targets[0], ast.Name)
                            and assignment.targets[0].id in field_names):
                        field_calls[(model, assignment.targets[0].id)] = assignment.value
    for model, links in REQUIRED_LINKS.items():
        for name in sorted(links - fields_by_model.get(model, set())):
            errors.append('Campo requerido por las relaciones del addon ausente: ' + model + '.' + name)
    commercial = addon / 'models' / 'commercial.py'
    branch = addon / 'models' / 'branch.py'
    if commercial.is_file() and branch.is_file() and commercial.read_bytes() == branch.read_bytes():
        errors.append('commercial.py es una copia de branch.py: restaure el archivo comercial completo.')
    try:
        version = tuple(int(part) for part in str(manifest.get('version', '')).split('.'))
    except ValueError:
        version = ()
    if version >= (19, 0, 3):
        for module in ('logistics', 'dispatch'):
            if module not in imported:
                errors.append('models/__init__.py no importa el módulo obligatorio de versión 3: ' + module)
        for model, names in V3_REQUIRED_FIELDS.items():
            for name in sorted(names - fields_by_model.get(model, set())):
                errors.append('Campo obligatorio de versión 3 ausente: ' + model + '.' + name)
        for model, names in V3_REQUIRED_METHODS.items():
            for name in sorted(names - methods_by_model.get(model, set())):
                errors.append('Método operativo obligatorio de versión 3 ausente: ' + model + '.' + name)
        for (model, name), expected in V3_FIELD_LINKS.items():
            call = field_calls.get((model, name))
            actual = None
            if call is not None:
                try:
                    values = {keyword.arg: ast.literal_eval(keyword.value) for keyword in call.keywords
                              if keyword.arg in ('comodel_name', 'inverse_name')}
                    args = [ast.literal_eval(arg) for arg in call.args[:2]]
                    actual = (call.func.attr,
                              args[0] if args else values.get('comodel_name'))
                    if expected[0] == 'One2many':
                        actual += (args[1] if len(args) > 1 else values.get('inverse_name'),)
                except (ValueError, TypeError):
                    pass
            if actual != expected:
                errors.append('Enlace relacional de versión 3 ausente o incorrecto: ' + model + '.' + name)
        try:
            with (addon / 'security/ir.model.access.csv').open(encoding='utf-8', newline='') as access_file:
                accessible = {row.get('model_id:id') for row in csv.DictReader(access_file)
                              if row.get('group_id:id') == 'group_requester' and row.get('perm_read') == '1'}
            for model in sorted(V3_ACCESS_LINKS - accessible):
                errors.append('Enlace de acceso de versión 3 ausente para Solicitante: ' + model)
        except (OSError, csv.Error) as error:
            errors.append('No se pueden leer los accesos de versión 3: ' + str(error))
        for filename, records in V3_XML_LINKS.items():
            if filename not in manifest.get('data', []):
                errors.append('XML obligatorio de versión 3 no cargado por el manifest: ' + filename)
                continue
            try:
                xml = ET.parse(addon / filename)
            except (OSError, ET.ParseError) as error:
                errors.append('XML obligatorio de versión 3 no se puede leer: ' + str(error))
                continue
            by_id = {node.get('id'): node for node in xml.iter('record')}
            if filename == 'report/dispatch_note_templates.xml' and not any(
                    node.get('id') == 'dispatch_note' for node in xml.iter('template')):
                errors.append('Plantilla PDF obligatoria de versión 3 ausente: dispatch_note')
            for identifier, (model, links) in records.items():
                record = by_id.get(identifier)
                if record is None or record.get('model') != model:
                    errors.append('Registro XML obligatorio de versión 3 ausente o incorrecto: ' + identifier)
                    continue
                for name, (kind, expected) in links.items():
                    field = record.find("field[@name='%s']" % name)
                    actual = None if field is None else (
                        field.get('ref') if kind == 'ref' else (field.text or '').strip())
                    if actual != expected:
                        errors.append('Enlace XML de versión 3 ausente o incorrecto: ' + identifier + '.' + name)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('addon', nargs='?', type=Path, default=DEFAULT_ADDON)
    args = parser.parse_args()
    errors = check_package(args.addon)
    if errors:
        print('PAQUETE INCOMPLETO O INCONSISTENTE:')
        for error in errors:
            print('- ' + error)
        return 1
    print('PACKAGE_LINKS_OK: archivos declarados, imports y enlaces comerciales/operativos presentes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
