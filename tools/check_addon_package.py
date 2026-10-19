"""Read-only preflight for this addon's model links before copying its files.

No Odoo/database is required and uploaded Python is parsed, never executed.
This catches the actual incident where commercial.py was replaced by branch.py;
it does not validate database migrations or Enterprise compatibility.
"""
import argparse
import ast
from pathlib import Path


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
    for model, links in REQUIRED_LINKS.items():
        for name in sorted(links - fields_by_model.get(model, set())):
            errors.append('Campo requerido por las relaciones del addon ausente: ' + model + '.' + name)
    commercial = addon / 'models' / 'commercial.py'
    branch = addon / 'models' / 'branch.py'
    if commercial.is_file() and branch.is_file() and commercial.read_bytes() == branch.read_bytes():
        errors.append('commercial.py es una copia de branch.py: restaure el archivo comercial completo.')
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
    print('PACKAGE_LINKS_OK: archivos declarados, imports y enlaces comerciales presentes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
