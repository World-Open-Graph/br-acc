MATCH (c:Company)
WHERE elementId(c) = $company_id
   OR c.cnpj = $company_identifier
   OR c.cnpj = $company_identifier_formatted
CALL {
  WITH c
  MATCH (a:Amendment)-[:BENEFICIOU]->(c)
  RETURN collect(DISTINCT a.amendment_id) AS amendment_ids
}
CALL {
  WITH c
  MATCH (c)-[:VENCEU]->(ct:Contract)
  RETURN collect(DISTINCT ct.contract_id) AS contract_ids,
         sum(coalesce(ct.value, 0.0)) AS contract_total,
         min(ct.date) AS contract_start,
         max(ct.date) AS contract_end
}
CALL {
  WITH c
  MATCH (a:Amendment)-[:BENEFICIOU]->(c)
  OPTIONAL MATCH (a)-[:GEROU_CONVENIO]->(cv:Convenio)
  RETURN collect(DISTINCT cv.convenio_id) AS convenio_ids,
         sum(DISTINCT coalesce(cv.value, 0.0)) AS convenio_total
}
WITH c,
     [x IN amendment_ids WHERE x IS NOT NULL AND x <> ''] AS amendment_ids,
     [x IN contract_ids WHERE x IS NOT NULL AND x <> ''] AS contract_ids,
     [x IN convenio_ids WHERE x IS NOT NULL AND x <> ''] AS convenio_ids,
     contract_total,
     convenio_total,
     contract_start,
     contract_end
WITH c,
     amendment_ids,
     contract_ids,
     convenio_ids,
     contract_total + convenio_total AS amount_total,
     contract_start AS window_start,
     contract_end AS window_end,
     [x IN amendment_ids + convenio_ids + contract_ids WHERE x IS NOT NULL AND x <> ''] AS evidence_refs
WHERE size(amendment_ids) > 0
  AND size(contract_ids) > 0
  AND size(evidence_refs) > 0
RETURN 'amendment_beneficiary_contracts' AS pattern_id,
       c.cnpj AS cnpj,
       c.razao_social AS company_name,
       toFloat(size(amendment_ids) + size(convenio_ids) + size(contract_ids)) AS risk_signal,
       amount_total AS amount_total,
       window_start AS window_start,
       window_end AS window_end,
       evidence_refs[0..toInteger($pattern_max_evidence_refs)] AS evidence_refs,
       size(evidence_refs) AS evidence_count
