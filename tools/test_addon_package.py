"""Regression for the broken manual upload, without executing supplied code."""
from pathlib import Path
import ast
import shutil
import tempfile
import unittest

from check_addon_package import check_package, DEFAULT_ADDON


class AddonPackageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.addon = Path(self.directory.name) / 'alvina_branch_requisition'
        shutil.copytree(DEFAULT_ADDON, self.addon, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

    def test_correct_addon_has_its_required_model_links(self):
        self.assertEqual(check_package(self.addon), [])

    def test_branch_code_in_commercial_file_breaks_the_required_inverse_fields(self):
        shutil.copyfile(self.addon / 'models/branch.py', self.addon / 'models/commercial.py')
        errors = check_package(self.addon)
        for field in ('sale.order.line.alvina_request_line_id',
                      'purchase.order.line.alvina_request_line_id',
                      'alvina.branch.request.supply_flow'):
            self.assertTrue(any(field in error for error in errors), errors)
        self.assertTrue(any('copia de branch.py' in error for error in errors))

    def test_a_file_present_but_not_imported_cannot_supply_model_links(self):
        imports = self.addon / 'models/__init__.py'
        imports.write_text(imports.read_text().replace(', commercial', ''), encoding='utf-8')
        errors = check_package(self.addon)
        self.assertTrue(any('sale.order.line.alvina_request_line_id' in error for error in errors), errors)

    def _replace(self, filename, before, after):
        path = self.addon / filename
        source = path.read_text(encoding='utf-8')
        self.assertIn(before, source, 'The negative fixture must change the current package')
        path.write_text(source.replace(before, after, 1), encoding='utf-8')

    def _manifest(self):
        return ast.literal_eval((self.addon / '__manifest__.py').read_text(encoding='utf-8'))

    def test_logistics_file_must_be_imported_and_supply_its_analysis_link(self):
        self._replace('models/__init__.py', 'from . import logistics', '')
        self.assertTrue((self.addon / 'models/logistics.py').is_file())
        errors = check_package(self.addon)
        self.assertTrue(any('no importa' in error and 'logistics' in error for error in errors), errors)
        self.assertTrue(any('sale.report.alvina_sale_order_id' in error for error in errors), errors)
        self.assertTrue(any('alvina.branch.binding._alvina_user_can_attend_supply' in error
                            for error in errors), errors)

    def test_dispatch_file_must_be_imported_and_supply_the_operational_models(self):
        self._replace('models/__init__.py', 'from . import dispatch', '')
        self.assertTrue((self.addon / 'models/dispatch.py').is_file())
        errors = check_package(self.addon)
        for name in ('stock.picking.alvina_dispatch_id',
                     'alvina.branch.dispatch.snapshot_json',
                     'alvina.branch.dispatch.receipt.action_confirm'):
            self.assertTrue(any(name in error for error in errors), errors)

    def test_a_truncated_operational_method_cannot_pass_on_field_presence(self):
        self._replace('models/dispatch.py', 'def action_confirm(self):', 'def incomplete_confirmation(self):')
        errors = check_package(self.addon)
        self.assertTrue(any('alvina.branch.dispatch.receipt.action_confirm' in error
                            for error in errors), errors)

    def test_receipt_inverse_must_point_to_its_real_parent_field(self):
        self._replace('models/dispatch.py',
                      "fields.One2many('alvina.branch.dispatch.receipt.line', 'wizard_id'",
                      "fields.One2many('alvina.branch.dispatch.receipt.line', 'dispatch_id'")
        errors = check_package(self.addon)
        self.assertTrue(any('alvina.branch.dispatch.receipt.line_ids' in error
                            for error in errors), errors)

    def test_v3_xml_present_but_missing_from_manifest_is_not_loaded(self):
        filename = 'security/dispatch_security.xml'
        manifest = self._manifest()
        manifest['data'].remove(filename)
        (self.addon / '__manifest__.py').write_text(repr(manifest), encoding='utf-8')
        self.assertTrue((self.addon / filename).is_file())
        errors = check_package(self.addon)
        self.assertTrue(any('no cargado' in error and filename in error for error in errors), errors)

    def test_wrong_window_action_model_is_rejected_even_with_a_complete_python_file(self):
        self._replace('views/dispatch_views.xml',
                      '<field name="res_model">alvina.branch.dispatch</field>',
                      '<field name="res_model">sale.order</field>')
        errors = check_package(self.addon)
        self.assertTrue(any('action_dispatch_notes.res_model' in error for error in errors), errors)

    def test_security_xml_must_declare_the_logistics_role(self):
        self._replace('security/groups.xml', 'id="group_industry_logistics"', 'id="unrelated_role"')
        errors = check_package(self.addon)
        self.assertTrue(any('group_industry_logistics' in error for error in errors), errors)

    def test_old_access_csv_without_receipt_models_is_not_a_complete_version_three(self):
        self._replace('security/ir.model.access.csv',
                      'model_alvina_branch_dispatch_receipt,group_requester',
                      'model_alvina_branch_request,group_requester')
        errors = check_package(self.addon)
        self.assertTrue(any('Enlace de acceso' in error and 'model_alvina_branch_dispatch_receipt' in error
                            for error in errors), errors)

    def test_report_action_without_its_pdf_template_is_incomplete(self):
        self._replace('report/dispatch_note_templates.xml', 'id="dispatch_note"', 'id="unrelated_template"')
        errors = check_package(self.addon)
        self.assertTrue(any('Plantilla PDF' in error for error in errors), errors)

    def test_version_two_does_not_require_version_three_imports(self):
        manifest = self._manifest()
        manifest['version'] = '19.0.2.0.0'
        (self.addon / '__manifest__.py').write_text(repr(manifest), encoding='utf-8')
        self._replace('models/__init__.py', 'from . import logistics', '')
        self._replace('models/__init__.py', 'from . import dispatch', '')
        self.assertEqual(check_package(self.addon), [])


if __name__ == '__main__':
    unittest.main()
