# Always On Top Utility (Windows)

A lightweight Windows utility written in Python that allows you to toggle the "Always On Top" state of any window using customizable hotkeys.

This tool was originally prototyped using AutoHotkey (AHK), but was re-implemented in Python to improve compatibility and reduce false-positive security flagging in certain environments.

---

## Features

- Toggle Always On Top for any window
- Tooltip status indicator on single toggle
- Double-click toggle to change window state
- Customizable keybinds
- Clean shutdown behavior
- No elevated/admin permissions required

---

## Default Keybinds

- `Ctrl + Alt + MB4` — Toggle (Mouse Button 4)
- `Ctrl + Alt + MB5` — Toggle (Mouse Button 5)
- `Ctrl + Alt + K` — Open keybind settings

---

## How It Works

- A **single toggle press** displays a tooltip showing the current Always On Top status of the window under your mouse cursor.
- A **double toggle press** switches the window between:
  - Always On Top
  - Normal window behavior

All windows modified by this utility will automatically lose their Always On Top status when the program exits.

---

## Technical Details

- Built with Python 3
- Uses Windows API calls
- Lightweight background process
- No external installer required

---

## Usage

1. Install Python 3 (if not already installed)
2. Run:

The program runs in the background and listens for hotkeys.

---

## Disclaimer

This utility is intended for productivity and window management purposes only.
