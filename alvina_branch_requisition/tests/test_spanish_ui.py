"""The requisition UI remains legible without an installed Spanish translation."""
from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSpanishRequisitionUI(TransactionCase):
    def test_new_and_saved_consolidation_have_a_readable_title(self):
        wizard_model = self.env['alvina.branch.consolidation'].with_context(lang='en_US')
        self.assertEqual(wizard_model.new({}).display_name, 'Consolidado de insumos')
        self.assertEqual(wizard_model.create({}).display_name, 'Consolidado de insumos')

    def test_consolidation_columns_are_spanish_in_an_english_session(self):
        model = self.env['alvina.branch.consolidation'].with_context(lang='en_US')
        view = model.get_view(
            view_id=self.env.ref('alvina_branch_requisition.consolidation_form').id,
            view_type='form')
        arch = etree.fromstring(view['arch'].encode())
        columns = {
            field.get('name'): field.get('string')
            for field in arch.xpath("//field[@name='line_ids']/list/field")
        }
        for name, label in {
            'product_id': 'Producto',
            'warehouse_id': 'Almacén abastecedor',
            'company_id': 'Compañía abastecedora',
            'product_uom_id': 'Unidad de medida',
            'unit_cost': 'Costo unitario actual',
            'estimated_value': 'Valor estimado pendiente',
        }.items():
            with self.subTest(field=name):
                self.assertEqual(columns[name], label)

    def test_consolidation_action_and_menu_use_the_readable_title(self):
        for xmlid in ('action_consolidation', 'menu_consolidation'):
            record = self.env.ref('alvina_branch_requisition.' + xmlid).with_context(lang='en_US')
            self.assertEqual(record.name, 'Consolidado de insumos')
