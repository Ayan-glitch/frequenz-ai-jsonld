#!/usr/bin/env python3
"""
fetch_api_md.py
Pulls metadata and README content from a GitHub repo, parses the README with markdown-it-py,
and produces a JSON-LD knowledge graph.
"""

import argparse
import base64
import json
from datetime import datetime, timezone

import requests
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode


# GitHub API helpers

def github_get(url, token=None):
    """Simple GET with optional token auth and error handling."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

def get_repo_info(owner, repo, token=None):
    return github_get(f"https://api.github.com/repos/{owner}/{repo}", token)

def get_readme(owner, repo, token=None):
    data = github_get(f"https://api.github.com/repos/{owner}/{repo}/readme", token)
    return base64.b64decode(data["content"]).decode("utf-8")



# Markdown parsing helpers

def parse_md(md_text):
    """Turning Markdown text into a syntax tree."""
    parser = MarkdownIt()
    return SyntaxTreeNode(parser.parse(md_text))

def first_para_after_title(ast):
    """Grabing the first paragraph after the H1 title."""
    for node in ast.children:
        if node.type == "heading" and node.level == 1:
            siblings = node.parent.children
            idx = siblings.index(node)
            for nxt in siblings[idx+1:]:
                if nxt.type == "paragraph":
                    return nxt.content.strip()
    return None

def find_install_cmds(ast):
    """Looking for pip install commands in fenced code blocks."""
    cmds = []
    for node in ast.walk():
        if node.type == "fence" and "pip install" in node.content:
            for line in node.content.splitlines():
                if "pip install" in line:
                    cmds.append(line.strip())
    # preserve order, drop duplicates
    return list(dict.fromkeys(cmds))

def list_after_heading(ast, keywords):
    """
    Finding a bullet list right after a heading containing any of the given keywords.
    Matching is case-insensitive and partial.
    """
    keys_lower = [kw.lower() for kw in keywords]
    for node in ast.walk():
        if node.type == "heading" and node.level in (2, 3):
            heading_text = node.content.strip().lower()
            if any(kw in heading_text for kw in keys_lower):
                siblings = node.parent.children
                idx = siblings.index(node)
                for nxt in siblings[idx+1:]:
                    if nxt.type == "bullet_list":
                        items = []
                        for item in nxt.children:
                            text = " ".join(
                                c.content.strip() for c in item.walk() if c.type == "text"
                            )
                            if text:
                                items.append(text)
                        return items
    return []


# JSON-LD builder

CONTEXT = {
    "@vocab": "http://schema.org/",
    "schema": "http://schema.org/",
    "doap": "http://usefulinc.com/ns/doap#",
    "dcterms": "http://purl.org/dc/terms/",
    "spdx": "https://spdx.org/licenses/"
}

def build_jsonld(meta, ast):
    now = datetime.now(timezone.utc).isoformat()
    repo_url = meta["html_url"]
    name = meta["name"]
    description = meta["description"] or first_para_after_title(ast)
    license_info = meta.get("license")
    topics = meta.get("topics", [])
    language = meta.get("language", "Python")

    install_cmds = find_install_cmds(ast)
    features = list_after_heading(ast, ["feature", "key feature"])
    platforms = list_after_heading(ast, ["supported platform", "compatibility"])

    root = {
        "@id": repo_url,
        "@type": ["SoftwareApplication", "doap:Project"],
        "name": name,
        "description": description,
        "codeRepository": repo_url,
        "programmingLanguage": language,
        "applicationCategory": topics or None,
        "license": {"@id": f"https://spdx.org/licenses/{license_info['spdx_id']}.html"} if license_info else None,
        "hasPart": []
    }

    graph = [root]

    if install_cmds:
        howto_id = f"{repo_url}#howto-install"
        root["hasPart"].append(howto_id)
        graph.append({
            "@id": howto_id,
            "@type": "HowTo",
            "name": f"Install {name}",
            "tool": install_cmds
        })

    if features:
        feat_id = f"{repo_url}#features"
        root["hasPart"].append(feat_id)
        graph.append({
            "@id": feat_id,
            "@type": "ItemList",
            "name": "Key Features",
            "itemListElement": [
                {"@type": "ListItem", "position": i+1, "name": f}
                for i, f in enumerate(features)
            ]
        })

    if platforms:
        plat_id = f"{repo_url}#supported-platforms"
        root["hasPart"].append(plat_id)
        graph.append({
            "@id": plat_id,
            "@type": "ItemList",
            "name": "Supported Platforms",
            "itemListElement": [
                {"@type": "ListItem", "position": i+1, "name": p}
                for i, p in enumerate(platforms)
            ]
        })

    return {
        "@context": CONTEXT,
        "@graph": graph,
        "dcterms:modified": now
    }


# CLI

def main():
    parser = argparse.ArgumentParser(
        description="Extract GitHub repo info + README into JSON-LD."
    )
    parser.add_argument("repo", help="owner/repo, frequenz-floss/frequenz-sdk-python")
    parser.add_argument("--token", help="GitHub personal access token")
    parser.add_argument("--out", default="project_knowledge.jsonld", help="Output file name")
    args = parser.parse_args()

    owner, repo = args.repo.split("/", 1)
    meta = get_repo_info(owner, repo, args.token)
    readme_md = get_readme(owner, repo, args.token)
    ast = parse_md(readme_md)
    doc = build_jsonld(meta, ast)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"Knowledge graph saved to {args.out}")

if __name__ == "__main__":
    main()