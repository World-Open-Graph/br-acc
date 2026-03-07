MATCH (p:Payment {source: 'tesouro_emendas'})
RETURN count(p) AS total
