# =============================================================================
# File: vector_store.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import logging
from functools import lru_cache
from json import JSONDecodeError, dumps, loads
from threading import Lock
from typing import Any, Dict, List, Optional, cast

from pymilvus import MilvusClient, MilvusException

from app.app_init import APP_SETTINGS
from app.exceptions.custom_exceptions import (
    CollectionError,
    VectorStoreError,
)
from app.logger import get_logger
from app.milvus.base_milvus import BaseMilvus
from app.milvus.connection_pool import milvus_pool
from app.models.embedded_meta import EmbeddedMeta
from app.models.embedded_vector import EmbeddedVector
from app.models.search_request import SearchEmbeddedRequest
from app.utils.log_sanitizer import sanitize_for_log
from app.utils.stopwords_util import get_stopwords

logger = get_logger("Vector Store")

# Check BM25 availability and sparse field support
try:
    from pymilvus import DataType
    from pymilvus.model.sparse import BM25EmbeddingFunction

    _bm25_available = True
    has_sparse_field = hasattr(DataType, "SPARSE_FLOAT_VECTOR")
    logger.info(
        f"BM25 available: {_bm25_available}, Sparse field supported: {has_sparse_field}"
    )
except ImportError as e:
    _bm25_available = False
    has_sparse_field = False
    BM25EmbeddingFunction = None
    logger.warning(f"BM25/Sparse vectors not available: {e}")

# Initialize global BM25 embedder
if _bm25_available and has_sparse_field:
    try:
        _bm25_embedder = cast(Any, BM25EmbeddingFunction)()
        logger.info("BM25 embedder initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize BM25 embedder: {e}")
        _bm25_embedder = None
        _bm25_available = False
else:
    _bm25_embedder = None


class VectorStore(BaseMilvus):
    """
    Thread-safe wrapper for Milvus vector store operations for a tenant.
    Handles collection creation, upsert, and search.
    """

    _milvus_admin_client: Optional[MilvusClient] = None

    OPTIONAL_SEARCH_KEYS = [
        "partition_names",
        "timeout",
        "_async",
        "_callback",
        "guarantee_timestamp",
        "graceful_time",
        "travel_timestamp",
    ]

    def __init__(
        self,
        tenant_code: str,
        user_id: str,
        password: str,
        model_name: str,
        vector_dimension: int = 0,
    ):
        """
        Initialize a thread-safe VectorStore for a tenant.

        Args:
            tenant_code (str): The tenant code.
            user_id (str): The user ID.
            password (str): The user's password.
            model_name (str): The model name.
            vector_dimension (int, optional): The vector dimension. Defaults to 0 (uses default).

        Raises:
            VectorStoreError: If required parameters are missing.
        """
        logger.debug(
            f"Initializing VectorStore for tenant '{sanitize_for_log(tenant_code)}' with user '{sanitize_for_log(user_id)}' and model '{sanitize_for_log(model_name)}'"
        )
        super().__init__()
        if not tenant_code or not user_id or not password or not model_name:
            logger.error(
                "Tenant code, user ID, password, and model name must be provided to initialize VectorStore."
            )
            raise VectorStoreError(
                "Tenant code, user ID, password, and model name must be provided to initialize VectorStore."
            )

        self._tenant_code: str = tenant_code
        self._user_id: str = user_id
        self._password: str = password
        self._model_name: str = model_name
        self._tenant_role_name: str = BaseMilvus._get_tenant_role_name_by_tenant_code(
            tenant_code
        )
        self._vector_dimension: int = (
            vector_dimension
            if vector_dimension > 0
            else getattr(APP_SETTINGS.vectordb, "default_dimension", 768)
        )
        logger.debug(
            f"Using vector dimension: {self._vector_dimension} for tenant '{tenant_code}' and model '{model_name}'"
        )
        self._db_name: str = BaseMilvus._get_db_name_by_tenant_code(tenant_code)
        self._store_name: str = (
            BaseMilvus._get_vector_store_name_by_tenant_code_modelname(
                self._tenant_code, self._model_name
            )
        )
        self._tenant_client: Optional[MilvusClient] = None
        self._lock: Lock = Lock()

    def _get_tenant_client(self) -> MilvusClient:
        """
        Get a pooled MilvusClient for this tenant.

        Returns:
            MilvusClient: The pooled client instance.
        """
        return milvus_pool.get_connection(
            uri=BaseMilvus._get_milvus_url(),
            user=self._user_id,
            password=self._password,
            database=self._db_name,
        )

    @staticmethod
    def _convert_sparse_to_dict(sparse_vec) -> dict:
        """
        Convert a scipy sparse vector to dictionary format for Milvus.

        Args:
            sparse_vec: The sparse vector (scipy format).

        Returns:
            dict: Dictionary representation for Milvus.
        """
        if hasattr(sparse_vec, "tocoo"):
            coo = sparse_vec.tocoo()
            return {int(idx): float(val) for idx, val in zip(coo.col, coo.data)}
        return {}

    @staticmethod
    def _generate_sparse_vectors(chunks: List[str]) -> List[dict]:
        """
        Generate sparse vectors for chunks using BM25.

        Args:
            chunks (List[str]): List of text chunks.

        Returns:
            List[dict]: List of sparse vector dictionaries.
        """
        if not (_bm25_available and _bm25_embedder and has_sparse_field):
            return [{}] * len(chunks)

        try:
            embedder = _bm25_embedder
            if not getattr(embedder, "_is_fitted", False):
                embedder.fit(chunks)
            sparse_result = embedder.encode_documents(chunks)
            sparse_vectors = [
                VectorStore._convert_sparse_to_dict(sv) for sv in sparse_result
            ]
            logger.debug(f"Generated {len(sparse_vectors)} sparse vectors")
            return sparse_vectors
        except (ImportError, AttributeError) as e:
            logger.warning(f"BM25 functionality not available: {e}")
            return [{}] * len(chunks)
        except Exception as e:
            logger.warning(f"Unexpected error generating sparse vectors: {e}")
            return [{}] * len(chunks)

    def _ensure_collection_ready(self) -> None:
        """
        Check if collection exists and load it, raise error if not found.

        Raises:
            CollectionError: If the collection does not exist.
        """
        client = self._get_tenant_client()
        if not client.has_collection(self._store_name):
            raise CollectionError(
                f"Collection '{self._store_name}' does not exist. Please create it first."
            )
        client.load_collection(self._store_name)

    @staticmethod
    def __convert_to_field_data(embedded_vectors: List[EmbeddedVector]) -> List[dict]:
        """
        Convert a list of EmbeddedVector objects to Milvus upsert-ready dicts.

        Args:
            embedded_vectors (List[EmbeddedVector]): List of embedded vectors.

        Returns:
            List[dict]: List of dicts ready for Milvus upsert.
        """
        vector_field_name = BaseMilvus._get_vector_field_name()
        primary_key_name = BaseMilvus._get_primary_key_name()
        chunks = [embedded_vec.chunk for embedded_vec in embedded_vectors]
        sparse_vectors = VectorStore._generate_sparse_vectors(chunks)

        return [
            {
                primary_key_name: embedded_vec.key,
                "chunk": embedded_vec.chunk,
                vector_field_name: embedded_vec.vector,
                "meta": dumps(embedded_vec.metadata) if embedded_vec.metadata else "{}",
                "sparse_vector": sparse_vectors[i],
            }
            for i, embedded_vec in enumerate(embedded_vectors)
        ]

    def insert_data(
        self, embedded_vectors: List[EmbeddedVector], **kwargs: Any
    ) -> None:
        """
        Upsert embedded vectors into the Milvus collection for this tenant (thread-safe).

        Args:
            embedded_vectors (List[EmbeddedVector]): List of vectors to upsert.
            **kwargs: Additional keyword arguments (e.g., auto_flush, partition_name).

        Returns:
            None

        Raises:
            VectorStoreError: If upsert fails.
        """
        import time

        try:
            t0 = time.perf_counter()
            primary_key_name = BaseMilvus._get_primary_key_name()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Primary key name for upsert: {primary_key_name}")

            logger.info(
                f"Upserting {len(embedded_vectors)} vectors into Milvus collection '{self._store_name}'"
            )
            self._ensure_collection_ready()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"Setting collection for tenant '{self._tenant_code}' with user '{self._user_id}'"
                )
            client = self._get_tenant_client()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Using tenant client for collection '{self._store_name}'")

            t1 = time.perf_counter()
            data_to_upsert = self.__convert_to_field_data(embedded_vectors)
            t2 = time.perf_counter()

            upsert_start = time.perf_counter()
            client.upsert(
                collection_name=self._store_name,
                data=data_to_upsert,
                partition_name=kwargs.get("partition_name", ""),
            )
            upsert_end = time.perf_counter()

            logger.info(
                f"Successfully upserted {len(embedded_vectors)} vectors into Milvus collection '{self._store_name}'"
            )

            # Only flush if explicitly requested or for large batches
            threshold = APP_SETTINGS.vectordb.auto_flush_min_batch
            if threshold == 0:
                auto_flush_default = True
            elif threshold > 0:
                auto_flush_default = len(embedded_vectors) >= threshold
            else:
                auto_flush_default = False
            should_auto_flush = kwargs.get("auto_flush", auto_flush_default)
            flush_time = None
            if should_auto_flush:
                flush_start = time.perf_counter()
                client.flush(self._store_name)
                flush_end = time.perf_counter()
                flush_time = flush_end - flush_start
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f"Flushed collection '{self._store_name}' after inserting {len(embedded_vectors)} vectors in {flush_time:.4f}s"
                    )

            logger.info(
                f"Insert timing: setup={t1-t0:.4f}s, convert={t2-t1:.4f}s, upsert={upsert_end-upsert_start:.4f}s, flush={'{:.4f}s'.format(flush_time) if flush_time is not None else 'N/A'}"
            )
        except MilvusException as ex:
            logger.exception(f"Milvus error upserting data into collection: {ex}")
            raise VectorStoreError(
                "Milvus error upserting data into collection"
            ) from ex
        except (ConnectionError, TimeoutError) as ex:
            logger.exception(f"Connection error upserting data into collection: {ex}")
            raise VectorStoreError(
                "Connection error upserting data into collection"
            ) from ex
        except Exception as ex:
            logger.exception(
                f"Unexpected error upserting data into Milvus collection: {ex}"
            )
            raise VectorStoreError(
                "Error upserting data into Milvus collection"
            ) from ex

    def flush_collection(self) -> None:
        """
        Manually flush the collection to ensure data persistence.
        Useful for batch operations where auto_flush is disabled.

        Returns:
            None

        Raises:
            VectorStoreError: If flush fails.
        """
        try:
            client = self._get_tenant_client()
            client.flush(self._store_name)
            logger.info(f"Manually flushed collection '{self._store_name}'")
        except MilvusException as ex:
            logger.exception(f"Milvus error flushing collection: {ex}")
            raise VectorStoreError("Milvus error flushing collection") from ex
        except Exception as ex:
            logger.exception(f"Unexpected error flushing collection: {ex}")
            raise VectorStoreError("Error flushing collection") from ex

    def _get_search_setup(self, request: SearchEmbeddedRequest):
        """
        Common search setup for both dense and hybrid search.

        Args:
            request (SearchEmbeddedRequest): The search request.

        Returns:
            Tuple[MilvusClient, str, Any]: (client, vector_field_name, filter_expr)
        """
        self._ensure_collection_ready()
        client = self._get_tenant_client()
        vector_field_name = BaseMilvus._get_vector_field_name()
        # Note: Model filtering removed as model field is not present in custom schema
        filter_expr = None
        return client, vector_field_name, filter_expr

    def _build_base_search_params(
        self, request: SearchEmbeddedRequest, search_limit: int
    ) -> dict:
        """
        Build base search parameters common to both search types.

        Args:
            request (SearchEmbeddedRequest): The search request.
            search_limit (int): The search result limit.

        Returns:
            dict: Search parameters.
        """
        return {
            "limit": min(search_limit, 100),
            "offset": request.offset or 0,
            "round_decimal": request.round_decimal or -1,
            "output_fields": request.output_fields or ["chunk", "meta"],
            "consistency_level": request.consistency_level or "Bounded",
        }

    def search_store(
        self, search_request: SearchEmbeddedRequest, **kwargs
    ) -> List[EmbeddedMeta]:
        """
        Search for embedded data in the tenant's vector store (thread-safe).

        Args:
            search_request (SearchEmbeddedRequest): The search request.
            **kwargs: Additional keyword arguments.

        Returns:
            List[EmbeddedMeta]: List of search results.
        """
        import time

        t0 = time.perf_counter()
        milvus_client, vector_field_name, filter_expr = self._get_search_setup(
            search_request
        )
        t1 = time.perf_counter()

        # Increase limit if text filtering is needed
        search_limit = search_request.limit or 5
        if (
            hasattr(search_request, "text_filter")
            and search_request.text_filter
            and search_request.text_filter.strip()
        ):
            search_limit += getattr(
                search_request, "increase_limit_for_text_search", 10
            )

        search_params = self._build_base_search_params(search_request, search_limit)
        search_params["search_params"] = {
            "metric_type": search_request.metric_type or "COSINE",
            "params": {"nprobe": min(search_request.nprobe or 16, 256)},
        }

        if filter_expr:
            search_params["filter"] = filter_expr

        for key in ["radius", "range_filter"]:
            if key in kwargs:
                search_params["search_params"]["params"][key] = kwargs[key]

        for key in self.OPTIONAL_SEARCH_KEYS:
            if key in kwargs:
                search_params[key] = kwargs[key]

        t2 = time.perf_counter()
        search_start = time.perf_counter()
        search_results = milvus_client.search(
            collection_name=self._store_name,
            data=[search_request.vector],
            anns_field=vector_field_name,
            **search_params,
        )
        search_end = time.perf_counter()

        # Fast result processing
        filtered_results = []
        score_threshold = getattr(search_request, "score_threshold", None)
        text_filter = getattr(search_request, "text_filter", None)

        if search_results and len(search_results) > 0:
            search_hits = search_results[0]
            for search_hit in search_hits:
                hit: Any = search_hit
                score = getattr(hit, "score", None)
                if (
                    score_threshold is not None
                    and score is not None
                    and score < score_threshold
                ):
                    continue

                entity = getattr(hit, "entity", None)
                if not entity:
                    continue

                if isinstance(entity, dict):
                    chunk_content = entity.get("chunk")
                else:
                    chunk_content = getattr(entity, "chunk", None)
                if not chunk_content:
                    continue

                # Apply text filter if provided
                if text_filter and text_filter.strip():
                    minimum_words_match = getattr(
                        search_request, "minimum_words_match", 1
                    )
                    include_stop_words = getattr(
                        search_request, "include_stop_words", False
                    )
                    if not self._matches_text_filter(
                        text_filter,
                        chunk_content,
                        minimum_words_match,
                        include_stop_words,
                    ):
                        continue

                if isinstance(entity, dict):
                    chunk_metadata = entity.get("meta", "{}")
                else:
                    chunk_metadata = getattr(entity, "meta", "{}")
                if search_request.meta_required:
                    parsed_metadata = self._parse_meta(chunk_metadata)
                    if not parsed_metadata or parsed_metadata == {}:
                        continue
                    chunk_metadata = parsed_metadata
                else:
                    chunk_metadata = (
                        self._parse_meta(chunk_metadata)
                        if isinstance(chunk_metadata, str)
                        else chunk_metadata
                    )

                # Apply metadata filter if provided
                if not self._matches_meta_filter(
                    chunk_metadata, getattr(search_request, "meta_filter", None)
                ):
                    continue

                filtered_results.append(
                    EmbeddedMeta(content=chunk_content, meta=chunk_metadata)
                )

        # Limit results to original requested limit
        original_limit = search_request.limit or 5
        if len(filtered_results) > original_limit:
            filtered_results = filtered_results[:original_limit]

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Retrieved {len(filtered_results)} results from vector store '{self._store_name}'"
            )
        if logger.isEnabledFor(logging.INFO):
            logger.info(
                f"Search timing: setup={t1-t0:.4f}s, param_build={t2-t1:.4f}s, milvus_search={search_end-search_start:.4f}s, results={len(filtered_results)}"
            )
        return filtered_results

    def hybrid_search_store(
        self, search_request: SearchEmbeddedRequest, **kwargs
    ) -> List[EmbeddedMeta]:
        """
        Perform hybrid search using both dense and sparse vectors. Combines results from both searches.

        Args:
            search_request (SearchEmbeddedRequest): The search request.
            **kwargs: Additional keyword arguments.

        Returns:
            List[EmbeddedMeta]: List of hybrid search results.
        """
        milvus_client, vector_field_name, filter_expr = self._get_search_setup(
            search_request
        )
        text_filter = getattr(search_request, "text_filter", None)
        search_limit = min(search_request.limit or 5, 50)  # Limit for each search

        base_search_params = self._build_base_search_params(
            search_request, search_limit
        )
        if filter_expr:
            base_search_params["filter"] = filter_expr

        # Dense vector search
        dense_search_params = base_search_params.copy()
        dense_search_params["search_params"] = {
            "metric_type": search_request.metric_type or "COSINE",
            "params": {"nprobe": min(search_request.nprobe or 16, 256)},
        }

        dense_results = milvus_client.search(
            collection_name=self._store_name,
            data=[search_request.vector],
            anns_field=vector_field_name,
            **dense_search_params,
        )

        # Sparse vector search (if text_filter provided and sparse vectors are available)
        sparse_results = None

        if (
            text_filter
            and text_filter.strip()
            and _bm25_available
            and _bm25_embedder
            and has_sparse_field
        ):
            sparse_query = self._encode_sparse_query_cached(text_filter)
            if sparse_query is not None:
                sparse_search_params = base_search_params.copy()
                sparse_search_params["search_params"] = {
                    "metric_type": "IP",
                    "params": {},
                }

                try:
                    sparse_results = milvus_client.search(
                        collection_name=self._store_name,
                        data=[sparse_query],
                        anns_field="sparse_vector",
                        **sparse_search_params,
                    )
                except MilvusException as e:
                    logger.warning(f"Milvus error during sparse vector search: {e}")
                    sparse_results = None
                except Exception as e:
                    logger.warning(f"Unexpected error during sparse vector search: {e}")
                    sparse_results = None

        # Combine and deduplicate results
        combined_results = self._combine_hybrid_results(
            dense_results, sparse_results, search_request
        )

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Retrieved {len(combined_results)} hybrid results from vector store '{self._store_name}'"
            )
        return combined_results

    @staticmethod
    @lru_cache(maxsize=256)
    def _encode_sparse_query_cached(text_filter: str):
        """Cache BM25 sparse query encoding to avoid repeated computation on identical filters."""
        try:
            if not (_bm25_available and _bm25_embedder and has_sparse_field):
                return None
            embedder = _bm25_embedder
            sparse_result = embedder.encode_queries([text_filter])[0]
            if hasattr(sparse_result, "tocoo"):
                coo = sparse_result.tocoo()
                return {int(idx): float(val) for idx, val in zip(coo.col, coo.data)}
            return {}
        except (ImportError, AttributeError):
            return None
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"BM25 sparse encode failed for filter: {sanitize_for_log(text_filter)} | {e}"
                )
            return None

    def _combine_hybrid_results(
        self, dense_results, sparse_results, search_request: SearchEmbeddedRequest
    ) -> List[EmbeddedMeta]:
        """
        Combine dense and sparse search results using Reciprocal Rank Fusion (RRF).

        Args:
            dense_results: Dense search results.
            sparse_results: Sparse search results.
            search_request (SearchEmbeddedRequest): The search request.

        Returns:
            List[EmbeddedMeta]: Combined search results.
        """
        # Collect results with scores and ranks
        dense_scores = {}
        sparse_scores = {}
        all_items = {}

        # Process dense results
        if dense_results and len(dense_results) > 0:
            for rank, hit in enumerate(dense_results[0]):
                h: Any = hit
                entity = getattr(h, "entity", None)
                if isinstance(entity, dict):
                    key = entity.get(BaseMilvus._get_primary_key_name())
                else:
                    key = (
                        getattr(entity, BaseMilvus._get_primary_key_name(), None)
                        if entity is not None
                        else None
                    )
                if key:
                    score = getattr(h, "score", None)
                    dense_scores[key] = (rank + 1, score)
                    all_items[key] = h

        # Process sparse results
        if sparse_results and len(sparse_results) > 0:
            for rank, hit in enumerate(sparse_results[0]):
                h: Any = hit
                entity = getattr(h, "entity", None)
                if isinstance(entity, dict):
                    key = entity.get(BaseMilvus._get_primary_key_name())
                else:
                    key = (
                        getattr(entity, BaseMilvus._get_primary_key_name(), None)
                        if entity is not None
                        else None
                    )
                if key:
                    score = getattr(h, "score", None)
                    sparse_scores[key] = (rank + 1, score)
                    all_items[key] = h

        # Apply RRF scoring
        rrf_scores = self._calculate_rrf_scores(dense_scores, sparse_scores)

        # Sort by RRF score and create results
        sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        combined_results = []
        score_threshold = getattr(search_request, "score_threshold", None)
        meta_filter = getattr(search_request, "meta_filter", None)

        for key, _ in sorted_items:
            search_hit = all_items[key]
            h: Any = search_hit

            # Apply score threshold to original dense score if available
            if score_threshold is not None and key in dense_scores:
                ds_score = dense_scores[key][1]
                if ds_score is not None and ds_score < score_threshold:
                    continue

            entity = getattr(h, "entity", None)
            if isinstance(entity, dict):
                chunk_content = entity.get("chunk")
            else:
                chunk_content = (
                    getattr(entity, "chunk", None) if entity is not None else None
                )
            if not chunk_content:
                continue

            if isinstance(entity, dict):
                meta_val = entity.get("meta", "{}")
            else:
                meta_val = getattr(entity, "meta", "{}")
            chunk_metadata = self._process_meta(meta_val, search_request)
            if chunk_metadata is None:
                continue

            if not self._matches_meta_filter(chunk_metadata, meta_filter):
                continue

            combined_results.append(
                EmbeddedMeta(content=chunk_content, meta=chunk_metadata)
            )

        # Limit final results
        original_limit = search_request.limit or 5
        return combined_results[:original_limit]

    def _calculate_rrf_scores(self, dense_scores, sparse_scores, k=60):
        """
        Calculate Reciprocal Rank Fusion (RRF) scores.

        RRF(d) = sum(1 / (k + rank(d, q))) for all queries q

        Args:
            dense_scores (dict): Dense result scores.
            sparse_scores (dict): Sparse result scores.
            k (int, optional): RRF parameter. Defaults to 60.

        Returns:
            dict: RRF scores for each key.
        """
        # Pre-calculate reciprocal values to avoid repeated division
        k_float = float(k)

        # Initialize with dense scores
        rrf_scores = {
            key: 1.0 / (k_float + rank) for key, (rank, _) in dense_scores.items()
        }

        # Add sparse score contributions
        for key, (rank, _) in sparse_scores.items():
            sparse_contrib = 1.0 / (k_float + rank)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + sparse_contrib

        return rrf_scores

    def _apply_text_filter(self, text_filter, chunk_content, search_request) -> bool:
        """
        Apply text filter if provided.

        Args:
            text_filter (str): The text filter string.
            chunk_content (str): The chunk content.
            search_request: The search request object.

        Returns:
            bool: True if filter matches, False otherwise.
        """
        if text_filter and text_filter.strip():
            minimum_words_match = getattr(search_request, "minimum_words_match", 1)
            include_stop_words = getattr(search_request, "include_stop_words", False)
            return self._matches_text_filter(
                text_filter, chunk_content, minimum_words_match, include_stop_words
            )
        return True

    def _process_meta(self, chunk_metadata, search_request):
        """
        Process metadata based on requirements.

        Args:
            chunk_metadata: The chunk metadata (str or dict).
            search_request: The search request object.

        Returns:
            dict or None: Parsed metadata or None if not required/invalid.
        """
        if search_request.meta_required:
            parsed_metadata = self._parse_meta(chunk_metadata)
            if not parsed_metadata or parsed_metadata == {}:
                return None
            return parsed_metadata
        return (
            self._parse_meta(chunk_metadata)
            if isinstance(chunk_metadata, str)
            else chunk_metadata
        )

    @staticmethod
    def _matches_meta_filter(
        meta: Optional[Dict[str, Any]], meta_filter: Optional[Dict[str, str]]
    ) -> bool:
        """Check simple case-insensitive substring matches for provided meta filters."""
        if not meta_filter:
            return True
        if not meta or not isinstance(meta, dict):
            return False
        for key, expected in meta_filter.items():
            value = meta.get(key)
            if value is None:
                return False
            if expected.lower() not in str(value).lower():
                return False
        return True

    @staticmethod
    def _matches_text_filter(
        text_filter: str,
        chunk: str,
        minimum_words_match: int = 1,
        include_stop_words: bool = False,
    ) -> bool:
        """
        Check if chunk matches text filter based on word matching criteria.

        Args:
            text_filter (str): The text filter string.
            chunk (str): The chunk content.
            minimum_words_match (int, optional): Minimum words to match. Defaults to 1.
            include_stop_words (bool, optional): Whether to include stop words. Defaults to False.

        Returns:
            bool: True if filter matches, False otherwise.
        """
        stop_words = get_stopwords()

        # Process filter words based on include_stop_words setting
        if include_stop_words:
            filter_words = [
                word.strip().lower() for word in text_filter.split() if word.strip()
            ]
        else:
            filter_words = [
                word.strip().lower()
                for word in text_filter.split()
                if word.strip() and word.strip().lower() not in stop_words
            ]

        # If no words left after processing, return False
        if not filter_words:
            return False

        chunk_lower = chunk.lower()

        # Use minimum of filter word count and minimum_words_match
        required_matches = min(len(filter_words), minimum_words_match)

        # Count matching words with early break
        matched_words = 0
        for word in filter_words:
            if word in chunk_lower:
                matched_words += 1
                if matched_words >= required_matches:
                    return True

        return False

    @staticmethod
    def _parse_meta(meta):
        """
        Robustly parse meta field from string or dict.

        Args:
            meta (str or dict): The meta field.

        Returns:
            dict: Parsed metadata dictionary (empty if invalid).
        """
        if isinstance(meta, str):
            try:
                return loads(meta)
            except JSONDecodeError:
                return {}
        return meta if isinstance(meta, dict) else {}
