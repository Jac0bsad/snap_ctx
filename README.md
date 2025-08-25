# snap_ctx

A lightweight CLI tool to automatically extract and copy context-aware code snippets from your project directory.

## Features

- Scans the current directory structure
- Identifies relevant code files based on user input
- Copies filtered context to clipboard (cross-platform support)
- Simple command invocation: `snap-ctx [query]`

## Installation

```bash
pip install snap-ctx
snap-ctx --init
```

## Basic Usage

1. Navigate to your project root directory
2. Run:

   ```bash
   snap-ctx query
   ```

3. Relevant code context is automatically copied to your clipboard

## Development Setup

```bash
git clone https://github.com/Jac0bsad/snap_ctx.git
cd snap-ctx
uv sync
```

create models.yaml under `config`

## License

MIT
