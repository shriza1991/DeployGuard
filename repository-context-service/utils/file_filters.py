import os
import re

IGNORED_DIRECTORIES = {
    ".git", "node_modules", "dist", "build", "target", "venv", 
    "__pycache__", ".idea", ".vscode", "coverage", ".next", "vendor"
}

SUPPORTED_EXTENSIONS = {
    ".py", ".java", ".kt", ".js", ".ts", ".tsx", ".jsx", ".go", 
    ".rs", ".tf", ".tfvars", ".yml", ".yaml", ".json", ".md", 
    ".xml", ".properties"
}

SUPPORTED_EXACT_NAMES = {
    ".env.example", "Dockerfile", "docker-compose.yml"
}

def is_ignored_directory(dir_name: str) -> bool:
    """Returns True if the directory should be ignored."""
    return dir_name in IGNORED_DIRECTORIES

def is_supported_file(file_name: str) -> bool:
    """Returns True if the file name matches a supported extension or exact name."""
    if file_name in SUPPORTED_EXACT_NAMES:
        return True
    _, ext = os.path.splitext(file_name)
    return ext.lower() in SUPPORTED_EXTENSIONS

def get_file_kind(relative_path: str) -> str:
    """
    Categorizes the file path into a kind string:
    'test', 'documentation', 'configuration', or 'source'.
    """
    normalized_path = relative_path.replace("\\", "/").lower()
    parts = normalized_path.split("/")
    filename = parts[-1] if parts else ""
    _, ext = os.path.splitext(filename)

    # 1. Check for test files or test directories
    # If any path component is exactly 'test' or 'tests', or contains test
    if any(p in {"test", "tests", "__tests__"} for p in parts) or \
       filename.startswith("test_") or \
       filename.endswith("_test" + ext) or \
       "test" in filename:
        return "test"

    # 2. Check for documentation
    if ext == ".md":
        return "documentation"

    # 3. Check for configuration files
    config_extensions = {".tf", ".tfvars", ".yml", ".yaml", ".json", ".properties", ".xml"}
    config_names = {".env.example", "Dockerfile", "docker-compose.yml"}
    if ext in config_extensions or filename in config_names:
        return "configuration"

    # 4. Default to source for other supported code extensions
    return "source"
