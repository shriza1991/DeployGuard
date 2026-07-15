import os
import re
from typing import Set, List

EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".java": "java",
    ".kt": "kotlin",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript-react",
    ".jsx": "javascript-react",
    ".go": "go",
    ".rs": "rust",
    ".tf": "terraform",
    ".tfvars": "terraform-vars",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".xml": "xml",
    ".properties": "properties",
}

FILENAME_TO_LANGUAGE = {
    "Dockerfile": "dockerfile",
    "docker-compose.yml": "yaml",
    ".env.example": "dotenv",
}

def detect_language(file_path: str) -> str:
    """Returns the canonical language name based on file extension or filename."""
    filename = os.path.basename(file_path)
    if filename in FILENAME_TO_LANGUAGE:
        return FILENAME_TO_LANGUAGE[filename]
    _, ext = os.path.splitext(filename)
    return EXTENSION_TO_LANGUAGE.get(ext.lower(), "text")

def detect_tech_signatures(repo_path: str) -> tuple[List[str], List[str], List[str]]:
    """
    Scans the repository path for project metadata files and parses them
    to detect languages, frameworks, and infrastructure technologies.
    Returns: (detected_languages, frameworks, infrastructure_technologies)
    """
    languages: Set[str] = set()
    frameworks: Set[str] = set()
    infra_techs: Set[str] = set()

    # Track found metadata files to parse
    package_json_paths: List[str] = []
    requirements_txt_paths: List[str] = []
    pyproject_toml_paths: List[str] = []
    go_mod_paths: List[str] = []
    cargo_toml_paths: List[str] = []
    pom_xml_paths: List[str] = []
    build_gradle_paths: List[str] = []
    tf_paths: List[str] = []

    # Walk the directory
    for root, dirs, files in os.walk(repo_path):
        # Prune ignored directories in-place
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "dist", "build", "target", "venv", "__pycache__", "vendor"}]
        
        for file in files:
            file_lower = file.lower()
            _, ext = os.path.splitext(file_lower)

            # Language detection from file extensions
            if ext in EXTENSION_TO_LANGUAGE:
                languages.add(EXTENSION_TO_LANGUAGE[ext])
            elif file in FILENAME_TO_LANGUAGE:
                languages.add(FILENAME_TO_LANGUAGE[file])

            # Gather metadata files
            if file == "package.json":
                package_json_paths.append(os.path.join(root, file))
            elif file == "requirements.txt":
                requirements_txt_paths.append(os.path.join(root, file))
            elif file == "pyproject.toml":
                pyproject_toml_paths.append(os.path.join(root, file))
            elif file == "go.mod":
                go_mod_paths.append(os.path.join(root, file))
            elif file == "Cargo.toml":
                cargo_toml_paths.append(os.path.join(root, file))
            elif file == "pom.xml":
                pom_xml_paths.append(os.path.join(root, file))
            elif file == "build.gradle":
                build_gradle_paths.append(os.path.join(root, file))
            elif ext == ".tf":
                tf_paths.append(os.path.join(root, file))
            elif file == "Dockerfile":
                infra_techs.add("Docker")
            elif file == "docker-compose.yml" or file == "docker-compose.yaml":
                infra_techs.add("Docker Compose")

    # 1. Parse package.json
    for path in package_json_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Simple regex check for dependencies instead of bringing in json parsing errors
                if '"react"' in content:
                    frameworks.add("React")
                if '"next"' in content:
                    frameworks.add("Next.js")
                if '"vue"' in content:
                    frameworks.add("Vue.js")
                if '"express"' in content:
                    frameworks.add("Express.js")
                if '"@nestjs/' in content or '"nest"' in content:
                    frameworks.add("NestJS")
                if '"angular"' in content:
                    frameworks.add("Angular")
        except Exception:
            pass

    # 2. Parse Python requirements
    for path in requirements_txt_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                if "fastapi" in content:
                    frameworks.add("FastAPI")
                if "django" in content:
                    frameworks.add("Django")
                if "flask" in content:
                    frameworks.add("Flask")
                if "celery" in content:
                    frameworks.add("Celery")
        except Exception:
            pass

    for path in pyproject_toml_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                if "fastapi" in content:
                    frameworks.add("FastAPI")
                if "django" in content:
                    frameworks.add("Django")
                if "flask" in content:
                    frameworks.add("Flask")
                if "poetry" in content:
                    infra_techs.add("Poetry")
        except Exception:
            pass

    # 3. Parse Go mod
    for path in go_mod_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                if "github.com/gin-gonic/gin" in content or "/gin " in content:
                    frameworks.add("Gin")
                if "github.com/gofiber/fiber" in content or "/fiber " in content:
                    frameworks.add("Fiber")
                if "github.com/astaxie/beego" in content:
                    frameworks.add("Beego")
                if "github.com/labstack/echo" in content or "/echo " in content:
                    frameworks.add("Echo")
        except Exception:
            pass

    # 4. Parse Rust cargo.toml
    for path in cargo_toml_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                if "actix-web" in content:
                    frameworks.add("Actix-web")
                if "axum" in content:
                    frameworks.add("Axum")
                if "tokio" in content:
                    frameworks.add("Tokio")
        except Exception:
            pass

    # 5. Parse Java POM/Gradle
    for path in pom_xml_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                if "spring-boot" in content:
                    frameworks.add("Spring Boot")
                if "micronaut" in content:
                    frameworks.add("Micronaut")
                if "quarkus" in content:
                    frameworks.add("Quarkus")
        except Exception:
            pass

    for path in build_gradle_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                if "spring-boot" in content or "springboot" in content:
                    frameworks.add("Spring Boot")
        except Exception:
            pass

    # 6. Parse Terraform files
    if tf_paths:
        infra_techs.add("Terraform")
        for path in tf_paths:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    # Find provider definitions
                    providers = re.findall(r'provider\s+"([^"]+)"', content)
                    for prov in providers:
                        if prov == "aws":
                            infra_techs.add("AWS")
                        elif prov in {"google", "google-beta"}:
                            infra_techs.add("GCP")
                        elif prov == "azurerm":
                            infra_techs.add("Azure")
                        elif prov == "kubernetes":
                            infra_techs.add("Kubernetes")
                        elif prov == "helm":
                            infra_techs.add("Helm")
            except Exception:
                pass

    # Add default language/infra tech fallback check
    if "dockerfile" in languages:
        infra_techs.add("Docker")
    if "terraform" in languages:
        infra_techs.add("Terraform")

    return sorted(list(languages)), sorted(list(frameworks)), sorted(list(infra_techs))
