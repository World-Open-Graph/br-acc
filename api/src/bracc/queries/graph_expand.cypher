MATCH (center)
WHERE elementId(center) = $entity_id
  AND (center:Person OR center:Company OR center:Contract OR center:Sanction OR center:Election
       OR center:Amendment OR center:Finance OR center:Embargo OR center:Health OR center:Education
       OR center:Convenio OR center:LaborStats OR center:PublicOffice
       OR center:OffshoreEntity OR center:OffshoreOfficer OR center:GlobalPEP
       OR center:CVMProceeding OR center:Expense)
OPTIONAL MATCH p=(center)-[:SOCIO_DE|DOOU|CANDIDATO_EM|VENCEU|AUTOR_EMENDA|SANCIONADA|OPERA_UNIDADE|DEVE|RECEBEU_EMPRESTIMO|EMBARGADA|MANTEDORA_DE|BENEFICIOU|GEROU_CONVENIO|SAME_AS|POSSIBLY_SAME_AS|OFFICER_OF|INTERMEDIARY_OF|GLOBAL_PEP_MATCH|CVM_SANCIONADA|GASTOU|FORNECEU*1..4]-(n)
WHERE length(p) <= $depth
  AND all(x IN nodes(p) WHERE NOT (x:User OR x:Investigation OR x:Annotation OR x:Tag))
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
