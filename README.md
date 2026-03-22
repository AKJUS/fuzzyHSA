# fuzzyHSA

KFD/GPU Firmware Fuzzer for AMD GPUs.

## Quick Start

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/amd/fuzzyHSA.git
cd fuzzyHSA

# Install dependencies and generate bindings
uv sync
uv run python generate_bindings.py

# Run the fuzzer
uv run fuzzyHSA fuzz -n 100 -v
```

## Requirements

- Linux with AMD GPU (KFD driver)
- Python 3.10+
- Linux kernel headers (for binding generation)

## Usage

```bash
# List available operations
uv run fuzzyHSA list-targets

# Fuzz for 1000 iterations
uv run fuzzyHSA fuzz -n 1000

# Fuzz specific operations
uv run fuzzyHSA fuzz --operations alloc_memory_of_gpu,create_queue

# Reproduce a crash
uv run fuzzyHSA reproduce crashes/crash_20240321_123456.json

# Show system info
uv run fuzzyHSA info
```

## Development

```bash
# Install with dev dependencies
uv sync

# Run tests
uv run pytest

# Run linter
uv run ruff check src/

# Regenerate bindings after kernel update
uv run python generate_bindings.py
```

## Project Structure

```
src/fuzzyHSA/
├── kfd/           # KFD driver interface
│   ├── device.py  # Device discovery
│   ├── ioctl.py   # IOCTL execution
│   ├── memory.py  # GPU memory management
│   └── autogen/   # Generated bindings
├── fuzz/          # Fuzzing framework
│   ├── mutators.py
│   ├── harness.py
│   └── targets/
├── monitor/       # Crash detection (dmesg)
├── logging/       # Crash logging (JSON)
└── cli.py         # Command-line interface
```

## Acknowledgments

This project thanks [tinycorp](https://tinygrad.org/) for their efforts pushing boundaries. Check out [tinygrad](https://github.com/tinygrad/tinygrad)!

## License

Apache 2.0 License. See [LICENSE](LICENSE).
