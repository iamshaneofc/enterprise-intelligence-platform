"""Document ingestion and lifecycle service."""
import os
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.core.exceptions import DocumentProcessingError, DuplicateEntityError, EntityNotFoundError
from backend.app.core.logging import logger
from backend.app.document_processing.storage import storage_manager
from backend.app.document_processing.parsers import DocumentParser
from backend.app.document_processing.chunker import document_chunker
from backend.app.embeddings.provider import get_embedding_provider, validate_embedding_batch
from backend.app.models.document import Document, Chunk


class DocumentService:
    """Manages document upload, deduplication, parsing, chunking, embedding generation, and retrieval."""

    def upload_and_process(
        self,
        workspace_id: str,
        user_id: str,
        filename: str,
        content: bytes,
        db: Session,
    ) -> Document:
        """Process an uploaded document through the complete ingestion pipeline."""
        file_hash = storage_manager.calculate_sha256(content)
        
        # Check for duplicate document in this workspace
        existing = db.query(Document).filter(
            Document.workspace_id == workspace_id,
            Document.file_hash == file_hash,
            Document.status == "completed",
        ).first()
        if existing:
            logger.info(f"Duplicate document detected (hash={file_hash[:8]}). Returning existing document {existing.id}.")
            return existing

        # Clean up any previous failed attempts for this file hash in this workspace
        failed_records = db.query(Document).filter(
            Document.workspace_id == workspace_id,
            Document.file_hash == file_hash,
            Document.status == "failed",
        ).all()
        for f_doc in failed_records:
            logger.info(f"Cleaning up previous failed document attempt {f_doc.id}")
            db.delete(f_doc)
        db.flush()

        # Persist file
        file_path, computed_hash, file_size = storage_manager.save_document(
            workspace_id=workspace_id,
            filename=filename,
            content=content,
        )

        _, ext = os.path.splitext(filename.lower())
        file_type = ext.lstrip(".")

        doc = Document(
            workspace_id=workspace_id,
            title=os.path.splitext(os.path.basename(filename))[0],
            filename=os.path.basename(filename),
            file_path=file_path,
            file_size_bytes=file_size,
            file_type=file_type,
            file_hash=computed_hash,
            status="processing",
            created_by=user_id,
            chunk_count=0,
            doc_metadata={},
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        try:
            # 1. Parse into structured blocks
            blocks = DocumentParser.parse(file_path, file_type)
            
            # 2. Chunk blocks with overlap
            chunks = document_chunker.chunk_blocks(blocks)
            
            if not chunks:
                raise DocumentProcessingError("No extractable chunks found in document")

            # 3. Generate embeddings
            embedder = get_embedding_provider()
            chunk_texts = [c.content for c in chunks]
            embeddings = embedder.embed_batch(chunk_texts)

            # 4. Save chunks with denormalized workspace_id
            for p_chunk, emb in zip(chunks, embeddings):
                db_chunk = Chunk(
                    document_id=doc.id,
                    workspace_id=workspace_id,
                    chunk_index=p_chunk.chunk_index,
                    content=p_chunk.content,
                    chunk_metadata=p_chunk.metadata,
                    embedding=emb,
                )
                db.add(db_chunk)

            doc.status = "completed"
            doc.chunk_count = len(chunks)
            doc.doc_metadata = {
                "blocks_parsed": len(blocks),
                "total_chunks": len(chunks),
                "embedding_model": getattr(embedder, "model", "fake-embedding-1536"),
            }
            db.commit()
            db.refresh(doc)
            logger.info(f"Document {doc.id} ('{doc.title}') processed successfully into {len(chunks)} chunks.")
            return doc

        except Exception as e:
            logger.error(f"Error processing document {doc.id}: {str(e)}", exc_info=True)
            doc.status = "failed"
            doc.error_message = str(e)
            db.commit()
            raise DocumentProcessingError(f"Failed to process document '{filename}': {str(e)}")

    def get_document(self, document_id: str, db: Session) -> Document:
        """Fetch a document by ID."""
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise EntityNotFoundError(f"Document {document_id} not found")
        return doc

    def list_workspace_documents(self, workspace_id: str, db: Session) -> List[Document]:
        """List all documents belonging to a workspace."""
        return db.query(Document).filter(Document.workspace_id == workspace_id).order_by(Document.created_at.desc()).all()

    def get_document_chunks(self, document_id: str, db: Session) -> List[Chunk]:
        """Fetch all indexed chunks for a document."""
        return db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index.asc()).all()

    def delete_document(self, document_id: str, db: Session) -> bool:
        """Delete document record, its indexed chunks, and file on disk."""
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise EntityNotFoundError(f"Document {document_id} not found")
        
        # Remove file from disk
        storage_manager.delete_document(doc.file_path)

        # Delete from DB (chunks cascade automatically)
        db.delete(doc)
        db.commit()
        return True

    def reindex_document(self, document_id: str, db: Session) -> Document:
        """Re-parse, re-chunk, and re-embed an existing document from disk using the active embedding provider."""
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise EntityNotFoundError(f"Document {document_id} not found")

        file_path = doc.file_path
        if not os.path.exists(file_path):
            from backend.app.core.config import settings
            candidate = os.path.join(settings.STORAGE_DIR, doc.workspace_id, os.path.basename(file_path or doc.filename))
            if os.path.exists(candidate):
                file_path = candidate
            else:
                raise DocumentProcessingError(f"Original document file not found on disk at {doc.file_path}")

        try:
            # 1. Re-parse
            blocks = DocumentParser.parse(file_path, doc.file_type)

            # 2. Re-chunk
            chunks = document_chunker.chunk_blocks(blocks)
            if not chunks:
                raise DocumentProcessingError("No extractable chunks found in document during re-indexing")

            # 3. Generate embeddings with active provider
            embedder = get_embedding_provider()
            chunk_texts = [c.content for c in chunks]
            embeddings = embedder.embed_batch(chunk_texts)

            # 4. Remove previous chunks
            db.query(Chunk).filter(Chunk.document_id == doc.id).delete()

            # 5. Insert new chunks
            for p_chunk, emb in zip(chunks, embeddings):
                db_chunk = Chunk(
                    document_id=doc.id,
                    workspace_id=doc.workspace_id,
                    chunk_index=p_chunk.chunk_index,
                    content=p_chunk.content,
                    chunk_metadata=p_chunk.metadata,
                    embedding=emb,
                )
                db.add(db_chunk)

            doc.status = "completed"
            doc.chunk_count = len(chunks)
            doc.doc_metadata = {
                "blocks_parsed": len(blocks),
                "total_chunks": len(chunks),
                "embedding_model": getattr(embedder, "model", "text-embedding-3-small"),
            }
            db.commit()
            db.refresh(doc)
            logger.info(f"Successfully re-indexed document {doc.id} ({doc.filename}) with {len(chunks)} chunks.")
            return doc
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to re-index document {doc.id}: {str(e)}")
            raise DocumentProcessingError(f"Failed to re-index document '{doc.filename}': {str(e)}")


document_service = DocumentService()

