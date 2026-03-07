# Notas para desenvolvedores

## cypher-shell e `bracc dev seed`

Se `bracc dev seed` falhar com `unrecognized arguments: '--env'`, substitua `--env NEO4J_PASSWORD` por `-p "${NEO4J_PASSWORD}"` no script `infra/scripts/seed-dev.sh`. O `--env` não funciona com o cypher-shell instalado localmente (ex.: via `pip install neo4j`) ps: pelo menos não no meu rsrs.
