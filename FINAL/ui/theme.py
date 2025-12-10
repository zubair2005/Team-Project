import tkinter as tk
from tkinter import ttk


_PALETTES = {
    "light": {
        "bg": "#f7f7fb",
        "surface": "#ffffff",
        "text": "#111827",
        "muted": "#6b7280",
        "border": "#e5e7eb",
        "accent": "#3a86ff",
        "danger": "#ef4444",
    },
    "dark": {
        "bg": "#0f172a",
        "surface": "#111827",
        "text": "#e5e7eb",
        "muted": "#9ca3af",
        "border": "#1f2937",
        "accent": "#60a5fa",
        "danger": "#f87171",
    },
}


def _configure_base_style(style: ttk.Style, palette: dict) -> None:
    # Pick a known theme for cross‑platform color support
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Global font and colors
    style.configure(
        ".",
        foreground=palette["text"],
        background=palette["bg"],
        fieldbackground=palette["surface"],
    )

    # Frames, labels, entries, buttons
    style.configure("TFrame", background=palette["bg"])
    style.configure("Card.TFrame", background=palette["surface"], relief="flat")
    style.configure("TLabel", background=palette["bg"], foreground=palette["text"])
    style.configure(
        "Muted.TLabel",
        background=palette["bg"],
        foreground=palette["muted"],
    )
    style.configure(
        "Error.TLabel",
        background=palette["bg"],
        foreground=palette["danger"],
    )

    style.configure(
        "TEntry",
        fieldbackground=palette["surface"],
        foreground=palette["text"],
        bordercolor=palette["border"],
        lightcolor=palette["border"],
        darkcolor=palette["border"],
        borderwidth=1,
        relief="flat",
        padding=6,
    )

    # Buttons
    style.configure(
        "TButton",
        padding=(12, 6),
        relief="flat",
        borderwidth=0,
        background=palette["surface"],
        foreground=palette["text"],
    )
    style.map(
        "TButton",
        background=[("active", palette["border"])],
    )
    style.configure(
        "Primary.TButton",
        background=palette["accent"],
        foreground="#ffffff",
    )
    style.map(
        "Primary.TButton",
        background=[("active", _tint(palette["accent"], -0.08))],
    )
    style.configure(
        "Danger.TButton",
        background=palette["danger"],
        foreground="#ffffff",
    )
    style.map(
        "Danger.TButton",
        background=[("active", _tint(palette["danger"], -0.08))],
    )

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground=palette["surface"],
        background=palette["surface"],
        foreground=palette["text"],
        selectbackground=palette["surface"],
        selectforeground=palette["text"],
        bordercolor=palette["border"],
        lightcolor=palette["border"],
        darkcolor=palette["border"],
        arrowcolor=palette["muted"],
        padding=6,
        relief="flat",
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", palette["surface"]), ("active", _tint(palette["surface"], -0.02))],
        background=[("active", _tint(palette["surface"], -0.02))],
        bordercolor=[("focus", palette["accent"])],
        arrowcolor=[("active", palette["text"]), ("focus", palette["text"])],
        foreground=[("readonly", palette["text"]), ("active", palette["text"]), ("focus", palette["text"])],
    )
    # Alias style for explicit usage where needed
    style.configure("Filled.TCombobox", **style.configure("TCombobox"))

    # Notebook (tabs)
    style.configure(
        "TNotebook",
        background=palette["bg"],
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        padding=(12, 6),
        background=palette["surface"],
        foreground=palette["text"],
    )
    # Visual feedback for tabs
    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", _tint(palette["surface"], -0.04)),
            ("active", _tint(palette["surface"], -0.02)),
        ],
        foreground=[
            ("selected", palette["text"]),
            ("active", palette["text"]),
        ],
    )

    # Treeview (tables)
    style.configure(
        "Treeview",
        background=palette["surface"],
        fieldbackground=palette["surface"],
        foreground=palette["text"],
        rowheight=28,
        bordercolor=palette["border"],
        lightcolor=palette["border"],
        darkcolor=palette["border"],
        borderwidth=1,
    )
    style.configure(
        "Treeview.Heading",
        background=_tint(palette["surface"], -0.02),
        foreground=palette["text"],
        relief="flat",
        padding=(8, 6),
    )


def _tint(hex_color: str, delta: float) -> str:
    """Lighten/darken a hex color by delta (-1..1)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    def clamp(x: int) -> int:
        return max(0, min(255, x))
    if delta >= 0:
        r = clamp(int(r + (255 - r) * delta))
        g = clamp(int(g + (255 - g) * delta))
        b = clamp(int(b + (255 - b) * delta))
    else:
        r = clamp(int(r * (1 + delta)))
        g = clamp(int(g * (1 + delta)))
        b = clamp(int(b * (1 + delta)))
    return f"#{r:02x}{g:02x}{b:02x}"


def apply_theme(root: tk.Misc, mode: str = "light") -> None:
    """Apply light theme only - dark mode removed."""
    # Always use light mode, ignore mode parameter
    palette = _PALETTES["light"]
    style = ttk.Style(root)
    _configure_base_style(style, palette)

    # Window background + global font
    try:
        root.configure(bg=palette["bg"])
    except Exception:
        pass
    # Set a clean default font stack (falls back to system)
    root.option_add("*Font", "Helvetica 11")
    root.option_add("*TButton.font", "Helvetica 11")
    root.option_add("*TLabel.font", "Helvetica 11")
    root.option_add("*Treeview.font", "Helvetica 10")
    root.option_add("*Treeview.Heading.font", "Helvetica 10 bold")

    # Always set light mode
    setattr(root, "_theme_mode", "light")
    # Notify widgets to refresh themselves (e.g., custom canvases)
    try:
        root.event_generate("<<ThemeChanged>>", when="tail")
    except Exception:
        pass


def toggle_theme(root: tk.Misc) -> None:
    """Dark mode removed - does nothing now."""
    # Always stay in light mode
    apply_theme(root, "light")


def get_palette(root: tk.Misc) -> dict:
    """Return the light palette only - dark mode removed."""
    # Always return light palette
    return _PALETTES["light"]


def tint(hex_color: str, delta: float) -> str:
    """Public wrapper to lighten/darken a hex color by delta (-1..1)."""
    return _tint(hex_color, delta)

