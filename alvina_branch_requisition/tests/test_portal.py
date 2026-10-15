from bs4 import BeautifulSoup
from odoo import Command, fields
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestPortal(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': 'Portal solicitante', 'login': 'alvina-portal-test',
            'password': 'local-test-only',
            'group_ids': [Command.set([cls.env.ref('base.group_portal').id,
                cls.env.ref('alvina_branch_requisition.group_requester').id])]})
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.partner = cls.env['res.partner'].create({'name': 'Sucursal portal prueba'})
        cls.branch = cls.env['alvina.branch.binding'].create({
            'resource_ref': 'res.partner,%s' % cls.partner.id, 'company_id': cls.env.company.id,
            'warehouse_id': cls.warehouse.id, 'user_ids': [Command.set(cls.user.ids)]})
        category = cls.env['product.category'].create({'name': 'Comerciales'})
        cls.product = cls.env['product.product'].create({'name': 'Producto portal',
            'categ_id': category.id, 'alvina_requisition_enabled': True})

    def form(self):
        self.authenticate('alvina-portal-test', 'local-test-only')
        response = self.url_open('/branch/requisition/new')
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, 'html.parser')

    def test_anonymous_requires_login(self):
        response = self.url_open('/branch/requisition/new')
        self.assertIn('/web/login', response.url)

    def test_single_branch_locked_and_submit(self):
        import json
        soup = self.form()
        self.assertTrue(soup.select_one('#alvina-branch').has_attr('disabled'))
        values = {i['name']: i.get('value', '') for i in soup.select('input[name]')}
        values.update(required_date=str(fields.Date.today()),
                      lines=json.dumps([{'id': self.product.id, 'qty': '2'}]))
        response = self.url_open('/branch/requisition/submit', data=values)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Requerimiento recibido', response.text)
        record = self.env['alvina.branch.request'].search([('user_id', '=', self.user.id)])
        self.assertEqual(len(record), 1)
        self.assertEqual(record.line_ids.product_qty, 2)
        self.url_open('/branch/requisition/submit', data=values)
        self.assertEqual(self.env['alvina.branch.request'].search_count([('user_id', '=', self.user.id)]), 1)

    def test_no_branch(self):
        self.branch.user_ids = [Command.clear()]
        soup = self.form()
        self.assertIsNone(soup.select_one('#alvina-request-form'))
        self.assertIn('No tienes sucursales asignadas', soup.get_text())

    def test_multiple_branches_require_configuration_instead_of_a_selector(self):
        partner = self.env['res.partner'].create({'name': 'Segunda sucursal portal'})
        self.env['alvina.branch.binding'].create({
            'resource_ref': 'res.partner,%s' % partner.id, 'company_id': self.env.company.id,
            'warehouse_id': self.warehouse.id, 'user_ids': [Command.set(self.user.ids)]})
        soup = self.form()
        self.assertIsNone(soup.select_one('#alvina-request-form'))
        self.assertIn('Tienes varias sucursales asignadas', soup.get_text())

    def test_csrf_required(self):
        self.authenticate('alvina-portal-test', 'local-test-only')
        response = self.url_open('/branch/requisition/submit', data={'branch_id': self.branch.id})
        self.assertEqual(response.status_code, 400)

    def test_browser_assets_categories_clear_quantity_and_submit(self):
        # HttpCase browser_js authenticates with login == password for test users.
        self.user.password = self.user.login
        self.product.default_code = '10'
        self.env['product.product'].create({
            'name': 'Orden anterior', 'default_code': '2',
            'categ_id': self.product.categ_id.id, 'alvina_requisition_enabled': True})
        cleaning = self.env['product.category'].create({'name': 'Útiles de limpieza'})
        self.env['product.product'].create({
            'name': 'Jabón navegador', 'categ_id': cleaning.id,
            'alvina_requisition_enabled': True})
        self.browser_js('/branch/requisition/new', r'''
            (async () => {
                const assert = (condition, message) => { if (!condition) throw new Error(message); };
                const form = document.querySelector('#alvina-request-form');
                const category = document.querySelector('#alvina-category');
                const changeCategory = value => {
                    category.value = value;
                    category.dispatchEvent(new Event('change', {bubbles: true}));
                };
                const quantity = name => [...document.querySelectorAll('#alvina-products tr')]
                    .find(row => row.textContent.includes(name)).querySelector('input');
                const setQuantity = (name, value) => {
                    const input = quantity(name);
                    input.value = value;
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                };
                assert(document.querySelector('#alvina-branch').disabled, 'Single branch must be locked');
                assert(!form.querySelector('[name="company_id"]'), 'Company must not be shown');
                assert(category.options.length === 5, 'Five approved supply categories required');
                assert(getComputedStyle(document.querySelector('.alvina-requisition h2')).color === 'rgb(104, 20, 18)', 'Corporate heading color');
                const rows = document.querySelectorAll('#alvina-products tr');
                assert(rows[0].textContent.includes('Orden anterior'), 'Natural order 2 before 10');
                setQuantity('Producto portal', '3');
                changeCategory('Útiles de limpieza');
                setQuantity('Jabón navegador', '5');
                changeCategory('Comerciales');
                assert(quantity('Producto portal').value === '3', 'Quantity must persist across categories');
                setQuantity('Producto portal', '');
                changeCategory('Útiles de limpieza');
                assert(quantity('Jabón navegador').value === '5', 'Other category quantity must persist');
                document.querySelector('#alvina-date').value = new Date().toISOString().slice(0,10);
                assert(form.checkValidity(), 'Form must be valid');
                const event = new Event('submit', {bubbles: true, cancelable: true});
                form.dispatchEvent(event);
                assert(!event.defaultPrevented, 'Cleared quantity must not block remaining products');
                const lines = JSON.parse(document.querySelector('#alvina-lines').value);
                assert(lines.length === 1 && lines[0].qty === '5', 'Only positive remaining product must be sent');
                const response = await fetch(form.action, {method: 'POST', body: new FormData(form)});
                const html = await response.text();
                assert(response.ok && html.includes('Requerimiento recibido'), 'Real browser POST must succeed');
                console.log('test successful');
            })().catch(error => { console.error(error.stack || error); });
        ''', login=self.user.login,
            ready="document.querySelector('#alvina-request-form')?.dataset.ready === '1'", timeout=90)
        record = self.env['alvina.branch.request'].search([('user_id', '=', self.user.id)])
        self.assertEqual(len(record), 1)
        self.assertEqual(len(record.line_ids), 1)
        self.assertEqual(record.line_ids.product_qty, 5)


@tagged('post_install', '-at_install')
class TestCrossCompanyPortal(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supply_company = cls.env.company
        cls.request_company = cls.env['res.company'].create({'name': 'UPAO portal test'})
        cls.user = cls.env['res.users'].create({
            'name': 'UPAO portal requester', 'login': 'upao-cross-portal', 'password': 'local-test-only',
            'company_id': cls.request_company.id, 'company_ids': [Command.set(cls.request_company.ids)],
            'group_ids': [Command.set([cls.env.ref('base.group_portal').id,
                cls.env.ref('alvina_branch_requisition.group_requester').id])]})
        warehouse = cls.env['stock.warehouse'].search([
            ('company_id', '=', cls.supply_company.id)], limit=1)
        partner = cls.env['res.partner'].create({
            'name': 'UPAO existing portal branch', 'company_id': cls.request_company.id})
        cls.branch = cls.env['alvina.branch.binding'].create({
            'resource_ref': f'res.partner,{partner.id}', 'company_id': cls.request_company.id,
            'warehouse_id': warehouse.id, 'user_ids': [Command.set(cls.user.ids)]})
        category = cls.env['product.category'].create({'name': 'Comerciales'})
        cls.product = cls.env['product.product'].create({
            'name': 'Shared UPAO portal product', 'categ_id': category.id, 'alvina_requisition_enabled': True})
        cls.private_products = cls.product.copy({'name': 'Private Industria catalog', 'company_id': cls.supply_company.id})
        cls.private_products |= cls.product.copy({'name': 'Private UPAO catalog', 'company_id': cls.request_company.id})

    def test_cross_company_form_catalog_and_real_submit(self):
        import json
        self.authenticate(self.user.login, 'local-test-only')
        response = self.url_open('/branch/requisition/new')
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.product.name, response.text)
        for private in self.private_products:
            self.assertNotIn(private.name, response.text)
        soup = BeautifulSoup(response.content, 'html.parser')
        values = {i['name']: i.get('value', '') for i in soup.select('input[name]')}
        values.update(required_date=str(fields.Date.today()),
                      lines=json.dumps([{'id': self.product.id, 'qty': '4'}]))
        response = self.url_open('/branch/requisition/submit', data=values)
        self.assertIn('Requerimiento recibido', response.text)
        rec = self.env['alvina.branch.request'].search([('user_id', '=', self.user.id)])
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec.supply_company_id, self.supply_company)
        self.assertEqual(rec.line_ids.company_id, self.request_company)
        self.assertEqual(rec.line_ids.qty_pending, 4)
        self.assertNotIn(self.supply_company, self.user.company_ids)

    def _form_values(self):
        import json
        self.authenticate(self.user.login, 'local-test-only')
        response = self.url_open('/branch/requisition/new')
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        self.assertIsNotNone(soup.select_one('#alvina-request-form'))
        self.assertTrue(soup.select_one('#alvina-branch').has_attr('disabled'))
        values = {i['name']: i.get('value', '') for i in soup.select('input[name]')}
        values.update(required_date=str(fields.Date.today()),
                      lines=json.dumps([{'id': self.product.id, 'qty': '4'}]))
        return values

    def test_supplier_website_does_not_hide_upao_for_a_multicompany_user(self):
        self.user.company_ids = [Command.link(self.supply_company.id)]
        website = self.env['website'].search([], limit=1)
        website.company_id = self.supply_company
        for main_company in (self.request_company, self.supply_company):
            with self.subTest(main_company=main_company.name):
                self.user.company_id = main_company
                values = self._form_values()
                response = self.url_open('/branch/requisition/submit', data=values)
                self.assertEqual(response.status_code, 200)
                self.assertIn('Requerimiento recibido', response.text)
        records = self.env['alvina.branch.request'].search([('user_id', '=', self.user.id)])
        self.assertEqual(len(records), 2)
        self.assertEqual(records.company_id, self.request_company)
        self.assertEqual(records.supply_company_id, self.supply_company)

    def test_multiple_assignments_cannot_be_selected_by_a_forged_post(self):
        values = self._form_values()
        partner = self.env['res.partner'].create({'name': 'Second assigned UPAO branch'})
        second = self.env['alvina.branch.binding'].create({
            'resource_ref': f'res.partner,{partner.id}', 'company_id': self.request_company.id,
            'warehouse_id': self.branch.warehouse_id.id, 'user_ids': [Command.set(self.user.ids)]})
        for branch in (self.branch, second):
            with self.subTest(branch=branch.id):
                response = self.url_open('/branch/requisition/submit', data={**values, 'branch_id': str(branch.id)})
                self.assertIn('Tienes varias sucursales asignadas', response.text)
                self.assertNotIn('Requerimiento recibido', response.text)
        self.assertFalse(self.env['alvina.branch.request'].search([('user_id', '=', self.user.id)]))

    def test_unassigned_branch_and_revoked_assignment_cannot_be_posted(self):
        values = self._form_values()
        partner = self.env['res.partner'].create({'name': 'Unassigned UPAO form branch'})
        other = self.env['alvina.branch.binding'].create({
            'resource_ref': f'res.partner,{partner.id}', 'company_id': self.request_company.id,
            'warehouse_id': self.branch.warehouse_id.id})
        response = self.url_open('/branch/requisition/submit', data={**values, 'branch_id': str(other.id)})
        self.assertIn('Sucursal no autorizada', response.text)
        self.branch.user_ids = [Command.clear()]
        response = self.url_open('/branch/requisition/submit', data=values)
        self.assertIn('Sucursal no autorizada', response.text)
        self.assertFalse(self.env['alvina.branch.request'].search([('user_id', '=', self.user.id)]))

    def test_binding_in_a_removed_company_is_not_visible(self):
        self.user.write({'company_ids': [Command.set(self.supply_company.ids)],
                         'company_id': self.supply_company.id})
        self.authenticate(self.user.login, 'local-test-only')
        response = self.url_open('/branch/requisition/new')
        self.assertIn('No tienes sucursales asignadas', response.text)
        self.assertNotIn(self.product.name, response.text)
