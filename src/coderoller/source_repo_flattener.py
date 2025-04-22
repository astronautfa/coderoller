import os
import pathspec

# Dictionary mapping file extensions to their corresponding long form names
FILE_TYPES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".swift": "swift",
    ".go": "go",
    ".java": "java",
    ".c": "c",
    ".cpp": "c++",
    ".h": "c",
    ".hpp": "c++",
    ".cs": "csharp",
    ".lua": "lua",
    ".rb": "ruby",
    ".php": "php",
    ".pl": "perl",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".conf": "config",
    ".ini": "ini",
    ".sh": "shell",
}


def load_gitignore_patterns(root_folder: str) -> list[str]:
    """
    Load .gitignore patterns from the root folder.

    Args:
        root_folder (str): The root folder of the repository.

    Returns:
        list[str]: A list of patterns from the .gitignore file.
    """
    gitignore_path = os.path.join(root_folder, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            patterns = f.read().splitlines()
        return patterns
    return []


def should_include_path(file_path: str, spec: pathspec.PathSpec) -> bool:
    """
    Determine if a path should be included based on .gitignore patterns and specific exclusions.

    Args:
        file_path (str): The path of the file or directory to check.
        spec (pathspec.PathSpec): The PathSpec object containing the .gitignore patterns.

    Returns:
        bool: True if the path should be included, False otherwise.
    """
    # Specific exclusions
    specific_exclusions = [
        "build",
        "dist",
        "node_modules",
        "__pycache__",
        ".flat.md",
        ".lock",
        "-lock.json",
        ".hidden",
    ]

    # Check if the file or directory matches specific exclusions
    if any(exclusion in file_path for exclusion in specific_exclusions):
        return False

    # Check against .gitignore patterns
    return not spec.match_file(file_path)


def find_readme(root_folder: str) -> str:
    """
    Find a README file in the root folder with any common README extension.

    Args:
        root_folder (str): The root folder to search in.

    Returns:
        str: The path to the README file if found, else an empty string.
    """
    for filename in os.listdir(root_folder):
        if filename.lower().startswith("readme"):
            return os.path.join(root_folder, filename)
    return ""


def flatten_repo(
    root_folder: str, output_folder: str = None, repo_name: str = None, structure_only: bool = False
) -> None:
    """
    Flatten the source repository into a single markdown file.

    Args:
        root_folder (str): The root folder of the repository.
        output_folder (str | None): The folder to save the flattened file. Defaults to the current working directory.
        repo_name (str | None): The name of the repository.
        structure_only (bool): If True, only include folder structure without file contents.
    """
    if repo_name is None:
        repo_name = os.path.basename(os.path.normpath(root_folder))
    if output_folder is None:
        output_folder = os.getcwd()
    flattened_file_path = os.path.join(output_folder, f"{repo_name}.flat.md")

    readme_path = find_readme(root_folder)

    with open(flattened_file_path, "w") as flat_file:
        flat_file.write(f"# Contents of {repo_name} source tree\n\n")

        if structure_only:
            flat_file.write("## Folder Structure\n\n")
            flat_file.write("```\n")

        # Handle README file
        if readme_path and not structure_only:
            with open(readme_path, "r") as readme_file:
                readme_contents = readme_file.read()
                flat_file.write("## README\n\n")
                flat_file.write("```markdown\n")
                flat_file.write(readme_contents)
                flat_file.write("\n```\n\n")
                print(f"Included README file: {readme_path}")

        # Collect patterns from .gitignore
        gitignore_patterns = load_gitignore_patterns(root_folder)
        spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern, gitignore_patterns
        )

        # For structure-only mode, build a tree representation
        if structure_only:
            tree = {}

            for dirpath, dirnames, filenames in os.walk(root_folder):
                # Exclude directories and files matching .gitignore patterns and specific exclusions
                dirnames[:] = [
                    d
                    for d in dirnames
                    if should_include_path(os.path.join(dirpath, d), spec)
                ]
                filenames[:] = [
                    f
                    for f in filenames
                    if should_include_path(os.path.join(dirpath, f), spec)
                ]

                # Skip the root folder in the output
                if dirpath == root_folder:
                    continue

                # Create relative path
                rel_path = os.path.relpath(dirpath, root_folder)
                if rel_path == ".":
                    continue

                # Add directories to the tree
                current_level = tree
                for part in rel_path.split(os.sep):
                    if part not in current_level:
                        current_level[part] = {}
                    current_level = current_level[part]

                # Add files to the current directory level
                for filename in filenames:
                    current_level[filename] = None

            # Print the tree structure
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

            # Add files from root directory
            root_files = [
                f
                for f in os.listdir(root_folder)
                if os.path.isfile(os.path.join(root_folder, f))
                and should_include_path(os.path.join(root_folder, f), spec)
            ]

            # Create root tree with directories and files
            root_tree = {}
            # Add all directories first
            for key in tree:
                root_tree[key] = tree[key]
            # Add root files
            for file in root_files:
                root_tree[file] = None

            # Print the tree
            flat_file.write(print_tree(root_tree))
            flat_file.write("```\n")
            print(f"Included folder structure only")

        else:
            # Original file content mode
            for dirpath, dirnames, filenames in os.walk(root_folder):
                # Exclude directories and files matching .gitignore patterns and specific exclusions
                dirnames[:] = [
                    d
                    for d in dirnames
                    if should_include_path(os.path.join(dirpath, d), spec)
                ]
                filenames[:] = [
                    f
                    for f in filenames
                    if should_include_path(os.path.join(dirpath, f), spec)
                ]

                for filename in filenames:
                    extension = os.path.splitext(filename)[1]
                    full_path = os.path.join(dirpath, filename)
                    if extension in FILE_TYPES and full_path != readme_path:
                        with open(full_path, "r") as file:
                            file_contents = file.read()
                            relative_path = os.path.relpath(
                                full_path, root_folder)
                            flat_file.write(f"## File: {relative_path}\n\n")
                            flat_file.write(f"```{FILE_TYPES[extension]}\n")
                            flat_file.write(file_contents)
                            flat_file.write("\n```\n\n")
                            print(f"Included file: {full_path}")

    print(f"Flattening complete. Output saved to {flattened_file_path}")
