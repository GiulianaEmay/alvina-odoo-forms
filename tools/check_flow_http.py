"""Concurrent HTTP submission and internal-guide PDF in one local disposable DB.

Only alvina_logistics_http_test over /tmp/alvina-ci-pg as odoo_test is used.
HTTP is fixed to 127.0.0.1:8094. Seed/deliver/receive use flow_smoke_fixture.py.
The password below belongs exclusively to the synthetic local fixture.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading

from bs4 import BeautifulSoup
import psycopg2
import requests


DATABASE = 'alvina_logistics_http_test'
SOCKET = '/tmp/alvina-ci-pg'
DB_USER = 'odoo_test'
BASE_URL = 'http://127.0.0.1:8094'
FIXTURE_KEY = 'alvina.flow.smoke.fixture'


def local_database():
    connection = psycopg2.connect(host=SOCKET, user=DB_USER, dbname=DATABASE)
    connection.set_session(readonly=True)
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(), current_user')
        assert cursor.fetchone() == (DATABASE, DB_USER), 'Unexpected database or role'
    return connection


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('submit', 'pdf'))
    phase = parser.parse_args().phase
    with local_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT value FROM ir_config_parameter WHERE key=%s', (FIXTURE_KEY,))
            row = cursor.fetchone()
            assert row, 'Seed the dedicated synthetic logistics fixture first'
            fixture = json.loads(row[0])
    assert fixture.get('scenario_version') == 3, 'The 19.0.3 synthetic fixture is required'
    session = requests.Session()
    response = session.post(BASE_URL + '/web/session/authenticate', json={
        'jsonrpc': '2.0', 'method': 'call', 'params': {
            'db': DATABASE, 'login': 'alvina-flow-http', 'password': 'flow-smoke-local-only',
        }, 'id': 1,
    }, timeout=20)
    response.raise_for_status()
    result = response.json()
    assert result.get('result', {}).get('uid') == fixture['requester_id'], result.get('error')

    if phase == 'submit':
        assert not fixture.get('guide_id'), 'Use a fresh fixture for the concurrent submission'
        page = session.get(BASE_URL + '/branch/requisition/new', timeout=20)
        page.raise_for_status()
        html = BeautifulSoup(page.text, 'html.parser')
        token_field = html.select_one('[name=submission_key]')
        date_field = html.select_one('[name=required_date]')
        csrf_field = html.select_one('[name=csrf_token]')
        assert token_field and date_field and csrf_field, 'The authorized request form must render'
        assert date_field.get('value') and date_field.get('value') == date_field.get('min')
        token = token_field['value']
        payload = {
            'csrf_token': csrf_field['value'], 'submission_key': token,
            'branch_id': str(fixture['branch_id']), 'required_date': date_field['value'],
            'note': 'MUESTRA — DATOS DE PRUEBA; no es un documento real de Alviña.',
            'lines': json.dumps([{'id': fixture['product_id'], 'qty': 20}]),
        }
        barrier = threading.Barrier(2)

        def post(_):
            with requests.Session() as browser:
                browser.cookies.update(session.cookies)
                barrier.wait(timeout=10)
                submitted = browser.post(
                    BASE_URL + '/branch/requisition/submit', data=payload,
                    allow_redirects=False, timeout=45)
                assert submitted.status_code in (200, 303), submitted.status_code
                return submitted.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(post, range(2)))
        assert sorted(responses) == [200, 303], responses
        with local_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT id, company_id, supply_company_id FROM alvina_branch_request '
                    'WHERE submission_key=%s', (token,))
                records = cursor.fetchall()
                assert len(records) == 1, records
                request_id, buyer_id, industry_id = records[0]
                assert (buyer_id, industry_id) == (fixture['buyer_id'], fixture['industry_id'])
                for table, expected_state, company_id in (
                        ('purchase_order', 'purchase', buyer_id), ('sale_order', 'sale', industry_id)):
                    # table is selected only from the constant whitelist above.
                    cursor.execute(
                        'SELECT state, company_id FROM ' + table + ' WHERE alvina_branch_request_id=%s',
                        (request_id,))
                    assert cursor.fetchall() == [(expected_state, company_id)]
                cursor.execute('SELECT cid FROM res_company_users_rel WHERE user_id=%s ORDER BY cid',
                               (fixture['requester_id'],))
                assert cursor.fetchall() == [(buyer_id,)]
                cursor.execute(
                    'SELECT count(*) FROM alvina_branch_dispatch WHERE request_id=%s', (request_id,))
                assert cursor.fetchone()[0] == 0, 'No guide exists before physical dispatch'
        print('FLOW_CONCURRENT_HTTP_PASSED: two concurrent POSTs, one request, one confirmed OC and OV; no Industry membership added.')
    else:
        assert fixture.get('guide_id') and fixture.get('receipt_id'), 'Run deliver and receive before exporting the PDF'
        guide_id = fixture['guide_id']
        assert type(guide_id) is int and guide_id > 0
        with local_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT branch_id, company_id, buyer_company_id, receipt_state, '
                    'snapshot_json, receipt_confirmation_json '
                    'FROM alvina_branch_dispatch WHERE id=%s', (guide_id,))
                rows = cursor.fetchall()
                assert len(rows) == 1
                branch_id, industry_id, buyer_id, state, dispatch, receipt = rows[0]
                assert (branch_id, industry_id, buyer_id) == (
                    fixture['branch_id'], fixture['industry_id'], fixture['buyer_id'])
                assert state == 'discrepancy'
                assert [(item['shipped'], item['received'], item['difference'])
                        for item in receipt['lines']] == [(15, 13, 2)]
                assert [(item['requested'], item['supplied'], item['pending'])
                        for item in dispatch['balances']] == [(20, 15, 5)]
                assert dispatch['totals']['total'] == 52.5
        report_path = '/report/pdf/alvina_branch_requisition.dispatch_note/' + str(guide_id)
        report = session.get(BASE_URL + report_path, timeout=60)
        report.raise_for_status()
        assert report.content.startswith(b'%PDF-') and len(report.content) > 2000
        target = Path('/workspace/exports/alvina-guia-interna-muestra.pdf')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(report.content)
        print('FLOW_AUTHENTICATED_GUIDE_PDF_PASSED: requester PDF, 20 requested / 15 dispatched / 13 received; pending 5, discrepancy 2; ' + str(target))


if __name__ == '__main__':
    main()
