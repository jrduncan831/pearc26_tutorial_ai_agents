import os
import re
import numpy as np
import pickle
from typing import List, Dict, Any, Optional, Tuple
import uuid
from sentence_transformers import SentenceTransformer

def recursive_chunk(text: str, max_size: int = 300, min_size: int = 100) -> List[str]:
    """Split text recursively into reasonable-length chunks."""
    if len(text) <= max_size:
        return [text]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_size:
            current += (" " if current else "") + sent
        else:
            if current:
                chunks.append(current)
            if len(sent) > max_size:
                words = sent.split()
                chunk = []
                for w in words:
                    if sum(len(x)+1 for x in chunk) + len(w) + 1 <= max_size:
                        chunk.append(w)
                    else:
                        chunks.append(' '.join(chunk))
                        chunk = [w]
                if chunk:
                    chunks.append(' '.join(chunk))
                current = ""
            else:
                current = sent
    if current:
        chunks.append(current)
    merged = []
    for ch in chunks:
        if merged and len(merged[-1]) + len(ch) + 1 < min_size:
            merged[-1] += " " + ch
        else:
            merged.append(ch)
    return [x.strip() for x in merged if x.strip()]

class HistoryVectorStore:
    def __init__(self, name: str, model_name: str = "all-MiniLM-L6-v2"):
        self.name = name
        self.model = SentenceTransformer(model_name)
        self.entries: List[Dict[str, Any]] = []
        self._dir = "vectorstores"
        os.makedirs(self._dir, exist_ok=True)
        self._path = os.path.join(self._dir, f"{self.name}.pkl")
        self._load_or_init()

    def _load_or_init(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "rb") as f:
                    self.entries = pickle.load(f)
            except Exception:
                self.entries = []
        else:
            self.entries = []

    def _save(self):
        with open(self._path, "wb") as f:
            pickle.dump(self.entries, f, protocol=pickle.HIGHEST_PROTOCOL)

    def add_message(self, session_id: str, role: str, content: str, chunk_size: int = 300):
        chunks = recursive_chunk(content, max_size=chunk_size)
        for idx, chunk in enumerate(chunks):
            embedding = self.model.encode(chunk, normalize_embeddings=True)
            entry = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "role": role,
                "orig_content": content,
                "chunk_index": idx,
                "chunk_text": chunk,
                "embedding": embedding
            }
            self.entries.append(entry)
        self._save()  # Save after each new message/chunk

    def build_from_history(self, history: List[Dict[str, Any]], session_id: Optional[str] = None, chunk_size: int = 300):
        for msg in history:
            sid = session_id or msg.get("session_id", "unknown")
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            self.add_message(sid, role, content, chunk_size=chunk_size)
        self._save()  # Save after massive build, in addition to per add

    def search(self, query: str, top_k: int = 5, session_id: Optional[str] = None) -> List[Tuple[float, Dict[str, Any]]]:
        query_embedding = self.model.encode(query, normalize_embeddings=True)
        filtered = [e for e in self.entries if (session_id is None or e["session_id"] == session_id)]
        if not filtered:
            return []
        embeddings = np.vstack([e["embedding"] for e in filtered])
        similarities = np.dot(embeddings, query_embedding)
        top_indices = np.argsort(-similarities)[:top_k]
        return [(float(similarities[i]), filtered[i]) for i in top_indices]

    @classmethod
    def load(cls, name: str, model_name: str = "all-MiniLM-L6-v2"):
        obj = cls(name=name, model_name=model_name)
        return obj

