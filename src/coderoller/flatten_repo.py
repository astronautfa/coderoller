import os
import sys
import shutil
import tempfile
import argparse
from typing import List, Dict, Set, Optional, Tuple, Any
from git import Repo
from coderoller.source_repo_flattener import flatten_repo, should_include_path, load_gitignore_patterns

# Rich library for terminal UI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich import box
from rich.table import Table
import pathspec

# Use prompt_toolkit instead of keyboard for interactive terminal UI
from prompt_toolkit import Application
from prompt_toolkit.layout.containers import HSplit, Window, VSplit, FloatContainer, Float
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style


def get_repo_name(input_path: str) -> str:
    """
    Infer the repository name from the input path or URL.

    Args:
        input_path (str): The path or URL of the repository.

    Returns:
        str: The inferred repository name.
    """
    if (
        input_path.startswith("http://")
        or input_path.startswith("https://")
        or input_path.startswith("git@")
    ):
        repo_name = os.path.basename(input_path).replace(".git", "")
    else:
        repo_name = os.path.basename(os.path.normpath(input_path))
    return repo_name


class InteractiveSelector:
    """
    Interactive file and directory selector for coderoller using prompt_toolkit.
    Allows users to navigate the file system and select/unselect items for flattening.
    """

    def __init__(self, root_folder: str):
        self.root_folder = root_folder
        self.console = Console()

        # Load gitignore patterns
        self.gitignore_patterns = load_gitignore_patterns(root_folder)
        self.spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern, self.gitignore_patterns
        )

        # Store file and directory structure
        self.paths: List[str] = []
        self.selected: Set[str] = set()  # Selected items
        self.cursor_position = 0
        # Maps paths to whether they are directories
        self.is_directory: Dict[str, bool] = {}
        self.confirmed = False
        self.cancelled = False

        # Scan root folder
        self._scan_folder()

        # Setup key bindings
        self.kb = KeyBindings()
        self._setup_keybindings()

        # Setup UI elements
        self.title_text = f"Coderoller Interactive Selection [{self.root_folder}]"
        self.item_window = Window(
            content=FormattedTextControl(self._get_formatted_items),
            style="class:main",
            wrap_lines=False,
            height=D(preferred=20),
            width=D(preferred=100),
        )

        self.status_text = f"Selected: {len(self.selected)}/{len(self.paths)} items"
        self.status_window = Window(
            content=FormattedTextControl(
                lambda: [("class:status", self.status_text)]),
            height=1,
            style="class:status",
        )

        self.help_window = Window(
            content=FormattedTextControl(lambda: [
                ("class:help", "↑/↓: Navigate | Space: Toggle | A: Select All | "
                 "U: Unselect All | Enter: Confirm | Esc: Cancel")
            ]),
            height=1,
            style="class:help",
        )

        # Container with title
        self.title_window = Window(
            content=FormattedTextControl(
                lambda: [("class:title", self.title_text)]),
            height=1,
            style="class:title",
        )

        # Main container
        self.container = FloatContainer(
            content=HSplit([
                self.title_window,
                self.item_window,
                self.status_window,
                self.help_window,
            ]),
            floats=[]
        )

        # Setup style
        self.style = Style.from_dict({
            'title': 'bg:darkblue fg:white bold',
            'main': '',
            'status': 'bg:darkgray fg:white',
            'help': 'bg:black fg:white',
            'cursor': 'reverse',
            'selected': 'fg:green',
            'dir': 'fg:blue bold',
            'file': 'fg:white',
        })

        # Create application
        self.application = Application(
            layout=Layout(self.container),
            key_bindings=self.kb,
            style=self.style,
            full_screen=True,
            mouse_support=True,
        )

    def _setup_keybindings(self) -> None:
        """Setup keybindings for the interactive selector."""

        @self.kb.add('up')
        def _(event):
            self.cursor_position = max(0, self.cursor_position - 1)

        @self.kb.add('down')
        def _(event):
            self.cursor_position = min(
                len(self.paths) - 1, self.cursor_position + 1)

        @self.kb.add('space')
        def _(event):
            if self.paths:
                path = self.paths[self.cursor_position]
                if path in self.selected:
                    self.selected.remove(path)
                else:
                    self.selected.add(path)
                self._update_status()

        @self.kb.add('a')
        def _(event):
            self.selected = set(self.paths)
            self._update_status()

        @self.kb.add('u')
        def _(event):
            self.selected.clear()
            self._update_status()

        @self.kb.add('enter')
        def _(event):
            self.confirmed = True
            event.app.exit()

        @self.kb.add('escape')
        def _(event):
            self.cancelled = True
            event.app.exit()

        @self.kb.add('c-c')
        def _(event):
            self.cancelled = True
            event.app.exit()

    def _update_status(self) -> None:
        """Update the status text."""
        self.status_text = f"Selected: {len(self.selected)}/{len(self.paths)} items"

    def _scan_folder(self) -> None:
        """Scan the root folder to collect all files and directories."""
        self.paths = []
        self.selected = set()
        self.is_directory = {}

        # Add all files and directories recursively
        for dirpath, dirnames, filenames in os.walk(self.root_folder):
            # Filter out paths based on gitignore
            dirnames[:] = [
                d for d in dirnames
                if should_include_path(os.path.join(dirpath, d), self.spec)
            ]
            filenames[:] = [
                f for f in filenames
                if should_include_path(os.path.join(dirpath, f), self.spec)
            ]

            # Add directories
            for dirname in dirnames:
                full_path = os.path.join(dirpath, dirname)
                rel_path = os.path.relpath(full_path, self.root_folder)
                self.paths.append(rel_path)
                self.is_directory[rel_path] = True
                self.selected.add(rel_path)  # Select by default

            # Add files
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, self.root_folder)
                self.paths.append(rel_path)
                self.is_directory[rel_path] = False
                self.selected.add(rel_path)  # Select by default

        # Sort paths for better navigation
        self.paths.sort()
        self._update_status()

    def _get_formatted_items(self) -> List[Tuple[str, str]]:
        """Get the formatted items for display."""
        result = []
        if not self.paths:
            result.append(("", "No files or directories found."))
            return result

        # Calculate visible range for pagination
        visible_items = 15
        start_idx = max(0, self.cursor_position - visible_items // 2)
        end_idx = min(len(self.paths), start_idx + visible_items)

        # Adjust start_idx if we're near the end
        if end_idx == len(self.paths):
            start_idx = max(0, end_idx - visible_items)

        # Add current position indicator
        for i in range(start_idx, end_idx):
            path = self.paths[i]
            is_selected = path in self.selected
            is_dir = self.is_directory[path]

            # Determine display style
            if i == self.cursor_position:
                style = "class:cursor"
            else:
                style = ""

            # Add checkbox and item type
            if is_selected:
                checkbox = "[✓] "
            else:
                checkbox = "[ ] "

            if is_dir:
                item_type = "[DIR] "
                path_style = "class:dir"
            else:
                item_type = "[FILE] "
                path_style = "class:file"

            if is_selected:
                checkbox_style = "class:selected"
            else:
                checkbox_style = ""

            # Combine styles
            if i == self.cursor_position:
                result.append((style, f" {checkbox}{item_type}{path}\n"))
            else:
                result.append((checkbox_style, f" {checkbox}"))
                result.append((path_style, f"{item_type}"))
                result.append(("", f"{path}\n"))

        return result

    def run(self) -> Tuple[bool, Set[str]]:
        """
        Run the interactive selector.

        Returns:
            Tuple[bool, Set[str]]: (success, selected_paths)
                success: True if the user confirmed the selection, False if canceled
                selected_paths: Set of selected file/directory paths
        """
        if not self.paths:
            self.console.print(
                "[yellow]No files or directories found to select![/yellow]")
            return False, set()

        try:
            # Run the application
            self.application.run()

            if self.confirmed:
                return True, self.selected
            else:
                return False, set()
        except Exception as e:
            self.console.print(f"[red]Error in interactive mode: {e}[/red]")
            return False, set()


def _get_selected_files(root_folder: str) -> Optional[Set[str]]:
    """
    Launch interactive mode to select files and directories.

    Args:
        root_folder (str): The root folder of the repository.

    Returns:
        Optional[Set[str]]: Set of selected paths or None if canceled
    """
    try:
        console = Console()
        console.print(
            "[bold blue]Entering interactive selection mode...[/bold blue]")

        selector = InteractiveSelector(root_folder)
        confirmed, selected = selector.run()

        if confirmed and selected:
            return selected
        elif confirmed and not selected:
            console.print("[yellow]Warning: No files were selected.[/yellow]")
            if Confirm.ask("Continue with empty selection?", default=False):
                return selected
            else:
                return None
        else:
            console.print("[yellow]Operation canceled by user.[/yellow]")
            return None
    except Exception as e:
        console = Console()
        console.print(f"[red]Error in interactive mode: {e}[/red]")

        # Fallback to simple selection mode if prompt_toolkit fails
        console.print(
            "[yellow]Falling back to simple selection mode...[/yellow]")
        return _fallback_simple_selection(root_folder)


def _fallback_simple_selection(root_folder: str) -> Optional[Set[str]]:
    """
    A simple fallback selection mode that doesn't use advanced UI libraries.

    Args:
        root_folder (str): The root folder of the repository.

    Returns:
        Optional[Set[str]]: Set of selected paths or None if canceled
    """
    console = Console()

    # Collect files and directories
    paths = []
    is_directory = {}

    # Load gitignore patterns
    gitignore_patterns = load_gitignore_patterns(root_folder)
    spec = pathspec.PathSpec.from_lines(
        pathspec.patterns.GitWildMatchPattern, gitignore_patterns
    )

    # Walk the filesystem
    for dirpath, dirnames, filenames in os.walk(root_folder):
        # Filter based on gitignore
        dirnames[:] = [
            d for d in dirnames
            if should_include_path(os.path.join(dirpath, d), spec)
        ]
        filenames[:] = [
            f for f in filenames
            if should_include_path(os.path.join(dirpath, f), spec)
        ]

        # Add directories
        for dirname in dirnames:
            full_path = os.path.join(dirpath, dirname)
            rel_path = os.path.relpath(full_path, root_folder)
            paths.append(rel_path)
            is_directory[rel_path] = True

        # Add files
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root_folder)
            paths.append(rel_path)
            is_directory[rel_path] = False

    # Sort paths
    paths.sort()

    if not paths:
        console.print(
            "[yellow]No files or directories found to select![/yellow]")
        return None

    # Display paths in a table
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("#", justify="right")
    table.add_column("Type", justify="center")
    table.add_column("Path")

    for i, path in enumerate(paths):
        is_dir = is_directory[path]
        table.add_row(
            str(i+1),
            "[blue][DIR][/blue]" if is_dir else "[green][FILE][/green]",
            path
        )

    console.print(table)

    # Ask for selection
    console.print("\nOptions:")
    console.print("  a - Select all (default)")
    console.print("  n - Select none")
    console.print("  s - Select specific items (comma-separated numbers)")
    console.print("  c - Cancel")

    choice = Prompt.ask("Choose an option", choices=[
                        "a", "n", "s", "c"], default="a")

    if choice == "a":
        # Select all
        return set(paths)
    elif choice == "n":
        # Select none
        return set()
    elif choice == "s":
        # Select specific items
        selection_input = Prompt.ask(
            "Enter numbers to select (comma-separated)")
        try:
            indices = [int(i.strip()) - 1 for i in selection_input.split(",")]
            selected = {paths[i] for i in indices if 0 <= i < len(paths)}
            return selected
        except ValueError:
            console.print("[red]Invalid input. Operation canceled.[/red]")
            return None
    else:
        # Cancel
        return None


def flatten_repo_interactive(
    root_folder: str,
    output_folder: str = None,
    repo_name: str = None,
    structure_only: bool = False
) -> None:
    """
    Flatten the source repository into a single markdown file with interactive selection.

    Args:
        root_folder (str): The root folder of the repository.
        output_folder (str | None): The folder to save the flattened file. Defaults to CWD.
        repo_name (str | None): The name of the repository.
        structure_only (bool): If True, only include folder structure without file contents.
    """
    console = Console()

    if repo_name is None:
        repo_name = os.path.basename(os.path.normpath(root_folder))
    if output_folder is None:
        output_folder = os.getcwd()

    # Get selected paths through interactive mode
    selected_paths = _get_selected_files(root_folder)

    if selected_paths is None:
        console.print("[yellow]Operation canceled by user.[/yellow]")
        return

    # Custom flatten implementation using selected paths
    from coderoller.source_repo_flattener import find_readme, FILE_TYPES

    flattened_file_path = os.path.join(output_folder, f"{repo_name}.flat.md")
    readme_path = find_readme(root_folder)

    # Collect specific dirs/files to be included
    console.print(
        f"[green]Processing {len(selected_paths)} selected items...[/green]")

    with open(flattened_file_path, "w") as flat_file:
        flat_file.write(f"# Contents of {repo_name} source tree\n\n")

        if structure_only:
            flat_file.write("## Folder Structure\n\n")
            flat_file.write("```\n")

            # Build the tree structure for selected items only
            tree = {}

            # Add directories to the tree
            for path in selected_paths:
                if os.path.isdir(os.path.join(root_folder, path)):
                    parts = path.split(os.sep)
                    current = tree
                    for part in parts:
                        if part not in current:
                            current[part] = {}
                        current = current[part]

            # Add files to the tree
            for path in selected_paths:
                if not os.path.isdir(os.path.join(root_folder, path)):
                    parts = path.split(os.sep)
                    filename = parts.pop()
                    current = tree

                    # Create parent directories if they don't exist
                    for part in parts:
                        if part not in current:
                            current[part] = {}
                        current = current[part]

                    # Add the file
                    current[filename] = None

            # Print tree function
            def print_tree(tree, prefix="", is_last=True, is_root=True):
                output = ""
                if is_root:
                    # This is the root node, process its children
                    keys = list(tree.keys())
                    for i, key in enumerate(keys):
                        is_last_item = i == len(keys) - 1
                        if tree[key] is None:  # It's a file
                            output += prefix + \
                                ("└── " if is_last_item else "├── ") + key + "\n"
                        else:  # It's a directory
                            output += prefix + \
                                ("└── " if is_last_item else "├── ") + key + "\n"
                            next_prefix = prefix + \
                                ("    " if is_last_item else "│   ")
                            output += print_tree(tree[key],
                                                 next_prefix, True, False)
                else:
                    # This is not root, process all items
                    keys = list(tree.keys())
                    for i, key in enumerate(keys):
                        is_last_item = i == len(keys) - 1
                        if tree[key] is None:  # It's a file
                            output += prefix + \
                                ("└── " if is_last_item else "├── ") + key + "\n"
                        else:  # It's a directory
                            output += prefix + \
                                ("└── " if is_last_item else "├── ") + key + "\n"
                            next_prefix = prefix + \
                                ("    " if is_last_item else "│   ")
                            output += print_tree(tree[key],
                                                 next_prefix, True, False)

                return output

            # Write the tree structure
            flat_file.write(print_tree(tree))
            flat_file.write("```\n")
            console.print(
                f"[green]Included folder structure only (interactive selection)[/green]")

        else:
            # Handle README file if included in selection
            readme_rel_path = os.path.relpath(
                readme_path, root_folder) if readme_path else None
            if readme_path and readme_rel_path in selected_paths:
                with open(readme_path, "r") as readme_file:
                    try:
                        readme_contents = readme_file.read()
                        flat_file.write("## README\n\n")
                        flat_file.write("```markdown\n")
                        flat_file.write(readme_contents)
                        flat_file.write("\n```\n\n")
                        console.print(
                            f"[green]Included README file: {readme_path}[/green]")
                    except UnicodeDecodeError:
                        console.print(
                            f"[yellow]Warning: README file contains binary data and was skipped.[/yellow]")

            # Process all selected files
            for path in selected_paths:
                full_path = os.path.join(root_folder, path)
                if os.path.isfile(full_path) and full_path != readme_path:
                    extension = os.path.splitext(path)[1]
                    if extension in FILE_TYPES:
                        try:
                            with open(full_path, "r") as file:
                                try:
                                    file_contents = file.read()
                                    flat_file.write(f"## File: {path}\n\n")
                                    flat_file.write(
                                        f"```{FILE_TYPES[extension]}\n")
                                    flat_file.write(file_contents)
                                    flat_file.write("\n```\n\n")
                                    console.print(
                                        f"[green]Included file: {path}[/green]")
                                except UnicodeDecodeError:
                                    console.print(
                                        f"[yellow]Skipping binary file: {path}[/yellow]")
                        except Exception as e:
                            console.print(
                                f"[yellow]Error reading file {path}: {e}[/yellow]")

    console.print(
        f"[bold green]Flattening complete. Output saved to {flattened_file_path}[/bold green]")


def main():
    parser = argparse.ArgumentParser(
        description="Flatten a repository into a single markdown file.")
    parser.add_argument("input_path", help="Path to the repository or Git URL")
    parser.add_argument("--structure-only", action="store_true",
                        help="Only include folder structure without file contents")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Use interactive mode to select files and directories")
    args = parser.parse_args()

    input_path = args.input_path
    structure_only = args.structure_only
    interactive_mode = args.interactive
    repo_name = get_repo_name(input_path)
    console = Console()

    # Check if the input is a Git URL
    if (
        input_path.startswith("http://")
        or input_path.startswith("https://")
        or input_path.startswith("git@")
    ):
        # Clone the repository to a temporary directory
        temp_dir = tempfile.mkdtemp()
        try:
            console.print(
                f"[green]Cloning repository from {input_path} to {temp_dir}[/green]")
            Repo.clone_from(input_path, temp_dir)

            if interactive_mode:
                flatten_repo_interactive(
                    temp_dir, repo_name=repo_name, structure_only=structure_only)
            else:
                flatten_repo(temp_dir, repo_name=repo_name,
                             structure_only=structure_only)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
        finally:
            # Clean up the temporary directory
            shutil.rmtree(temp_dir)
            console.print(
                f"[green]Deleted temporary directory {temp_dir}[/green]")
    else:
        try:
            if interactive_mode:
                flatten_repo_interactive(
                    input_path, repo_name=repo_name, structure_only=structure_only)
            else:
                flatten_repo(input_path, repo_name=repo_name,
                             structure_only=structure_only)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
