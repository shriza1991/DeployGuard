import os
import logging
import datetime
from typing import List, Dict, Any
from models import RepoStatus, RepoManifest, CodeChunk, CodeChunkMetadata
from config import Settings
from services.clone_service import CloneService, get_repo_name
from services.redis_service import RedisService
from services.qdrant_service import QdrantService
from services.chunker import Chunker
from services.embedding_service import EmbeddingService
from utils.file_filters import is_ignored_directory, is_supported_file, get_file_kind
from utils.language_detector import detect_language, detect_tech_signatures

logger = logging.getLogger("repository-context-service")

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
        Clones, parses, chunks, embeds, and indexes a repository into Qdrant.
        Stores status and manifest metadata in Redis.
        """
        repository = get_repo_name(repository_url)
        logger.info(f"Starting indexing for repository: {repository} (branch: {branch})")
        
        # 1. Update status to 'indexing'
        initial_status = RepoStatus(
            status="indexing",
            branch=branch,
            last_indexed=datetime.datetime.utcnow().isoformat() + "Z"
        )
        self.redis_service.save_status(repository, branch, initial_status)

        clone_path = None
        try:
            # 2. Clone repository
            clone_path, head_commit = self.clone_service.clone_repository(repository_url, branch)
            
            # 3. Detect framework and technology signatures
            detected_languages, frameworks, infra_techs = detect_tech_signatures(clone_path)
            logger.info(f"Tech signatures detected - Languages: {detected_languages}, Frameworks: {frameworks}, Infra: {infra_techs}")

            # 4. Walk directories to gather files
            all_chunks: List[CodeChunk] = []
            processed_files_count = 0
            
            for root, dirs, files in os.walk(clone_path):
                # Prune excluded directories
                dirs[:] = [d for d in dirs if not is_ignored_directory(d)]

                for file in files:
                    if not is_supported_file(file):
                        continue

                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, clone_path).replace("\\", "/")
                    
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                    except Exception as fe:
                        logger.warning(f"Could not read file {rel_path}: {fe}")
                        continue

                    processed_files_count += 1
                    language = detect_language(rel_path)
                    kind = get_file_kind(rel_path)

                    # Chunk file content
                    raw_chunks = self.chunker.chunk_file(content, rel_path, language)
                    chunk_count = len(raw_chunks)

                    # Build CodeChunk list
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

            logger.info(f"Parsed {processed_files_count} files, generated {len(all_chunks)} chunks.")

            # 5. Generate embeddings in batch
            embeddings: List[List[float]] = []
            if all_chunks:
                logger.info("Generating embeddings for all chunks...")
                chunk_texts = [c.text for c in all_chunks]
                embeddings = self.embedding_service.embed_batch(chunk_texts)
                logger.info(f"Generated {len(embeddings)} embedding vectors.")

            # 6. Delete previous indexing records in Qdrant for this branch
            logger.info(f"Purging existing points in Qdrant for {repository} (branch: {branch})...")
            self.qdrant_service.delete_by_repository(repository, branch)

            # 7. Ingest vectors and payloads into Qdrant
            if all_chunks:
                logger.info(f"Upserting points to Qdrant...")
                upsert_ok = self.qdrant_service.upsert_chunks(all_chunks, embeddings)
                if not upsert_ok:
                    raise RuntimeError("Qdrant upsert failed.")

            # 8. Store manifest and completed status in Redis
            now_str = datetime.datetime.utcnow().isoformat() + "Z"
            
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
                detected_languages=detected_languages,
                frameworks=frameworks,
                infrastructure_technologies=infra_techs,
                number_of_files=processed_files_count,
                number_of_chunks=len(all_chunks),
                commit=head_commit,
                branch=branch,
                last_indexed=now_str
            )
            self.redis_service.save_manifest(repository, branch, manifest)
            
            logger.info(f"Indexing completed successfully for {repository} (branch: {branch})")

        except Exception as e:
            logger.error(f"Indexing failed for {repository} (branch: {branch}): {e}", exc_info=True)
            failed_status = RepoStatus(
                status="failed",
                branch=branch,
                last_indexed=datetime.datetime.utcnow().isoformat() + "Z"
            )
            self.redis_service.save_status(repository, branch, failed_status)
        finally:
            # 9. Cleanup cloned folder
            if clone_path:
                logger.info(f"Cleaning up temporary path: {clone_path}")
                try:
                    self.clone_service.cleanup(clone_path)
                except Exception as ce:
                    logger.warning(f"Error cleaning up clone folder {clone_path}: {ce}")
