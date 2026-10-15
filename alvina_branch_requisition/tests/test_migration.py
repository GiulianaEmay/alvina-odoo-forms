"""Execute the real pre-upgrade SQL against isolated legacy PostgreSQL tables."""
import importlib.util
from pathlib import Path

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSupplyMigration(TransactionCase):
    def _migration(self):
        path = Path(__file__).resolve().parents[1] / 'migrations/19.0.1.1.0/pre-migrate.py'
        spec = importlib.util.spec_from_file_location('alvina_supply_migration', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.migrate

    def _legacy(self, cr):
        # Separate cursor/transaction: temp tables shadow only these four names
        # and are rolled back when closed, never altering the application's tables.
        cr.execute('CREATE TEMP TABLE stock_warehouse (id integer PRIMARY KEY, company_id integer)')
        cr.execute('CREATE TEMP TABLE alvina_branch_binding (id integer PRIMARY KEY, warehouse_id integer)')
        cr.execute('CREATE TEMP TABLE alvina_branch_request (id integer PRIMARY KEY, branch_id integer)')
        cr.execute('CREATE TEMP TABLE alvina_branch_request_line (id integer PRIMARY KEY, request_id integer)')
        cr.execute('INSERT INTO stock_warehouse VALUES (10, 1), (20, 2)')
        cr.execute('INSERT INTO alvina_branch_binding VALUES (100, 10), (200, 20)')
        cr.execute('INSERT INTO alvina_branch_request VALUES (1, 100), (2, 200)')
        cr.execute('INSERT INTO alvina_branch_request_line VALUES (11, 1), (12, 1), (21, 2)')

    def test_backfills_all_headers_and_historical_lines_and_is_idempotent(self):
        with self.registry.cursor() as cr:
            self._legacy(cr)
            migrate = self._migration()
            migrate(cr, '19.0.1.0.1')
            migrate(cr, '19.0.1.0.1')
            cr.execute('SELECT id, supply_company_id, warehouse_id FROM alvina_branch_request ORDER BY id')
            self.assertEqual(cr.fetchall(), [(1, 1, 10), (2, 2, 20)])
            cr.execute('SELECT id, supply_company_id, warehouse_id FROM alvina_branch_request_line ORDER BY id')
            self.assertEqual(cr.fetchall(), [(11, 1, 10), (12, 1, 10), (21, 2, 20)])

    def test_partial_backfill_uses_header_snapshot_not_current_binding(self):
        with self.registry.cursor() as cr:
            self._legacy(cr)
            migrate = self._migration()
            migrate(cr, '19.0.1.0.1')
            cr.execute('UPDATE alvina_branch_binding SET warehouse_id=20 WHERE id=100')
            cr.execute('UPDATE alvina_branch_request SET supply_company_id=NULL WHERE id=1')
            cr.execute('UPDATE alvina_branch_request_line SET warehouse_id=NULL, supply_company_id=NULL WHERE id=11')
            migrate(cr, '19.0.1.0.1')
            cr.execute('SELECT supply_company_id, warehouse_id FROM alvina_branch_request_line WHERE id=11')
            self.assertEqual(cr.fetchone(), (1, 10))

    def test_missing_legacy_warehouse_blocks_upgrade_instead_of_guessing(self):
        with self.registry.cursor() as cr:
            self._legacy(cr)
            cr.execute('UPDATE alvina_branch_binding SET warehouse_id=NULL WHERE id=100')
            with self.assertRaises(ValueError):
                self._migration()(cr, '19.0.1.0.1')

    def test_conflicting_line_snapshot_blocks_upgrade(self):
        with self.registry.cursor() as cr:
            self._legacy(cr)
            migrate = self._migration()
            migrate(cr, '19.0.1.0.1')
            cr.execute('UPDATE alvina_branch_request_line SET warehouse_id=20 WHERE id=11')
            with self.assertRaises(ValueError):
                migrate(cr, '19.0.1.0.1')
