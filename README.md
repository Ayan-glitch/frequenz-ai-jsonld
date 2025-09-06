# Making the Frequenz SDK “AI‑Native”

This mini‑project takes the [Frequenz SDK for Python](https://github.com/frequenz-floss/frequenz-sdk-python) and makes it more understandable and accessible to AI systems by turning its README into a small, machine‑readable knowledge graph and then showing how to query it.

---

## 1. Schema Design

I modelled the project using a mix of [Schema.org](https://schema.org/), [DOAP](https://github.com/edumbill/doap/wiki), and [Dublin Core Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/):

- **Root node**:  
  `SoftwareApplication` + `doap:Project` - covers both end‑user and developer perspectives.
- **Installation**:  
  `HowTo` with `tool` for pip commands.
- **Features**:  
  `ItemList` of `ListItem` entries for functional capabilities.
- **Supported Platforms**:  
  Separate `ItemList` for Python versions, OS, and architectures.
- **License**:  
  `dcterms:license` mapped to an SPDX URL when possible.
- **Topics**:  
  `applicationCategory` from GitHub repo topics.

This shape is simple enough for a small project but still rich enough for search engines, LLMs, and other agents to consume.

---

## 2. Process

### Extraction
- **Metadata**: Pulled from the GitHub REST API (name, description, topics, license, language).
- **README**: Fetched via API, parsed with [`markdown-it-py`](https://markdown-it-py.readthedocs.io/) into an AST
- **Section detection**:  
  - Install commands: fenced code blocks containing `pip install`.
  - Features: bullet list under a heading containing “feature”.
  - Supported platforms: bullet list under a heading containing “platform” or “compatibility”.
- **Output**: Assembled into a JSON‑LD document (`project_knowledge.jsonld`) with the schema above.

### Querying
- Loads the JSON‑LD.
- Detects intent from the question using keyword matching.
- Scores each field for relevance and returns the best match.
- Supports queries like:
  - “What is the Frequenz SDK for”
  - “How do I install the SDK”
  - “List its key features”
  - “What platforms are supported”
  - “What license does it use”

---

## 3. Challenges & Assumptions

- **README variability**: Headings and section names aren’t standardised, so I used partial, case‑insensitive matches for robustness.
- **Features section**: The current README doesn’t have a “Features” list, the extractor will omit that node if it’s not found.
- **No regex**: Parsing with a Markdown AST is more robust but requires a bit more code to walk the tree.

---

## 4. Next Steps & Improvements

If I had more time, I’d:
- **Enrich the graph** with:
  - Usage examples (`CreativeWork` nodes with code snippets).
  - Dependencies from `pyproject.toml` or the GitHub dependency graph API.
  - Release/version info.
- **Integrate with LLMs**:
  - Chunk JSON‑LD nodes and embed them in a vector DB for semantic search.
  - Use the JSON‑LD as a high‑precision grounding source in a RAG pipeline (LangChain, LlamaIndex).
- **Automate updates**:
  - GitHub Action to regenerate JSON‑LD on README changes.
  - Publish to GitHub Pages with `<script type="application/ld+json">` for SEO and AI visibility.

---

## 5. Public Visibility

Publishing this JSON‑LD on a webpage (or embedding it in the project’s README HTML) makes the project more legible to:
- **Search engines** (Google, Bing) for rich snippets.
- **Generative AI tools** (Perplexity, ChatGPT, Copilot) for accurate, grounded answers.
- **Other developers** building tools that consume linked data.

---

## 6. Deliverables

- `fetch.py`- extractor script.
- `query.py`- query script.
- `project_knowledge.jsonld`
- `requirements.txt`
- `README.md`

---
## Closing Notes with LLMO Perspective

If extended for production in the **Large Language Model Optimization (LLMO)** context, I would along with the things mentioned above:


- **Chunking & Metadata Strategy**  
   Split documentation into small, semantically meaningful chunks with metadata (title, file, commit hash) to improve LLM grounding and traceability.

- **Continuous Synchronization**  
   Automate the regeneration of JSON-LD and embeddings via CI/CD pipelines whenever the SDK documentation changes.

- **Ontologies & RDF for relational knowledge**:  
  Moving beyond flat JSON-LD into RDF triples would enable explicit relationships between entities (e.g., “InstallationInstruction dependsOn Dependency”), improving reasoning and graph traversal for LLMs.

- **Hierarchical retrieval with metadata-enhanced embeddings**:  
  Pairing the hierarchical structure of the documentation with embeddings enriched by metadata (such as section titles, commit hashes, and file paths) would allow LLMs to retrieve information with more precision and traceability.

- **Domain-Specific Extensions**  
   Extend the schema with **energy-domain terms** (microgrids, batteries, flexibility markets) so LLMs can link SDK functions to real-world use cases.
