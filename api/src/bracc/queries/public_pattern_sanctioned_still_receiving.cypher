MATCH (c:Company)
WHERE elementId(c) = $company_id
   OR c.cnpj = $company_identifier
   OR c.cnpj = $company_identifier_formatted
CALL {
  WITH c
  MATCH (c)-[:SANCIONADA]->(s:Sanction)
  WHERE s.date_start IS NOT NULL
    AND trim(s.date_start) <> ''
  RETURN collect(DISTINCT {
    sanction_id: s.sanction_id,
    date_start: s.date_start,
    date_end: s.date_end
  }) AS sanctions
}
WITH c, sanctions
WHERE size(sanctions) > 0
MATCH (c)-[:VENCEU]->(ct:Contract)
WHERE ct.date IS NOT NULL
  AND trim(ct.date) <> ''
  AND any(s IN sanctions WHERE
    ct.date >= s.date_start
    AND (s.date_end IS NULL OR trim(coalesce(s.date_end, '')) = '' OR ct.date <= s.date_end)
  )
WITH c,
     [s IN sanctions WHERE s.sanction_id IS NOT NULL AND s.sanction_id <> '' | s.sanction_id] AS sanction_ids,
     collect(DISTINCT ct.contract_id) AS contract_ids,
     sum(coalesce(ct.value, 0.0)) AS amount_total,
     min(ct.date) AS window_start,
     max(ct.date) AS window_end
WITH c,
     sanction_ids,
     [x IN contract_ids WHERE x IS NOT NULL AND x <> ''] AS contract_ids,
     amount_total,
     window_start,
     window_end,
     [x IN sanction_ids + contract_ids WHERE x IS NOT NULL AND x <> ''] AS evidence_refs
WHERE size(sanction_ids) > 0
  AND size(contract_ids) > 0
  AND size(evidence_refs) > 0
RETURN 'sanctioned_still_receiving' AS pattern_id,
       c.cnpj AS cnpj,
       c.razao_social AS company_name,
       toFloat(size(sanction_ids) + size(contract_ids)) AS risk_signal,
       amount_total AS amount_total,
       window_start AS window_start,
       window_end AS window_end,
       evidence_refs[0..toInteger($pattern_max_evidence_refs)] AS evidence_refs,
       size(evidence_refs) AS evidence_count
