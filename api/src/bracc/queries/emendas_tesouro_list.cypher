MATCH (p:Payment {source: 'tesouro_emendas'})
OPTIONAL MATCH (p)-[r:PAGO_PARA]->(c:Company)
RETURN p, r, c
ORDER BY coalesce(p.date, "1900-01-01") DESC, coalesce(p.value, 0.0) DESC
SKIP $skip
LIMIT $limit
