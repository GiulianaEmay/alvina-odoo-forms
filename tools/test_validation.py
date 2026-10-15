"""Run without Odoo: python -m unittest discover -s tools -v."""
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('validation', ROOT / 'alvina_branch_requisition/models/validation.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

class ValidationTests(unittest.TestCase):
    def test_natural_order(self):
        codes = ['10', None, '2', '001', '1', 'A10', 'A2']
        self.assertEqual(sorted(codes, key=lambda c: v.natural_key(c, 'x', 1)),
                         ['1', '001', '2', '10', 'A2', 'A10', None])
    def test_quantity(self):
        self.assertEqual(v.quantity('1.25', '.25'), 1.25)
        self.assertEqual(v.quantity('0', '1'), 0)
    def test_invalid_quantities(self):
        for q in ['-1', 'NaN', 'Infinity', 'abc', '1.1', '1e999', None]:
            with self.subTest(q=q), self.assertRaises(ValueError):
                v.quantity(q, 1)
    def test_pending(self):
        self.assertEqual(v.pending(10, 3), 7)
        self.assertEqual(v.pending(10, 20), 0)
    def test_stock_and_incoming(self):
        for args, expected in [((45, 0, 0),45), ((30,10,0),20),
                               ((30,10,5),15), ((5,-10,0),5), ((5,10,10),0)]:
            self.assertEqual(v.suggested(*args), expected)
    def test_xml_and_purchase_menus(self):
        for path in (ROOT / 'alvina_branch_requisition').rglob('*.xml'):
            ET.parse(path)
        tree = ET.parse(ROOT / 'alvina_branch_requisition/views/backend.xml')
        for ident in ['menu_web', 'menu_requests', 'menu_consolidation']:
            menu = tree.find(f".//menuitem[@id='{ident}']")
            self.assertEqual(menu.attrib['parent'], 'purchase.menu_procurement_management')
        self.assertTrue(all('parent' in menu.attrib for menu in tree.findall('.//menuitem')))

if __name__ == '__main__':
    unittest.main()
