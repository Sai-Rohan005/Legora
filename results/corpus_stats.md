# Corpus statistics — completed

Attempted at 2026-11-17T10:58:48.496307+00:00; Qdrant collection `legal_rag`.

| Act | Unique stored chunks | Graph nodes | Directed graph edges |
|---|---:|---:|---:|
| BNS | 1025 | 1046 | 2090 |
| BNSS | 1694 | 1734 | 1733 |
| BSA | 556 | 569 | 568 |
| Constitution | 1569 | 1578 | 1594 |
| Unmapped | 0 | 0 | 0 |
| Total | 4844 | 4927 | 5985 |

Unavailable counts are not zeros. Chunk counts use distinct stored chunk_id values; graph edges include every stored relationship, including inverse hierarchy edges, and are grouped by their source node's act. Unmapped metadata is retained. Freeze ingestion while collecting these independent read-only counts.

- qdrant: ok.

- neo4j: ok.

Stored points: 4844; unique chunk IDs: 4844; duplicate chunk points: 0; points without chunk IDs: 0.
