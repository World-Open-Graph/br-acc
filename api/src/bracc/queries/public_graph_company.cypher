MATCH (center:Company)
WHERE elementId(center) = $company_id
   OR center.cnpj = $company_identifier
   OR center.cnpj = $company_identifier_formatted
OPTIONAL MATCH p=(center)-[:SOCIO_DE|VENCEU|SANCIONADA|DEVE|RECEBEU_EMPRESTIMO|BENEFICIOU|GEROU_CONVENIO|MUNICIPAL_VENCEU|MUNICIPAL_LICITOU*1..4]-(n)
WHERE length(p) <= $depth
  AND all(
    x IN nodes(p)
    WHERE NOT (
      "Person" IN labels(x)
      OR "Partner" IN labels(x)
      OR "User" IN labels(x)
      OR "Investigation" IN labels(x)
      OR "Annotation" IN labels(x)
      OR "Tag" IN labels(x)
    )
  )
  AND (
    n:Company OR n:Contract OR n:Sanction OR n:Finance OR n:Amendment OR n:Convenio
    OR n:Bid OR n:MunicipalContract OR n:MunicipalBid OR n IS NULL
  )
WITH center, collect(p) AS paths
WITH center,
     reduce(ns = [center], p IN paths | ns + CASE WHEN p IS NULL THEN [] ELSE nodes(p) END) AS raw_nodes,
     reduce(rs = [], p IN paths | rs + CASE WHEN p IS NULL THEN [] ELSE relationships(p) END) AS raw_rels
UNWIND raw_nodes AS n
WITH center, collect(DISTINCT n) AS nodes, raw_rels
UNWIND CASE WHEN size(raw_rels) = 0 THEN [NULL] ELSE raw_rels END AS r
WITH center, nodes, collect(DISTINCT r) AS rels
RETURN nodes,
       [x IN rels WHERE x IS NOT NULL] AS relationships,
       elementId(center) AS center_id
