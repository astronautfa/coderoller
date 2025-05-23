# Coderoller

![Coderoller banner](https://raw.githubusercontent.com/btfranklin/coderoller/main/.github/social%20preview/coderoller_social_preview.jpg "Coderoller")

[![Build Status](https://github.com/btfranklin/coderoller/actions/workflows/python-package.yml/badge.svg)](https://github.com/btfranklin/coderoller/actions/workflows/python-package.yml) [![Supports Python versions 3.10+](https://img.shields.io/pypi/pyversions/coderoller.svg)](https://pypi.python.org/pypi/coderoller)

Coderoller is a Python utility that flattens a source code repository into a single markdown file. This tool collects all relevant source and configuration files, including Python, JavaScript, TypeScript, HTML, CSS, JSON, and more, and compiles them into a markdown document. The flattened file provides an organized overview of the repository's contents, making it easy to use in conjunction with LLMs. Simply copy the contents of the flattened file and paste it into your LLM chat context. The flattened form is also great for API-based uses of LLMs in automated workflows.

## Features

- **Flattens source code repositories** into a single markdown file.
- **Supports multiple file types** including `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.swift`, `.go`, `.java`, `.c`, `.cpp`, `.h`, `.hpp`, `.cs`, `.lua`, `.rb`, `.php`, `.pl`, `.html`, `.css`, `.json`, `.toml`, `.md`, `.yaml`, `.yml`, `.conf`, `.ini`, and `.sh`.
- **Interactive mode** for selecting specific files and directories to include in the flattened output.
- **Automatically includes README** files if present, placing it at the start of the flattened file.
- **Excludes hidden files and directories** (those starting with a dot), specific directories (`build`, `dist`, `node_modules`, `__pycache__`), specific files (lockfiles, hidden files, other flattened files, etc.), and any paths specified in `.gitignore`.
- **Supports flattening directly from Git URLs** even if the repository is not cloned locally.
- **Provides a structure-only option** that shows just the folder structure without file contents.

## Installation

Coderoller requires Python 3.10 or later.

### Using pipx

You can install Coderoller globally using pipx:

```bash
pipx install coderoller
```

## Usage

To flatten a source repository, use the `coderoller-flatten-repo` script.

```bash
coderoller-flatten-repo /path/to/reponame
```

To flatten a source repository directly from a Git URL, use the coderoller-flatten-repo script with the repository URL:

```bash
coderoller-flatten-repo https://github.com/username/reponame.git
```

To show only the folder structure without file contents:

```bash
coderoller-flatten-repo /path/to/reponame --structure-only
```

To use the interactive mode for selecting which files and directories to include:

```bash
coderoller-flatten-repo /path/to/reponame --interactive
# or use the short form
coderoller-flatten-repo /path/to/reponame -i
```

When using interactive mode, you'll be presented with a list of all files and directories in the repository. You can navigate through them with the arrow keys and select/deselect items using the space bar. All items are selected by default.

### Interactive Mode Controls

- **↑/↓**: Navigate up and down through the file list
- **Space**: Toggle selection of the current item
- **A**: Select all items
- **U**: Unselect all items
- **Enter**: Confirm your selection and proceed with flattening
- **Esc**: Cancel and exit

These commands will create a markdown file named `reponame.flat.md` in the current working directory, containing the flattened contents of the repository.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
