"""Real concurrent HTTP submission and PDF, only against the local smoke fixture."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
from pathlib import Path
import threading

from bs4 import BeautifulSoup
import psycopg2
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('submit', 'pdf'))
    phase = parser.parse_args().phase
    base = 'http://127.0.0.1:8094'
    database = 'alvina_flow_smoke_test'
    with psycopg2.connect(host='/tmp/alvina-test-pg', user='alvina_test', dbname=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT value FROM ir_config_parameter WHERE key='alvina.flow.smoke.fixture'")
            fixture = json.loads(cursor.fetchone()[0])
    session = requests.Session()
    result = session.post(base + '/web/session/authenticate', json={
        'jsonrpc': '2.0', 'method': 'call', 'params': {
            'db': database, 'login': 'alvina-flow-http', 'password': 'flow-smoke-local-only'}, 'id': 1}, timeout=20).json()
    assert result.get('result', {}).get('uid') == fixture['requester_id'], result.get('error')
    if phase == 'submit':
        page = session.get(base + '/branch/requisition/new', timeout=20)
        page.raise_for_status()
        html = BeautifulSoup(page.text, 'html.parser')
        token = html.select_one('[name=submission_key]')['value']
        payload = {'csrf_token': html.select_one('[name=csrf_token]')['value'],
            'submission_key': token, 'branch_id': str(fixture['branch_id']),
            'required_date': date.today().isoformat(),
            'note': 'MUESTRA — DATOS DE PRUEBA; no es un documento real de Alviña.',
            'lines': json.dumps([{'id': fixture['product_id'], 'qty': 20}])}
        barrier = threading.Barrier(2)
        def post():
            browser = requests.Session()
            browser.cookies.update(session.cookies)
            barrier.wait(timeout=10)
            return browser.post(base + '/branch/requisition/submit', data=payload,
                                allow_redirects=False, timeout=30).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: post(), range(2)))
        assert sorted(responses) == [200, 303], responses
        with psycopg2.connect(host='/tmp/alvina-test-pg', user='alvina_test', dbname=database) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT id FROM alvina_branch_request WHERE submission_key=%s', (token,))
                ids = [row[0] for row in cursor.fetchall()]
                assert len(ids) == 1
                for table in ('purchase_order', 'sale_order'):
                    cursor.execute('SELECT state FROM ' + table + ' WHERE alvina_branch_request_id=%s', (ids[0],))
                    assert cursor.fetchall() == [('draft',)]
                cursor.execute('SELECT cid FROM res_company_users_rel WHERE user_id=%s', (fixture['requester_id'],))
                assert cursor.fetchall() == [(fixture['buyer_id'],)]
        print('FLOW_CONCURRENT_HTTP_PASSED: one request, one draft purchase, one draft sale; no company access added.')
    else:
        with psycopg2.connect(host='/tmp/alvina-test-pg', user='alvina_test', dbname=database) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT id FROM alvina_branch_request WHERE branch_id=%s', (fixture['branch_id'],))
                request_id = cursor.fetchone()[0]
        report = session.get(base + '/report/pdf/alvina_branch_requisition.dispatch_request/' + str(request_id), timeout=45)
        report.raise_for_status()
        assert report.content.startswith(b'%PDF-') and len(report.content) > 2000
        target = Path('/workspace/exports/alvina-despacho-ejemplo-pruebas.pdf')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(report.content)
        print('FLOW_AUTHENTICATED_PDF_PASSED: portal user, own request; saved synthetic partial-delivery sample.')


if __name__ == '__main__':
    main()
