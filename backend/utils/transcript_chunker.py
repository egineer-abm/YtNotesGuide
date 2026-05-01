"""
Transcript chunking utility for handling long transcripts.
Splits transcripts that exceed the model's token limit.
"""

import re
from typing import Optional

import tiktoken


class TranscriptChunker:
    """Handles splitting and managing transcript chunks for LLM processing."""
    
    def __init__(
        self,
        max_tokens: int = 30000,
        overlap_ratio: float = 0.1,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize the chunker.
        
        Args:
            max_tokens: Maximum tokens per chunk (default 30k for 32k model with buffer)
            overlap_ratio: Overlap between chunks as ratio (default 10%)
            encoding_name: Tiktoken encoding to use
        """
        self.max_tokens = max_tokens
        self.overlap_ratio = overlap_ratio
        self.encoding = tiktoken.get_encoding(encoding_name)
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))
    
    def needs_chunking(self, text: str) -> bool:
        """
        Check if text needs to be chunked.
        
        Args:
            text: Text to check
            
        Returns:
            True if text exceeds max_tokens
        """
        return self.count_tokens(text) > self.max_tokens
    
    def chunk_transcript(self, text: str) -> list[str]:
        """
        Split transcript into chunks that fit within token limits.
        
        Uses sentence boundaries to avoid cutting mid-sentence.
        Includes overlap between chunks for context continuity.
        
        Args:
            text: Full transcript text
            
        Returns:
            List of text chunks
        """
        total_tokens = self.count_tokens(text)
        
        if total_tokens <= self.max_tokens:
            return [text]
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        overlap_tokens = int(self.max_tokens * self.overlap_ratio)
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            # If single sentence exceeds limit, split it further
            if sentence_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split long sentence by words
                word_chunks = self._split_long_text(sentence)
                chunks.extend(word_chunks)
                continue
            
            # Check if adding this sentence would exceed limit
            if current_tokens + sentence_tokens > self.max_tokens:
                # Save current chunk
                chunks.append(" ".join(current_chunk))
                
                # Start new chunk with overlap from previous
                overlap_start = self._find_overlap_start(current_chunk, overlap_tokens)
                current_chunk = current_chunk[overlap_start:] + [sentence]
                current_tokens = sum(self.count_tokens(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Pattern matches sentence boundaries
        pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(pattern, text)
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _split_long_text(self, text: str) -> list[str]:
        """
        Split very long text (like a single long sentence) by words.
        
        Args:
            text: Long text to split
            
        Returns:
            List of chunks
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for word in words:
            word_tokens = self.count_tokens(word + " ")
            
            if current_tokens + word_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_tokens = word_tokens
            else:
                current_chunk.append(word)
                current_tokens += word_tokens
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _find_overlap_start(self, sentences: list[str], target_tokens: int) -> int:
        """
        Find the starting index for overlap sentences.
        
        Args:
            sentences: List of sentences in current chunk
            target_tokens: Target number of overlap tokens
            
        Returns:
            Index to start overlap from
        """
        if not sentences:
            return 0
        
        total_tokens = 0
        for i in range(len(sentences) - 1, -1, -1):
            total_tokens += self.count_tokens(sentences[i])
            if total_tokens >= target_tokens:
                return i
        
        return 0
    
    def estimate_chunks_needed(self, text: str) -> int:
        """
        Estimate how many chunks will be needed.
        
        Args:
            text: Text to estimate for
            
        Returns:
            Estimated number of chunks
        """
        total_tokens = self.count_tokens(text)
        if total_tokens <= self.max_tokens:
            return 1
        
        effective_tokens_per_chunk = self.max_tokens * (1 - self.overlap_ratio)
        return max(1, int(total_tokens / effective_tokens_per_chunk) + 1)
