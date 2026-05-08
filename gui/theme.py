import customtkinter as ctk

BG_MAIN      = "#16213e"
BG_SIDEBAR   = "#1a1040"
BG_SURFACE   = "#0d0d26"
BORDER       = "#2d2d4e"
ACCENT       = "#00B4D8"
ACCENT_HOVER = "#0096b4"
TEXT         = "#e0e0e0"
TEXT_DIM     = "#888888"
SUCCESS      = "#4CAF50"
WARNING      = "#FF9800"
ERROR        = "#ef5350"
LOG_BG       = "#0a0a1a"

FONT_NORMAL = ("Segoe UI", 12)
FONT_SMALL  = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 12, "bold")
FONT_TITLE  = ("Segoe UI", 14, "bold")
FONT_LOG    = ("Consolas", 10)

VERSION = "3.0.0"

_THEME_MAP = {"dark": "Dark", "light": "Light", "system": "System"}


def apply_theme(name: str) -> None:
    ctk.set_appearance_mode(_THEME_MAP.get(name, "Dark"))


def setup():
    apply_theme("dark")
    ctk.set_default_color_theme("dark-blue")
