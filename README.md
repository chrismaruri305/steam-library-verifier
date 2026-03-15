# 🎮 Steam Library Verifier

A free, open-source desktop GUI tool that verifies the integrity of **all your installed Steam games**, one at a time — the way Steam actually requires it.

Steam only allows one game to be verified at a time. This tool automates the tedious process of manually right-clicking → Properties → Verify for every single game in your library. It queues each game, monitors when it finishes, then moves to the next.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)
![Dependencies](https://img.shields.io/badge/Dependencies-None-brightgreen)
![Open Source](https://img.shields.io/badge/Open%20Source-%E2%9D%A4-red)

---

## ✨ Features

- **Truly sequential verification** — monitors each game's `appmanifest` StateFlags to wait for completion before starting the next
- **Per-game checkboxes** — click any row to include/exclude it; Select All, Deselect All, and Invert buttons
- **Sortable columns** — click the Game or Size headers to sort A→Z, Z→A, or by size
- **Live progress tracking** — per-game elapsed timer, overall progress bar, and stat cards (Total / Selected / Verified / Failed / Remaining / Elapsed)
- **Configurable timeouts** — set a max wait per game so it doesn't hang forever on a problem title
- **Auto-detects Steam** — finds your Steam install and all library folders automatically; manual browse as fallback
- **Steam-inspired dark theme** — easy on the eyes during long verification sessions
- **Zero dependencies** — uses only Python's standard library (tkinter)

## 📸 Screenshot

```
┌────────────────────────────────────────────────────────────┐
│  🎮  Steam Library Verifier                                │
│  C:\Program Files (x86)\Steam                              │
│                                                            │
│  ☑ Select All  ☐ Deselect All  ⇄ Invert    12/42 selected │
│ ┌──┬────────────────────┬─────────┬───────────┬──────┐     │
│ │☑ │ Game           ▲   │ Size    │ Status    │ Time │     │
│ ├──┼────────────────────┼─────────┼───────────┼──────┤     │
│ │☑ │ Counter-Strike 2   │ 35.2 GB │ ✓ Complete│ 4:23 │     │
│ │☑ │ Cyberpunk 2077     │ 70.1 GB │ Verifying │ 2:01 │     │
│ │☐ │ Half-Life 2        │  6.4 GB │ — Skipped │      │     │
│ │☑ │ Portal 2           │ 12.8 GB │ Pending   │      │     │
│ └──┴────────────────────┴─────────┴───────────┴──────┘     │
│                                                            │
│  Total  Selected  Verified  Failed  Remaining  Elapsed     │
│   42      12        1         0        11       6:24       │
│                                                            │
│  Startup delay: 5s   Timeout: 120 min                      │
│  ████████████░░░░░░░░░░░░░  [2/12] Verifying: Cyberpunk   │
│                                            ▶ Verify Selected│
└────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** (tkinter is included with most Python installations)
- **Steam** must be running

### Run It

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/steam-library-verifier.git
cd steam-library-verifier

# Run
python verify_steam_gui.py
```

That's it. No `pip install`, no virtual env, no dependencies.

### Windows Users

If you have Python installed, you can also just double-click `verify_steam_gui.py`.

## 🎯 How to Use

1. **Launch the app** — it auto-detects your Steam installation and lists all installed games
2. **Uncheck games** you want to skip (click any row to toggle, or use the toolbar buttons)
3. **Sort** by clicking the Game or Size column headers
4. **Adjust settings** — startup delay (time before polling begins) and timeout (max wait per game)
5. **Click "▶ Verify Selected"** and confirm
6. **Watch progress** — each game shows its current status and elapsed time
7. **Stop anytime** — the current game finishes its poll cycle, then the process halts

## ⚙️ How It Works

Unlike scripts that blast `steam://validate` URLs in rapid succession (which Steam ignores), this tool does it properly:

1. **Trigger** — sends `steam://validate/{appid}` for one game
2. **Detect start** — polls the game's `appmanifest_*.acf` file until `StateFlags` changes from `4` (fully installed) to another value
3. **Wait for completion** — continues polling until `StateFlags` returns to `4`
4. **Next game** — only then moves to the next title in the queue

This matches how Steam internally handles verification — one game at a time, sequentially.

## 🔧 Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Startup delay | 5 seconds | Time to wait after triggering before polling begins |
| Timeout | 120 minutes | Max wait per game before marking it as timed out and moving on |

## 🖥️ Platform Support

| OS | Steam Detection | Tested |
|----|----------------|--------|
| Windows | Registry + default paths | ✅ |
| macOS | `~/Library/Application Support/Steam` | ✅ |
| Linux | `~/.steam/steam`, `~/.local/share/Steam` | ✅ |

## 📁 Project Structure

```
steam-library-verifier/
├── verify_steam_gui.py   # The entire application (single file)
├── README.md
├── LICENSE
└── .gitignore
```

## 🤝 Contributing

Contributions are welcome! This is an open-source project and PRs are encouraged. Some ideas:

- [ ] Export verification report (CSV/JSON)
- [ ] Remember excluded games between sessions
- [ ] System tray mode for background operation
- [ ] Notification when all games are done
- [ ] Filter/search bar for large libraries
- [ ] Packaging as a standalone `.exe` via PyInstaller

## 🤖 Credits

This project was built collaboratively by **Christopher** and **[Claude AI](https://claude.ai)** (by [Anthropic](https://www.anthropic.com)). The entire application — architecture, Steam integration logic, GUI design, and documentation — was developed through an iterative conversation between a human and an AI.

If you find this useful, consider starring the repo so others can find it too. The whole point was so nobody else has to burn tokens or time solving this same problem. 🙂

## 📄 License

MIT — free to use, modify, and distribute. See [LICENSE](LICENSE) for details.

---

*Built because nobody wants to right-click → Properties → Verify 200 games one at a time.*
