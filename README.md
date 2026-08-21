# 🌐 Fibrowser Pro – Python Web Browser with PyQt5 🚀

Fibrowser Pro is a sleek, modern, and feature-rich desktop **web browser** built with **Python**, **PyQt5**, and **PyQtWebEngine**. It comes packed with multi-tab browsing, isolated private mode, full theme support (Light, Dark, Blue, Nord, Dracula), Web Dark Mode, bookmark manager with undo/redo, real-time download manager, developer console, and robust error recovery.

---

## 🎯 Features

- 🌍 **Multi-Tabbed Browsing**: Fluid tab management with throttling, closed-tab restore stack, and maximum safety limits.
- 🔒 **Isolated Private Mode**: Strict in-memory session isolation (`MemoryHttpCache`, `NoPersistentCookies`) preventing disk leaks.
- 🎨 **Rich Theme Support**: Dark, Light, Blue, Nord, and Dracula themes with live preview and custom styling.
- 🌓 **Web Dark Mode**: Intelligent smart contrast script injection for dark web reading without inverted images/media.
- 🔍 **Smart Search Engine Switcher**: Quick switching between Google, Bing, DuckDuckGo, YouTube, and Wikipedia.
- 📥 **Real-Time Download Manager**: Accurate speed metrics in KB/s and MB/s, ETA estimation, folder navigation, and error handling.
- ⭐ **Organized Bookmarks Toolbar**: Sorted bookmark entries, right-click context menu, and full Undo/Redo stack.
- 📜 **Searchable History**: Fast indexed filtering, individual item removal, and debounced disk persistence.
- 🛡️ **Security & Validation**: Local filesystem path safety checking (protecting sensitive OS files) and sanitization.
- 🧰 **Developer Console & DevTools**: Integrated QWebEngine developer console and status/action logger.

---

## 📦 Project Structure

```text
Fibrowser/
├── assets/                  # Icons and visual assets
│   └── icons/
├── fibrowser/               # Core application package
│   ├── config.py            # Themes, dimensions, and path security
│   ├── main.py              # Application runner and global error hook
│   ├── core/                # Web engine integration
│   │   └── page.py          # BrowserPage with SSL & fullscreen handlers
│   └── ui/                  # UI components and dialogs
│       ├── window.py        # MainWindow coordinator
│       ├── tab.py           # Tab component
│       ├── widgets.py       # AnimatedButton & ToastNotification
│       ├── downloads.py     # DownloadManager & progress tracking
│       ├── shortcut_manager.py # Centralized keyboard shortcut manager
│       ├── theme_manager.py    # Dynamic stylesheet generator
│       └── dialogs/
│           ├── settings_dialog.py # Preferences and cache controls
│           └── history_dialog.py  # Searchable history manager
├── tests/                   # Automated unit test suite
│   ├── test_config.py
│   ├── test_downloads.py
│   ├── test_page_security.py
│   ├── test_shortcuts.py
│   ├── test_theme.py
│   └── test_window_core.py
├── .env.example             # Environment configuration template
├── main.py                  # Root entry point wrapper
├── pyproject.toml           # PEP 517/518 build definition
└── requirements.txt         # Runtime dependencies
```

---

## 🚀 Getting Started

### ✅ Prerequisites

- Python 3.8+
- pip

### 📦 Install Dependencies

```bash
pip install PyQt5 PyQtWebEngine
```

### ▶️ Run the App

```bash
python main.py
```

### 🧪 Run Automated Tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl + T` | New Tab |
| `Ctrl + W` | Close Tab |
| `Ctrl + Tab` | Next Tab |
| `Ctrl + Shift + Tab` | Previous Tab |
| `Ctrl + Shift + T` | Reopen Closed Tab |
| `Ctrl + L` | Focus URL / Address Bar |
| `F5` | Refresh Page |
| `Ctrl + Shift + R` | Hard Refresh (Bypass Cache) |
| `Ctrl + H` | Open Browsing History |
| `Ctrl + B` | Toggle Bookmarks Toolbar |
| `Ctrl + J` | Open Downloads Manager |
| `Ctrl + Shift + P` | Toggle Private Browsing Mode |
| `Ctrl + F` | Find in Page |
| `F11` | Toggle Fullscreen |
| `F12` | Toggle Developer Tools |
| `Ctrl + =` / `Ctrl + -` | Zoom In / Zoom Out |
| `Ctrl + 0` | Reset Zoom (100%) |
| `Ctrl + Z` | Undo Bookmark Action |

---

## 🎨 Theme Support

Choose from 5 curated themes:
- **Dark** (Default)
- **Light**
- **Blue**
- **Nord**
- **Dracula**

Switch themes in **Settings (⚙️)** with live preview, or right-click any empty area of the window.

---

## 🧾 License

This project is open-source and available under the **MIT License**.
