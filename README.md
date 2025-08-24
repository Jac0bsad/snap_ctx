# snap_ctx

A lightweight CLI tool to automatically extract and copy context-aware code snippets from your project directory.

## Features

- Scans the current directory structure
- Identifies relevant code files based on user input
- Copies filtered context to clipboard (cross-platform support)
- Simple command invocation: `snap_ctx [query]`

## Installation

```bash
pip install snap_ctx
```

## Basic Usage

1. Navigate to your project root directory
2. Run:

   ```bash
   snap_ctx "your prompt"
   ```

3. Relevant code context is automatically copied to your clipboard

## Development Setup

```bash
git clone https://github.com/your_username/snap_ctx.git
cd snap_ctx
uv sync
```

## License

pass
