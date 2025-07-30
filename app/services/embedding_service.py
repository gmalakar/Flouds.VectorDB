# =============================================================================
# File: embedding_service.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import hashlib
from typing import List


class EmbeddingService:
    """
    Service for generating text embeddings.
    Note: This is a demo implementation. For production, use actual embedding models.
    """

    @staticmethod
    def generate_embedding(
        text: str, model: str = "sentence-transformers"
    ) -> List[float]:
        """
        Generate deterministic embedding for text based on content hash.
        This ensures identical text produces identical vectors.
        """
        # Normalize text
        normalized_text = text.lower().strip()

        # Create deterministic hash
        text_hash = hashlib.sha256(normalized_text.encode()).hexdigest()

        # Convert to 384-dimensional vector
        embedding = []
        for i in range(384):
            # Use hash bytes to create consistent float values
            byte_idx = i % len(text_hash)
            char_val = int(text_hash[byte_idx], 16) / 15.0  # Normalize to 0-1
            embedding.append(char_val)

        return embedding

    @staticmethod
    def generate_search_embedding(
        query: str, model: str = "sentence-transformers"
    ) -> List[float]:
        """Generate embedding for search query using same method as insert."""
        return EmbeddingService.generate_embedding(query, model)
