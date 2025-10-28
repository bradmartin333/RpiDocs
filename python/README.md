# WIZ Lights Control

A Python package for discovering and controlling WIZ smart lights on your local network.

## Features

- **Network Discovery**: Automatically discover WIZ lights on your network (no broadcasts)
- **13 Control Modes**: Including rainbow effects, themed effects, and nature simulations
- **Interactive TUI**: Arrow-key navigation menu for easy control selection
- **Modular Design**: Clean separation of concerns across multiple modules
- **Configuration**: Persistent configuration and device caching

## Installation

Using `uv` (recommended):

```bash
cd python
uv sync
```

With optional audio support for reactive mode:

```bash
uv sync --extra audio
```

## Usage

Run the application:

```bash
uv run wiz-lights
```

Or using Python module:

```bash
python -m wiz_lights
```

## Control Modes

### 🌈 Rainbow Controls
- **rainbow_in_unison**: All lights cycle through colors together
- **rainbow**: Lights cycle colors with offsets
- **party**: Random colorful flashing
- **fungi**: Psychedelic funky animation

### 🎃 Themed Controls
- **spooky**: Halloween orange/purple flickers
- **seasonal**: Colors based on current season
- **danger**: Scary red strobe alarm

### ⛈️ Nature Controls
- **lightning**: Stormy skies with lightning
- **waterfall**: Flowing blues and white

### 🎵 Interactive
- **reactive**: Responds to microphone audio (requires PyAudio)
- **synth**: Flash colors with number keys

### ⚙️ Utilities
- **white**: Set to white color temperature
- **rgba**: Set custom RGBA color

## Project Structure

```
python/
├── pyproject.toml          # Project configuration (uv)
├── .python-version         # Python version specification
└── src/
    └── wiz_lights/
        ├── __init__.py     # Package initialization
        ├── __main__.py     # Main entry point
        ├── config.py       # Configuration and caching
        ├── network.py      # Network discovery and communication
        ├── colors.py       # Color conversion utilities
        ├── controls.py     # Control mode implementations
        └── ui.py           # User interface functions
```

## Module Overview

### config.py
Handles configuration file management and caching of discovered devices.

### network.py
Network communication including:
- IP range scanning
- UDP communication with WIZ bulbs
- Color setting commands

### colors.py
Color space conversion utilities:
- HSV to RGB conversion
- Kelvin temperature to RGB conversion

### controls.py
All 13 control mode implementations. Each mode is a function that can:
- Run continuously until stopped
- Respond to stop events
- Handle threading for background operation

### ui.py
User interface functions:
- Device selection menus
- Interactive TUI with arrow-key navigation
- Input prompts for configuration

### __main__.py
Main application loop that:
- Discovers devices
- Presents menu interface
- Manages control mode execution
- Handles mode switching

## Development

The project uses `uv` for dependency management and virtual environments.

### Running Tests

```bash
uv run python -m pytest
```

### Type Checking

```bash
uv run mypy src/wiz_lights
```

## Dependencies

- Python >= 3.12
- No required dependencies (uses standard library)
- Optional: PyAudio for reactive mode

## Configuration

Configuration is stored in `config.json` in the same directory as the package.
Default configuration:

```json
{
  "base_ip": "192.168.1"
}
```

Discovered devices are cached in `wiz_bulb_cache.json` for faster startup.

## License

This project is part of the RpiDocs repository.
