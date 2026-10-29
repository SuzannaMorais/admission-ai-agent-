from admission_agent.knowledge_base import load_knowledge_base, search_knowledge_base


def test_search_finds_relevant_fee_entry():
    kb = load_knowledge_base()
    results = search_knowledge_base("admission fee for grade 3", kb)
    assert any("fee" in r["category"] for r in results)


def test_search_returns_empty_for_unrelated_query():
    kb = load_knowledge_base()
    assert search_knowledge_base("xyzxyz nonsense query", kb) == []
