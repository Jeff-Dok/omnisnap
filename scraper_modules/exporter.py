# scraper_modules/exporter.py
import os, json, csv, re, subprocess, sys
from pathlib import Path

DEFAULT_DEST = Path.home() / "Downloads/Scraper"


def url_to_folder(url: str) -> str:
    name = re.sub(r'^https?://', '', url)
    name = re.sub(r'[?#].*$', '', name)
    name = name.rstrip('/')
    name = name.replace('/', '_')
    name = re.sub(r'[\\*?"<>|]', '_', name)
    return name[:100] or 'page'


def safe_name(url: str) -> str:
    name = re.split(r'[/=]', url.rstrip('/'))[-1] or "page"
    return re.sub(r'[\\/*?:"<>|]', '_', name)[:80]


def unique_path(folder: Path, filename: str) -> Path:
    path = folder / filename
    stem, suffix = Path(filename).stem, Path(filename).suffix
    i = 1
    while path.exists():
        path = folder / f"{stem}_{i}{suffix}"
        i += 1
    return path


def save_text(content: str, folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / filename
    if base.exists():
        return base
    path = unique_path(folder, filename)
    path.write_text(content, encoding='utf-8')
    return path


def save_bytes(content: bytes, folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / filename
    if base.exists():
        return base
    path = unique_path(folder, filename)
    path.write_bytes(content)
    return path


def save_json(data: dict | list, folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / filename
    if base.exists():
        return base
    path = unique_path(folder, filename)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def save_csv(data: list[dict], folder: Path, filename: str) -> Path | None:
    if not data:
        return None
    folder.mkdir(parents=True, exist_ok=True)
    path = unique_path(folder, filename)
    keys: set[str] = set()
    for item in data:
        keys.update(k for k in item if k != 'infobox')
        keys.update(item.get('infobox', {}).keys())
    fieldnames = sorted(keys)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for item in data:
            row = {k: v for k, v in item.items() if k != 'infobox'}
            row.update(item.get('infobox', {}))
            writer.writerow(row)
    return path


def open_folder(folder: Path):
    if sys.platform == 'win32':
        os.startfile(str(folder))
    elif sys.platform == 'darwin':
        subprocess.run(['open', str(folder)])
    else:
        subprocess.run(['xdg-open', str(folder)])