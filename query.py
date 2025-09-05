#!/usr/bin/env python3
"""
search_api_md.py
Loads a JSON-LD knowledge graph and answer natural language
questions about the project.
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict


# JSON-LD navigation helpers

def graph_nodes(doc):
    return doc.get("@graph", [])

def project_node(doc):
    for n in graph_nodes(doc):
        types = n.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if "SoftwareApplication" in types:
            return n
    return {}

def node_by_id(doc, node_id):
    return next((n for n in graph_nodes(doc) if n.get("@id") == node_id), {})

def install_node(doc):
    proj = project_node(doc)
    for pid in proj.get("hasPart", []):
        n = node_by_id(doc, pid)
        if n.get("@type") == "HowTo":
            return n
    return {}

def itemlist_by_name(doc, keyword):
    """Find an ItemList whose name contains the keyword (case-insensitive)."""
    for n in graph_nodes(doc):
        if n.get("@type") == "ItemList" and keyword.lower() in (n.get("name") or "").lower():
            return n
    return {}

def example_nodes(doc):
    proj = project_node(doc)
    return [node_by_id(doc, pid) for pid in proj.get("hasPart", [])
            if node_by_id(doc, pid).get("@type") == "CreativeWork"]

def license_text(lic):
    if isinstance(lic, dict) and "@id" in lic:
        return lic["@id"]
    if isinstance(lic, str):
        return lic
    return ""


# Retrieval config

FIELDS = [
    ("project:name", lambda g: project_node(g).get("name")),
    ("project:description", lambda g: project_node(g).get("description")),
    ("install:commands", lambda g: "\n".join(install_node(g).get("tool", []) or [])),
    ("features:list", lambda g: "\n".join(li.get("name","") for li in itemlist_by_name(g, "feature").get("itemListElement", []) if isinstance(li, dict))),
    ("platforms:list", lambda g: "\n".join(li.get("name","") for li in itemlist_by_name(g, "platform").get("itemListElement", []) if isinstance(li, dict))),
    ("examples:code", lambda g: "\n\n".join(ex.get("text", "") for ex in example_nodes(g))),
    ("project:license", lambda g: license_text(project_node(g).get("license"))),
    ("project:topics", lambda g: ", ".join(project_node(g).get("applicationCategory", []) or [])),
]

INTENT_KEYWORDS = {
    "purpose": ["what is", "what does", "purpose", "about", "overview"],
    "install": ["install", "installation", "setup", "pip", "how to install"],
    "example": ["example", "usage", "code", "snippet", "how to use"],
    "features": ["feature", "capability", "highlights"],
    "platforms": ["platform", "supported", "python version", "os", "operating system", "architecture"],
    "license": ["license", "licence"],
    "topics": ["topic", "category", "tags", "keywords"],
}

INTENT_FIELD_WEIGHTS = {
    "purpose": {"project:description": 3, "project:name": 1},
    "install": {"install:commands": 3},
    "example": {"examples:code": 3},
    "features": {"features:list": 3},
    "platforms": {"platforms:list": 3},
    "license": {"project:license": 3},
    "topics": {"project:topics": 3},
}


# Retrieval logic

def tokenize(text):
    return [t.lower() for t in text.split()]

def score_chunk(query, text):
    if not text:
        return 0
    qtokens = tokenize(query)
    ttokens = tokenize(text)
    tf = defaultdict(int)
    for t in ttokens:
        tf[t] += 1
    return sum(tf.get(q, 0) for q in qtokens)

def guess_intents(query):
    ql = query.lower()
    hits = [intent for intent, keys in INTENT_KEYWORDS.items() if any(k in ql for k in keys)]
    return hits or ["purpose"]

def format_answer(label, content):
    pretty_label = label.replace(":", " → ").replace("_", " ").title()
    return f"{pretty_label}\n{'-' * len(pretty_label)}\n{content.strip()}"


# CLI

def main():
    parser = argparse.ArgumentParser(
        description="Ask natural language questions about the project_knowledge.jsonld file."
    )
    parser.add_argument("question", help="asking a question, e.g. 'How do I install the sdk?'")
    parser.add_argument("--file", default="project_knowledge.jsonld", help="Path to JSON-LD file")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f" Can't find {path}")
        return

    doc = json.loads(path.read_text(encoding="utf-8"))
    intents = guess_intents(args.question)

    # Gathering all candidate chunks
    chunks = [(label, getter(doc)) for label, getter in FIELDS if getter(doc)]
    if not chunks:
        print("No knowledge found in the JSON-LD.")
        return

    # Picking the best match
    best_label, best_content, best_score = None, None, -1
    for label, content in chunks:
        base = score_chunk(args.question, content)
        weight = 1
        for intent in intents:
            weight += INTENT_FIELD_WEIGHTS.get(intent, {}).get(label, 0)
        total = base * weight if base > 0 else weight if any(i in intents for i in INTENT_FIELD_WEIGHTS) else base
        if total > best_score:
            best_label, best_content, best_score = label, content, total

    if best_label:
        # For long lists or code, just show the first block/line
        if best_label in ("examples:code", "install:commands", "features:list", "platforms:list"):
            best_content = best_content.split("\n\n")[0].strip()
        print(format_answer(best_label, best_content))
    else:
        print("No relevant information found.")

if __name__ == "__main__":
    main()