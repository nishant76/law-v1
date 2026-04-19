import asyncio
import re
from typing import Any, Dict, List, Optional

import httpx

from backend.services.llm_service import get_llm_service
from backend.core.config import settings
from backend.core.logger import get_logger

try:
    import tiktoken
except ImportError:  # pragma: no cover
    tiktoken = None

logger = get_logger(__name__)


class RAGService:
    """RAG pipeline: chunking, embedding, indexing, retrieval."""

    CHUNK_SIZE_TOKENS = 500
    OVERLAP_TOKENS = 50
    EMBED_BATCH_SIZE = 100
    SEARCH_API_VERSION = "2021-04-30-Preview"
    VECTOR_FIELD_NAME = "embedding"
    SEARCH_TIMEOUT = 30
    MAX_DELETE_BATCH = 1000

    def __init__(self):
        self.llm_service = get_llm_service()
        self.search_endpoint = settings.AZURE_SEARCH_ENDPOINT.rstrip("/")
        self.search_key = settings.AZURE_SEARCH_KEY

    def _ensure_configured(self):
        if not self.search_endpoint or not self.search_key:
            raise RuntimeError(
                "Azure Search is not configured. Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY."
            )

    def _validate_firm_id(self, firm_id: str) -> str:
        if not re.fullmatch(r"[0-9a-fA-F\-]+", firm_id):
            raise ValueError("Invalid firm_id format")
        return firm_id

    def _get_index_name(self, firm_id: str) -> str:
        firm_id = self._validate_firm_id(firm_id)
        return f"nikhar-law-{firm_id}"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "api-key": self.search_key,
            "Content-Type": "application/json",
        }

    async def _http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.SEARCH_TIMEOUT)

    def _get_tokenizer(self):
        if tiktoken is None:
            raise ImportError(
                "tiktoken is required for chunking. Install tiktoken in the Python environment."
            )

        return tiktoken.encoding_for_model("text-embedding-ada-002")

    def chunk_document(self, text: str, document_id: str, firm_id: str) -> List[Dict[str, Any]]:
        """Split document text into overlapping chunks using tiktoken."""
        tokenizer = self._get_tokenizer()
        token_ids = tokenizer.encode(text)

        if not token_ids:
            return []

        chunks: List[Dict[str, Any]] = []
        start = 0
        chunk_index = 0

        while start < len(token_ids):
            end = min(start + self.CHUNK_SIZE_TOKENS, len(token_ids))
            chunk_tokens = token_ids[start:end]
            chunk_text = tokenizer.decode(chunk_tokens).strip()

            if chunk_text:
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                        "token_count": len(chunk_tokens),
                        "page_number": 0,
                    }
                )
                chunk_index += 1

            if end == len(token_ids):
                break

            start = end - self.OVERLAP_TOKENS
            if start < 0:
                start = 0

        logger.info(
            f"chunk_document: document_id={document_id}, firm_id={firm_id}, "
            f"chunks={len(chunks)}"
        )
        return chunks

    async def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Embed chunks in batches using text-embedding-ada-002."""
        if not chunks:
            return []

        all_embeddings: List[List[float]] = []
        for start in range(0, len(chunks), self.EMBED_BATCH_SIZE):
            batch = chunks[start : start + self.EMBED_BATCH_SIZE]
            texts = [chunk["text"] for chunk in batch]
            embeddings = await self.llm_service.embed_texts(texts)
            all_embeddings.extend(embeddings)

        if len(all_embeddings) != len(chunks):
            raise ValueError("Embedding service returned an unexpected number of vectors")

        for chunk, embedding in zip(chunks, all_embeddings):
            chunk["embedding"] = embedding

        logger.info(f"embed_chunks: embedded {len(chunks)} chunks")
        return chunks

    async def _ensure_search_index(self, index_name: str) -> None:
        """Ensure Azure AI Search index exists for the firm."""
        self._ensure_configured()
        index_url = f"{self.search_endpoint}/indexes/{index_name}?api-version={self.SEARCH_API_VERSION}"
        headers = self._get_headers()

        async with await self._http_client() as client:
            response = await client.get(index_url, headers=headers)
            if response.status_code == 200:
                return
            if response.status_code != 404:
                response.raise_for_status()

            create_url = index_url
            body = {
                "name": index_name,
                "fields": [
                    {"name": "id", "type": "Edm.String", "key": True, "filterable": False},
                    {"name": "document_id", "type": "Edm.String", "filterable": True, "searchable": False},
                    {"name": "firm_id", "type": "Edm.String", "filterable": True, "searchable": False},
                    {"name": "vertical", "type": "Edm.String", "filterable": True, "searchable": False},
                    {"name": "chunk_index", "type": "Edm.Int32", "filterable": True, "sortable": True},
                    {"name": "text", "type": "Edm.String", "searchable": True, "analyzerName": "en.microsoft"},
                    {
                        "name": self.VECTOR_FIELD_NAME,
                        "type": "Collection(Edm.Single)",
                        "searchable": False,
                        "vectorSearchDimensions": 1536,
                    },
                    {"name": "document_name", "type": "Edm.String", "filterable": True, "searchable": True},
                    {"name": "page_number", "type": "Edm.Int32", "filterable": True},
                ],
                "vectorSearch": {
                    "algorithmConfigurations": [
                        {
                            "@odata.type": "#Microsoft.Azure.Search.HnswVectorSearchAlgorithmConfiguration",
                            "name": "default",
                        }
                    ]
                },
            }

            response = await client.put(create_url, json=body, headers=headers)
            response.raise_for_status()
            logger.info(f"Created Azure Search index: {index_name}")

    async def _upload_documents(self, index_name: str, documents: List[Dict[str, Any]]) -> bool:
        self._ensure_configured()
        payload = {
            "value": [
                {"@search.action": "upload", **document} for document in documents
            ]
        }
        url = f"{self.search_endpoint}/indexes/{index_name}/docs/index?api-version={self.SEARCH_API_VERSION}"
        headers = self._get_headers()

        async with await self._http_client() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code not in (200, 201):
                logger.error(
                    f"Azure Search upload failed ({response.status_code}): {response.text}"
                )
                return False

            logger.info(
                f"Uploaded {len(documents)} chunks to Azure Search index {index_name}"
            )
            return True

    async def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_id: str,
        firm_id: str,
        vertical: str,
        document_name: str,
    ) -> bool:
        """Index embedded chunks into Azure AI Search."""
        if not chunks:
            logger.warning("index_chunks: no chunks to index")
            return True

        if not self.search_endpoint or not self.search_key:
            logger.warning(
                "index_chunks: Azure Search not configured — skipping indexing. "
                "Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY to enable."
            )
            return True

        index_name = self._get_index_name(firm_id)
        await self._ensure_search_index(index_name)

        documents = []
        for chunk in chunks:
            documents.append(
                {
                    "id": f"{document_id}-{chunk['chunk_index']}",
                    "document_id": document_id,
                    "firm_id": firm_id,
                    "vertical": vertical,
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    self.VECTOR_FIELD_NAME: chunk["embedding"],
                    "document_name": document_name,
                    "page_number": chunk.get("page_number", 0),
                }
            )

        return await self._upload_documents(index_name, documents)

    async def delete_document_chunks(self, document_id: str, firm_id: str) -> bool:
        """Remove all chunks for a document from Azure AI Search."""
        index_name = self._get_index_name(firm_id)
        ids = await self._find_chunk_ids(document_id, index_name)
        if not ids:
            logger.info(
                f"delete_document_chunks: no chunks found for document {document_id}"
            )
            return True

        actions = [{"@search.action": "delete", "id": doc_id} for doc_id in ids]
        payload = {"value": actions}
        url = f"{self.search_endpoint}/indexes/{index_name}/docs/index?api-version={self.SEARCH_API_VERSION}"

        async with await self._http_client() as client:
            response = await client.post(url, json=payload, headers=self._get_headers())
            if response.status_code not in (200, 201):
                logger.error(
                    f"Azure Search delete failed ({response.status_code}): {response.text}"
                )
                return False

            logger.info(
                f"Deleted {len(ids)} chunks for document {document_id} from index {index_name}"
            )
            return True

    async def _find_chunk_ids(self, document_id: str, index_name: str) -> List[str]:
        self._ensure_configured()
        search_url = (
            f"{self.search_endpoint}/indexes/{index_name}/docs/search?api-version={self.SEARCH_API_VERSION}"
        )
        payload = {
            "search": "*",
            "filter": f"document_id eq '{document_id}'",
            "select": ["id"],
            "top": self.MAX_DELETE_BATCH,
        }

        async with await self._http_client() as client:
            response = await client.post(search_url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            body = response.json()

        return [hit.get("id") for hit in body.get("value", []) if hit.get("id")]

    async def retrieve_chunks(
        self,
        query: str,
        firm_id: str,
        top_k: int = 10,
        query_vector: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Search firm's RAG index and return the top relevant chunks."""
        if not firm_id:
            return []

        index_name = self._get_index_name(firm_id)
        if query_vector is None:
            query_vector = await self.llm_service.embed_query(query)

        search_url = (
            f"{self.search_endpoint}/indexes/{index_name}/docs/search?api-version={self.SEARCH_API_VERSION}"
        )

        payload: Dict[str, Any] = {
            "search": query or "*",
            "vector": {
                "value": query_vector,
                "fields": self.VECTOR_FIELD_NAME,
                "k": top_k,
                "similarityAlgorithm": "cosine",
            },
            "filter": f"firm_id eq '{firm_id}'",
            "select": [
                "document_id",
                "chunk_index",
                "text",
                "document_name",
                "page_number",
            ],
            "top": top_k,
        }

        async with await self._http_client() as client:
            response = await client.post(search_url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            body = response.json()

        hits = []
        for hit in body.get("value", []):
            hits.append(
                {
                    "document_id": hit.get("document_id"),
                    "chunk_index": hit.get("chunk_index"),
                    "text": hit.get("text", ""),
                    "document_name": hit.get("document_name"),
                    "page_number": hit.get("page_number", 0),
                    "score": hit.get("@search.score", 0.0),
                }
            )

        logger.info(
            f"retrieve_chunks: query='{query[:50]}', firm_id={firm_id}, top_k={top_k}, returned={len(hits)}"
        )
        return hits


_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
