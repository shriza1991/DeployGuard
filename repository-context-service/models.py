from pydantic import BaseModel, Field
from typing import List, Optional

class IndexRequest(BaseModel):
    repository_url: str
    branch: str = "main"

class SearchRequest(BaseModel):
    repository: str
    branch: str = "main"
    query: str
    top_k: int = 10

class ContextRequest(BaseModel):
    repository: str
    branch: str = "main"
    changed_files: List[str]
    diff: str = ""

class CodeChunkMetadata(BaseModel):
    repository: str
    branch: str
    commit: str
    language: str
    relative_path: str
    filename: str
    directory: str
    chunk_index: int
    chunk_count: int
    start_line: int
    end_line: int
    kind: str  # source, documentation, configuration, test
    last_indexed: str

class CodeChunk(BaseModel):
    text: str
    metadata: CodeChunkMetadata

class RepoStatus(BaseModel):
    status: str
    files: int = 0
    chunks: int = 0
    last_indexed: str = ""
    commit: str = ""
    branch: str = ""

class RepoManifest(BaseModel):
    detected_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    infrastructure_technologies: List[str] = Field(default_factory=list)
    number_of_files: int = 0
    number_of_chunks: int = 0
    commit: str = ""
    branch: str = ""
    last_indexed: str = ""
