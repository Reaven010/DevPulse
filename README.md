# DevPulse

DevPulse is a system monitoring and developer dashboard framework powered by Python, Lua, and Conky.

## Project Structure

```
devpulse/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── workflows/
│   ├── pull_request_template.md
│   └── FUNDING.yml
├── docs/           - Project documentation & guides
├── config/         - Configuration files & templates
├── cache/          - Local data cache
├── resources/      - Media, icons, wallpapers & screenshots
├── themes/         - Color palettes & visual themes
├── conky/          - Conky configurations & renderer modules
├── widgets/        - Desktop widget implementations (GitHub, LeetCode, Weather, System, etc.)
├── src/            - Core Python services & API integration modules
├── daemon/         - Service daemon, dispatcher & background monitor
├── systemd/        - Systemd service & timer configurations
├── install/        - Modular installer & setup scripts
├── tests/          - Test suite
├── tools/          - Theme generation & development tools
├── .editorconfig
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── requirements.txt
├── pyproject.toml
└── Makefile
```

## Quick Start

Run the installer:
```bash
./install/install.sh
```

Or run directly:
```bash
python3 src/main.py
```
