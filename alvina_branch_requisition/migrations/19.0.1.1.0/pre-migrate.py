"""Backfill supply snapshots before the ORM initializes required/related fields.

Legacy bindings required their warehouse to belong to the requesting company.
Never guess a new central warehouse or rewrite an existing historical snapshot.
"""


def migrate(cr, version):
    if not version:
        return
    for table in ('alvina_branch_request', 'alvina_branch_request_line'):
        cr.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS supply_company_id integer')
        cr.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS warehouse_id integer')
    cr.execute('''
        UPDATE alvina_branch_request AS r
           SET warehouse_id = COALESCE(r.warehouse_id, b.warehouse_id),
               supply_company_id = COALESCE(r.supply_company_id, w.company_id)
          FROM alvina_branch_binding AS b, stock_warehouse AS w
         WHERE b.id = r.branch_id
           AND w.id = COALESCE(r.warehouse_id, b.warehouse_id)
           AND (r.warehouse_id IS NULL OR r.supply_company_id IS NULL)
    ''')
    # Do this explicitly: relying on stored-related recomputation alone can leave
    # pre-existing lines empty during an upgrade.
    cr.execute('''
        UPDATE alvina_branch_request_line AS l
           SET warehouse_id = COALESCE(l.warehouse_id, r.warehouse_id),
               supply_company_id = COALESCE(l.supply_company_id, r.supply_company_id)
          FROM alvina_branch_request AS r
         WHERE r.id = l.request_id
           AND (l.warehouse_id IS NULL OR l.supply_company_id IS NULL)
    ''')
    cr.execute('''
        SELECT 1 FROM alvina_branch_request r
        LEFT JOIN stock_warehouse w ON w.id = r.warehouse_id
        WHERE r.warehouse_id IS NULL OR r.supply_company_id IS NULL
           OR w.company_id IS DISTINCT FROM r.supply_company_id
        UNION ALL
        SELECT 1 FROM alvina_branch_request_line l
        LEFT JOIN alvina_branch_request r ON r.id = l.request_id
        WHERE l.warehouse_id IS NULL OR l.supply_company_id IS NULL
           OR l.warehouse_id IS DISTINCT FROM r.warehouse_id
           OR l.supply_company_id IS DISTINCT FROM r.supply_company_id
        LIMIT 1
    ''')
    if cr.fetchone():
        raise ValueError('Alviña: historial sin abastecedor válido o con snapshots inconsistentes; revise los vínculos antes de actualizar.')
