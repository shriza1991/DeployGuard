import os
import logging
import datetime
import re
import yaml
import git
import time
from typing import List, Dict, Any, Tuple
from models import RepoStatus, RepoManifest, CodeChunk, CodeChunkMetadata
from config import Settings
from services.clone_service import CloneService, get_repo_name
from services.redis_service import RedisService
from services.qdrant_service import QdrantService
from services.chunker import Chunker
from services.embedding_service import EmbeddingService
from utils.file_filters import is_supported_file, get_file_kind
from utils.language_detector import detect_language

logger = logging.getLogger("repository-context-service")

def is_ignored_path(relative_path: str, ignore_rules_str: str) -> bool:
    """Checks if the relative path matches any of the ignore rules."""
    normalized = relative_path.replace("\\", "/").lower()
    rules = [r.strip().lower() for r in ignore_rules_str.split(",") if r.strip()]
    parts = normalized.split("/")
    filename = parts[-1]
    
    for rule in rules:
        if rule.endswith("/"):
            dir_pattern = rule[:-1]
            if any(p == dir_pattern for p in parts[:-1]) or dir_pattern in parts:
                return True
        else:
            if filename == rule or rule in parts or rule in normalized:
                return True
    return False

def detect_frameworks_from_files(files_set: set[str]) -> list[str]:
    """Detects software frameworks/technologies based on the filenames present."""
    frameworks = []
    if any(f in {"requirements.txt", "pyproject.toml", "poetry.lock"} for f in files_set) or \
       any("requirements.txt" in f or "pyproject.toml" in f or "poetry.lock" in f for f in files_set):
        frameworks.append("Python Project")
    if any(f in {"package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"} for f in files_set) or \
       any("package.json" in f or "yarn.lock" in f or "pnpm-lock.yaml" in f for f in files_set):
        frameworks.append("Node.js Project")
    if any(f in {"pom.xml", "build.gradle", "gradlew"} for f in files_set) or \
       any("pom.xml" in f or "build.gradle" in f for f in files_set):
        frameworks.append("Java Project")
    if any(f in {"go.mod", "go.sum"} for f in files_set) or \
       any("go.mod" in f for f in files_set):
        frameworks.append("Go Project")
    if any(f in {"Cargo.toml", "Cargo.lock"} for f in files_set) or \
       any("Cargo.toml" in f for f in files_set):
        frameworks.append("Rust Project")
    if any(f.endswith((".csproj", ".sln")) for f in files_set):
        frameworks.append(".NET Project")
    return frameworks

def build_architecture_metadata(clone_path: str, detected_languages: list[str]) -> dict:
    """Helper to heuristically detect services, message buses, datastores, and languages."""
    services = []
    message_bus = "None"
    datastores = []
    
    dc_path = os.path.join(clone_path, "docker-compose.yml")
    dc_content = ""
    if os.path.exists(dc_path):
        try:
            with open(dc_path, "r", encoding="utf-8") as f:
                dc_content = f.read()
                dc = yaml.safe_load(dc_content)
                if isinstance(dc, dict) and "services" in dc:
                    services = list(dc["services"].keys())
        except Exception:
            pass

    if not services:
        for item in os.listdir(clone_path):
            item_path = os.path.join(clone_path, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                if any(os.path.exists(os.path.join(item_path, f)) for f in ("Dockerfile", "requirements.txt", "package.json")):
                    services.append(item)

    dc_content_lower = dc_content.lower()
    if "kafka" in dc_content_lower:
        message_bus = "Kafka"
    elif "rabbitmq" in dc_content_lower:
        message_bus = "RabbitMQ"

    if "redis" in dc_content_lower:
        datastores.append("Redis")
    if "qdrant" in dc_content_lower:
        datastores.append("Qdrant")
    if "postgres" in dc_content_lower or "postgresql" in dc_content_lower:
        datastores.append("PostgreSQL")

    if not datastores:
        all_text = ""
        for r, d, files in os.walk(clone_path):
            for f in files:
                if f.endswith((".txt", ".json", ".py", ".tf")):
                    try:
                        with open(os.path.join(r, f), "r", errors="ignore") as file:
                            all_text += file.read(1000)
                    except Exception:
                        pass
        all_text_lower = all_text.lower()
        if "redis" in all_text_lower:
            datastores.append("Redis")
        if "qdrant" in all_text_lower:
            datastores.append("Qdrant")
        if "postgres" in all_text_lower:
            datastores.append("PostgreSQL")

    languages = [l.capitalize() for l in detected_languages]

    return {
        "services": services,
        "message_bus": message_bus,
        "datastores": datastores,
        "languages": languages
    }

def extract_python_imports(content: str) -> list[str]:
    """Lightweight regex parser for Python import dependencies."""
    imports = []
    matches1 = re.findall(r'import\s+([\w\.]+)', content)
    matches2 = re.findall(r'from\s+([\w\.]+)\s+import', content)
    for m in matches1 + matches2:
        base = m.split('.')[0]
        if base and base not in imports:
            imports.append(base)
    return imports

def extract_js_imports(content: str) -> list[str]:
    """Lightweight regex parser for JavaScript/TypeScript import dependencies."""
    imports = []
    matches1 = re.findall(r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]', content)
    matches2 = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content)
    for m in matches1 + matches2:
        if m.startswith('.'):
            base = os.path.basename(m)
            if base and base not in imports:
                imports.append(base)
        else:
            base = m.split('/')[0]
            if base and base not in imports:
                imports.append(base)
    return imports

def extract_file_imports(content: str, rel_path: str) -> list[str]:
    """Extracts imports or dependencies statically based on file type."""
    ext = os.path.splitext(rel_path)[1].lower()
    if ext == ".py":
        return extract_python_imports(content)
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        return extract_js_imports(content)
    return []

def get_changed_files_between_commits(repo_path: str, prev_commit: str, head_commit: str) -> Tuple[set, set]:
    """Gets sets of (modified_or_added, deleted) files between two commits."""
    repo = git.Repo(repo_path)
    modified_or_added = set()
    deleted = set()
    
    diff_index = repo.commit(prev_commit).diff(repo.commit(head_commit))
    for diff in diff_index:
        a_path = diff.a_path.replace("\\", "/") if diff.a_path else None
        b_path = diff.b_path.replace("\\", "/") if diff.b_path else None
        
        if diff.change_type in ('A', 'M'):
            if b_path:
                modified_or_added.add(b_path)
        elif diff.change_type == 'D':
            if a_path:
                deleted.add(a_path)
        elif diff.change_type == 'R':
            if a_path:
                deleted.add(a_path)
            if b_path:
                modified_or_added.add(b_path)
                
    return modified_or_added, deleted

class Indexer:
    def __init__(
        self,
        settings: Settings,
        clone_service: CloneService,
        redis_service: RedisService,
        qdrant_service: QdrantService,
        chunker: Chunker,
        embedding_service: EmbeddingService
    ):
        self.settings = settings
        self.clone_service = clone_service
        self.redis_service = redis_service
        self.qdrant_service = qdrant_service
        self.chunker = chunker
        self.embedding_service = embedding_service

    def index_repository(self, repository_url: str, branch: str = "main") -> None:
        """
        Clones or updates the repository. Computes changes between commits to perform
        incremental indexing. Falls back to full re-indexing if incremental fails.
        """
        t_index_start = time.perf_counter()
        repository = get_repo_name(repository_url)
        logger.info(f"Starting indexing for repository: {repository} (branch: {branch})")
        
        initial_status = RepoStatus(
            status="indexing",
            branch=branch,
            last_indexed=datetime.datetime.utcnow().isoformat() + "Z"
        )
        self.redis_service.save_status(repository, branch, initial_status)

        clone_path = None
        incremental_success = False

        try:
            clone_path, head_commit = self.clone_service.clone_repository(repository_url, branch)
            
            # Fetch previous manifest to identify commit
            prev_manifest = self.redis_service.get_manifest(repository, branch)
            prev_status = self.redis_service.get_status(repository, branch)
            
            prev_commit = None
            if prev_manifest and prev_status and prev_status.status == "completed":
                prev_commit = prev_manifest.commit

            if prev_commit == head_commit:
                logger.info(f"HEAD commit {head_commit} is unchanged. Skipping indexing entirely.")
                completed_status = RepoStatus(
                    status="completed",
                    files=prev_manifest.number_of_files,
                    chunks=prev_manifest.number_of_chunks,
                    last_indexed=prev_manifest.last_indexed,
                    commit=prev_manifest.commit,
                    branch=prev_manifest.branch
                )
                self.redis_service.save_status(repository, branch, completed_status)
                return

            if self.settings.enable_incremental_indexing and prev_commit:
                logger.info(f"Attempting incremental indexing from {prev_commit} to {head_commit}...")
                try:
                    incremental_success = self._run_incremental_indexing(
                        clone_path, repository, branch, prev_commit, head_commit, prev_manifest, t_index_start
                    )
                except Exception as inc_err:
                    logger.warning(f"Incremental indexing failed: {inc_err}. Falling back to full indexing.")
                    incremental_success = False

            if not incremental_success:
                logger.info("Executing full repository indexing...")
                self._run_full_indexing(clone_path, repository, branch, head_commit, t_index_start)

        except Exception as e:
            logger.error(f"Indexing failed for {repository} (branch: {branch}): {e}", exc_info=True)
            failed_status = RepoStatus(
                status="failed",
                branch=branch,
                last_indexed=datetime.datetime.utcnow().isoformat() + "Z"
            )
            self.redis_service.save_status(repository, branch, failed_status)
        finally:
            if clone_path:
                try:
                    self.clone_service.cleanup(clone_path)
                except Exception as ce:
                    logger.warning(f"Error during repository cleanup: {ce}")

    def _run_incremental_indexing(
        self, clone_path: str, repository: str, branch: str, prev_commit: str, head_commit: str, prev_manifest: RepoManifest, t_index_start: float
    ) -> bool:
        """Runs incremental indexing by computing differences and selectively updates Qdrant vectors."""
        t_chunk_start = time.perf_counter()
        modified_or_added, deleted = get_changed_files_between_commits(clone_path, prev_commit, head_commit)
        
        # 1. Walk repository to reconstruct statistics, framework details, and gather files
        files_set = set()
        detected_languages = set()
        repository_size_bytes = 0
        lines_of_code = 0
        test_count = 0
        configuration_count = 0
        docker_images = []
        terraform_modules = []
        helm_charts = []
        dependency_graph = {}

        # Cache of chunks we keep or re-index
        all_chunks: List[CodeChunk] = []
        chunks_to_embed: List[CodeChunk] = []

        processed_files_count = 0

        for root, dirs, files in os.walk(clone_path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if not is_ignored_path(os.path.join(root, d), self.settings.repository_ignore_rules)]

            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, clone_path).replace("\\", "/")

                if is_ignored_path(rel_path, self.settings.repository_ignore_rules):
                    continue

                if not is_supported_file(file):
                    continue

                files_set.add(file)
                processed_files_count += 1
                
                try:
                    file_size = os.path.getsize(full_path)
                    repository_size_bytes += file_size
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue

                lines_of_code += len(content.splitlines())
                language = detect_language(rel_path)
                detected_languages.add(language)
                kind = get_file_kind(rel_path)

                if kind == "test":
                    test_count += 1
                elif kind == "configuration":
                    configuration_count += 1

                # Extrapolate Docker/Terraform/Helm specifics
                if file.lower() == "dockerfile":
                    images = re.findall(r"(?i)^FROM\s+([\w\.\:\-\/]+)", content, re.MULTILINE)
                    docker_images.extend(images)
                elif file.endswith(".tf"):
                    modules = re.findall(r'module\s+"[^"]+"\s+\{\s*source\s*=\s*"([^"]+)"', content)
                    terraform_modules.extend(modules)
                elif file.lower() == "chart.yaml":
                    helm_charts.append(os.path.basename(os.path.dirname(rel_path)))

                # Parse imports for dependency graph
                imports = extract_file_imports(content, rel_path)
                if imports:
                    dependency_graph[rel_path] = imports

                # Logical block chunking
                raw_chunks = self.chunker.chunk_file(content, rel_path, language)
                chunk_count = len(raw_chunks)

                for item in raw_chunks:
                    metadata = CodeChunkMetadata(
                        repository=repository,
                        branch=branch,
                        commit=head_commit,
                        language=language,
                        relative_path=rel_path,
                        filename=file,
                        directory=os.path.dirname(rel_path) or ".",
                        chunk_index=item["chunk_index"],
                        chunk_count=chunk_count,
                        start_line=item["start_line"],
                        end_line=item["end_line"],
                        kind=kind,
                        last_indexed=datetime.datetime.utcnow().isoformat() + "Z"
                    )
                    chunk = CodeChunk(text=item["text"], metadata=metadata)
                    all_chunks.append(chunk)

                    if rel_path in modified_or_added:
                        chunks_to_embed.append(chunk)

        # 2. Deletes from Qdrant
        # For deleted files
        for del_file in deleted:
            logger.info(f"Incremental Indexing: Deleting Qdrant vectors for deleted file {del_file}")
            self.qdrant_service.delete_by_file(repository, branch, del_file)
            
        # For modified files
        for mod_file in modified_or_added:
            logger.info(f"Incremental Indexing: Deleting Qdrant vectors for modified file {mod_file}")
            self.qdrant_service.delete_by_file(repository, branch, mod_file)

        chunk_generation_latency = (time.perf_counter() - t_chunk_start) * 1000

        # 3. Generate embeddings and upsert modified/added chunks
        t_embed_start = time.perf_counter()
        embeddings: List[List[float]] = []
        if chunks_to_embed:
            logger.info(f"Incremental Indexing: Re-indexing {len(chunks_to_embed)} chunks for modified files...")
            chunk_texts = [c.text for c in chunks_to_embed]
            embeddings = self.embedding_service.embed_batch(chunk_texts)
            
            upsert_ok = self.qdrant_service.upsert_chunks(
                chunks_to_embed, embeddings, batch_size=self.settings.qdrant_batch_size
            )
            if not upsert_ok:
                raise RuntimeError("Incremental upsert failed.")
        embedding_latency = (time.perf_counter() - t_embed_start) * 1000

        # 4. Save metadata back to Redis
        now_str = datetime.datetime.utcnow().isoformat() + "Z"
        frameworks = detect_frameworks_from_files(files_set)
        arch_summary = build_architecture_metadata(clone_path, list(detected_languages))

        final_status = RepoStatus(
            status="completed",
            files=processed_files_count,
            chunks=len(all_chunks),
            last_indexed=now_str,
            commit=head_commit,
            branch=branch
        )
        self.redis_service.save_status(repository, branch, final_status)

        manifest = RepoManifest(
            detected_languages=list(detected_languages),
            frameworks=frameworks,
            infrastructure_technologies=prev_manifest.infrastructure_technologies if prev_manifest else [],
            number_of_files=processed_files_count,
            number_of_chunks=len(all_chunks),
            commit=head_commit,
            branch=branch,
            last_indexed=now_str,
            repository_size_bytes=repository_size_bytes,
            lines_of_code=lines_of_code,
            number_of_services=len(arch_summary.get("services", [])),
            test_count=test_count,
            configuration_count=configuration_count,
            docker_images=docker_images,
            terraform_modules=terraform_modules,
            helm_charts=helm_charts,
            architecture_summary=arch_summary,
            dependency_graph=dependency_graph
        )
        self.redis_service.save_manifest(repository, branch, manifest)
        
        t_index_end = time.perf_counter()
        incremental_indexing_duration = (t_index_end - t_index_start) * 1000

        logger.info("Incremental Indexing Performance Metrics:")
        logger.info(f"chunks indexed: {len(chunks_to_embed)}")
        logger.info(f"repository size: {repository_size_bytes} bytes")
        logger.info(f"chunk generation latency: {int(chunk_generation_latency)} ms")
        logger.info(f"embedding latency: {int(embedding_latency)} ms")
        logger.info(f"incremental indexing duration: {int(incremental_indexing_duration)} ms")

        return True

    def _run_full_indexing(self, clone_path: str, repository: str, branch: str, head_commit: str, t_index_start: float) -> None:
        """Cleans collection and indexes all codebase files from scratch."""
        t_chunk_start = time.perf_counter()
        files_set = set()
        detected_languages = set()
        repository_size_bytes = 0
        lines_of_code = 0
        test_count = 0
        configuration_count = 0
        docker_images = []
        terraform_modules = []
        helm_charts = []
        dependency_graph = {}

        all_chunks: List[CodeChunk] = []
        processed_files_count = 0

        for root, dirs, files in os.walk(clone_path):
            dirs[:] = [d for d in dirs if not is_ignored_path(os.path.join(root, d), self.settings.repository_ignore_rules)]

            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, clone_path).replace("\\", "/")

                if is_ignored_path(rel_path, self.settings.repository_ignore_rules):
                    continue

                if not is_supported_file(file):
                    continue

                files_set.add(file)
                processed_files_count += 1
                
                try:
                    file_size = os.path.getsize(full_path)
                    repository_size_bytes += file_size
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue

                lines_of_code += len(content.splitlines())
                language = detect_language(rel_path)
                detected_languages.add(language)
                kind = get_file_kind(rel_path)

                if kind == "test":
                    test_count += 1
                elif kind == "configuration":
                    configuration_count += 1

                if file.lower() == "dockerfile":
                    images = re.findall(r"(?i)^FROM\s+([\w\.\:\-\/]+)", content, re.MULTILINE)
                    docker_images.extend(images)
                elif file.endswith(".tf"):
                    modules = re.findall(r'module\s+"[^"]+"\s+\{\s*source\s*=\s*"([^"]+)"', content)
                    terraform_modules.extend(modules)
                elif file.lower() == "chart.yaml":
                    helm_charts.append(os.path.basename(os.path.dirname(rel_path)))

                imports = extract_file_imports(content, rel_path)
                if imports:
                    dependency_graph[rel_path] = imports

                raw_chunks = self.chunker.chunk_file(content, rel_path, language)
                chunk_count = len(raw_chunks)

                for item in raw_chunks:
                    metadata = CodeChunkMetadata(
                        repository=repository,
                        branch=branch,
                        commit=head_commit,
                        language=language,
                        relative_path=rel_path,
                        filename=file,
                        directory=os.path.dirname(rel_path) or ".",
                        chunk_index=item["chunk_index"],
                        chunk_count=chunk_count,
                        start_line=item["start_line"],
                        end_line=item["end_line"],
                        kind=kind,
                        last_indexed=datetime.datetime.utcnow().isoformat() + "Z"
                    )
                    all_chunks.append(
                        CodeChunk(text=item["text"], metadata=metadata)
                    )

        chunk_generation_latency = (time.perf_counter() - t_chunk_start) * 1000

        # Purge Qdrant
        logger.info(f"Purging Qdrant points for {repository} (branch: {branch})...")
        self.qdrant_service.delete_by_repository(repository, branch)

        # Generate embeddings
        t_embed_start = time.perf_counter()
        embeddings: List[List[float]] = []
        if all_chunks:
            logger.info("Generating embeddings for all chunks...")
            chunk_texts = [c.text for c in all_chunks]
            embeddings = self.embedding_service.embed_batch(chunk_texts)
            
            upsert_ok = self.qdrant_service.upsert_chunks(
                all_chunks, embeddings, batch_size=self.settings.qdrant_batch_size
            )
            if not upsert_ok:
                raise RuntimeError("Full upsert failed.")
        embedding_latency = (time.perf_counter() - t_embed_start) * 1000

        now_str = datetime.datetime.utcnow().isoformat() + "Z"
        frameworks = detect_frameworks_from_files(files_set)
        arch_summary = build_architecture_metadata(clone_path, list(detected_languages))

        final_status = RepoStatus(
            status="completed",
            files=processed_files_count,
            chunks=len(all_chunks),
            last_indexed=now_str,
            commit=head_commit,
            branch=branch
        )
        self.redis_service.save_status(repository, branch, final_status)
        docker_images = sorted(set(docker_images))
        terraform_modules = sorted(set(terraform_modules))
        helm_charts = sorted(set(helm_charts))
        logger.info(f"Docker images after dedup: {docker_images}")

        manifest = RepoManifest(
            detected_languages=list(detected_languages),
            frameworks=frameworks,
            infrastructure_technologies=["Docker"] if docker_images else [],
            number_of_files=processed_files_count,
            number_of_chunks=len(all_chunks),
            commit=head_commit,
            branch=branch,
            last_indexed=now_str,
            repository_size_bytes=repository_size_bytes,
            lines_of_code=lines_of_code,
            number_of_services=len(arch_summary.get("services", [])),
            test_count=test_count,
            configuration_count=configuration_count,
            docker_images=docker_images,
            terraform_modules=terraform_modules,
            helm_charts=helm_charts,
            architecture_summary=arch_summary,
            dependency_graph=dependency_graph
        )
        self.redis_service.save_manifest(repository, branch, manifest)
        
        t_index_end = time.perf_counter()
        incremental_indexing_duration = (t_index_end - t_index_start) * 1000

        logger.info("Full Indexing Performance Metrics:")
        logger.info(f"chunks indexed: {len(all_chunks)}")
        logger.info(f"repository size: {repository_size_bytes} bytes")
        logger.info(f"chunk generation latency: {int(chunk_generation_latency)} ms")
        logger.info(f"embedding latency: {int(embedding_latency)} ms")
        logger.info(f"incremental indexing duration: {int(incremental_indexing_duration)} ms")
