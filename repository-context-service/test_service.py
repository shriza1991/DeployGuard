import os
import sys
import unittest
import tempfile
import json
import shutil

# Make sure imports from repository-context-service work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.file_filters import is_ignored_directory, is_supported_file, get_file_kind
from utils.language_detector import detect_language, detect_tech_signatures
from services.chunker import Chunker, estimate_tokens
from services.clone_service import get_repo_name, force_rmtree
from services.redis_service import RedisService
from services.qdrant_service import QdrantService, get_stable_uuid
from models import RepoStatus, RepoManifest, CodeChunk, CodeChunkMetadata

class TestUtilities(unittest.TestCase):
    def test_file_filters(self):
        # Ignored directories
        self.assertTrue(is_ignored_directory(".git"))
        self.assertTrue(is_ignored_directory("node_modules"))
        self.assertFalse(is_ignored_directory("src"))
        self.assertFalse(is_ignored_directory("app"))

        # Supported files
        self.assertTrue(is_supported_file("main.py"))
        self.assertTrue(is_supported_file("Dockerfile"))
        self.assertTrue(is_supported_file(".env.example"))
        self.assertFalse(is_supported_file("image.png"))
        self.assertFalse(is_supported_file("data.zip"))

        # File kind detection
        self.assertEqual(get_file_kind("src/app/main.py"), "source")
        self.assertEqual(get_file_kind("README.md"), "documentation")
        self.assertEqual(get_file_kind("docker-compose.yml"), "configuration")
        self.assertEqual(get_file_kind("tests/test_auth.py"), "test")
        self.assertEqual(get_file_kind("src/app_test.go"), "test")

    def test_language_detector(self):
        self.assertEqual(detect_language("main.py"), "python")
        self.assertEqual(detect_language("App.tsx"), "typescript-react")
        self.assertEqual(detect_language("Dockerfile"), "dockerfile")
        self.assertEqual(detect_language("unknown.foo"), "text")

    def test_tech_signature_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create subdirs
            os.makedirs(os.path.join(tmpdir, "src"))
            os.makedirs(os.path.join(tmpdir, "infra"))

            # Create package.json
            with open(os.path.join(tmpdir, "package.json"), "w") as f:
                f.write('{"dependencies": {"react": "^18.2.0", "next": "13.0.0"}}')

            # Create requirements.txt
            with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
                f.write("fastapi>=0.100.0\nuvicorn\n")

            # Create Dockerfile
            with open(os.path.join(tmpdir, "Dockerfile"), "w") as f:
                f.write("FROM python:3.9-slim\nRUN pip install -r requirements.txt\n")

            # Create main.tf
            with open(os.path.join(tmpdir, "infra", "main.tf"), "w") as f:
                f.write('provider "aws" {\n  region = "us-east-1"\n}\nresource "aws_s3_bucket" "b" {}')

            # Create a dummy python file
            with open(os.path.join(tmpdir, "src", "app.py"), "w") as f:
                f.write("print('hello')\n")

            langs, frameworks, infra = detect_tech_signatures(tmpdir)
            
            self.assertIn("python", langs)
            self.assertIn("terraform", langs)
            self.assertIn("dockerfile", langs)
            
            self.assertIn("React", frameworks)
            self.assertIn("Next.js", frameworks)
            self.assertIn("FastAPI", frameworks)
            
            self.assertIn("Docker", infra)
            self.assertIn("Terraform", infra)
            self.assertIn("AWS", infra)

class TestChunker(unittest.TestCase):
    def setUp(self):
        self.chunker = Chunker(chunk_size_tokens=20, overlap_tokens=5)

    def test_chunk_source_code(self):
        code = "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10"
        chunks = self.chunker.chunk_file(code, "test.py", "python")
        self.assertTrue(len(chunks) > 0)
        self.assertEqual(chunks[0]["start_line"], 1)
        self.assertTrue(chunks[0]["end_line"] >= 1)

    def test_chunk_markdown(self):
        doc = "Paragraph one with some text to fill details.\n\nParagraph two is another section here.\n\nParagraph three is a final part."
        chunks = self.chunker.chunk_file(doc, "test.md", "markdown")
        self.assertTrue(len(chunks) > 0)
        # Verify text holds paragraphs
        self.assertIn("Paragraph one", chunks[0]["text"])

    def test_chunk_terraform(self):
        hcl = """
provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "web" {
  ami           = "ami-123456"
  instance_type = "t2.micro"

  tags = {
    Name = "HelloWorld"
  }
}
"""
        chunks = self.chunker.chunk_file(hcl, "main.tf", "terraform")
        self.assertTrue(len(chunks) > 0)
        # First chunk should contain the provider block
        self.assertIn("provider", chunks[0]["text"])

    def test_chunk_dockerfile(self):
        df = """
FROM python:3.9-slim
ENV PORT=8080
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt \
    && echo "Done"
CMD ["python", "app.py"]
"""
        chunks = self.chunker.chunk_file(df, "Dockerfile", "dockerfile")
        self.assertTrue(len(chunks) > 0)
        self.assertIn("FROM", chunks[0]["text"])

class TestIntegrationConnections(unittest.TestCase):
    def test_redis_integration_if_available(self):
        # Attempt to run connection integration tests if Redis is up
        try:
            redis_service = RedisService("redis://127.0.0.1:6379/0")
            # Try to ping
            redis_service.client.ping()
        except Exception:
            self.skipTest("Local Redis instance is not running on 127.0.0.1:6379. Skipping integration test.")

        # If available, test write, read, delete status
        status = RepoStatus(
            status="completed",
            files=10,
            chunks=25,
            last_indexed="2026-07-15T00:00:00Z",
            commit="abcdef12345",
            branch="test-branch"
        )
        redis_service.save_status("mock_repo", "test-branch", status)
        retrieved_status = redis_service.get_status("mock_repo", "test-branch")
        
        self.assertIsNotNone(retrieved_status)
        self.assertEqual(retrieved_status.status, "completed")
        self.assertEqual(retrieved_status.branch, "test-branch")

        # Test manifest
        manifest = RepoManifest(
            detected_languages=["python", "yaml"],
            frameworks=["FastAPI"],
            infrastructure_technologies=["Docker"],
            number_of_files=10,
            number_of_chunks=25,
            commit="abcdef12345",
            branch="test-branch",
            last_indexed="2026-07-15T00:00:00Z"
        )
        redis_service.save_manifest("mock_repo", "test-branch", manifest)
        retrieved_manifest = redis_service.get_manifest("mock_repo", "test-branch")
        
        self.assertIsNotNone(retrieved_manifest)
        self.assertIn("FastAPI", retrieved_manifest.frameworks)

        # Test delete
        redis_service.delete_repository_data("mock_repo", "test-branch")
        self.assertNilOrNone(redis_service.get_status("mock_repo", "test-branch"))

    def assertNilOrNone(self, val):
        self.assertIsNone(val)

    def test_qdrant_integration_if_available(self):
        try:
            qdrant_service = QdrantService("http://127.0.0.1:6333", "test_collection_context")
            health = qdrant_service.health_check()
            if not health:
                self.skipTest("Local Qdrant is not healthy or running on port 6333. Skipping integration test.")
        except Exception:
            self.skipTest("Local Qdrant is offline. Skipping integration test.")

        # Test collection creation and connection
        vector_size = 4
        created = qdrant_service.ensure_collection(vector_size)
        self.assertTrue(created)
        self.assertTrue(qdrant_service.collection_exists())

        # Test upsert and retrieval
        chunk_meta = CodeChunkMetadata(
            repository="test_repo",
            branch="test-branch",
            commit="sha123",
            language="python",
            relative_path="main.py",
            filename="main.py",
            directory=".",
            chunk_index=0,
            chunk_count=1,
            start_line=1,
            end_line=10,
            kind="source",
            last_indexed="2026-07-15T00:00:00Z"
        )
        chunk = CodeChunk(text="def hello():\n    print('world')", metadata=chunk_meta)
        
        # Insert
        upsert_ok = qdrant_service.upsert_chunks([chunk], [[0.1, 0.2, 0.3, 0.4]])
        self.assertTrue(upsert_ok)

        # Search
        results = qdrant_service.search([0.1, 0.2, 0.3, 0.4], "test_repo", "test-branch", top_k=2)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["payload"]["repository"], "test_repo")

        # Search with branch=None
        results_no_branch = qdrant_service.search([0.1, 0.2, 0.3, 0.4], "test_repo", None, top_k=2)
        self.assertTrue(len(results_no_branch) > 0)
        self.assertEqual(results_no_branch[0]["payload"]["repository"], "test_repo")

        # Delete
        delete_ok = qdrant_service.delete_by_repository("test_repo", "test-branch")
        self.assertTrue(delete_ok)

        # Confirm deleted (search returns nothing for this repo)
        import time
        for _ in range(5):
            empty_results = qdrant_service.search([0.1, 0.2, 0.3, 0.4], "test_repo", "test-branch", top_k=2)
            if len(empty_results) == 0:
                break
            time.sleep(0.2)
        self.assertEqual(len(empty_results), 0)

class DummyState:
    def __init__(self, embedding_service, qdrant_service, settings=None):
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service
        from config import get_settings
        self.settings = settings or get_settings()
        from unittest.mock import MagicMock
        self.redis_service = MagicMock()

class DummyRequest:
    def __init__(self, app):
        self.app = app

class TestRepositoryContextRoute(unittest.TestCase):
    def test_context_fallback_prioritization_and_deduplication(self):
        from unittest.mock import MagicMock
        import asyncio
        from models import ContextRequest
        from routes.search import get_repository_context

        # Mock embedding service
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_text.return_value = [0.1, 0.2]

        # Mock Qdrant service search behavior
        # Search returns duplicate chunks and unsorted order to verify prioritization & deduplication
        mock_hits_fallback = [
            {
                "id": "point-1",
                "score": 0.9,
                "payload": {
                    "repository": "test_repo",
                    "branch": "main",
                    "relative_path": "other_file.py",
                    "filename": "other_file.py",
                    "text": "content 1"
                }
            },
            {
                "id": "point-2",
                "score": 0.8,
                "payload": {
                    "repository": "test_repo",
                    "branch": "main",
                    "relative_path": "changed_file.py",
                    "filename": "changed_file.py",
                    "text": "content 2"
                }
            },
            {
                "id": "point-1",  # Duplicate point-id
                "score": 0.9,
                "payload": {
                    "repository": "test_repo",
                    "branch": "main",
                    "relative_path": "other_file.py",
                    "filename": "other_file.py",
                    "text": "content 1"
                }
            }
        ]

        mock_qdrant_service = MagicMock()
        def mock_search(vector, repository, branch, top_k):
            if branch == "feature-branch":
                # First search fails (returns zero hits)
                return []
            elif branch is None:
                # Fallback search succeeds
                return mock_hits_fallback
            return []

        mock_qdrant_service.search.side_effect = mock_search

        # Construct request & body
        app_mock = MagicMock()
        app_mock.state = DummyState(mock_embedding_service, mock_qdrant_service)
        request_mock = DummyRequest(app_mock)

        body = ContextRequest(
            repository="test_repo",
            branch="feature-branch",
            changed_files=["changed_file.py"],
            diff="some diff"
        )

        # Call endpoint handler directly
        response = asyncio.run(get_repository_context(request_mock, body))
        results = response.get("results", [])
        metrics = response.get("metrics", {})

        # 1. Verification of Fallback search:
        # qdrant_service.search should be called twice: first with branch, second without branch (None)
        self.assertEqual(mock_qdrant_service.search.call_count, 2)
        mock_qdrant_service.search.assert_any_call(
            vector=[0.1, 0.2], repository="test_repo", branch="feature-branch", top_k=10
        )
        mock_qdrant_service.search.assert_any_call(
            vector=[0.1, 0.2], repository="test_repo", branch=None, top_k=10
        )

        # 2. Verification of Deduplication:
        # duplicate point-1 should be removed
        self.assertEqual(len(results), 2)

        # 3. Verification of Prioritization:
        # "changed_file.py" should be ranked first because it is in changed_files,
        # even though "other_file.py" has a higher similarity score (0.9 vs 0.8)
        self.assertEqual(results[0]["metadata"]["relative_path"], "changed_file.py")
        self.assertEqual(results[1]["metadata"]["relative_path"], "other_file.py")

        # 4. Metrics Verification:
        self.assertTrue(metrics.get("repository_context_available"))
        self.assertTrue(metrics.get("branch_filter_used"))
        self.assertTrue(metrics.get("fallback_used"))
        self.assertEqual(metrics.get("top_similarity"), 0.9)
        self.assertEqual(metrics.get("average_similarity"), 0.85)
        self.assertEqual(metrics.get("unique_files"), 2)

    def test_context_metrics_thresholding_and_error_handling(self):
        from unittest.mock import MagicMock
        import asyncio
        from models import ContextRequest
        from routes.search import get_repository_context
        from config import Settings

        # Custom settings with min_similarity = 0.85 (should drop the 0.80 hit)
        custom_settings = Settings(
            min_similarity=0.85,
            top_k_default=5,
            top_k_max=10
        )

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_text.return_value = [0.1, 0.2]

        mock_hits = [
            {
                "id": "p-1",
                "score": 0.90,
                "payload": {"repository": "test_repo", "branch": "main", "relative_path": "a.py", "text": "a"}
            },
            {
                "id": "p-2",
                "score": 0.80, # below threshold 0.85
                "payload": {"repository": "test_repo", "branch": "main", "relative_path": "b.py", "text": "b"}
            }
        ]

        mock_qdrant_service = MagicMock()
        mock_qdrant_service.search.return_value = mock_hits

        app_mock = MagicMock()
        app_mock.state = DummyState(mock_embedding_service, mock_qdrant_service, settings=custom_settings)
        request_mock = DummyRequest(app_mock)

        body = ContextRequest(
            repository="test_repo",
            branch="main",
            changed_files=["a.py"],
            diff="diff"
        )

        # Call endpoint handler directly
        response = asyncio.run(get_repository_context(request_mock, body))
        results = response.get("results", [])
        metrics = response.get("metrics", {})

        # Should only return 1 hit (score 0.90 >= 0.85)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["score"], 0.90)
        self.assertEqual(metrics["top_similarity"], 0.90)

        # Verify error handling
        mock_qdrant_service.search.side_effect = Exception("Qdrant offline!")
        response_err = asyncio.run(get_repository_context(request_mock, body))
        self.assertEqual(response_err.get("results"), [])
        self.assertFalse(response_err.get("metrics", {}).get("repository_context_available"))

class TestPhase2Features(unittest.TestCase):
    def test_python_chunker(self):
        py_code = """
# Header comment
import os

@decorator
class MyClass:
    def method(self):
        pass

def top_func():
    pass
"""
        chunker = Chunker(chunk_size_tokens=5)
        chunks = chunker.chunk_file(py_code, "test.py", "python")
        self.assertTrue(len(chunks) >= 2)
        
    def test_jsonc_cleaner(self):
        jsonc = """
        {
            // single line comment
            "key": "value", /* block comment */
            "arr": [1, 2,], // trailing comma
        }
        """
        chunker = Chunker()
        cleaned = chunker.clean_json_content(jsonc)
        parsed = json.loads(cleaned)
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["arr"], [1, 2])

    def test_heuristic_scoring(self):
        from routes.search import compute_ranking_score_and_reason
        from config import Settings
        
        settings = Settings(
            weight_semantic=0.75,
            bonus_exact_file=0.10,
            bonus_same_dir=0.05,
            bonus_same_module=0.05,
            bonus_config_file=0.05,
            penalty_test_file=0.10,
            penalty_mock_generated=0.15,
            penalty_tiny_chunk=0.10
        )
        
        hit = {
            "score": 0.80,
            "payload": {
                "relative_path": "gateway/redis.py",
                "filename": "redis.py",
                "directory": "gateway",
                "kind": "source",
                "text": "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\nline11"
            }
        }
        score, reason = compute_ranking_score_and_reason(hit, ["gateway/redis.py"], {}, settings)
        self.assertAlmostEqual(score, 0.80)
        self.assertEqual(reason, "Exact changed file")

        hit_test = {
            "score": 0.80,
            "payload": {
                "relative_path": "tests/test_redis.py",
                "filename": "test_redis.py",
                "directory": "tests",
                "kind": "test",
                "text": "def test_redis(): pass"
            }
        }
        score_test, reason_test = compute_ranking_score_and_reason(hit_test, ["gateway/redis.py"], {}, settings)
        self.assertAlmostEqual(score_test, 0.40)
        self.assertEqual(reason_test, "Semantic similarity (Test file)")
        
    def test_framework_and_architecture_detection(self):
        from services.indexer import detect_frameworks_from_files, build_architecture_metadata
        files_set = {"requirements.txt", "Dockerfile", "package.json"}
        frameworks = detect_frameworks_from_files(files_set)
        self.assertIn("Python Project", frameworks)
        self.assertIn("Node.js Project", frameworks)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dc = {
                "services": {
                    "gateway": {"image": "python"},
                    "aggregator": {"image": "python"}
                }
            }
            with open(os.path.join(tmpdir, "docker-compose.yml"), "w") as f:
                import yaml
                yaml.dump(dc, f)
            arch = build_architecture_metadata(tmpdir, ["python"])
            self.assertIn("gateway", arch["services"])
            self.assertEqual(arch["message_bus"], "None")

if __name__ == "__main__":
    unittest.main()
