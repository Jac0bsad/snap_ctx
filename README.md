# snap_ctx

A lightweight CLI tool to automatically extract and copy context-aware code snippets from your project directory.

## Features

- Scans the current directory structure
- Identifies relevant code files based on user input
- Copies filtered context to clipboard (cross-platform support)
- Simple command invocation: `snap_ctx [query]`

## Installation

```bash
git clone https://github.com/Jac0bsad/snap_ctx.git
cd snap_ctx
```

create models.yaml under `config/`

```bash
uv build
uv tool install dist/snap_ctx-0.1.0-py3-none-any.whl
```

## Basic Usage

1. Navigate to your project root directory
2. Run:

   ```bash
   snap_ctx <your prompt>
   ```

3. Relevant code context is automatically copied to your clipboard

## License

pass
