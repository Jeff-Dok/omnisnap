# OmniSnap Phase 4 — Installateur Windows

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer un installateur Windows professionnel (`OmniSnap_Setup_3.0.0.exe`) via Inno Setup, avec icône multi-tailles, métadonnées version Windows, wizard bilingue EN/FR, et installation automatique de Playwright Chromium au moment du setup.

**Architecture:** Un script Python one-shot génère l'icône `.ico`. `build/version_info.txt` (format PyInstaller VSVersionInfo) embarque les métadonnées dans l'exe. `OmniSnap.spec` est mis à jour pour inclure l'icône, la version, le driver Playwright (100 MB) et yt-dlp. `main.py` reçoit un flag `--install-chromium` déclenché par Inno Setup après installation pour télécharger le navigateur Chromium (~300 MB). `build/OmniSnap.iss` définit le wizard complet.

**Tech Stack:** Python 3.11+, Pillow, PyInstaller 6+, Inno Setup 6, Playwright (driver Node.js bundlé), yt-dlp

---

## Fichiers

| Action | Fichier | Rôle |
|---|---|---|
| Créer | `assets/omnisnap.ico` | Icône 16/32/48/256px (générée par make_icon.py) |
| Créer | `build/make_icon.py` | Script one-shot : PNG → ICO via Pillow |
| Créer | `build/version_info.txt` | Métadonnées Windows VSVersionInfo pour PyInstaller |
| Créer | `LICENSE.txt` | Licence MIT (affichée dans le wizard) |
| Modifier | `gui/theme.py` | VERSION = "3.0.0" |
| Modifier | `build/OmniSnap.spec` | icon, version, playwright driver datas, yt_dlp hiddenimport |
| Modifier | `main.py` | Fonction `_install_chromium()` + flag `--install-chromium` |
| Créer | `build/OmniSnap.iss` | Script Inno Setup — wizard complet bilingue |
| Créer | `tests/test_install_chromium.py` | Tests unitaires pour `_install_chromium()` |

---

## Task 1 : Générer l'icône (build/make_icon.py → assets/omnisnap.ico)

**Files:**
- Create: `build/make_icon.py`
- Create: `assets/omnisnap.ico` (généré par le script)

- [ ] **Step 1 : Créer build/make_icon.py**

```python
# build/make_icon.py
from pathlib import Path
from PIL import Image

src = Path(__file__).parent.parent / "omnisnap_transparent.png"
dst = Path(__file__).parent.parent / "assets" / "omnisnap.ico"
dst.parent.mkdir(exist_ok=True)

img = Image.open(src).convert("RGBA")
sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]
resized = [img.resize(s, Image.LANCZOS) for s in sizes]
resized[0].save(dst, format="ICO", sizes=sizes, append_images=resized[1:])
print(f"Icone creee : {dst}")
```

- [ ] **Step 2 : Exécuter le script**

```
python build/make_icon.py
```

Attendu : `Icone creee : ...\assets\omnisnap.ico`
Vérifier que le fichier existe : `assets/omnisnap.ico`

- [ ] **Step 3 : Vérifier l'icône**

```python
from PIL import Image
ico = Image.open("assets/omnisnap.ico")
print(ico.info)  # doit lister les tailles 16, 32, 48, 256
```

- [ ] **Step 4 : Commit**

```bash
git add build/make_icon.py assets/omnisnap.ico
git commit -m "feat: add multi-size ICO icon from PNG via make_icon.py"
```

---

## Task 2 : Fichiers statiques (version_info.txt, LICENSE.txt, theme.py)

**Files:**
- Create: `build/version_info.txt`
- Create: `LICENSE.txt`
- Modify: `gui/theme.py`

- [ ] **Step 1 : Créer build/version_info.txt**

```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(3, 0, 0, 0),
    prodvers=(3, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'JeffDok Média'),
         StringStruct('FileDescription', 'OmniSnap — Web Scraper'),
         StringStruct('FileVersion', '3.0.0.0'),
         StringStruct('LegalCopyright', '© 2026 JeffDok Média — MIT License'),
         StringStruct('ProductName', 'OmniSnap'),
         StringStruct('ProductVersion', '3.0.0')])
    ]),
    VarFileInfo([VarStruct('Translation', [0x0409, 1200])])
  ]
)
```

- [ ] **Step 2 : Créer LICENSE.txt à la racine du projet**

```
MIT License

Copyright (c) 2026 JeffDok Média

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3 : Mettre à jour gui/theme.py**

Changer la ligne VERSION :

```python
VERSION = "3.0.0"
```

- [ ] **Step 4 : Lancer tous les tests — vérifier que tout passe**

```
python -m pytest tests/ -v
```

Attendu : 67 tests PASSED (aucun cassé par le changement de VERSION)

- [ ] **Step 5 : Commit**

```bash
git add build/version_info.txt LICENSE.txt gui/theme.py
git commit -m "feat: add version_info, MIT license, bump VERSION to 3.0.0"
```

---

## Task 3 : Mettre à jour build/OmniSnap.spec

**Files:**
- Modify: `build/OmniSnap.spec`

Le spec doit inclure : icône dans EXE, version_info dans EXE, driver Playwright dans datas, yt_dlp + playwright dans hiddenimports.

- [ ] **Step 1 : Remplacer build/OmniSnap.spec par le contenu complet suivant**

```python
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
```

- [ ] **Step 2 : Commit**

```bash
git add build/OmniSnap.spec
git commit -m "build: update spec — add icon, version_info, playwright driver, yt_dlp"
```

---

## Task 4 : main.py — flag --install-chromium

**Files:**
- Modify: `main.py`
- Create: `tests/test_install_chromium.py`

- [ ] **Step 1 : Écrire le test (fichier complet)**

Créer `tests/test_install_chromium.py` :

```python
# tests/test_install_chromium.py
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib
import sys


def _get_install_fn():
    """Importe _install_chromium depuis main sans déclencher l'appel."""
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
```

- [ ] **Step 2 : Lancer les tests — vérifier qu'ils échouent**

```
python -m pytest tests/test_install_chromium.py -v
```

Attendu : FAILED (`_install_chromium` n'existe pas encore dans `main.py`)

- [ ] **Step 3 : Modifier main.py (contenu complet)**

```python
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
```

- [ ] **Step 4 : Lancer les tests — vérifier qu'ils passent**

```
python -m pytest tests/test_install_chromium.py -v
```

Attendu : 2 tests PASSED

- [ ] **Step 5 : Lancer tous les tests**

```
python -m pytest tests/ -v
```

Attendu : 69 tests PASSED

- [ ] **Step 6 : Commit**

```bash
git add main.py tests/test_install_chromium.py
git commit -m "feat: add --install-chromium flag to main.py for post-install Chromium setup"
```

---

## Task 5 : build/OmniSnap.iss — Script Inno Setup

**Files:**
- Create: `build/OmniSnap.iss`

Pas de test automatisé — validation manuelle après build Inno Setup.

- [ ] **Step 1 : Créer build/OmniSnap.iss (contenu complet)**

```ini
; build/OmniSnap.iss
; OmniSnap — Installateur Windows
; Prérequis : Inno Setup 6 (https://jrsoftware.org/isinfo.php)
; Build : ouvrir ce fichier dans Inno Setup Compiler -> Build

#define MyAppName "OmniSnap"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "JeffDok Média"
#define MyAppURL "https://github.com/Jeff-Dok/omnisnap"
#define MyAppExeName "OmniSnap.exe"

[Setup]
AppId={{A7F3C2D1-4E8B-4F9A-B2C3-D4E5F6A7B8C9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE.txt
OutputDir=installer
OutputBaseFilename=OmniSnap_Setup_{#MyAppVersion}
SetupIconFile=..\assets\omnisnap.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[CustomMessages]
english.InstallingChromium=Installing browser engine (Playwright Chromium, ~300 MB — internet required)...
french.InstallingChromium=Installation du moteur de navigation (Playwright Chromium, ~300 Mo — internet requis)...

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "..\build\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
  Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--install-chromium"; \
  StatusMsg: "{cm:InstallingChromium}"; \
  Flags: waituntilterminated runhidden
Filename: "{app}\{#MyAppExeName}"; \
  Description: "{cm:LaunchProgram,{#MyAppName}}"; \
  Flags: nowait postinstall skipifsilent
```

- [ ] **Step 2 : Créer le dossier de sortie**

```bash
mkdir build\installer
```

- [ ] **Step 3 : Commit**

```bash
git add build/OmniSnap.iss
git commit -m "feat: add Inno Setup script for bilingual Windows installer"
```

---

## Validation manuelle (après implémentation)

Les étapes suivantes sont **manuelles** — pas automatisées.

### Rebuild PyInstaller (exe avec icône + version + driver Playwright)

```
pyinstaller build/OmniSnap.spec
```

Attendu : `build/dist/OmniSnap.exe` régénéré (~183 MB avec le driver Playwright bundlé)

Vérifier :
- Clic droit sur `build/dist/OmniSnap.exe` → Propriétés → Détails → "Version du fichier" : `3.0.0.0`, "Société" : `JeffDok Média`
- L'icône OmniSnap apparaît dans l'explorateur (plus d'icône générique)
- L'app se lance correctement

### Build Inno Setup

1. Ouvrir Inno Setup Compiler
2. Ouvrir `build/OmniSnap.iss`
3. Build → vérifier que `build/installer/OmniSnap_Setup_3.0.0.exe` est créé

### Test de l'installateur

1. Lancer `build/installer/OmniSnap_Setup_3.0.0.exe`
2. Sélecteur de langue → choisir Français → vérifier que tout le texte bascule
3. Parcourir le wizard : Bienvenue → Licence → Dossier → Menu Démarrer → Bureau → Installation
4. Vérifier la progression "Installation du moteur de navigation..."
5. Finaliser → case "Lancer OmniSnap" cochée → vérifier que l'app se lance
6. Vérifier raccourci Bureau + Menu Démarrer
7. Vérifier "Ajouter/Supprimer des programmes" → OmniSnap 3.0.0 avec icône
8. Désinstaller → vérifier que tout est nettoyé
