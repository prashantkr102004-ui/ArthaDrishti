import re
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.vector import vector_literal
from app.models.user import User
from app.rag.embeddings import EmbeddingProvider, get_embedding_provider
from app.schemas.document_search import DocumentSearchResult
from app.services.documents import get_user_document

STOPWORDS = {
    "a",
    "about",
    "and",
    "are",
    "did",
    "do",
    "does",
    "find",
    "in",
    "is",
    "me",
    "mentioned",
    "my",
    "of",
    "on",
    "say",
    "statement",
    "the",
    "this",
    "to",
    "what",
    "where",
}


@dataclass(frozen=True)
class RetrievalConfig:
    top_k: int = 5
    min_score: float = settings.rag_retrieval_min_score


def search_user_document_chunks(
    *,
    db: Session,
    current_user: User,
    query: str,
    document_id: UUID | None = None,
    top_k: int = 5,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[DocumentSearchResult]:
    if top_k < 1 or top_k > 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="top_k must be between 1 and 10.",
        )
    if document_id is not None:
        get_user_document(db, current_user, document_id)

    provider = embedding_provider or get_embedding_provider()
    query_vector = provider.embed(query)
    if any(value != 0 for value in query_vector):
        results = _vector_search(db, current_user, query_vector, provider.model, document_id, top_k)
        if results:
            return results
    return _keyword_fallback(db, current_user, query, document_id, top_k)


def _vector_search(
    db: Session,
    current_user: User,
    query_vector: list[float],
    embedding_model: str,
    document_id: UUID | None,
    top_k: int,
) -> list[DocumentSearchResult]:
    document_filter = "AND c.document_id = :document_id" if document_id is not None else ""
    sql = text(
        f"""
        SELECT
            c.id AS chunk_id,
            c.document_id,
            d.original_filename AS document_name,
            c.page_number,
            c.chunk_index,
            c.text,
            1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.user_id = :user_id
          AND c.embedding_model = :embedding_model
          {document_filter}
          AND (1 - (c.embedding <=> CAST(:embedding AS vector))) >= :min_score
        ORDER BY c.embedding <=> CAST(:embedding AS vector), c.id
        LIMIT :top_k
        """
    )
    rows = db.execute(
        sql,
        {
            "embedding": vector_literal(query_vector),
            "embedding_model": embedding_model,
            "user_id": current_user.id,
            "document_id": document_id,
            "min_score": settings.rag_retrieval_min_score,
            "top_k": top_k,
        },
    ).mappings()
    return [
        DocumentSearchResult(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            document_name=row["document_name"],
            page_number=row["page_number"],
            chunk_index=row["chunk_index"],
            text=row["text"],
            score=round(float(row["score"]), 4),
        )
        for row in rows
    ]


def _keyword_fallback(
    db: Session,
    current_user: User,
    query: str,
    document_id: UUID | None,
    top_k: int,
) -> list[DocumentSearchResult]:
    terms = _search_terms(query)
    if not terms:
        return []
    clauses = []
    params = {
        "user_id": current_user.id,
        "document_id": document_id,
        "top_k": top_k,
    }
    for index, term in enumerate(terms[:5]):
        key = f"term_{index}"
        clauses.append(f"c.text ILIKE :{key}")
        params[key] = f"%{term}%"
    document_filter = "AND c.document_id = :document_id" if document_id is not None else ""
    sql = text(
        f"""
        SELECT
            c.id AS chunk_id,
            c.document_id,
            d.original_filename AS document_name,
            c.page_number,
            c.chunk_index,
            c.text,
            0.5 AS score
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.user_id = :user_id
          {document_filter}
          AND ({' OR '.join(clauses)})
        ORDER BY c.document_id, c.chunk_index
        LIMIT :top_k
        """
    )
    rows = db.execute(sql, params).mappings()
    return [
        DocumentSearchResult(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            document_name=row["document_name"],
            page_number=row["page_number"],
            chunk_index=row["chunk_index"],
            text=row["text"],
            score=float(row["score"]),
        )
        for row in rows
    ]


def _search_terms(query: str) -> list[str]:
    terms = re.findall(r"[a-z0-9₹.]+", query.casefold())
    return [term for term in terms if len(term) >= 3 and term not in STOPWORDS]
