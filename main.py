import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from gui.theme import setup
from gui.app import App

if __name__ == "__main__":
    setup()
    app = App()
    app.mainloop()
