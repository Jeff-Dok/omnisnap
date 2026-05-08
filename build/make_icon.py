# build/make_icon.py
from pathlib import Path
from PIL import Image

src = Path(__file__).parent.parent / "omnisnap_transparent.png"
dst = Path(__file__).parent.parent / "assets" / "omnisnap.ico"
dst.parent.mkdir(exist_ok=True)

img = Image.open(src).convert("RGBA")
img.save(dst, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
print(f"Icone creee : {dst}")
