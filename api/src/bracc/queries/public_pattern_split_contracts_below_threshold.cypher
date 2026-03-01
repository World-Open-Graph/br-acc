MATCH (c:Company)
WHERE elementId(c) = $company_id
   OR c.cnpj = $company_identifier
   OR c.cnpj = $company_identifier_formatted
MATCH (c)-[:VENCEU]->(ct:Contract)
WHERE ct.value IS NOT NULL
  AND ct.value <= toFloat($pattern_split_threshold_value)
  AND ct.contracting_org IS NOT NULL AND trim(ct.contracting_org) <> ''
  AND ct.object IS NOT NULL AND trim(ct.object) <> ''
  AND ct.date IS NOT NULL AND trim(ct.date) <> ''
WITH c,
     ct.contracting_org AS contracting_org,
     toLower(trim(ct.object)) AS object_key,
     substring(ct.date, 0, 7) AS year_month,
     collect(DISTINCT ct.contract_id) AS group_contract_ids,
     sum(coalesce(ct.value, 0.0)) AS group_total,
     min(ct.date) AS group_start,
     max(ct.date) AS group_end
WHERE size(group_contract_ids) >= toInteger($pattern_split_min_count)
WITH c,
     collect(group_contract_ids) AS id_groups,
     sum(group_total) AS amount_total,
     min(group_start) AS window_start,
     max(group_end) AS window_end,
     count(*) AS grouped_occurrences
WITH c,
     amount_total,
     window_start,
     window_end,
     grouped_occurrences,
     reduce(flat = [], ids IN id_groups | flat + ids) AS evidence_refs
WHERE size(evidence_refs) > 0
RETURN 'split_contracts_below_threshold' AS pattern_id,
       c.cnpj AS cnpj,
       c.razao_social AS company_name,
       toFloat(grouped_occurrences + size(evidence_refs)) AS risk_signal,
       amount_total AS amount_total,
       window_start AS window_start,
       window_end AS window_end,
       evidence_refs[0..toInteger($pattern_max_evidence_refs)] AS evidence_refs,
       size(evidence_refs) AS evidence_count
