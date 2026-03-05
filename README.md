# satctl

**Terminal-native satellite OSINT tool for tracking and analyzing satellite positions.**

satctl is a terminal-based satellite intelligence tool that allows users to track, inspect, and analyze satellite positions using publicly available orbital data. The entire experience occurs inside the terminal, with a btop-style interactive interface for exploration and analysis.

## Features

- **Terminal-first UX**: Pure CLI/TUI experience, no web interfaces
- **Local processing**: All satellite calculations performed locally using SGP4
- **Interactive TUI**: btop-style dashboard with real-time satellite positions
- **Multiple filters**: Filter by orbit type (LEO/MEO/GEO), region, and more
- **CelesTrak integration**: Download latest TLE data from public catalogs
- **SQLite storage**: Efficient local database for satellite catalog

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/satctl/satctl.git
cd satctl

# Install dependencies
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Prerequisites

- Python 3.11 or higher
- SQLite3

## Quick Start

```bash
# Initialize the database
satctl init

# Download satellite catalog
satctl sync

# Check status
satctl status

# Launch interactive dashboard
satctl tui

# Search for satellites
satctl search "starlink"

# Get current position of a specific satellite
satctl now --id 25544
```

## Run Locally (Step-by-Step)

Follow these exact steps to run `satctl` on your machine.

1. **Clone the repo and enter it**

   ```bash
   git clone https://github.com/satctl/satctl.git
   cd satctl
   ```

2. **Create and activate a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the project in editable mode**

   ```bash
   pip install -e .
   ```

   For development tools and tests:

   ```bash
   pip install -e ".[dev]"
   ```

4. **Initialize local data**

   ```bash
   satctl init
   ```

5. **Download a satellite catalog**

   ```bash
   satctl sync
   ```

6. **Verify it is working**

   ```bash
   satctl status
   satctl search "ISS"
   satctl now --id 25544
   ```

7. **Launch the interactive dashboard (optional)**

   ```bash
   satctl tui
   ```

### Optional: Use a custom data directory

By default, satctl stores data in `~/.local/share/satctl/`. To override this:

```bash
export SATCTL_DATA_DIR=/path/to/satctl-data
```

Then run `satctl init` again to initialize that location.

## Usage

### Commands

| Command | Description |
|---------|-------------|
| `satctl init` | Initialize database and directories |
| `satctl sync` | Download latest TLE data from CelesTrak |
| `satctl status` | Show catalog information |
| `satctl search "query"` | Search satellites by name |
| `satctl now --id <NORAD>` | Show current position |
| `satctl tui` | Launch interactive dashboard |

### TUI Controls

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh positions |
| `s` | Sync catalog |
| `/` | Search |
| `g` | Cycle group filter |
| `o` | Cycle orbit filter |
| `m` | Cycle region mode |
| `?` | Show help |

## Configuration

satctl stores data in `~/.local/share/satctl/` by default.

You can customize the data directory:

```bash
export SATCTL_DATA_DIR=/path/to/data
```

## Data Sources

satctl uses [CelesTrak](https://celestrak.org/) public TLE catalogs:

- Active satellites
- Space stations
- Weather satellites
- GPS constellation
- GLONASS constellation
- Galileo constellation
- And more...

## Architecture

satctl is built with:

- **Python 3.11+**: Core language
- **Textual**: TUI framework
- **SQLAlchemy**: Database ORM
- **sgp4**: Orbital propagation
- **httpx**: HTTP client for downloads
- **Click**: CLI framework

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Disclaimer

satctl is provided for educational and research purposes. It uses only publicly available satellite orbital data and is not intended for any military or harmful applications.

---

**satctl** - Terminal-native satellite OSINT tool
