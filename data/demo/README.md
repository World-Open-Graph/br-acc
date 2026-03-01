# Demo Data (Synthetic)

This directory is reserved for synthetic, public-safe demo data only.

Rules:
- No real CPF or personal identifiers.
- No `Person` / `Partner` labels.
- No operational metadata.

Use generator:

```bash
python3 scripts/generate_demo_dataset.py --output data/demo/synthetic_graph.json
```
If your are using Docker:

```bash
$ docker exec -it infra-api /bin/bash
root@container:/app app_scripts/generate_demo_dataset.py --output data/demo/synthetic_graph.json

```

