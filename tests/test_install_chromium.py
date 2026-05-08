# tests/test_install_chromium.py
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys


def _get_install_fn():
    if 'main' in sys.modules:
        return sys.modules['main']._install_chromium
    import main
    return main._install_chromium


def test_install_chromium_calls_driver_correctly():
    fake_node = Path('/fake/node.exe')
    fake_cli = Path('/fake/cli.js')
    fake_result = MagicMock(returncode=0)

    with patch('playwright._impl._driver.compute_driver_executable',
               return_value=(fake_node, fake_cli)):
        with patch('subprocess.run', return_value=fake_result) as mock_run:
            fn = _get_install_fn()
            code = fn()

    mock_run.assert_called_once_with(
        [fake_node, fake_cli, 'install', 'chromium'], check=False
    )
    assert code == 0


def test_install_chromium_propagates_nonzero_returncode():
    fake_node = Path('/fake/node.exe')
    fake_cli = Path('/fake/cli.js')
    fake_result = MagicMock(returncode=1)

    with patch('playwright._impl._driver.compute_driver_executable',
               return_value=(fake_node, fake_cli)):
        with patch('subprocess.run', return_value=fake_result):
            fn = _get_install_fn()
            code = fn()

    assert code == 1
