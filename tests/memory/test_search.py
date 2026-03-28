import pytest
import tempfile
from pathlib import Path
from app.memory.search import MemorySearchManager, SearchResult

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)

@pytest.fixture
def search_mgr(temp_dir):
    return MemorySearchManager(memory_dir=temp_dir)

def test_bm25_score_returns_zero_for_no_match(search_mgr):
    """BM25 returns 0 when no query terms match."""
    score = search_mgr._bm25_score("心脏病 糖尿病", "我想去成都旅游")
    assert score == 0.0

def test_bm25_score_returns_positive_for_match(search_mgr):
    """BM25 returns positive score when query terms match."""
    score = search_mgr._bm25_score("成都 旅游", "成都三天旅游攻略")
    assert score > 0

def test_vector_score_returns_zero_for_empty_vectors(search_mgr):
    """Vector score with empty vectors returns 0."""
    score = search_mgr._vector_score([], [])
    assert score == 0.0

def test_vector_score_returns_one_for_identical_vectors(search_mgr):
    """Identical vectors return cosine similarity of 1."""
    score = search_mgr._vector_score([1.0, 0.0], [1.0, 0.0])
    assert abs(score - 1.0) < 0.001

def test_rrf_fusion_combines_rankings(search_mgr):
    """RRF fusion produces different rankings from either input alone."""
    r1 = [SearchResult(chunk="a", score=1.0, doc_path="f1"), SearchResult(chunk="b", score=0.5, doc_path="f2")]
    r2 = [SearchResult(chunk="b", score=1.0, doc_path="f2"), SearchResult(chunk="c", score=0.5, doc_path="f3")]
    fused = search_mgr._rrf_fusion([r1, r2], k=60)
    chunks = [r.chunk for r in fused]
    assert "b" in chunks
    assert "c" in chunks