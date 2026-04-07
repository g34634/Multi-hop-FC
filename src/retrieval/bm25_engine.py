import pickle
import re
from pathlib import Path
from rank_bm25 import BM25Okapi
from nltk.stem.porter import PorterStemmer
from src.common.config import Config

# Standard English stopwords
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at", 
    "from", "by", "for", "with", "about", "against", "between", "into", "through", 
    "during", "before", "after", "above", "below", "to", "up", "down", "in", "out", 
    "on", "off", "over", "under", "again", "further", "then", "once", "here", 
    "there", "all", "any", "both", "each", "few", "more", "most", "other", "some", 
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", 
    "s", "t", "can", "will", "just", "don", "should", "now", "i", "me", "my", 
    "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", 
    "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", 
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves", 
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", 
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", 
    "do", "does", "did", "doing", "was", "were", "be", "been", "being"
}

class BM25Engine:
    def __init__(self, config: Config):
        self.config = config
        self.bm25 = None
        self.chunks = []  # To store the original chunk objects (for metadata and text)
        self.stemmer = PorterStemmer()
        self.load_index()

    def tokenize(self, text: str) -> list[str]:
        """
        Refined tokenizer: 
        1. lowercase 
        2. split by alphanum patterns (preserving years/entities)
        3. filter stopwords
        4. Apply Porter Stemming
        """
        if not text:
            return []
        
        # Keep alphanumeric and some special chars if needed, but for BM25 usually just words+numbers
        raw_tokens = re.findall(r"\b\w+\b", text.lower())
        
        refined_tokens = [
            self.stemmer.stem(t) for t in raw_tokens 
            if t not in STOPWORDS and len(t) > 1
        ]
        
        return refined_tokens

    def build_index(self, chunks: list[dict]):
        """
        Build BM25 index from a list of chunks.
        Each chunk is a dict: {'id': str, 'text': str, 'metadata': dict}
        """
        if not chunks:
            print("[BM25] No chunks provided to build index.")
            return

        print(f"[BM25] Building index for {len(chunks)} chunks (with stemming & stopword removal)...")
        self.chunks = chunks
        tokenized_corpus = [self.tokenize(c["text"]) for c in chunks]
        
        # Pass k1 and b from config
        self.bm25 = BM25Okapi(
            tokenized_corpus, 
            k1=self.config.bm25_k1, 
            b=self.config.bm25_b
        )
        self.save_index()

    def save_index(self):
        """
        Save the BM25 index and the associated chunks to a pickle file.
        """
        if self.bm25 is None or not self.chunks:
            return

        self.config.bm25_index_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "bm25": self.bm25,
            "chunks": self.chunks
        }
        with open(self.config.bm25_index_path, "wb") as f:
            pickle.dump(data, f)
        print(f"[BM25] Index saved to {self.config.bm25_index_path}")

    def load_index(self):
        """
        Load the BM25 index and chunks from the pickle file if it exists.
        """
        if self.config.bm25_index_path.exists():
            try:
                with open(self.config.bm25_index_path, "rb") as f:
                    data = pickle.load(f)
                    self.bm25 = data["bm25"]
                    self.chunks = data["chunks"]
                print(f"[BM25] Index loaded from {self.config.bm25_index_path} ({len(self.chunks)} chunks)")
            except Exception as e:
                print(f"[BM25] Failed to load index: {e}")

    def query(self, query_text: str, n_results: int = 5) -> dict:
        """
        Query the BM25 index and return results in a format similar to ChromaDB.
        """
        if self.bm25 is None or not self.chunks:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        tokenized_query = self.tokenize(query_text)
        # scores are not normalized, but higher is better
        scores = self.bm25.get_scores(tokenized_query)
        
        # Sort by score (descending)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n_results]
        
        ids = []
        docs = []
        metas = []
        dist_scores = []  # We use the raw BM25 score here

        for i in top_indices:
            chunk = self.chunks[i]
            ids.append(chunk["id"])
            docs.append(chunk["text"])
            metas.append(chunk["metadata"])
            dist_scores.append(scores[i])

        return {
            "ids": [ids],
            "documents": [docs],
            "metadatas": [metas],
            "distances": [dist_scores],  # Named distances for compatibility, but contains BM25 scores
        }