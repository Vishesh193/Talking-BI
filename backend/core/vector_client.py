import os
import logging
import chromadb
from chromadb.utils import embedding_functions
from core.config import settings

logger = logging.getLogger(__name__)

# Persistent storage directory
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma")
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

# Shared client
_client = None

def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        logger.info(f"🚀 ChromaDB persistent client initialized at {CHROMA_PERSIST_DIR}")
    return _client

def get_session_collection(session_id: str):
    client = get_chroma_client()
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    # We use a single collection for all sessions but filter by metadata for performance,
    # or separate collections for isolation. Let's use one collection for "semantic recall" 
    # as the user specified, which might involve cross-session/long-term recall later.
    return client.get_or_create_collection(
        name="talking_bi_memory",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )
