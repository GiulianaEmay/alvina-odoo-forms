"""Capture/verify a disposable 1.2 -> 2.0 upgrade; no remote DB or production.

Run with the project's test venv, before/after the normal Odoo module upgrade:
  python tools/check_intercompany_upgrade.py capture|verify SNAPSHOT.json
Fixtures must already exist in the strictly named local test database.
Capture is read-only; verify compares recorded history and document identities.
"""
import argparse
from decimal import Decimal
import json
from pathlib import Path

import psycopg2


def normalized(value):
    return str(Decimal(str(value)).normalize()) if value is not None else None


def snapshot(cursor):
    cursor.execute("SELECT latest_version FROM ir_module_module WHERE name='alvina_branch_requisition'")
    result = {'version': cursor.fetchone()[0]}
    cursor.execute('SELECT id FROM alvina_branch_request ORDER BY id')
    result['request_ids'] = [row[0] for row in cursor.fetchall()]
    cursor.execute('''SELECT id, request_id, product_id, product_qty::text,
                     qty_supplied::text, qty_pending::text, price_unit::text,
                     price_subtotal::text FROM alvina_branch_request_line ORDER BY id''')
    result['lines'] = [list(row) for row in cursor.fetchall()]
    for table in ('purchase_order', 'stock_move'):
        cursor.execute('SELECT id FROM ' + table + ' ORDER BY id')
        result[table] = [row[0] for row in cursor.fetchall()]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('capture', 'verify'))
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
    with psycopg2.connect(host='/tmp/alvina-test-pg', user='alvina_test',
                          dbname='alvina_supply_upgrade_test') as connection:
        connection.set_session(readonly=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT value FROM ir_config_parameter WHERE key='alvina.supply_upgrade.fixture'")
            assert cursor.fetchone(), 'Dedicated historical upgrade fixture required'
            current = snapshot(cursor)
            if args.phase == 'capture':
                assert current['version'] == '19.0.1.2.0', current['version']
                assert current['lines'], 'Historical lines required'
                assert not args.snapshot.exists(), 'Do not replace the baseline snapshot'
                args.snapshot.write_text(json.dumps(current))
                print('FLOW_UPGRADE_BASELINE_CAPTURED')
                return
            before = json.loads(args.snapshot.read_text())
            assert before['version'] == '19.0.1.2.0'
            assert current['version'] == '19.0.2.0.0', current['version']
            for key in ('request_ids', 'purchase_order', 'stock_move'):
                assert current[key] == before[key], key
            def canonical(lines):
                return [line[:3] + [normalized(value) for value in line[3:]] for line in lines]
            actual = canonical(current['lines'])
            expected = canonical(before['lines'])
            # A missing historical price remains explicitly uncaptured. Odoo
            # may recompute its stored subtotal from NULL to zero; that zero
            # must never be relabelled as a captured historical valuation.
            for new, old in zip(actual, expected):
                if old[6:] == [None, None] and new[6:] == [None, '0']:
                    cursor.execute('SELECT price_snapshot_set FROM alvina_branch_request_line WHERE id=%s', (new[0],))
                    assert cursor.fetchone()[0] is not True
                    new[7] = None
            assert actual == expected, 'Historical quantities or captured prices changed'
            cursor.execute('SELECT id, legacy_qty_supplied FROM alvina_branch_request_line ORDER BY id')
            historical = {line[0]: normalized(line[4]) for line in before['lines']}
            assert all(normalized(quantity) == historical[line_id] for line_id, quantity in cursor.fetchall())
            cursor.execute('SELECT count(*) FROM alvina_branch_request WHERE supply_flow OR sale_order_id IS NOT NULL')
            assert cursor.fetchone()[0] == 0, 'No retrospective flow/documents'
            cursor.execute('SELECT count(*) FROM alvina_supply_configuration WHERE enabled')
            assert cursor.fetchone()[0] == 0, 'New flow must not be activated by migration'
            print('FLOW_UPGRADE_PASSED: historical quantities, prices and documents preserved; no retrospective flow.')


if __name__ == '__main__':
    main()
