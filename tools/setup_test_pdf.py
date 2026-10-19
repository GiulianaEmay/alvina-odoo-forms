"""Extract a checksum-pinned PDF test runtime into /tmp, without system install."""
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import urllib.request

PACKAGES = (
    ('wkhtmltox.deb',
     'https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.jammy_amd64.deb',
     '4f723b2691ad8638a9df960e0421d346d7315083e3583a334f33362280ddba15'),
    ('libjpeg.deb',
     'https://archive.ubuntu.com/ubuntu/pool/main/libj/libjpeg-turbo/libjpeg-turbo8_2.1.2-0ubuntu1_amd64.deb',
     'bb9538fa94f06bf6b7907105439f0a0a30e3ec27030832820a6c2cc2dc6578a8'),
)


def main():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise SystemExit('This disposable runtime is for Linux amd64; use a supported wkhtmltopdf for your platform.')
    target = Path('/tmp/alvina-pdf-runtime')
    cache = target / 'packages'
    cache.mkdir(parents=True, exist_ok=True)
    for filename, url, expected in PACKAGES:
        archive = cache / filename
        if not archive.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise SystemExit('Checksum mismatch; refusing to use ' + filename)
        subprocess.run(['dpkg-deb', '-x', str(archive), str(target)], check=True)
    binaries = target / 'usr/local/bin'
    libraries = target / 'usr/lib/x86_64-linux-gnu'
    runtime_env = dict(os.environ, LD_LIBRARY_PATH=str(libraries))
    version = subprocess.check_output([str(binaries / 'wkhtmltopdf'), '--version'],
                                      env=runtime_env, text=True).strip()
    if '0.12.6.1' not in version or 'with patched qt' not in version:
        raise SystemExit('Unexpected PDF test runtime: ' + version)
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        with Path(os.environ['GITHUB_PATH']).open('a') as output:
            output.write(str(binaries) + '\n')
        with Path(os.environ['GITHUB_ENV']).open('a') as output:
            output.write('LD_LIBRARY_PATH=' + str(libraries) + '\n')
    print(version + '; extracted to ' + str(target))


if __name__ == '__main__':
    main()
