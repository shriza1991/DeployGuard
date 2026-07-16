import os
import json
import yaml
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger("repository-context-service")

def estimate_tokens(text: str) -> int:
    """Estimates the number of tokens in a text based on word count."""
    return max(1, len(text.split()))

class Chunker:
    def __init__(self, chunk_size_tokens: int = 450, overlap_tokens: int = 100):
        self.chunk_size_tokens = chunk_size_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_file(self, content: str, file_path: str, language: str) -> List[Dict[str, Any]]:
        """
        Chooses the optimal chunking strategy based on file type/language.
        Returns: list of chunks, each dict containing 'text', 'start_line', 'end_line', 'chunk_index'
        """
        if not content.strip():
            return []

        filename = os.path.basename(file_path).lower()
        _, ext = os.path.splitext(filename)

        try:
            if ext == ".py" or language.lower() == "python":
                return self.chunk_python(content)
            elif ext == ".md":
                return self.chunk_markdown(content)
            elif ext in {".json", ".yml", ".yaml"}:
                return self.chunk_json_yaml(content, ext)
            elif ext in {".tf", ".tfvars"}:
                return self.chunk_terraform(content)
            elif filename == "dockerfile":
                return self.chunk_dockerfile(content)
            else:
                return self.chunk_source_code(content)
        except Exception as e:
            logger.warning(f"Specialized chunking failed for {file_path} ({e}). Falling back to line-based chunking.")
            return self.chunk_source_code(content)

    def chunk_source_code(self, content: str) -> List[Dict[str, Any]]:
        """
        Line-based sliding window chunker.
        Preserves whole lines and enforces a token size window with overlap.
        """
        lines = content.splitlines(keepends=True)
        if not lines:
            return []

        # Token count per line
        line_tokens = [estimate_tokens(line) for line in lines]
        chunks = []
        
        start_idx = 0
        chunk_idx = 0
        while start_idx < len(lines):
            current_tokens = 0
            end_idx = start_idx
            
            while end_idx < len(lines):
                current_tokens += line_tokens[end_idx]
                if current_tokens >= self.chunk_size_tokens:
                    break
                end_idx += 1
                
            actual_end_idx = min(end_idx, len(lines) - 1)
            chunk_lines = lines[start_idx:actual_end_idx + 1]
            chunk_text = "".join(chunk_lines)
            
            chunks.append({
                "text": chunk_text,
                "start_line": start_idx + 1,
                "end_line": actual_end_idx + 1,
                "chunk_index": chunk_idx
            })
            chunk_idx += 1
            
            if actual_end_idx == len(lines) - 1:
                break
                
            # Backtrack to satisfy overlap
            overlap_accum = 0
            overlap_start_idx = actual_end_idx
            while overlap_start_idx > start_idx:
                overlap_accum += line_tokens[overlap_start_idx]
                if overlap_accum > self.overlap_tokens:
                    break
                overlap_start_idx -= 1
                
            # Advance start index ensuring forward progress
            if overlap_start_idx == start_idx:
                next_start_idx = actual_end_idx + 1
            else:
                next_start_idx = overlap_start_idx
                
            if next_start_idx <= start_idx:
                next_start_idx = start_idx + 1
                
            start_idx = next_start_idx
            
        return chunks

    def _group_blocks_into_chunks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups small logical blocks into chunks of ~chunk_size_tokens.
        Falls back to line-based chunking for any single block exceeding limits.
        """
        if not blocks:
            return []
            
        chunks = []
        current_group = []
        current_tokens = 0
        group_start = 1
        chunk_idx = 0
        
        for idx, block in enumerate(blocks):
            block_text = block["text"]
            tokens = estimate_tokens(block_text)
            
            if tokens > self.chunk_size_tokens:
                # Flush existing group first
                if current_group:
                    chunks.append({
                        "text": "".join(current_group),
                        "start_line": group_start,
                        "end_line": blocks[idx - 1]["end_line"],
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                    current_group = []
                    current_tokens = 0
                
                # Split the large block using sliding window
                sub_chunks = self.chunk_source_code(block_text)
                offset = block["start_line"] - 1
                for sc in sub_chunks:
                    chunks.append({
                        "text": sc["text"],
                        "start_line": sc["start_line"] + offset,
                        "end_line": sc["end_line"] + offset,
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                
                if idx + 1 < len(blocks):
                    group_start = blocks[idx + 1]["start_line"]
            else:
                if not current_group:
                    group_start = block["start_line"]
                current_group.append(block_text)
                current_tokens += tokens
                
                if current_tokens >= self.chunk_size_tokens:
                    chunks.append({
                        "text": "".join(current_group),
                        "start_line": group_start,
                        "end_line": block["end_line"],
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                    current_group = []
                    current_tokens = 0
                    
        if current_group:
            chunks.append({
                "text": "".join(current_group),
                "start_line": group_start,
                "end_line": blocks[-1]["end_line"],
                "chunk_index": chunk_idx
            })
            
        return chunks

    def chunk_python(self, content: str) -> List[Dict[str, Any]]:
        """
        Specialized Python chunker. Splits code by top-level class or function definition blocks
        before checking token window limits.
        """
        lines = content.splitlines(keepends=True)
        blocks = []
        current_block = []
        start_line = 1
        
        for idx, line in enumerate(lines):
            stripped = line.strip()
            is_decorator = line.startswith('@')
            is_definition = line.startswith('class ') or line.startswith('def ')
            
            if (is_decorator or is_definition) and not line.startswith((' ', '\t')):
                if current_block:
                    blocks.append({
                        "text": "".join(current_block),
                        "start_line": start_line,
                        "end_line": idx
                    })
                    current_block = []
                start_line = idx + 1
            current_block.append(line)
            
        if current_block:
            blocks.append({
                "text": "".join(current_block),
                "start_line": start_line,
                "end_line": len(lines)
            })
            
        return self._group_blocks_into_chunks(blocks)

    def chunk_markdown(self, content: str) -> List[Dict[str, Any]]:
        """
        Specialized Markdown chunker. Splits content by section headings.
        """
        lines = content.splitlines(keepends=True)
        blocks = []
        current_block = []
        start_line = 1
        
        for idx, line in enumerate(lines):
            if line.startswith('#') and (' ' in line or '\t' in line):
                header_match = re.match(r'^#+\s', line)
                if header_match:
                    if current_block:
                        blocks.append({
                            "text": "".join(current_block),
                            "start_line": start_line,
                            "end_line": idx
                        })
                        current_block = []
                    start_line = idx + 1
            current_block.append(line)
            
        if current_block:
            blocks.append({
                "text": "".join(current_block),
                "start_line": start_line,
                "end_line": len(lines)
            })
            
        return self._group_blocks_into_chunks(blocks)

    def clean_json_content(self, content: str) -> str:
        """Strips single/block comments and trailing commas for JSONC/JSON5 parsing."""
        # Strip block comments /* ... */
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Strip single line comments // ...
        content = re.sub(r'//.*', '', content)
        # Strip trailing commas
        content = re.sub(r',\s*([\]}])', r'\1', content)
        return content

    def chunk_json_yaml(self, content: str, ext: str) -> List[Dict[str, Any]]:
        """
        Parses JSON or YAML files and chunks them by preserving complete structures.
        Supports comments and trailing commas for JSON.
        """
        parsed_data = None
        if ext == ".json":
            try:
                cleaned = self.clean_json_content(content)
                parsed_data = json.loads(cleaned)
            except Exception:
                try:
                    parsed_data = yaml.safe_load(content)
                except Exception:
                    pass
        else:
            try:
                parsed_data = yaml.safe_load(content)
            except Exception:
                pass

        if not isinstance(parsed_data, (dict, list)):
            return self.chunk_source_code(content)

        blocks = []
        if isinstance(parsed_data, list):
            for item in parsed_data:
                blocks.append(json.dumps(item, indent=2))
        else:
            for key, val in parsed_data.items():
                blocks.append(json.dumps({key: val}, indent=2))

        chunks = []
        current_blocks = []
        current_tokens = 0
        chunk_idx = 0
        
        for block in blocks:
            tokens = estimate_tokens(block)
            if tokens > self.chunk_size_tokens:
                if current_blocks:
                    chunks.append({
                        "text": "\n\n".join(current_blocks),
                        "start_line": 1,
                        "end_line": 1,
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                    current_blocks = []
                    current_tokens = 0
                
                sub_chunks = self.chunk_source_code(block)
                for sc in sub_chunks:
                    chunks.append({
                        "text": sc["text"],
                        "start_line": sc["start_line"],
                        "end_line": sc["end_line"],
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
            else:
                current_blocks.append(block)
                current_tokens += tokens
                if current_tokens >= self.chunk_size_tokens:
                    chunks.append({
                        "text": "\n\n".join(current_blocks),
                        "start_line": 1,
                        "end_line": 1,
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                    current_blocks = []
                    current_tokens = 0
                    
        if current_blocks:
            chunks.append({
                "text": "\n\n".join(current_blocks),
                "start_line": 1,
                "end_line": 1,
                "chunk_index": chunk_idx
            })
            
        for ch in chunks:
            search_prefix = ch["text"][:100].strip()
            if search_prefix:
                lines = content.splitlines()
                for idx, line in enumerate(lines):
                    if search_prefix in line:
                        ch["start_line"] = idx + 1
                        ch["end_line"] = min(len(lines), idx + ch["text"].count('\n') + 1)
                        break
        return chunks

    def chunk_terraform(self, content: str) -> List[Dict[str, Any]]:
        """
        Parses HCL / Terraform files and extracts resource/data/variable blocks,
        grouping them into semantic chunks.
        """
        lines = content.splitlines(keepends=True)
        blocks = []
        current_block = []
        brace_depth = 0
        in_block = False
        start_line = 1
        
        # Simple brace depth block parser
        for idx, line in enumerate(lines):
            # Ignore comments for brace counting
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
                if in_block:
                    current_block.append((idx + 1, line))
                continue
                
            if not in_block:
                # Check if block starts on this line
                if '{' in line:
                    in_block = True
                    start_line = idx + 1
                    # count '{' and '}' ignoring quotes
                    brace_depth = self._count_unquoted_braces(line)
                    current_block.append((idx + 1, line))
                else:
                    # lines outside blocks (like comments/variables at root)
                    # we can group them as a small block
                    blocks.append({
                        "text": line,
                        "start_line": idx + 1,
                        "end_line": idx + 1
                    })
            else:
                current_block.append((idx + 1, line))
                brace_depth += self._count_unquoted_braces(line)
                if brace_depth <= 0:
                    # Block finished
                    block_text = "".join(l for _, l in current_block)
                    blocks.append({
                        "text": block_text,
                        "start_line": start_line,
                        "end_line": idx + 1
                    })
                    current_block = []
                    brace_depth = 0
                    in_block = False

        if current_block:
            block_text = "".join(l for _, l in current_block)
            blocks.append({
                "text": block_text,
                "start_line": start_line,
                "end_line": len(lines)
            })

        # Group HCL blocks into chunks of ~300-600 tokens
        grouped_chunks = []
        current_group = []
        current_tokens = 0
        group_start = 1
        chunk_idx = 0
        
        for b in blocks:
            tokens = estimate_tokens(b["text"])
            if tokens > self.chunk_size_tokens:
                # Flush current group
                if current_group:
                    grouped_chunks.append({
                        "text": "\n".join(current_group),
                        "start_line": group_start,
                        "end_line": b["start_line"] - 1,
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                    current_group = []
                    current_tokens = 0
                
                # Split large HCL block using line-based chunker
                large_chunks = self.chunk_source_code(b["text"])
                offset = b["start_line"] - 1
                for lc in large_chunks:
                    grouped_chunks.append({
                        "text": lc["text"],
                        "start_line": lc["start_line"] + offset,
                        "end_line": lc["end_line"] + offset,
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                group_start = b["end_line"] + 1
            else:
                if not current_group:
                    group_start = b["start_line"]
                current_group.append(b["text"])
                current_tokens += tokens
                if current_tokens >= self.chunk_size_tokens:
                    grouped_chunks.append({
                        "text": "\n".join(current_group),
                        "start_line": group_start,
                        "end_line": b["end_line"],
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                    current_group = []
                    current_tokens = 0
                    
        if current_group:
            grouped_chunks.append({
                "text": "\n".join(current_group),
                "start_line": group_start,
                "end_line": blocks[-1]["end_line"] if blocks else len(lines),
                "chunk_index": chunk_idx
            })
            
        return grouped_chunks

    def chunk_dockerfile(self, content: str) -> List[Dict[str, Any]]:
        r"""
        Parses Dockerfile and splits by logical instruction groups (handling \ line continuations).
        """
        lines = content.splitlines(keepends=True)
        instructions = []
        current_inst = []
        start_line = 1
        
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if not current_inst:
                start_line = idx + 1
            current_inst.append(line)
            
            # Check if line ends with backslash (line continuation)
            if not stripped.endswith("\\"):
                # Complete instruction
                inst_text = "".join(current_inst)
                instructions.append({
                    "text": inst_text,
                    "start_line": start_line,
                    "end_line": idx + 1
                })
                current_inst = []

        if current_inst:
            inst_text = "".join(current_inst)
            instructions.append({
                "text": inst_text,
                "start_line": start_line,
                "end_line": len(lines)
            })

        # Group Dockerfile instructions into ~300-600 tokens
        grouped_chunks = []
        current_group = []
        current_tokens = 0
        group_start = 1
        chunk_idx = 0
        
        for inst in instructions:
            tokens = estimate_tokens(inst["text"])
            if tokens > self.chunk_size_tokens:
                if current_group:
                    grouped_chunks.append({
                        "text": "\n".join(current_group),
                        "start_line": group_start,
                        "end_line": inst["start_line"] - 1,
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                    current_group = []
                    current_tokens = 0
                
                # Split large instruction using line splitter
                large_chunks = self.chunk_source_code(inst["text"])
                offset = inst["start_line"] - 1
                for lc in large_chunks:
                    grouped_chunks.append({
                        "text": lc["text"],
                        "start_line": lc["start_line"] + offset,
                        "end_line": lc["end_line"] + offset,
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                group_start = inst["end_line"] + 1
            else:
                if not current_group:
                    group_start = inst["start_line"]
                current_group.append(inst["text"])
                current_tokens += tokens
                if current_tokens >= self.chunk_size_tokens:
                    grouped_chunks.append({
                        "text": "\n".join(current_group),
                        "start_line": group_start,
                        "end_line": inst["end_line"],
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                    current_group = []
                    current_tokens = 0
                    
        if current_group:
            grouped_chunks.append({
                "text": "\n".join(current_group),
                "start_line": group_start,
                "end_line": instructions[-1]["end_line"] if instructions else len(lines),
                "chunk_index": chunk_idx
            })
            
        return grouped_chunks

    def _count_unquoted_braces(self, line: str) -> int:
        """Helper to count opening and closing braces ignoring double-quoted strings."""
        count = 0
        in_quotes = False
        escaped = False
        
        for char in line:
            if char == '\\' and in_quotes:
                escaped = not escaped
                continue
            if char == '"' and not escaped:
                in_quotes = not in_quotes
            elif not in_quotes:
                if char == '{':
                    count += 1
                elif char == '}':
                    count -= 1
            escaped = False
        return count
