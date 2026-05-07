import sys
from pathlib import Path
import customtkinter

block_cipher = None

ctk_path = Path(customtkinter.__file__).parent

a = Analysis(
    ['../main.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        (str(ctk_path), 'customtkinter'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._imagingtk',
        'scraper_modules.crawler',
        'scraper_modules.downloader',
        'scraper_modules.exporter',
        'scraper_modules.detector',
        'scraper_modules.session',
        'scraper_modules.mediawiki',
        'scraper_modules.progress',
        'core.runner',
        'gui.app',
        'gui.sidebar',
        'gui.wizard',
        'gui.scrape_view',
        'gui.theme',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='OmniSnap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    windowed=True,
)
