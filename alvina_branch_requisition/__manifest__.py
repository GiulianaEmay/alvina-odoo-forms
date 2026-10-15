{
    'name': 'Alviña - Requerimientos de sucursales',
    'version': '19.0.1.1.0',
    'author': 'Grupo Alviña',
    'license': 'LGPL-3',
    'depends': ['purchase', 'stock', 'purchase_stock', 'portal', 'website'],
    'data': ['security/groups.xml', 'security/ir.model.access.csv',
             'security/rules.xml', 'data/sequence.xml', 'views/backend.xml',
             'views/templates.xml'],
    'assets': {'web.assets_frontend': ['alvina_branch_requisition/static/src/form.js',
                                      'alvina_branch_requisition/static/src/form.css']},
    'installable': True,
    'application': False,
}
