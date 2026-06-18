"""
SELENE OS — FAISS & BM25 Hybrid Vector Store
Semantic memory backend combining dense FAISS approximate nearest-neighbor search
and sparse BM25 keyword retrieval using Reciprocal Rank Fusion (RRF 70/30) and BGE-2 reranking.
"""

import json
import os
import re
import math
from pathlib import Path
from typing import Optional, List, Tuple
from collections import Counter
import structlog

logger = structlog.get_logger(__name__)


def tokenize(text: str) -> List[str]:
    """Tokenize helper for sparse BM25 indexing."""
    return re.findall(r'\w+', text.lower())


class BM25Index:
    """Lightweight pure-Python BM25 keyword search index."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_lengths = []
        self.docs = []  # list of tokenized documents
        self.vocab = set()
        self.df = Counter()  # Document frequencies of terms
        self.avg_doc_len = 0.0

    def add_document(self, text: str):
        tokens = tokenize(text)
        self.docs.append(tokens)
        self.doc_lengths.append(len(tokens))
        
        unique_tokens = set(tokens)
        for token in unique_tokens:
            self.df[token] += 1
            self.vocab.add(token)
            
        self.avg_doc_len = sum(self.doc_lengths) / len(self.docs) if self.docs else 0.0

    def search(self, query: str, limit: int = 20) -> List[Tuple[int, float]]:
        q_tokens = tokenize(query)
        scores = []
        N = len(self.docs)
        if N == 0:
            return []

        for idx, doc_tokens in enumerate(self.docs):
            score = 0.0
            doc_len = self.doc_lengths[idx]
            tf = Counter(doc_tokens)
            
            for q_term in q_tokens:
                if q_term not in self.vocab:
                    continue
                
                df_term = self.df[q_term]
                idf = math.log((N - df_term + 0.5) / (df_term + 0.5) + 1.0)
                
                term_tf = tf[q_term]
                numerator = term_tf * (self.k1 + 1.0)
                denominator = term_tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0)))
                score += idf * (numerator / denominator)
                
            scores.append((idx, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]


class BGEReranker:
    """Cross-encoder reranking helper supporting SentenceTransformers (BGE-2) and Jaccard fallback."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._model = None
        self._failed = False

    def rerank(self, query: str, candidates: List[dict], top_k: int = 5) -> List[dict]:
        if not candidates:
            return []
        
        # Try loading SentenceTransformers CrossEncoder if not already failed
        if not self._failed and self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                import torch
                # Enable CPU execution to prevent GPU out of memory
                device = "cpu"
                if torch.cuda.is_available():
                    device = "cuda"
                self._model = CrossEncoder(self.model_name, device=device)
                logger.info("bge_reranker_loaded", model=self.model_name, device=device)
            except Exception as e:
                logger.warning("bge_reranker_load_failed_using_fallback", error=str(e))
                self._failed = True

        if self._model is not None:
            try:
                pairs = [(query, c.get("text", "")) for c in candidates]
                scores = self._model.predict(pairs)
                for score, c in zip(scores, candidates):
                    c["_score"] = float(score)
                sorted_candidates = sorted(candidates, key=lambda x: x["_score"], reverse=True)
                return sorted_candidates[:top_k]
            except Exception as e:
                logger.error("bge_reranker_prediction_failed", error=str(e))

        # Jaccard lexical overlap + Dense similarity fallback
        query_tokens = set(tokenize(query))
        for c in candidates:
            text_tokens = set(tokenize(c.get("text", "")))
            overlap = len(query_tokens.intersection(text_tokens))
            union = len(query_tokens.union(text_tokens))
            jaccard = overlap / (union if union > 0 else 1.0)
            
            # Combine current RRF score with Jaccard overlap
            c["_score"] = float(c.get("_score", 0.0) * 0.5 + jaccard * 0.5)
        
        sorted_candidates = sorted(candidates, key=lambda x: x["_score"], reverse=True)
        return sorted_candidates[:top_k]


class VectorStore:
    """
    FAISS-backed and BM25-backed vector store for SELENE's Context Engine (Layer 3).
    
    Supports:
    - add(text, metadata)  → embeds (FAISS) and indexes (BM25)
    - search(query, k=5)   → runs dense + sparse hybrid retrieval with RRF 70/30 & BGE-2 reranking
    - persist() / load()   → saves and restores the index and metadata from disk
    """

    def __init__(self, index_path: str, dimension: int = 1536):
        self._index_path = Path(index_path)
        self._dimension = dimension
        self._index = None       # faiss.IndexFlatL2
        self._metadata: List[dict] = []  # parallel list to index vectors
        self._bm25 = BM25Index()
        self._reranker = BGEReranker()
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        try:
            import faiss
            import numpy as np
            self._faiss = faiss
            self._np = np
            self._index = faiss.IndexFlatL2(self._dimension)
            self._initialized = True
            logger.info("vector_store_initialized", dimension=self._dimension)
        except ImportError:
            logger.error("faiss_not_installed", hint="pip install faiss-cpu")
            raise

    async def add(self, text: str, metadata: dict) -> bool:
        """Embeds text and adds it to the FAISS dense index and BM25 sparse index."""
        self._ensure_initialized()
        try:
            vector = await self._embed(text)
            if vector is None:
                return False

            import numpy as np
            vec_array = np.array([vector], dtype="float32")
            self._index.add(vec_array)
            self._metadata.append({"text": text, **metadata})
            
            # Index in BM25
            self._bm25.add_document(text)
            
            logger.debug("vector_added", text_preview=text[:80])
            return True
        except Exception as e:
            logger.error("vector_add_failed", error=str(e))
            return False

    async def search(self, query: str, k: int = 5) -> List[dict]:
        """
        Returns the top-k hybrid search results using RRF 70/30 and BGE-2 reranking.
        """
        self._ensure_initialized()
        if self._index.ntotal == 0:
            return []

        try:
            # ── 1. Dense FAISS Search ──
            vector = await self._embed(query)
            if vector is None:
                return []

            import numpy as np
            query_array = np.array([vector], dtype="float32")
            
            # Retrieve slightly more than k to allow reranking candidates
            faiss_k = max(20, k * 2)
            actual_k = min(faiss_k, self._index.ntotal)
            distances, indices = self._index.search(query_array, actual_k)

            dense_ranks = {}
            for rank_idx, (dist, idx) in enumerate(zip(distances[0], indices[0]), 1):
                if idx < 0 or idx >= len(self._metadata):
                    continue
                dense_ranks[idx] = rank_idx

            # ── 2. Sparse BM25 Search ──
            sparse_results = self._bm25.search(query, limit=faiss_k)
            sparse_ranks = {}
            for rank_idx, (idx, score) in enumerate(sparse_results, 1):
                sparse_ranks[idx] = rank_idx

            # ── 3. Reciprocal Rank Fusion (RRF 70/30) ──
            rrf_candidates = []
            all_candidate_indices = set(dense_ranks.keys()).union(set(sparse_ranks.keys()))
            
            for idx in all_candidate_indices:
                dense_rank = dense_ranks.get(idx)
                sparse_rank = sparse_ranks.get(idx)
                
                # RRF calculation (standard constant k=60)
                dense_rrf = 1.0 / (60.0 + dense_rank) if dense_rank else 0.0
                sparse_rrf = 1.0 / (60.0 + sparse_rank) if sparse_rank else 0.0
                
                # 70/30 weighting
                rrf_score = 0.7 * dense_rrf + 0.3 * sparse_rrf
                
                entry = dict(self._metadata[idx])
                entry["_score"] = float(rrf_score)
                entry["_idx"] = idx
                rrf_candidates.append(entry)

            # Sort by RRF score descending
            rrf_candidates.sort(key=lambda x: x["_score"], reverse=True)

            # ── 4. Cross-Encoder Reranking ──
            top_candidates = rrf_candidates[:faiss_k]
            final_results = self._reranker.rerank(query, top_candidates, top_k=k)
            
            logger.debug("vector_search_complete", query_preview=query[:60], results=len(final_results))
            return final_results
        except Exception as e:
            logger.error("vector_search_failed", error=str(e))
            return []

    def persist(self) -> None:
        """Saves the FAISS index and metadata to disk."""
        if not self._initialized or self._index is None:
            return
        try:
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            import faiss
            faiss.write_index(self._index, str(self._index_path) + ".index")
            with open(str(self._index_path) + ".meta.json", "w") as f:
                json.dump(self._metadata, f)
            logger.info("vector_store_persisted", path=str(self._index_path), entries=len(self._metadata))
        except Exception as e:
            logger.error("vector_store_persist_failed", error=str(e))

    def load(self) -> bool:
        """Loads the FAISS index and metadata, reconstructing the BM25 index."""
        self._ensure_initialized()
        index_file = str(self._index_path) + ".index"
        meta_file = str(self._index_path) + ".meta.json"
        if not os.path.exists(index_file):
            logger.info("vector_store_no_existing_index", path=index_file)
            return False
        try:
            import faiss
            self._index = faiss.read_index(index_file)
            with open(meta_file) as f:
                self._metadata = json.load(f)
            
            # Reconstruct the BM25 index from loaded metadata
            self._bm25 = BM25Index()
            for entry in self._metadata:
                self._bm25.add_document(entry.get("text", ""))
                
            logger.info("vector_store_loaded", entries=len(self._metadata))
            return True
        except Exception as e:
            logger.error("vector_store_load_failed", error=str(e))
            return False

    async def _embed(self, text: str) -> Optional[list[float]]:
        """Generates an embedding vector using OpenAI text-embedding-3-small."""
        try:
            from config.settings import settings
            from openai import AsyncOpenAI

            if not settings.OPENAI_API_KEY:
                # No API key — return a deterministic zero vector for offline testing
                logger.warning("openai_key_missing_using_zero_vector")
                return [0.0] * self._dimension

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=self._dimension,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("embedding_failed", error=str(e))
            return None


# Singleton — initialized lazily on first use
from config.settings import settings as _settings
vector_store = VectorStore(
    index_path=_settings.VECTOR_INDEX_PATH,
    dimension=_settings.VECTOR_DIMENSION,
)
