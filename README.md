MikroTik Script Manager 🌐✨
A beautiful Python GUI for managing RouterOS scripts

https://screenshot.png
(Light and dark mode shown side-by-side)

🚀 Key Features
Feature	Description
Syntax-Highlighted Editor	Write scripts with RouterOS-specific highlighting. ▶️ Demo
Smart Variables	Replace placeholders via forms (e.g., {ip-address} → GUI input).
Project Templates	Save script collections as reusable templates.
GitHub Sync	Import/export scripts directly to GitHub repositories.
Cross-Platform	Windows, macOS, and Linux support.
📦 Quick Start
Requirements
Python 3.6+

PyQt5

bash
# Clone & run
git clone https://github.com/NorthFi/mikrotik-script-manager-py.git
cd mikrotik-script-manager-py
pip install -r requirements.txt
python src/main.py
Tip: For a portable version, see Releases for pre-built binaries.

🖼️ UI Showcase
Light Mode	Dark Mode
https://light-ui.png	https://dark-ui.png
(Hover animations? Add a GIF showing theme switching!)

🛠️ Built With
PyQt5 – Modern GUI framework

QScintilla – Syntax highlighting engine

PyRouterOS – MikroTik API integration

🤝 Contributing
Fork → git checkout -b feature/your-idea

Test changes: pytest tests/

Submit a PR!

Before major changes, open an issue to discuss.

📜 License
MIT © Daniel
https://img.shields.io/badge/License-MIT-blue.svg
