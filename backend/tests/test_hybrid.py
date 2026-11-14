from backend.app.retrieval.hybrid import HybridRetriever

def test_hybrid_retriever_returns_relevant_document():
    docs=["The supplier must maintain insurance coverage.","Either party may terminate this agreement with thirty days notice."]
    results=HybridRetriever(docs).search("termination notice",top_k=1)
    assert results and results[0][0]==1
