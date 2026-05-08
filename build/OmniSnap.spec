# build/OmniSnap.spec
import sys
from pathlib import Path
import customtkinter
import playwright

block_cipher = None

ctk_path = Path(customtkinter.__file__).parent
playwright_driver = Path(playwright.__file__).parent / 'driver'

a = Analysis(
    ['../main.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        (str(ctk_path), 'customtkinter'),
        (str(playwright_driver), 'playwright/driver'),
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
        'core.store',
        'core.notifier',
        'core.queue',
        'gui.app',
        'gui.sidebar',
        'gui.wizard',
        'gui.scrape_view',
        'gui.history_view',
        'gui.settings_view',
        'gui.queue_view',
        'gui.theme',
        'winotify',
        'playwright',
        'playwright._impl._driver',
        'yt_dlp',
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
    icon='../assets/omnisnap.ico',
    version='version_info.txt',
)
