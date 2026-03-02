# Reference Metrics

This document tracks **reference production snapshot** metrics for transparency.

- dataset_scope: `reference_production_snapshot`
- as_of_utc: `2026-03-01T23:05:00Z`
- node_count: `219430848`
- relationship_count: `97451843`

These numbers are not the expected output of `make bootstrap-demo`.

## Provenance Queries

```cypher
MATCH (n) RETURN count(n) AS node_count;
MATCH ()-[r]->() RETURN count(r) AS relationship_count;
```
