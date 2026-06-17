"""Curated, real, publicly-available document sources across domains + noise."""

# arXiv search queries → technical research papers (abstracts = small; full PDF = large)
ARXIV_QUERIES = [
    ("cat:cs.CL AND abs:large language model", "technical_paper"),
    ("cat:cs.IR AND abs:retrieval", "technical_paper"),
    ("cat:cs.CL AND abs:retrieval augmented generation", "technical_paper"),
    ("cat:cs.AI AND abs:agent", "technical_paper"),
    ("cat:cs.CL AND abs:context", "technical_paper"),
    ("cat:cs.LG AND abs:transformer", "technical_paper"),
    ("cat:cs.CL AND abs:prompt", "technical_paper"),
    ("cat:cs.IR AND abs:ranking", "technical_paper"),
]

# Real framework/product documentation pages (static HTML → trafilatura).
DOC_URLS = [
    ("https://fastapi.tiangolo.com/tutorial/first-steps/", "framework_docs"),
    ("https://fastapi.tiangolo.com/tutorial/body/", "framework_docs"),
    ("https://fastapi.tiangolo.com/async/", "framework_docs"),
    ("https://fastapi.tiangolo.com/tutorial/dependencies/", "framework_docs"),
    ("https://kubernetes.io/docs/concepts/overview/", "framework_docs"),
    ("https://kubernetes.io/docs/concepts/workloads/pods/", "framework_docs"),
    ("https://kubernetes.io/docs/concepts/services-networking/service/", "framework_docs"),
    ("https://react.dev/learn/thinking-in-react", "framework_docs"),
    ("https://react.dev/learn/state-a-components-memory", "framework_docs"),
    ("https://modelcontextprotocol.io/docs/concepts/architecture", "framework_docs"),
    ("https://modelcontextprotocol.io/docs/concepts/transports", "framework_docs"),
    ("https://docs.python.org/3/tutorial/classes.html", "framework_docs"),
    ("https://docs.python.org/3/tutorial/datastructures.html", "framework_docs"),
    ("https://peps.python.org/pep-0008/", "framework_docs"),
]

# Wikipedia article titles by domain (real long-form/business/technical articles).
WIKI_TITLES = {
    "technical_article": [
        "Large language model", "Transformer (deep learning architecture)",
        "Retrieval-augmented generation", "Vector database", "Information retrieval",
        "Attention (machine learning)", "Word embedding", "BERT (language model)",
        "Reinforcement learning from human feedback", "Prompt engineering",
        "Semantic search", "Knowledge graph", "Cosine similarity", "Tf–idf",
    ],
    "business": [
        "Annual report", "Financial statement", "Balance sheet", "Income statement",
        "Initial public offering", "Venture capital", "Software as a service",
        "Business model", "Return on investment", "Market capitalization",
    ],
    "noise_food": [
        "Chocolate chip cookie", "Lasagne", "Sushi", "Pizza", "Risotto",
        "Croissant", "Tiramisu", "Pad thai", "Paella", "Ramen",
    ],
    "noise_sports": [
        "Association football", "FIFA World Cup", "Basketball", "Cricket",
        "Tennis", "Formula One", "Marathon", "Olympic Games", "Rugby football", "Baseball",
    ],
    "noise_travel": [
        "Backpacking (travel)", "Mount Everest", "Grand Canyon", "Eiffel Tower",
        "Kyoto", "Santorini", "Patagonia", "Great Barrier Reef", "Machu Picchu", "Banff National Park",
    ],
    "noise_finance": [
        "Stock market", "Cryptocurrency", "Bitcoin", "Inflation", "Interest rate",
        "Hedge fund", "Mutual fund", "Exchange-traded fund", "Bond (finance)", "Foreign exchange market",
    ],
}

# Wikipedia categories to pull extra volume from (category members → extracts).
WIKI_CATEGORIES = [
    ("Category:Machine learning", "technical_article", 120),
    ("Category:Natural language processing", "technical_article", 120),
    ("Category:Large language models", "technical_article", 60),
    ("Category:Italian cuisine", "noise_food", 80),
    ("Category:Association football", "noise_sports", 80),
    ("Category:World Heritage Sites", "noise_travel", 80),
    ("Category:Financial markets", "noise_finance", 80),
    ("Category:Software companies", "business", 80),
]
