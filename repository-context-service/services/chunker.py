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
            if ext == ".md":
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

    def chunk_markdown(self, content: str) -> List[Dict[str, Any]]:
        """
        Paragraph-based chunker. Groups markdown paragraphs to preserve context.
        """
        # Split by double newlines or similar
        paragraphs = re.split(r'\n\s*\n', content)
        chunks = []
        
        current_paragraphs = []
        current_tokens = 0
        start_line = 1
        chunk_idx = 0
        
        # Track line numbers manually
        para_line_ranges = []
        running_line = 1
        for p in paragraphs:
            p_lines = p.count('\n') + 1
            para_line_ranges.append((running_line, running_line + p_lines - 1))
            running_line += p_lines + 1 # +1 for the double newline split
            
        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]
            tokens = estimate_tokens(para)
            
            # If paragraph itself is huge, chunk it line-by-line as a fallback
            if tokens > self.chunk_size_tokens and not current_paragraphs:
                sub_chunks = self.chunk_source_code(para)
                # Offset line numbers
                offset = para_line_ranges[i][0] - 1
                for sc in sub_chunks:
                    chunks.append({
                        "text": sc["text"],
                        "start_line": sc["start_line"] + offset,
                        "end_line": sc["end_line"] + offset,
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                i += 1
                start_line = para_line_ranges[i][0] if i < len(paragraphs) else running_line
                continue

            current_paragraphs.append(para)
            current_tokens += tokens
            
            if current_tokens >= self.chunk_size_tokens or i == len(paragraphs) - 1:
                end_line = para_line_ranges[i][1]
                chunks.append({
                    "text": "\n\n".join(current_paragraphs),
                    "start_line": start_line,
                    "end_line": end_line,
                    "chunk_index": chunk_idx
                })
                chunk_idx += 1
                
                if i == len(paragraphs) - 1:
                    break
                    
                # Backtrack to overlap (keep last 1-2 paragraphs if appropriate)
                backtrack_count = 0
                backtrack_tokens = 0
                for r_para in reversed(current_paragraphs):
                    r_tokens = estimate_tokens(r_para)
                    if backtrack_tokens + r_tokens > self.overlap_tokens:
                        break
                    backtrack_tokens += r_tokens
                    backtrack_count += 1
                
                # Make sure we don't backtrack all paragraphs
                if backtrack_count >= len(current_paragraphs):
                    backtrack_count = len(current_paragraphs) - 1
                    
                if backtrack_count > 0:
                    i = i - backtrack_count + 1
                else:
                    i += 1
                
                current_paragraphs = []
                current_tokens = 0
                start_line = para_line_ranges[i][0] if i < len(paragraphs) else running_line
            else:
                i += 1
                
        return chunks

    def chunk_json_yaml(self, content: str, ext: str) -> List[Dict[str, Any]]:
        """
        Parses JSON or YAML files and chunks them by preserving complete structures.
        """
        parsed_data = None
        if ext == ".json":
            parsed_data = json.loads(content)
        else:
            parsed_data = yaml.safe_load(content)

        # If data is not a dict or list, fall back
        if not isinstance(parsed_data, (dict, list)):
            return self.chunk_source_code(content)

        blocks = []
        if isinstance(parsed_data, list):
            # Serialize each item
            for item in parsed_data:
                blocks.append(json.dumps(item, indent=2))
        else:
            # Serialize each top-level key-value pair
            for key, val in parsed_data.items():
                blocks.append(json.dumps({key: val}, indent=2))

        # Group blocks together into chunks
        chunks = []
        current_blocks = []
        current_tokens = 0
        chunk_idx = 0
        
        for block in blocks:
            tokens = estimate_tokens(block)
            if tokens > self.chunk_size_tokens:
                # If a single object is larger than chunk limit, split it
                if current_blocks:
                    chunks.append({
                        "text": "\n\n".join(current_blocks),
                        "start_line": 1, # approximate line numbers for parsed structures
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
                        "start_line": 1,
                        "end_line": 1,
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
            
        # Re-assign line numbers by doing string searching in the original content if possible
        # Or simply assign lines by parsing their positions. For simplicity and robustness,
        # we can locate the blocks in the file content.
        for ch in chunks:
            # Try to find the lines containing the first 100 chars of the block text
            search_prefix = ch["text"][:100].strip()
            if search_prefix:
                lines = content.splitlines()
                for idx, line in enumerate(lines):
                    if search_prefix in line:
                        ch["start_line"] = idx + 1
                        # find the end line based on line count of block
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
