# Query Model

The starter query model is deliberately small and deterministic.

## Keyword Index

The index tokenizes title and post text, preserves exact technical terms such
as `init_boot.img`, `vendor_boot.img`, `CP2A.260605.012`, `husky`, `Magisk`,
and `fastboot`, and ranks local posts by BM25-like term frequency plus exact
technical term boosts.

## Graph Enrichment

`query-graph` attaches claim and relation context from the graph to each local
result:

- claim IDs
- relation kinds
- claim nodes
- source refs
- tool/target/context labels

## Insufficient Evidence

If a query lacks enough grounded local evidence, the answer renderer returns
`insufficient_evidence`. That is a successful result because it prevents the
agent from pretending the local database knows more than it does.
