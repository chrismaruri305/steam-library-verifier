#!/usr/bin/env python3
"""
Steam Library Verifier — GUI Edition
=====================================
Verifies all installed Steam games ONE AT A TIME by monitoring each game's
appmanifest StateFlags to detect when verification finishes before moving
to the next game.

Requirements: Python 3.8+ (uses only stdlib — no pip installs needed)
Works on: Windows, macOS, Linux

Author: Christopher & Claude AI (Anthropic)
License: MIT
Source: https://github.com/chrismaruri305/steam-library-verifier
"""

import os
import sys
import re
import time
import platform
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


# ─── Constants ───────────────────────────────────────────────────────────────

CHK_ON  = "\u2611"   # ☑
CHK_OFF = "\u2610"   # ☐

# Steam StateFlags: 4 = fully installed. Anything else = updating/verifying.
STATE_FULLY_INSTALLED = 4

# How often (seconds) to poll the manifest while waiting
POLL_INTERVAL = 2

# Sort direction symbols
SORT_ASC  = " \u25B2"  # ▲
SORT_DESC = " \u25BC"  # ▼


# ─── Steam Discovery ────────────────────────────────────────────────────────

def get_default_steam_paths():
    system = platform.system()
    home = Path.home()
    if system == "Windows":
        return [
            Path(r"C:\Program Files (x86)\Steam"),
            Path(r"C:\Program Files\Steam"),
            home / "Steam",
        ]
    elif system == "Darwin":
        return [home / "Library" / "Application Support" / "Steam"]
    else:
        return [
            home / ".steam" / "steam",
            home / ".steam" / "debian-installation",
            home / ".local" / "share" / "Steam",
        ]


def find_steam_path():
    for path in get_default_steam_paths():
        if path.exists() and (path / "steamapps").exists():
            return path
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Valve\Steam",
            )
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            p = Path(install_path)
            if p.exists():
                return p
        except (OSError, ImportError):
            pass
    return None


def parse_vdf_value(text, key):
    match = re.search(rf'"{key}"\s+"([^"]*)"', text, re.IGNORECASE)
    return match.group(1) if match else None


def get_library_folders(steam_path):
    vdf = steam_path / "steamapps" / "libraryfolders.vdf"
    folders = []
    if vdf.exists():
        content = vdf.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'"path"\s+"([^"]+)"', content):
            f = Path(m.group(1).replace("\\\\", "\\")) / "steamapps"
            if f.exists():
                folders.append(f)
    if not folders:
        folders.append(steam_path / "steamapps")
    return folders


def get_installed_games(library_folders):
    games = {}
    for folder in library_folders:
        for manifest in folder.glob("appmanifest_*.acf"):
            try:
                content = manifest.read_text(encoding="utf-8", errors="replace")
                appid = parse_vdf_value(content, "appid")
                name = parse_vdf_value(content, "name")
                size = parse_vdf_value(content, "SizeOnDisk")
                if appid and name:
                    games[appid] = {
                        "name": name,
                        "appid": appid,
                        "size": int(size) if size else 0,
                        "library": str(folder),
                        "manifest": str(manifest),
                    }
            except Exception:
                pass
    return games


def read_state_flags(manifest_path):
    try:
        content = Path(manifest_path).read_text(encoding="utf-8", errors="replace")
        val = parse_vdf_value(content, "StateFlags")
        return int(val) if val else None
    except Exception:
        return None


def is_steam_running():
    """Return True if the Steam process is currently running."""
    system = platform.system()
    try:
        if system == "Windows":
            import subprocess as _sp
            out = _sp.check_output(
                ["tasklist", "/FI", "IMAGENAME eq steam.exe"],
                stderr=_sp.DEVNULL
            ).decode(errors="replace")
            return "steam.exe" in out.lower()
        else:
            # macOS / Linux: use pgrep
            result = subprocess.run(
                ["pgrep", "-x", "steam" if system == "Linux" else "Steam"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return result.returncode == 0
    except Exception:
        return False  # Can't tell — allow the run


def trigger_verify(appid):
    uri = f"steam://validate/{appid}"
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(uri)
        elif system == "Darwin":
            subprocess.Popen(["open", uri], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", uri], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def format_size(size_bytes):
    if size_bytes <= 0:
        return "—"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_elapsed(seconds):
    seconds = int(seconds)
    if seconds < 3600:
        return f"{seconds // 60}:{seconds % 60:02d}"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}"


# ─── Color Palette ───────────────────────────────────────────────────────────

C = {
    "bg":           "#1b2838",
    "bg_light":     "#1e3044",
    "bg_card":      "#16202d",
    "accent":       "#66c0f4",
    "accent_hover": "#4db2ec",
    "accent_dark":  "#2a475e",
    "green":        "#5ba32b",
    "green_light":  "#8bc34a",
    "red":          "#c0392b",
    "yellow":       "#f39c12",
    "orange":       "#e67e22",
    "text":         "#c7d5e0",
    "text_dim":     "#56707e",
    "text_bright":  "#ffffff",
    "progress_bg":  "#0e1a26",
    "progress_fill":"#66c0f4",
    "row_even":     "#1b2838",
    "row_odd":      "#16202d",
    "row_hover":    "#243447",
    "row_verified": "#1a2e1a",
    "row_failed":   "#2e1a1a",
}


# ─── Hoverable Treeview ─────────────────────────────────────────────────────

class HoverTreeview(ttk.Treeview):
    """Treeview subclass that highlights the row under the cursor without
    changing text color to white (which is the default 'selected' behaviour
    that was causing readability issues)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hover_item = None
        self._hover_prev_tags = ()
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)

    def _on_motion(self, event):
        item = self.identify_row(event.y)
        if item == self._hover_item:
            return
        # Restore previous
        self._restore_hover()
        if item:
            self._hover_item = item
            self._hover_prev_tags = self.item(item, "tags")
            self.item(item, tags=("hover",))

    def _on_leave(self, _event):
        self._restore_hover()

    def _restore_hover(self):
        if self._hover_item:
            try:
                self.item(self._hover_item, tags=self._hover_prev_tags)
            except tk.TclError:
                pass
            self._hover_item = None
            self._hover_prev_tags = ()


# ─── Main Application ───────────────────────────────────────────────────────

class SteamVerifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Steam Library Verifier")
        self.root.geometry("920x700")
        self.root.minsize(720, 520)
        self.root.configure(bg=C["bg"])

        # State
        self.games = {}
        self.sorted_games = []
        self.steam_path = None
        self.is_verifying = False
        self.stop_requested = False
        self.delay_var = tk.IntVar(value=5)
        self.timeout_var = tk.IntVar(value=120)
        self.verified_count = 0
        self.failed_count = 0
        self.checked = {}          # appid -> bool
        self.sort_col = "name"     # current sort column
        self.sort_asc = True       # current direction

        self._build_styles()
        self._build_ui()
        self.root.after(100, self._auto_scan)

    # ── Styles ───────────────────────────────────────────────────────────

    def _build_styles(self):
        s = ttk.Style()
        s.theme_use("clam")

        s.configure(".", background=C["bg"], foreground=C["text"],
                     fieldbackground=C["bg_card"], borderwidth=0)
        s.configure("TFrame", background=C["bg"])
        s.configure("Card.TFrame", background=C["bg_card"])

        s.configure("TLabel", background=C["bg"], foreground=C["text"],
                     font=("Segoe UI", 10))
        s.configure("Title.TLabel", font=("Segoe UI", 18, "bold"),
                     foreground=C["text_bright"])
        s.configure("Subtitle.TLabel", font=("Segoe UI", 10),
                     foreground=C["text_dim"])
        s.configure("Status.TLabel", font=("Segoe UI", 10),
                     foreground=C["accent"])
        s.configure("Selected.TLabel", font=("Segoe UI", 10, "bold"),
                     foreground=C["accent"])
        s.configure("Card.TLabel", background=C["bg_card"])
        s.configure("StatValue.TLabel", font=("Segoe UI", 20, "bold"),
                     foreground=C["text_bright"], background=C["bg_card"])
        s.configure("StatLabel.TLabel", font=("Segoe UI", 9),
                     foreground=C["text_dim"], background=C["bg_card"])

        s.configure("Accent.TButton", font=("Segoe UI", 10, "bold"),
                     background=C["accent"], foreground=C["bg"], padding=(20, 10))
        s.map("Accent.TButton",
               background=[("pressed", C["accent_hover"]),
                           ("active", C["accent_hover"]),
                           ("disabled", C["accent_dark"])],
               foreground=[("pressed", C["bg"]),
                           ("active", C["bg"]),
                           ("disabled", C["text_dim"])])

        s.configure("Stop.TButton", font=("Segoe UI", 10, "bold"),
                     background=C["red"], foreground="#fff", padding=(20, 10))
        s.map("Stop.TButton",
               background=[("pressed", "#e74c3c"), ("active", "#e74c3c")],
               foreground=[("pressed", "#fff"), ("active", "#fff")])

        s.configure("Link.TButton", font=("Segoe UI", 9),
                     background=C["bg"], foreground=C["accent"], padding=(8, 5))
        s.map("Link.TButton",
               background=[("pressed", C["bg"]), ("active", C["bg"])],
               foreground=[("pressed", C["accent_hover"]),
                           ("active", C["accent_hover"])])

        s.configure("SelectBtn.TButton", font=("Segoe UI", 9, "bold"),
                     background=C["accent_dark"], foreground=C["text"],
                     padding=(12, 6))
        s.map("SelectBtn.TButton",
               background=[("pressed", C["accent"]), ("active", C["accent"])],
               foreground=[("pressed", C["bg"]), ("active", C["bg"])])

        s.configure("Horizontal.TProgressbar",
                     troughcolor=C["progress_bg"],
                     background=C["progress_fill"], thickness=12)

        s.configure("Treeview",
                     background=C["bg_card"], foreground=C["text"],
                     fieldbackground=C["bg_card"],
                     font=("Segoe UI", 10), rowheight=30, borderwidth=0)
        s.configure("Treeview.Heading",
                     background=C["accent_dark"], foreground=C["text_bright"],
                     font=("Segoe UI", 10, "bold"), borderwidth=0,
                     relief="flat")
        s.map("Treeview.Heading",
               background=[("active", C["accent"]), ("pressed", C["accent"])],
               foreground=[("active", C["bg"]), ("pressed", C["bg"])])
        # Disable the default white-on-blue selected row styling
        s.map("Treeview",
               background=[("selected", C["bg_card"])],
               foreground=[("selected", C["text"])])

    # ── UI Layout ────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        header = ttk.Frame(self.root)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 2))
        header.columnconfigure(1, weight=1)

        left = ttk.Frame(header)
        left.grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="\U0001F3AE  Steam Library Verifier",
                  style="Title.TLabel").pack(anchor="w")
        self.path_label = ttk.Label(left, text="Scanning for Steam...",
                                     style="Subtitle.TLabel")
        self.path_label.pack(anchor="w", pady=(2, 0))

        right = ttk.Frame(header)
        right.grid(row=0, column=1, sticky="e")
        ttk.Button(right, text="Browse...", style="Link.TButton",
                   command=self._browse_steam).pack(side="left", padx=4)
        ttk.Button(right, text="Rescan", style="Link.TButton",
                   command=self._auto_scan).pack(side="left", padx=4)

    def _build_toolbar(self):
        bar = ttk.Frame(self.root)
        bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(6, 2))
        bar.columnconfigure(3, weight=1)

        ttk.Button(bar, text=f"{CHK_ON}  Select All", style="SelectBtn.TButton",
                   command=self._select_all).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(bar, text=f"{CHK_OFF}  Deselect All", style="SelectBtn.TButton",
                   command=self._deselect_all).grid(row=0, column=1, padx=4)
        ttk.Button(bar, text="\u21C4  Invert", style="SelectBtn.TButton",
                   command=self._invert_selection).grid(row=0, column=2, padx=4)

        self.selected_label = ttk.Label(bar, text="0 / 0 selected",
                                         style="Selected.TLabel")
        self.selected_label.grid(row=0, column=3, sticky="e")

    def _build_body(self):
        body = ttk.Frame(self.root)
        body.grid(row=2, column=0, sticky="nsew", padx=20, pady=5)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        # ── Treeview ──
        tf = ttk.Frame(body)
        tf.grid(row=0, column=0, sticky="nsew")
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)

        cols = ("check", "name", "size", "status", "time")
        self.tree = HoverTreeview(tf, columns=cols, show="headings",
                                   selectmode="none")

        self.tree.heading("check",  text=CHK_ON, anchor="center")
        self.tree.heading("name",   text=f"Game{SORT_ASC}", anchor="w",
                          command=lambda: self._sort_by("name"))
        self.tree.heading("size",   text="Size", anchor="e",
                          command=lambda: self._sort_by("size"))
        self.tree.heading("status", text="Status", anchor="center")
        self.tree.heading("time",   text="Time", anchor="center")

        self.tree.column("check",  width=40,  minwidth=40,  stretch=False, anchor="center")
        self.tree.column("name",   width=400, minwidth=200, anchor="w")
        self.tree.column("size",   width=100, minwidth=70,  anchor="e")
        self.tree.column("status", width=160, minwidth=100, anchor="center")
        self.tree.column("time",   width=80,  minwidth=60,  anchor="center")

        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Button-1>", self._on_tree_click)

        # Row color tags — every tag uses an explicit foreground so hover /
        # selection never causes text to flip to white.
        self.tree.tag_configure("even",
            background=C["row_even"], foreground=C["text"])
        self.tree.tag_configure("odd",
            background=C["row_odd"], foreground=C["text"])
        self.tree.tag_configure("unchecked_even",
            background=C["row_even"], foreground=C["text_dim"])
        self.tree.tag_configure("unchecked_odd",
            background=C["row_odd"], foreground=C["text_dim"])
        self.tree.tag_configure("hover",
            background=C["row_hover"], foreground=C["text_bright"])
        self.tree.tag_configure("verified",
            background=C["row_verified"], foreground=C["green_light"])
        self.tree.tag_configure("failed",
            background=C["row_failed"], foreground=C["red"])
        self.tree.tag_configure("active",
            background=C["accent_dark"], foreground=C["accent"])
        self.tree.tag_configure("waiting",
            background=C["bg_light"], foreground=C["yellow"])
        self.tree.tag_configure("timeout",
            background=C["row_failed"], foreground=C["orange"])
        self.tree.tag_configure("skipped",
            background=C["row_even"], foreground=C["text_dim"])

        # ── Stats ──
        stats = ttk.Frame(body, style="Card.TFrame")
        stats.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for i in range(6):
            stats.columnconfigure(i, weight=1)

        self._stat_total     = self._make_stat(stats, "Total",     "0", 0)
        self._stat_selected  = self._make_stat(stats, "Selected",  "0", 1)
        self._stat_verified  = self._make_stat(stats, "Verified",  "0", 2)
        self._stat_failed    = self._make_stat(stats, "Failed",    "0", 3)
        self._stat_remaining = self._make_stat(stats, "Remaining", "0", 4)
        self._stat_elapsed   = self._make_stat(stats, "Elapsed",   "—", 5)

    def _make_stat(self, parent, label, value, col):
        f = ttk.Frame(parent, style="Card.TFrame")
        f.grid(row=0, column=col, padx=6, pady=10, sticky="ew")
        v = ttk.Label(f, text=value, style="StatValue.TLabel")
        v.pack(anchor="center")
        ttk.Label(f, text=label, style="StatLabel.TLabel").pack(anchor="center")
        return v

    def _build_footer(self):
        footer = ttk.Frame(self.root)
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(5, 15))
        footer.columnconfigure(2, weight=1)

        # Options
        opts = ttk.Frame(footer)
        opts.grid(row=0, column=0, sticky="w")

        ttk.Label(opts, text="Startup delay:").pack(side="left", padx=(0, 3))
        tk.Spinbox(opts, from_=2, to=30, width=3, textvariable=self.delay_var,
                   bg=C["bg_card"], fg=C["text"],
                   buttonbackground=C["accent_dark"],
                   insertbackground=C["text"],
                   relief="flat", font=("Segoe UI", 10)).pack(side="left")
        ttk.Label(opts, text="s").pack(side="left", padx=(1, 12))

        ttk.Label(opts, text="Timeout:").pack(side="left", padx=(0, 3))
        tk.Spinbox(opts, from_=5, to=300, width=4, textvariable=self.timeout_var,
                   bg=C["bg_card"], fg=C["text"],
                   buttonbackground=C["accent_dark"],
                   insertbackground=C["text"],
                   relief="flat", font=("Segoe UI", 10)).pack(side="left")
        ttk.Label(opts, text="min").pack(side="left", padx=(1, 0))

        # Progress
        pf = ttk.Frame(footer)
        pf.grid(row=0, column=2, sticky="ew", padx=20)
        pf.columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(pf, variable=self.progress_var,
                                             maximum=100, mode="determinate",
                                             style="Horizontal.TProgressbar")
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        self.progress_label = ttk.Label(pf, text="Ready", style="Status.TLabel")
        self.progress_label.grid(row=1, column=0, sticky="w")

        # Buttons
        self.btn_frame = ttk.Frame(footer)
        self.btn_frame.grid(row=0, column=3, sticky="e")

        self.verify_btn = ttk.Button(self.btn_frame, text="\u25B6  Verify Selected",
                                      style="Accent.TButton",
                                      command=self._start_verification)
        self.verify_btn.pack(side="right")
        self.stop_btn = ttk.Button(self.btn_frame, text="\u25A0  Stop",
                                    style="Stop.TButton",
                                    command=self._stop_verification)

    # ── Sorting ──────────────────────────────────────────────────────────

    def _sort_by(self, col):
        """Sort the treeview by column. Toggles direction on repeat click."""
        if self.is_verifying:
            return

        if self.sort_col == col:
            self.sort_asc = not self.sort_asc
        else:
            self.sort_col = col
            self.sort_asc = True

        # Update heading arrows
        arrow = SORT_ASC if self.sort_asc else SORT_DESC
        self.tree.heading("name", text="Game" + (arrow if col == "name" else ""))
        self.tree.heading("size", text="Size" + (arrow if col == "size" else ""))

        # Re-sort
        if col == "name":
            self.sorted_games.sort(key=lambda g: g["name"].lower(),
                                    reverse=not self.sort_asc)
        elif col == "size":
            self.sorted_games.sort(key=lambda g: g["size"],
                                    reverse=not self.sort_asc)

        self._repopulate_tree()

    def _repopulate_tree(self):
        """Clear and re-insert all rows preserving check state and status."""
        # Save current status/time per row
        row_data = {}
        for appid in self.checked:
            try:
                vals = self.tree.item(appid, "values")
                row_data[appid] = {"status": vals[3], "time": vals[4]}
            except (tk.TclError, IndexError):
                row_data[appid] = {"status": "Pending", "time": ""}

        self.tree.delete(*self.tree.get_children())

        for i, game in enumerate(self.sorted_games):
            aid = game["appid"]
            is_on = self.checked.get(aid, True)
            if is_on:
                tag = "even" if i % 2 == 0 else "odd"
            else:
                tag = "unchecked_even" if i % 2 == 0 else "unchecked_odd"

            saved = row_data.get(aid, {"status": "Pending", "time": ""})
            self.tree.insert("", "end", iid=aid,
                             values=(CHK_ON if is_on else CHK_OFF,
                                     game["name"],
                                     format_size(game["size"]),
                                     saved["status"], saved["time"]),
                             tags=(tag,))

    # ── Checkbox Logic ───────────────────────────────────────────────────

    def _on_tree_click(self, event):
        if self.is_verifying:
            return
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.checked[row_id] = not self.checked.get(row_id, True)
        self._refresh_row_visual(row_id)
        self._update_selected_count()

    def _refresh_row_visual(self, appid):
        try:
            vals = list(self.tree.item(appid, "values"))
            is_on = self.checked.get(appid, True)
            vals[0] = CHK_ON if is_on else CHK_OFF
            idx = self.tree.index(appid)
            if is_on:
                tag = "even" if idx % 2 == 0 else "odd"
            else:
                tag = "unchecked_even" if idx % 2 == 0 else "unchecked_odd"
            self.tree.item(appid, values=vals, tags=(tag,))
        except tk.TclError:
            pass

    def _update_selected_count(self):
        total = len(self.sorted_games)
        sel = sum(1 for g in self.sorted_games if self.checked.get(g["appid"], True))
        self.selected_label.config(text=f"{sel} / {total} selected")
        self._stat_selected.config(text=str(sel))

    def _select_all(self):
        for g in self.sorted_games:
            self.checked[g["appid"]] = True
            self._refresh_row_visual(g["appid"])
        self._update_selected_count()

    def _deselect_all(self):
        for g in self.sorted_games:
            self.checked[g["appid"]] = False
            self._refresh_row_visual(g["appid"])
        self._update_selected_count()

    def _invert_selection(self):
        for g in self.sorted_games:
            a = g["appid"]
            self.checked[a] = not self.checked.get(a, True)
            self._refresh_row_visual(a)
        self._update_selected_count()

    # ── Actions ──────────────────────────────────────────────────────────

    def _auto_scan(self):
        self.steam_path = find_steam_path()
        if self.steam_path:
            self.path_label.config(text=str(self.steam_path))
            self._load_games()
        else:
            self.path_label.config(text="Steam not found \u2014 use Browse...")

    def _browse_steam(self):
        folder = filedialog.askdirectory(title="Select your Steam installation folder")
        if folder:
            p = Path(folder)
            if (p / "steamapps").exists():
                self.steam_path = p
                self.path_label.config(text=str(p))
                self._load_games()
            else:
                messagebox.showerror("Invalid Path",
                                      "No 'steamapps' folder found in that directory.")

    def _load_games(self):
        self.tree.delete(*self.tree.get_children())
        self.checked.clear()

        library_folders = get_library_folders(self.steam_path)
        self.games = get_installed_games(library_folders)
        self.sorted_games = sorted(self.games.values(), key=lambda g: g["name"].lower())
        self.sort_col = "name"
        self.sort_asc = True
        self.tree.heading("name", text=f"Game{SORT_ASC}")
        self.tree.heading("size", text="Size")

        for i, game in enumerate(self.sorted_games):
            tag = "even" if i % 2 == 0 else "odd"
            self.checked[game["appid"]] = True
            self.tree.insert("", "end", iid=game["appid"],
                             values=(CHK_ON, game["name"],
                                     format_size(game["size"]), "Pending", ""),
                             tags=(tag,))

        total = len(self.sorted_games)
        self._stat_total.config(text=str(total))
        self._stat_selected.config(text=str(total))
        self._stat_remaining.config(text=str(total))
        self._stat_verified.config(text="0")
        self._stat_failed.config(text="0")
        self._stat_elapsed.config(text="\u2014")
        self.progress_var.set(0)
        self.progress_label.config(text=f"{total} games found \u2014 ready to verify")
        self._update_selected_count()

    def _start_verification(self):
        if not self.sorted_games:
            messagebox.showinfo("Nothing to verify", "No games found. Scan first.")
            return

        verify_ids = [g["appid"] for g in self.sorted_games
                      if self.checked.get(g["appid"], True)]
        if not verify_ids:
            messagebox.showinfo("Nothing selected",
                                "No games are checked. Select at least one game.")
            return

        # Bug fix #1 — validate spinbox values before proceeding
        try:
            delay_val = int(self.delay_var.get())
            timeout_val = int(self.timeout_var.get())
            if delay_val < 2 or timeout_val < 5:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror(
                "Invalid Settings",
                "Startup delay must be a whole number ≥ 2 and "
                "timeout must be a whole number ≥ 5."
            )
            return

        # Bug fix #2 — check Steam is running before queuing anything
        if not is_steam_running():
            messagebox.showerror(
                "Steam Not Running",
                "Steam doesn't appear to be running.\n\n"
                "Please launch Steam first, then click Verify again."
            )
            return

        for game in self.sorted_games:
            if not self.checked.get(game["appid"], True):
                self._set_row_status(game["appid"], "\u2014 Skipped", "skipped", "")

        self.verify_list = verify_ids
        self.is_verifying = True
        self.stop_requested = False
        self.verified_count = 0
        self.failed_count = 0
        self._stat_remaining.config(text=str(len(verify_ids)))

        self.verify_btn.pack_forget()
        self.stop_btn.pack(side="right")

        threading.Thread(target=self._verify_thread, daemon=True).start()

    def _stop_verification(self):
        self.stop_requested = True
        self.progress_label.config(text="Stopping after current game...")

    def _verify_thread(self):
        total = len(self.verify_list)
        startup_delay = self.delay_var.get()
        timeout_sec = self.timeout_var.get() * 60
        session_start = time.time()

        for i, appid in enumerate(self.verify_list):
            if self.stop_requested:
                self.root.after(0, self._on_finish, "Stopped by user")
                return

            game = self.games.get(appid, {})
            name = game.get("name", appid)
            manifest = game.get("manifest", "")

            # Phase 1 — trigger
            self.root.after(0, self._set_row_status, appid,
                            "Starting...", "active", "")
            self.root.after(0, self._update_progress, i, total,
                            f"Starting: {name}")

            if not trigger_verify(appid):
                self.failed_count += 1
                self.root.after(0, self._set_row_status, appid,
                                "\u2717 Launch failed", "failed", "")
                self.root.after(0, self._update_stats, total, i + 1, session_start)
                continue

            time.sleep(startup_delay)
            if self.stop_requested:
                self.root.after(0, self._on_finish, "Stopped by user")
                return

            # Phase 2 — wait for Steam to start verifying
            self.root.after(0, self._set_row_status, appid,
                            "Waiting for Steam...", "waiting", "")
            game_start = time.time()
            verify_started = False

            for _ in range(15):  # up to ~30s
                if self.stop_requested:
                    self.root.after(0, self._on_finish, "Stopped by user")
                    return
                flags = read_state_flags(manifest)
                if flags is not None and flags != STATE_FULLY_INSTALLED:
                    verify_started = True
                    break
                time.sleep(2)

            if not verify_started:
                # Bug fix #3 — StateFlags never changed after triggering.
                # Steam is running (checked before queue started) but didn't
                # begin verification — mark as failed rather than falsely
                # reporting success.
                self.failed_count += 1
                self.root.after(0, self._set_row_status, appid,
                                "\u26A0 Not started", "failed", "")
                self.root.after(0, self._update_stats, total, i + 1, session_start)
                continue

            # Phase 3 — poll until finished
            self.root.after(0, self._set_row_status, appid,
                            "Verifying...", "active", "")
            timed_out = False

            while True:
                if self.stop_requested:
                    self.root.after(0, self._on_finish, "Stopped by user")
                    return

                elapsed = time.time() - game_start
                self.root.after(0, self._set_row_time, appid,
                                format_elapsed(elapsed))
                self.root.after(0, self._update_progress, i, total,
                                f"Verifying: {name}  ({format_elapsed(elapsed)})")

                flags = read_state_flags(manifest)
                if flags is not None and flags == STATE_FULLY_INSTALLED:
                    break
                if elapsed > timeout_sec:
                    timed_out = True
                    break
                time.sleep(POLL_INTERVAL)

            elapsed = time.time() - game_start
            if timed_out:
                self.failed_count += 1
                self.root.after(0, self._set_row_status, appid,
                                "\u26A0 Timed out", "timeout",
                                format_elapsed(elapsed))
            else:
                self.verified_count += 1
                self.root.after(0, self._set_row_status, appid,
                                "\u2713 Complete", "verified",
                                format_elapsed(elapsed))

            self.root.after(0, self._update_stats, total, i + 1, session_start)

        self.root.after(0, self._on_finish, "All done!")

    # ── UI helpers ───────────────────────────────────────────────────────

    def _set_row_status(self, appid, status, tag, time_str):
        try:
            vals = list(self.tree.item(appid, "values"))
            vals[3] = status
            vals[4] = time_str
            self.tree.item(appid, values=vals, tags=(tag,))
            self.tree.see(appid)
        except tk.TclError:
            pass

    def _set_row_time(self, appid, time_str):
        try:
            vals = list(self.tree.item(appid, "values"))
            vals[4] = time_str
            self.tree.item(appid, values=vals)
        except tk.TclError:
            pass

    def _update_progress(self, current, total, msg):
        pct = ((current + 0.5) / total) * 100
        self.progress_var.set(pct)
        self.progress_label.config(text=f"[{current + 1}/{total}] {msg}")

    def _update_stats(self, total, processed, session_start):
        remaining = total - processed
        elapsed = time.time() - session_start
        self._stat_verified.config(text=str(self.verified_count))
        self._stat_failed.config(text=str(self.failed_count))
        self._stat_remaining.config(text=str(remaining))
        self._stat_elapsed.config(text=format_elapsed(elapsed))

    def _on_finish(self, msg):
        self.is_verifying = False
        self.progress_var.set(100 if not self.stop_requested
                              else self.progress_var.get())
        self.progress_label.config(
            text=f"{msg}  \u2014  {self.verified_count} verified, "
                 f"{self.failed_count} failed"
        )
        self.stop_btn.pack_forget()
        self.verify_btn.pack(side="right")


# ─── Entry ───────────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    if platform.system() == "Windows":
        try:
            root.iconbitmap(default="")
        except Exception:
            pass
    SteamVerifierApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
