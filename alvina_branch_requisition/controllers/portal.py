import json
import secrets
from psycopg2 import IntegrityError
from odoo import http, fields, Command, _
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError
from ..models.validation import CATEGORIES, natural_key, quantity

class RequisitionPortal(http.Controller):
    def _authorize(self):
        if not request.env.user.has_group('alvina_branch_requisition.group_requester'):
            raise AccessError(_('No tiene permiso para solicitar productos.'))

    def _branches(self):
        return request.env['alvina.branch.binding'].search([
            ('user_ids', 'in', request.env.uid), ('company_id', 'in', request.env.companies.ids)]).filtered(
                lambda branch: branch._resource_is_available())

    def _products(self, company):
        # Narrow sudo: expose only name/code/UoM and IDs of explicitly enabled products.
        # Portal users have no general product catalog access. Creation uses normal ACLs.
        return request.env['product.product'].sudo().search([
            ('active', '=', True), ('product_tmpl_id.active', '=', True),
            ('alvina_requisition_enabled', '=', True), ('categ_id.name', 'in', CATEGORIES),
            ('company_id', 'in', [False, company.id])])

    def _render(self, error=None):
        branches = self._branches()
        token = secrets.token_urlsafe(32)
        tokens = request.session.get('alvina_form_tokens', [])[-9:]
        request.session['alvina_form_tokens'] = tokens + [token]
        catalogs = {}
        for branch in branches:
            products = sorted(self._products(branch.company_id), key=lambda p: natural_key(p.default_code, p.name, p.id))
            catalogs[str(branch.id)] = [{'id': p.id, 'name': p.display_name, 'category': p.categ_id.name,
                'uom': p.uom_id.name, 'rounding': p.uom_id.rounding} for p in products]
        return request.render('alvina_branch_requisition.form', {
            'branches': branches, 'categories': CATEGORIES, 'catalogs': json.dumps(catalogs),
            'submission_key': token, 'error': error, 'today': fields.Date.context_today(request.env.user)})

    @http.route('/branch/requisition/new', type='http', auth='user', website=True, methods=['GET'])
    def new(self, **kw):
        self._authorize()
        return self._render()

    @http.route('/branch/requisition/submit', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def submit(self, **post):
        self._authorize()
        token = post.get('submission_key', '')
        if token not in request.session.get('alvina_form_tokens', []):
            return self._render(_('Formulario vencido o ya enviado.'))
        try:
            branch = self._branches().filtered(lambda b: str(b.id) == post.get('branch_id'))
            if len(branch) != 1:
                raise ValidationError(_('Sucursal no autorizada.'))
            raw = json.loads(post.get('lines', '[]'))
            if not isinstance(raw, list) or len(raw) > 10000:
                raise ValueError('Detalle inválido')
            products = {p.id: p for p in self._products(branch.company_id)}
            seen, commands = set(), []
            for item in raw:
                pid = item['id']
                if type(pid) is not int or pid in seen or pid not in products:
                    raise ValueError('Producto inválido o repetido')
                seen.add(pid)
                qty = quantity(item['qty'], products[pid].uom_id.rounding)
                if qty:
                    commands.append(Command.create({'product_id': pid, 'product_qty': qty}))
            with request.env.cr.savepoint():
                rec = request.env['alvina.branch.request'].create({
                    'branch_id': branch.id, 'required_date': post.get('required_date'),
                    'note': post.get('note', ''), 'submission_key': token, 'line_ids': commands})
            request.session['alvina_last_request'] = rec.id
        except IntegrityError:
            return self._render(_('El formulario ya fue registrado. No vuelva a enviarlo.'))
        except (ValueError, TypeError, KeyError, ValidationError) as exc:
            return self._render(str(exc))
        request.session['alvina_form_tokens'] = [t for t in request.session.get('alvina_form_tokens', []) if t != token]
        return request.redirect('/branch/requisition/success')

    @http.route('/branch/requisition/success', type='http', auth='user', website=True, methods=['GET'])
    def success(self, **kw):
        self._authorize()
        rec = request.env['alvina.branch.request'].browse(request.session.get('alvina_last_request', 0)).exists()
        rec.check_access('read')
        return request.render('alvina_branch_requisition.success', {'record': rec})
