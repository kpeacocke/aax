"""Exercise the actual startup normalization, including the fail-closed path."""
import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize('service', ['awx-web', 'awx-task'])
@pytest.mark.parametrize('value', [
    'https://awx.example.com,http://localhost:18080',
    '["https://awx.example.com", "http://localhost:18080"]',
])
def test_startup_preserves_origins(service, value):
    compose = yaml.safe_load(Path('docker-compose.yml').read_text())
    script = compose['services'][service]['entrypoint'][-1]
    prefix = script.split('# End origin normalization')[0].replace('$$', '$')
    result = subprocess.run(
        ['bash', '-c', prefix + '\nprintf "%s" "$AWX_CSRF_TRUSTED_ORIGINS"'],
        env={**os.environ, 'AWX_CSRF_TRUSTED_ORIGINS': value},
        text=True, capture_output=True, check=True,
    )
    assert json.loads(result.stdout) == ['https://awx.example.com', 'http://localhost:18080']


def test_invalid_origins_prevent_startup():
    compose = yaml.safe_load(Path('docker-compose.yml').read_text())
    script = compose['services']['awx-web']['entrypoint'][-1]
    prefix = script.split('# End origin normalization')[0].replace('$$', '$')
    result = subprocess.run(
        ['bash', '-c', prefix + '\necho SHOULD_NOT_START'],
        env={**os.environ, 'AWX_CSRF_TRUSTED_ORIGINS': 'awx.example.com'},
        text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert 'SHOULD_NOT_START' not in result.stdout
