import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from gui.theme import setup

if __name__ == "__main__":
    from gui.app import App
    setup()
    app = App()
    app.mainloop()
