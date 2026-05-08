# main.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _install_chromium() -> int:
    import subprocess
    from playwright._impl._driver import compute_driver_executable
    node_exe, cli_js = compute_driver_executable()
    result = subprocess.run([node_exe, cli_js, 'install', 'chromium'], check=False)
    return result.returncode


if '--install-chromium' in sys.argv:
    sys.exit(_install_chromium())

from gui.theme import setup

if __name__ == "__main__":
    from gui.app import App
    setup()
    app = App()
    app.mainloop()
