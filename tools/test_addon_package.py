"""Regression for the broken manual upload, without executing supplied code."""
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
