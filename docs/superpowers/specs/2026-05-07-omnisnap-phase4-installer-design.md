# OmniSnap Phase 4 — Installateur Windows (Design Spec)

## Objectif

Créer un installateur Windows professionnel pour OmniSnap via Inno Setup. L'installateur embarque l'exe PyInstaller, une icône multi-tailles, des métadonnées de version Windows, et présente un wizard complet bilingue (English / Français). Il installe aussi automatiquement Playwright Chromium (téléchargé pendant l'installation) et embarque yt-dlp pour les fonctionnalités optionnelles.

---

## Architecture

### Fichiers nouveaux

| Fichier | Rôle |
|---|---|
| `assets/omnisnap.ico` | Icône multi-tailles (16/32/48/256px) générée depuis `omnisnap_transparent.png` via Pillow |
| `build/make_icon.py` | Script Python one-shot : génère `assets/omnisnap.ico` depuis le PNG |
| `build/version_info.txt` | Métadonnées Windows embarquées dans l'exe PyInstaller |
| `build/OmniSnap.iss` | Script Inno Setup — configuration complète de l'installateur |
| `LICENSE.txt` | Licence MIT affichée dans le wizard |

### Fichiers modifiés

| Fichier | Changement |
|---|---|
| `gui/theme.py` | `VERSION = "3.0.0"` |
| `build/OmniSnap.spec` | Ajout `icon`, `version`, et `'yt_dlp'` dans `hiddenimports` dans `EXE()` |

### Sortie de build

`build/installer/OmniSnap_Setup_3.0.0.exe` — généré manuellement par Inno Setup Compiler après un build PyInstaller.

---

## Icône et métadonnées exe

### assets/omnisnap.ico

Générée via un script Python one-shot (Pillow) depuis `omnisnap_transparent.png` :
- Tailles embarquées : 16×16, 32×32, 48×48, 256×256 px
- Format : ICO multi-résolution standard Windows

### build/version_info.txt

Format PyInstaller `VSVersionInfo` :

```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(3, 0, 0, 0),
    prodvers=(3, 0, 0, 0),
  ),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', 'OmniSnap — Web Scraper'),
      StringStruct('FileVersion', '3.0.0.0'),
      StringStruct('ProductName', 'OmniSnap'),
      StringStruct('ProductVersion', '3.0.0'),
      StringStruct('CompanyName', 'JeffDok Média'),
      StringStruct('LegalCopyright', '© 2026 JeffDok Média — MIT License'),
    ])]),
    VarFileInfo([VarStruct('Translation', [0x0409, 1200])])
  ]
)
```

Ces infos apparaissent dans l'onglet "Détails" des propriétés Windows de l'exe.

---

## Script Inno Setup (build/OmniSnap.iss)

### Langues

Un sélecteur de langue (`English / Français`) s'affiche avant le wizard. Tout le texte (boutons, messages, écrans) bascule automatiquement.

```ini
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
```

### Pages du wizard (dans l'ordre)

1. **Sélecteur de langue** — `English` / `Français` (avant le wizard principal)
2. **Bienvenue** — nom + version de l'app
3. **Licence** — affiche `LICENSE.txt` (MIT), case "J'accepte"
4. **Dossier d'installation** — défaut : `{autopf}\OmniSnap`
5. **Groupe menu Démarrer** — défaut : `OmniSnap`
6. **Tâches** — case "Créer un raccourci sur le Bureau" (cochée par défaut)
7. **Installation** — barre de progression
8. **Fin** — case "Lancer OmniSnap" (cochée par défaut)

### Configuration principale

```ini
[Setup]
AppName=OmniSnap
AppVersion=3.0.0
AppPublisher=JeffDok Média
AppId={{A7F3C2D1-4E8B-4F9A-B2C3-D4E5F6A7B8C9}}
DefaultDirName={autopf}\OmniSnap
DefaultGroupName=OmniSnap
OutputDir=installer
OutputBaseFilename=OmniSnap_Setup_3.0.0
SetupIconFile=..\assets\omnisnap.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE.txt
UninstallDisplayIcon={app}\OmniSnap.exe
```

### Fichiers installés

```ini
[Files]
Source: "..\build\dist\OmniSnap.exe"; DestDir: "{app}"; Flags: ignoreversion
```

### Raccourcis

```ini
[Icons]
Name: "{group}\OmniSnap"; Filename: "{app}\OmniSnap.exe"
Name: "{group}\Désinstaller OmniSnap"; Filename: "{uninstallexe}"
Name: "{commondesktop}\OmniSnap"; Filename: "{app}\OmniSnap.exe"; Tasks: desktopicon
```

### Tâches

```ini
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
```

### Installation de Playwright Chromium

Après l'installation des fichiers, Inno Setup lance `playwright install chromium` silencieusement. L'exe de Playwright est bundlé dans l'exe PyInstaller via `playwright._impl._driver` — Inno Setup appelle l'exe installé avec la commande Python embarquée.

Méthode : Inno Setup appelle un helper `install_chromium.bat` déposé temporairement dans `{tmp}` :

```bat
@echo off
"{app}\OmniSnap.exe" --install-chromium
```

Alternativement, si l'exe PyInstaller ne supporte pas les args CLI, on appelle directement `playwright install chromium` via `cmd /c` avec le Python système si disponible, ou via le module embarqué dans l'exe.

**Implémentation concrète** : ajouter dans `main.py` la détection de `--install-chromium` comme argument CLI :

```python
if '--install-chromium' in sys.argv:
    import subprocess
    subprocess.run(['playwright', 'install', 'chromium'], check=False)
    sys.exit(0)
```

Dans Inno Setup `[Run]` :

```ini
[Run]
Filename: "{app}\OmniSnap.exe"; Parameters: "--install-chromium"; \
  StatusMsg: "Installation de Playwright Chromium (connexion internet requise)..."; \
  Flags: waituntilterminated runhidden
Filename: "{app}\OmniSnap.exe"; Description: "{cm:LaunchProgram,OmniSnap}"; \
  Flags: nowait postinstall skipifsilent
```

L'utilisateur voit une barre de progression "Installation de Playwright Chromium..." pendant le téléchargement (~300 MB). C'est transparent et silencieux.

---

## Licence (LICENSE.txt)

Fichier MIT standard à la racine du projet :

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

---

## Prérequis (non automatisés)

- **Inno Setup 6** installé sur la machine Windows (`iscc.exe` disponible)
- **Pillow** installé dans l'environnement Python (`pip install Pillow`)
- Rebuild PyInstaller requis après changement de spec (pour embarquer icône + version)

---

## Workflow de build (manuel)

1. Exécuter le script de génération d'icône (`python build/make_icon.py`)
2. Rebuilder PyInstaller : `pyinstaller build/OmniSnap.spec`
3. Ouvrir `build/OmniSnap.iss` dans Inno Setup Compiler → Build
4. Récupérer `build/installer/OmniSnap_Setup_3.0.0.exe`

---

## Dépendances optionnelles incluses

### yt-dlp

Ajouté aux `hiddenimports` de PyInstaller dans `OmniSnap.spec` :
```python
'yt_dlp',
```
Embarqué dans l'exe — aucune installation supplémentaire requise pour l'utilisateur.

### Playwright Chromium

- Le package Python `playwright` est déjà dans les `hiddenimports`
- Le navigateur Chromium (~300 MB) est téléchargé automatiquement lors de l'installation via `--install-chromium`
- Stocké dans `%USERPROFILE%\AppData\Local\ms-playwright\` (comportement standard Playwright)
- Internet requis pendant l'installation (cohérent : OmniSnap est un web scraper)

---

## Ce qui ne change pas

- `core/`, `gui/` (sauf `theme.py`) — aucun changement sauf `main.py` (arg `--install-chromium`)
- `tests/` — aucun test automatisé pour l'installateur (validation manuelle)
- `scraper_modules/` — aucun changement
