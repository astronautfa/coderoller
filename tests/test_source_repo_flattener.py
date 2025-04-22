import os
import tempfile
import shutil
from unittest.mock import patch
from git import Repo
from coderoller.source_repo_flattener import flatten_repo
from coderoller.flatten_repo import main


def test_flatten_repo():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock repository structure
        os.makedirs(os.path.join(temp_dir, "src"))

        readme_content = "# This is the README"
        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write(readme_content)

        python_content = 'print("Hello, World!")'
        with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
            f.write(python_content)

        json_content = '{"key": "value"}'
        with open(os.path.join(temp_dir, "config.json"), "w") as f:
            f.write(json_content)

        output_dir = tempfile.mkdtemp()
        flatten_repo(temp_dir, output_dir)

        # Check if the flattened file is created
        flattened_file_path = os.path.join(
            output_dir, f"{os.path.basename(temp_dir)}.flat.md"
        )
        assert os.path.exists(
            flattened_file_path), "Flattened file was not created"

        with open(flattened_file_path, "r") as f:
            flattened_content = f.read()

        # Check if the README content is included
        assert "## README" in flattened_content, "README section is missing"
        assert (
            "```markdown" in flattened_content
        ), "README content is not properly formatted"
        assert readme_content in flattened_content, "README content is incorrect"

        # Check if the Python file content is included
        assert (
            "## File: src/main.py" in flattened_content
        ), "Python file section is missing"
        assert (
            "```python" in flattened_content
        ), "Python content is not properly formatted"
        assert python_content in flattened_content, "Python content is incorrect"

        # Check if the JSON file content is included
        assert (
            "## File: config.json" in flattened_content
        ), "JSON file section is missing"
        assert "```json" in flattened_content, "JSON content is not properly formatted"
        assert json_content in flattened_content, "JSON content is incorrect"


def test_flatten_repo_structure_only():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock repository structure
        os.makedirs(os.path.join(temp_dir, "src"))
        os.makedirs(os.path.join(temp_dir, "docs"))

        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write("# This is the README")

        with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
            f.write('print("Hello, World!")')

        with open(os.path.join(temp_dir, "config.json"), "w") as f:
            f.write('{"key": "value"}')

        with open(os.path.join(temp_dir, "docs", "guide.md"), "w") as f:
            f.write('# User Guide')

        output_dir = tempfile.mkdtemp()
        flatten_repo(temp_dir, output_dir, structure_only=True)

        # Check if the flattened file is created
        flattened_file_path = os.path.join(
            output_dir, f"{os.path.basename(temp_dir)}.flat.md"
        )
        assert os.path.exists(
            flattened_file_path), "Flattened file was not created"

        with open(flattened_file_path, "r") as f:
            flattened_content = f.read()

        # Check if the structure is included
        assert "## Folder Structure" in flattened_content, "Folder structure section is missing"
        assert "src" in flattened_content, "Source directory is missing in structure"
        assert "docs" in flattened_content, "Docs directory is missing in structure"
        assert "main.py" in flattened_content, "Python file is missing in structure"
        assert "guide.md" in flattened_content, "Markdown file is missing in structure"

        # Make sure file contents are not included
        assert 'print("Hello, World!")' not in flattened_content, "File content should not be included"
        assert "# User Guide" not in flattened_content, "File content should not be included"


def test_hidden_files_and_directories():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a hidden directory and file
        os.makedirs(os.path.join(temp_dir, ".hidden_dir"))
        with open(os.path.join(temp_dir, ".hidden_file.py"), "w") as f:
            f.write('print("This should not be included")')

        output_dir = tempfile.mkdtemp()
        flatten_repo(temp_dir, output_dir)

        # Check if the flattened file is created
        flattened_file_path = os.path.join(
            output_dir, f"{os.path.basename(temp_dir)}.flat.md"
        )
        assert os.path.exists(
            flattened_file_path), "Flattened file was not created"

        with open(flattened_file_path, "r") as f:
            flattened_content = f.read()

        # Check if hidden files and directories are excluded
        assert (
            ".hidden_dir" not in flattened_content
        ), "Hidden directory should be excluded"
        assert (
            ".hidden_file.py" not in flattened_content
        ), "Hidden file should be excluded"


@patch("sys.argv", ["coderoller-flatten-repo", "dummy_path", "--structure-only"])
@patch("coderoller.flatten_repo.flatten_repo")
def test_cli_structure_only_option(mock_flatten_repo):
    main()
    # Check if flatten_repo was called with structure_only=True
    assert mock_flatten_repo.call_args[1]["structure_only"] == True


@patch.object(Repo, "clone_from")
def test_flatten_repo_from_git(mock_clone_from):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the clone_from method to copy a local repository structure instead
        def mock_clone(repo_url, to_path):
            shutil.copytree(temp_dir, to_path, dirs_exist_ok=True)

        mock_clone_from.side_effect = mock_clone

        # Create a mock repository structure
        os.makedirs(os.path.join(temp_dir, "src"))

        readme_content = "# This is the README"
        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write(readme_content)

        python_content = 'print("Hello, World!")'
        with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
            f.write(python_content)

        json_content = '{"key": "value"}'
        with open(os.path.join(temp_dir, "config.json"), "w") as f:
            f.write(json_content)

        # Test the CLI with a mock GitHub URL
        with patch(
            "sys.argv", ["coderoller-flatten-repo",
                         "https://github.com/mock/repo.git"]
        ):
            main()

        # Check if the flattened file is created
        flattened_file_path = os.path.join(os.getcwd(), "repo.flat.md")
        assert os.path.exists(
            flattened_file_path), "Flattened file was not created"

        with open(flattened_file_path, "r") as f:
            flattened_content = f.read()

        # Check if the README content is included
        assert "## README" in flattened_content, "README section is missing"
        assert (
            "```markdown" in flattened_content
        ), "README content is not properly formatted"
        assert readme_content in flattened_content, "README content is incorrect"

        # Check if the Python file content is included
        assert (
            "## File: src/main.py" in flattened_content
        ), "Python file section is missing"
        assert (
            "```python" in flattened_content
        ), "Python content is not properly formatted"
        assert python_content in flattened_content, "Python content is incorrect"

        # Check if the JSON file content is included
        assert (
            "## File: config.json" in flattened_content
        ), "JSON file section is missing"
        assert "```json" in flattened_content, "JSON content is not properly formatted"
        assert json_content in flattened_content, "JSON content is incorrect"

        # Clean up the flattened file
        os.remove(flattened_file_path)


@patch.object(Repo, "clone_from")
def test_flatten_repo_from_git_structure_only(mock_clone_from):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the clone_from method to copy a local repository structure instead
        def mock_clone(repo_url, to_path):
            shutil.copytree(temp_dir, to_path, dirs_exist_ok=True)

        mock_clone_from.side_effect = mock_clone

        # Create a mock repository structure
        os.makedirs(os.path.join(temp_dir, "src"))
        os.makedirs(os.path.join(temp_dir, "docs"))

        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write("# This is the README")

        with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
            f.write('print("Hello, World!")')

        with open(os.path.join(temp_dir, "config.json"), "w") as f:
            f.write('{"key": "value"}')

        # Test the CLI with a mock GitHub URL and structure-only option
        with patch(
            "sys.argv", ["coderoller-flatten-repo",
                         "https://github.com/mock/repo.git", "--structure-only"]
        ):
            main()

        # Check if the flattened file is created
        flattened_file_path = os.path.join(os.getcwd(), "repo.flat.md")
        assert os.path.exists(
            flattened_file_path), "Flattened file was not created"

        with open(flattened_file_path, "r") as f:
            flattened_content = f.read()

        # Check if structure info is included
        assert "## Folder Structure" in flattened_content, "Folder structure section is missing"
        assert "src" in flattened_content, "Source directory is missing in structure"

        # Make sure file contents are not included
        assert 'print("Hello, World!")' not in flattened_content, "File content should not be included"
        assert "# This is the README" not in flattened_content, "README content should not be included in structure-only mode"

        # Clean up the flattened file
        os.remove(flattened_file_path)
