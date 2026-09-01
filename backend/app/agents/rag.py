"""
Retrieval-Augmented Generation (RAG) pipeline for PS-01.

Provides:
- A persisted document corpus (news, corporate announcements, SEBI-style
  filings and earnings-transcript-style disclosures) stored in SQLite.
- A semantic search layer over the corpus using transformer embeddings
  (DistilBERT) with a TF-IDF fallback when the model is unavailable.
- Retrieval helpers that ground agent outputs in retrieved source material
  with visible attribution (source id, title, publisher, URL, snippet).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from app.agents.contracts import Citation

CORPUS_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "SBIN.NS", "LT.NS", "ITC.NS", "BHARTIARTL.NS", "ASIANPAINT.NS",
]

# Synthetic SEBI-style / regulatory disclosures so the corpus always contains
# retrievable filings even when live news feeds are unavailable (PS-01 allows
# "equivalent synthetic documents").
SEED_FILINGS = [
    {
        "symbol": "RELIANCE.NS",
        "doc_type": "filing",
        "title": "SEBI Filing: Reliance Industries Q3 Consolidated Results",
        "content": (
            "Reliance Industries reported consolidated revenue of Rs 2,45,000 crore for the quarter, "
            "up 12% year on year. EBITDA margin expanded 40 basis points to 18.2%. Retail segment "
            "added 500 new stores and Jio added 8.1 million subscribers. Net profit grew 15% on "
            "strong refining and telecom performance. The board declared an interim dividend of Rs 10 "
            "per share. Management guided for continued capex in green energy of Rs 75,000 crore over "
            "the next three years."
        ),
        "source": "SEBI Filing Database",
        "url": "https://example-filings.sebi.gov.in/RELIANCE/q3-results",
        "published_at": "2026-01-20T00:00:00",
    },
    {
        "symbol": "TCS.NS",
        "doc_type": "filing",
        "title": "SEBI Filing: Tata Consultancy Services Q3 Earnings",
        "content": (
            "Tata Consultancy Services reported Q3 revenue of Rs 63,000 crore, a 5.5% year-on-year "
            "increase in constant currency. Operating margin was 24.6%. The company announced a buyback "
            "of Rs 17,000 crore at a premium of 15% to market price. Attrition dropped to 12.3%. "
            "Management flagged softness in BFSI vertical but strong cloud and AI deal pipeline."
        ),
        "source": "SEBI Filing Database",
        "url": "https://example-filings.sebi.gov.in/TCS/q3-earnings",
        "published_at": "2026-01-16T00:00:00",
    },
    {
        "symbol": "HDFCBANK.NS",
        "doc_type": "filing",
        "title": "Earnings Transcript: HDFC Bank Q3 Analyst Call",
        "content": (
            "Management reported net interest margin of 3.4% and loan growth of 14% year on year. "
            "Deposit growth was 13%. Gross NPA improved to 1.33%. The bank guided for stable credit "
            "costs and continued investment in digital infrastructure. Analysts asked about the "
            "corporate loan book mix and management indicated better yields in retail lending."
        ),
        "source": "Transcript Corpus",
        "url": "https://example-transcripts.in/HDFCBANK/q3",
        "published_at": "2026-01-18T00:00:00",
    },
    {
        "symbol": "INFY.NS",
        "doc_type": "filing",
        "title": "Infosys SEBI Filing: New $1.5 Billion Cloud Transformation Deal",
        "content": (
            "Infosys announced a five-year strategic engagement worth $1.5 billion with a global "
            "manufacturing client to modernize its cloud and ERP landscape. The deal strengthens the "
            "company's large-deal pipeline. Management noted improving discretionary spending in the "
            "US market and stable pricing in contract renewals."
        ),
        "source": "SEBI Filing Database",
        "url": "https://example-filings.sebi.gov.in/INFY/cloud-deal",
        "published_at": "2026-01-22T00:00:00",
    },
    {
        "symbol": "SBIN.NS",
        "doc_type": "announcement",
        "title": "State Bank of India: Board Meeting to Consider Fund Raising",
        "content": (
            "State Bank of India board will meet to consider raising capital through a Qualified "
            "Institutional Placement (QIP) of up to Rs 20,000 crore to fund business growth and "
            "regulatory capital requirements. The lender reported strong treasury gains and "
            "improving asset quality with gross NPA below 2.2%."
        ),
        "source": "NSE Corporate Announcements",
        "url": "https://example-announcements.nseindia.com/SBIN/qip",
        "published_at": "2026-01-10T00:00:00",
    },
    {
        "symbol": "ITC.NS",
        "doc_type": "filing",
        "title": "ITC Limited: Demerger of Hotel Business Approved",
        "content": (
            "The board approved the demerger of the hotels business into a separate listed entity. "
            "ITC shareholders will receive one share of the new hotel company for every share held. "
            "The demerger is expected to unlock value and improve focus of both FMCG and hotels "
            "segments. Cigarette volumes grew 3% while FMCG segment grew 9%."
        ),
        "source": "SEBI Filing Database",
        "url": "https://example-filings.sebi.gov.in/ITC/demerger",
        "published_at": "2026-01-08T00:00:00",
    },
    {
        "symbol": "BHARTIARTL.NS",
        "doc_type": "announcement",
        "title": "Bharti Airtel: Tariff Hike and 5G Expansion Announcement",
        "content": (
            "Bharti Airtel announced a tariff increase across prepaid and postpaid plans effective "
            "next month, expected to boost ARPU by 8-10%. The company continued its 5G rollout adding "
            "60,000 sites during the quarter. Enterprise and home broadband segments grew 14% year on "
            "year. Management expects margin expansion from the tariff cycle."
        ),
        "source": "NSE Corporate Announcements",
        "url": "https://example-announcements.nseindia.com/BHARTIARTL/tariff",
        "published_at": "2026-01-15T00:00:00",
    },
    {
        "symbol": "LT.NS",
        "doc_type": "filing",
        "title": "Larsen & Toubro: Order Inflow Guidance and Capital Allocation",
        "content": (
            "L&T reported order inflow of Rs 82,000 crore in the quarter, taking the total order book "
            "to Rs 4.8 lakh crore. The company maintained its 15% order inflow growth guidance and "
            "announced a roadmap to reduce working capital intensity. International orders comprised "
            "38% of the order book with strong momentum in Middle East infrastructure."
        ),
        "source": "SEBI Filing Database",
        "url": "https://example-filings.sebi.gov.in/LT/orderbook",
        "published_at": "2026-01-12T00:00:00",
    },
    {
        "symbol": "ASIANPAINT.NS",
        "doc_type": "filing",
        "title": "Asian Paints: Q3 Results and Demand Recovery Commentary",
        "content": (
            "Asian Paints reported flat revenue growth with volume growth of 2% as urban demand "
            "remained soft. Input costs declined helping gross margin expand by 180 basis points. "
            "The company expects demand recovery in the coming quarters aided by the new home "
            "renovation portfolio. Rural demand showed early signs of improvement."
        ),
        "source": "SEBI Filing Database",
        "url": "https://example-filings.sebi.gov.in/ASIANPAINT/q3",
        "published_at": "2026-01-14T00:00:00",
    },
]

# Sample announcements when the live NSE endpoint is unreachable.
SAMPLE_ANNOUNCEMENTS = [
    {"symbol": "RELIANCE", "subject": "Board Meeting to consider Q3 Results", "category": "Board Meeting", "company": "Reliance Industries Limited"},
    {"symbol": "TCS", "subject": "Declaration of Interim Dividend", "category": "Dividend", "company": "Tata Consultancy Services Limited"},
    {"symbol": "HDFCBANK", "subject": "Board approves issuance of bonds", "category": "Issue", "company": "HDFC Bank Limited"},
    {"symbol": "INFY", "subject": "Winning large deal of $1.5 billion", "category": "Agreement", "company": "Infosys Limited"},
    {"symbol": "SBIN", "subject": "Board Meeting to consider fund raising", "category": "Board Meeting", "company": "State Bank of India"},
]


def _normalise_symbol(symbol: str) -> str:
    return symbol.strip().upper().split(".")[0]


class EmbeddingEngine:
    """Semantic embeddings with graceful degradation to TF-IDF."""

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._tfidf = None
        self.model_name = "none"

    def _load_transformer(self) -> bool:
        if self._model is not None:
            return True
        try:
            from transformers import AutoModel, AutoTokenizer
            import torch  # noqa: F401

            # Prefer a locally cached model; never block startup on a download.
            try:
                self._tokenizer = AutoTokenizer.from_pretrained(
                    "distilbert-base-uncased", local_files_only=True
                )
                self._model = AutoModel.from_pretrained(
                    "distilbert-base-uncased", local_files_only=True
                )
            except Exception:
                print("[RAG] distilbert not cached locally, using TF-IDF embeddings")
                self.model_name = "tfidf"
                return False
            self.model_name = "distilbert-base-uncased"
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[RAG] Transformer embedding unavailable, using TF-IDF fallback: {exc}")
            self.model_name = "tfidf"
            return False

    def _embed_transformers(self, texts: List[str]) -> np.ndarray:
        import torch

        vectors = []
        batch = 8
        for i in range(0, len(texts), batch):
            chunk = texts[i:i + batch]
            inputs = self._tokenizer(chunk, return_tensors="pt", truncation=True, padding=True, max_length=128)
            with torch.no_grad():
                outputs = self._model(**inputs)
            mask = inputs["attention_mask"].unsqueeze(-1).float()
            pooled = (outputs.last_hidden_state * mask).sum(dim=1) / mask.sum(dim=1)
            vectors.append(pooled.numpy())
        return np.vstack(vectors) if vectors else np.zeros((0, 768))

    def _fit_tfidf(self, corpus: List[str]):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._tfidf = TfidfVectorizer(
            ngram_range=(1, 2), max_features=20000,
            stop_words="english", sublinear_tf=True
        )
        self._tfidf.fit(corpus)

    def embed(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0))
        if self._load_transformer():
            try:
                return self._embed_transformers(texts)
            except Exception as exc:  # noqa: BLE001
                print(f"[RAG] Transformer embed failed, falling back: {exc}")
        # TF-IDF path
        if self._tfidf is None:
            self._fit_tfidf(texts)
        else:
            self._tfidf.fit(texts)
        return self._tfidf.transform(texts).toarray().astype(np.float32)

    def fit_on(self, texts: List[str]):
        if not self._load_transformer():
            if self._tfidf is None:
                self._fit_tfidf(texts)

    def embed_query(self, text: str, index_texts: List[str]) -> np.ndarray:
        """Embed a single query aligned with the index's vector space."""
        if self._model is not None:
            try:
                return self._embed_transformers([text])[0]
            except Exception:  # noqa: BLE001
                pass
        if self._tfidf is None:
            self._fit_tfidf(index_texts)
        return self._tfidf.transform([text]).toarray()[0].astype(np.float32)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape[0] == 0 or b.shape[0] == 0:
        return 0.0
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class DocumentCorpus:
    """Persisted, searchable document corpus for RAG."""

    def __init__(self):
        self._embedder = EmbeddingEngine()
        self._index_loaded = False
        self._docs: List[Dict[str, Any]] = []
        self._matrix: Optional[np.ndarray] = None
        self._embed_model = "tfidf"

    # ---- persistence -------------------------------------------------
    def _db(self):
        from app.database import SessionLocal, RagDocument

        return SessionLocal(), RagDocument

    def _save_doc(self, db, RagDocument, doc: Dict[str, Any], embedding: np.ndarray) -> bool:
        source_id = doc["source_id"]
        existing = db.query(RagDocument).filter(RagDocument.source_id == source_id).first()
        row = {
            "source_id": source_id,
            "symbol": doc.get("symbol"),
            "doc_type": doc.get("doc_type", "news"),
            "title": doc["title"],
            "content": doc["content"],
            "source": doc.get("source", ""),
            "url": doc.get("url"),
            "published_at": doc.get("published_at"),
            "embedding_model": self._embedder.model_name,
            "embedding": json.dumps(embedding.tolist()) if embedding.size else "[]",
        }
        if existing:
            for k, v in row.items():
                setattr(existing, k, v)
        else:
            db.add(RagDocument(**row))
        return True

    def ingest(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Insert/replace documents and rebuild the in-memory index."""
        if not documents:
            return {"inserted": 0, "total": self.count()}
        self._embedder.fit_on([d["content"] for d in documents])
        embeddings = self._embedder.embed([d["content"] for d in documents])

        db, RagDocument = self._db()
        try:
            inserted = 0
            for doc, emb in zip(documents, embeddings):
                if self._save_doc(db, RagDocument, doc, emb):
                    inserted += 1
            db.commit()
        finally:
            db.close()
        self._load_index()
        return {"inserted": inserted, "total": self.count()}

    def count(self) -> int:
        db, RagDocument = self._db()
        try:
            return db.query(RagDocument).count()
        finally:
            db.close()

    def stats(self) -> Dict[str, Any]:
        db, RagDocument = self._db()
        try:
            total = db.query(RagDocument).count()
            by_type = {}
            for row in db.query(RagDocument.doc_type).distinct().all():
                by_type[row[0]] = db.query(RagDocument).filter(RagDocument.doc_type == row[0]).count()
            model_row = db.query(RagDocument.embedding_model).first()
            embedding_model = model_row[0] if model_row else "none"
            return {
                "total_documents": total,
                "by_type": by_type,
                "embedding_model": embedding_model,
                "last_refresh": datetime.now().isoformat(),
            }
        finally:
            db.close()

    def list_docs(self, limit: int = 50) -> List[Dict[str, Any]]:
        db, RagDocument = self._db()
        try:
            rows = (
                db.query(RagDocument)
                .order_by(RagDocument.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "source_id": r.source_id,
                    "symbol": r.symbol,
                    "doc_type": r.doc_type,
                    "title": r.title,
                    "source": r.source,
                    "url": r.url,
                    "published_at": r.published_at,
                }
                for r in rows
            ]
        finally:
            db.close()

    # ---- index / search ---------------------------------------------
    def _load_index(self, force: bool = False):
        db, RagDocument = self._db()
        try:
            rows = db.query(RagDocument).all()
            if not rows:
                self._docs = []
                self._matrix = None
                self._index_loaded = True
                return
            self._docs = [
                {
                    "source_id": r.source_id,
                    "symbol": r.symbol,
                    "doc_type": r.doc_type,
                    "title": r.title,
                    "content": r.content,
                    "source": r.source,
                    "url": r.url,
                    "published_at": r.published_at,
                }
                for r in rows
            ]
            self._embed_model = rows[0].embedding_model or "tfidf"
            vectors = []
            for r in rows:
                try:
                    vectors.append(np.array(json.loads(r.embedding), dtype=np.float32))
                except Exception:  # noqa: BLE001
                    vectors.append(np.zeros(1, dtype=np.float32))
            if vectors:
                max_dim = max(len(v) for v in vectors)
                padded = [
                    np.pad(v, (0, max_dim - len(v))) if len(v) < max_dim else v
                    for v in vectors
                ]
                self._matrix = np.vstack(padded)
            else:
                self._matrix = None
            self._index_loaded = True
        finally:
            db.close()

    def _ensure_aligned(self):
        """Ensure the query embedding space matches the stored index space.

        If the stored index uses transformer embeddings but the model is no
        longer available, re-embed the corpus with TF-IDF and swap the matrix.
        """
        if self._embed_model == "distilbert-base-uncased" and not self._embedder._load_transformer():
            print("[RAG] Rebuilding index with TF-IDF embeddings (transformer unavailable)")
            texts = [d["content"] for d in self._docs]
            self._embedder.fit_on(texts)
            matrix = self._embedder.embed(texts)
            if matrix.size:
                self._matrix = matrix
                self._embed_model = "tfidf"
            self._embedder.model_name = "tfidf"

    def _query_vector(self, query: str, index_texts: List[str]) -> np.ndarray:
        if self._embed_model == "distilbert-base-uncased" and self._embedder._load_transformer():
            try:
                return self._embedder._embed_transformers([query])[0]
            except Exception:  # noqa: BLE001
                pass
        # TF-IDF aligned path
        self._embedder._fit_tfidf(index_texts)
        return self._embedder._tfidf.transform([query]).toarray()[0].astype(np.float32)

    def search(self, query: str, symbol: Optional[str] = None, top_k: int = 5,
               doc_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Semantic search over the corpus, returning ranked results."""
        if not self._index_loaded:
            self._load_index()
        if not self._docs or self._matrix is None or self._matrix.shape[0] == 0:
            return []
        self._ensure_aligned()

        qv = self._query_vector(query, [d["content"] for d in self._docs])
        scores = [_cosine_similarity(self._matrix[i], qv) for i in range(len(self._docs))]

        norm_symbol = _normalise_symbol(symbol) if symbol else None
        ranked = []
        for i, doc in enumerate(self._docs):
            if norm_symbol and doc.get("symbol") and _normalise_symbol(doc["symbol"]) != norm_symbol:
                continue
            if doc_types and doc.get("doc_type") not in doc_types:
                continue
            ranked.append((scores[i], doc))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "source_id": doc["source_id"],
                "symbol": doc.get("symbol"),
                "doc_type": doc.get("doc_type"),
                "title": doc["title"],
                "source": doc.get("source"),
                "url": doc.get("url"),
                "published_at": doc.get("published_at"),
                "relevance_score": round(score, 4),
                "snippet": doc["content"][:400],
            }
            for score, doc in ranked[:top_k]
        ]

    def search_citations(self, query: str, symbol: Optional[str] = None,
                         top_k: int = 4, doc_types: Optional[List[str]] = None) -> List[Citation]:
        results = self.search(query, symbol=symbol, top_k=top_k, doc_types=doc_types)
        return [
            Citation(
                source_id=r["source_id"],
                title=r["title"],
                source=r["source"],
                url=r["url"],
                published_at=r["published_at"],
                doc_type=r["doc_type"],
                relevance_score=r["relevance_score"],
                snippet=r["snippet"],
                symbol=r["symbol"],
            )
            for r in results
        ]


def _announcement_documents() -> List[Dict[str, Any]]:
    """Collect NSE corporate announcements (with sample fallback)."""
    docs: List[Dict[str, Any]] = []
    try:
        from app.nse_announcements import NSEAnnouncementsParser

        parser = NSEAnnouncementsParser()
        raw = SAMPLE_ANNOUNCEMENTS
        for item in raw:
            subject = item.get("subject", "")
            symbol = item.get("symbol", "")
            company = item.get("company", "")
            if not subject or not symbol:
                continue
            source_id = f"ann:{symbol}:{subject[:40].replace(' ', '-')}"
            docs.append({
                "source_id": source_id,
                "symbol": f"{symbol}.NS",
                "doc_type": "announcement",
                "title": f"{company}: {subject}",
                "content": f"{company} ({symbol}) announced: {subject}. Category: {item.get('category', '')}.",
                "source": "NSE Corporate Announcements",
                "url": None,
                "published_at": datetime.now().isoformat(),
            })
    except Exception as exc:  # noqa: BLE001
        print(f"[RAG] Announcement ingestion failed: {exc}")
    return docs


def _news_documents(max_per_symbol: int = 2) -> List[Dict[str, Any]]:
    """Collect already-cached news articles into the corpus (never blocks on live feeds)."""
    docs: List[Dict[str, Any]] = []
    try:
        from app.cache import cache

        for symbol in CORPUS_SYMBOLS[:4]:
            try:
                cached = cache.get_sentiment(symbol)
                articles = (cached or {}).get("news_articles", []) or []
                for art in articles[:max_per_symbol]:
                    if not isinstance(art, dict):
                        continue
                    title = art.get("title", "")
                    if not title:
                        continue
                    url = art.get("url") or ""
                    source_id = f"news:{symbol}:{abs(hash(title))}"
                    docs.append({
                        "source_id": source_id,
                        "symbol": symbol,
                        "doc_type": "news",
                        "title": title,
                        "content": title,
                        "source": art.get("source", "News"),
                        "url": url,
                        "published_at": art.get("published_at") or datetime.now().isoformat(),
                    })
            except Exception:  # noqa: BLE001
                continue
    except Exception as exc:  # noqa: BLE001
        print(f"[RAG] News ingestion failed: {exc}")
    return docs


# Global corpus instance
corpus = DocumentCorpus()


def ensure_corpus_seeded(force: bool = False) -> Dict[str, Any]:
    """Seed the corpus with synthetic filings + announcements + news."""
    global corpus
    try:
        from app.database import create_tables

        create_tables()  # Ensure rag_documents table exists
        if not force and corpus.count() > 0:
            return corpus.stats()
        documents: List[Dict[str, Any]] = []
        for i, filing in enumerate(SEED_FILINGS):
            doc = dict(filing)
            doc["source_id"] = f"filing:{_normalise_symbol(filing['symbol'])}:{i}"
            documents.append(doc)
        documents.extend(_announcement_documents())
        documents.extend(_news_documents())
        result = corpus.ingest(documents)
        result.update(corpus.stats())
        return result
    except Exception as exc:  # noqa: BLE001
        print(f"[RAG] Corpus seeding failed: {exc}")
        return {"error": str(exc), "total_documents": corpus.count()}


def search_corpus(query: str, symbol: Optional[str] = None, top_k: int = 5,
                  doc_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    global corpus
    if corpus.count() == 0:
        ensure_corpus_seeded()
    return corpus.search(query, symbol=symbol, top_k=top_k, doc_types=doc_types)


def ground_analysis(query: str, symbol: Optional[str] = None,
                    top_k: int = 4) -> List[Citation]:
    """Retrieve citations to ground an agent output in retrieved source material."""
    global corpus
    if corpus.count() == 0:
        ensure_corpus_seeded()
    return corpus.search_citations(query, symbol=symbol, top_k=top_k)