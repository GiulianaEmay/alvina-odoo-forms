"""Start the isolated GitHub Actions database; never connect to an Odoo server.

The fixed temporary directory belongs exclusively to this workflow. pgserver
disables TCP listeners and keeps the server alive for the following job step.
"""
import os
from pathlib import Path
import subprocess

import pgserver
import psycopg2
from psycopg2 import sql


PGDATA = Path('/tmp/alvina-ci-pg')
ROLE = 'odoo_test'
DATABASE = 'alvina_ci_test'


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('This helper is limited to the disposable GitHub Actions runner.')
    if os.geteuid() == 0:
        raise SystemExit('Run this helper as the unprivileged Actions runner user.')
    if PGDATA.is_symlink() or PGDATA.resolve() != PGDATA:
        raise SystemExit('The dedicated CI database directory must not be a symlink.')
    server = pgserver.get_server(PGDATA, cleanup_mode=None)
    info = server.get_postmaster_info()
    if info.socket_dir != PGDATA:
        raise SystemExit('PostgreSQL must use the dedicated CI Unix socket.')
    connection = psycopg2.connect(
        host=str(PGDATA), port=info.port, user='postgres', dbname='postgres',
        connect_timeout=5,
    )
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute('SHOW listen_addresses')
            if cursor.fetchone()[0]:
                raise SystemExit('The disposable database must not listen on TCP.')
            cursor.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (ROLE,))
            if not cursor.fetchone():
                cursor.execute(sql.SQL('CREATE ROLE {}').format(sql.Identifier(ROLE)))
            cursor.execute(sql.SQL(
                'ALTER ROLE {} LOGIN CREATEDB NOSUPERUSER NOCREATEROLE '
                'NOREPLICATION PASSWORD NULL'
            ).format(sql.Identifier(ROLE)))
            cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (DATABASE,))
            if not cursor.fetchone():
                cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(
                    sql.Identifier(DATABASE), sql.Identifier(ROLE),
                ))
    finally:
        connection.close()
    executable = Path(pgserver.__file__).parent / 'pginstall' / 'bin' / 'pg_isready'
    subprocess.run([
        str(executable), '-h', str(PGDATA), '-p', str(info.port),
        '-U', ROLE, '-d', DATABASE, '-t', '5',
    ], check=True)
    with psycopg2.connect(
        host=str(PGDATA), port=info.port, user=ROLE, dbname=DATABASE,
        connect_timeout=5,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT 1, current_user, rolcreatedb, rolsuper FROM pg_roles '
                'WHERE rolname = current_user'
            )
            if cursor.fetchone() != (1, ROLE, True, False):
                raise SystemExit('The CI database role did not pass its connection check.')
    print(f'Disposable PostgreSQL ready: socket={PGDATA}, role={ROLE}, database={DATABASE}')


if __name__ == '__main__':
    main()
