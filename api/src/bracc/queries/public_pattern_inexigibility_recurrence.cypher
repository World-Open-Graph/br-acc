MATCH (c:Company)
WHERE elementId(c) = $company_id
   OR c.cnpj = $company_identifier
   OR c.cnpj = $company_identifier_formatted
MATCH (c)-[:VENCEU]->(ct:Contract)-[:REFERENTE_A]->(b:Bid)
WHERE toLower(coalesce(b.modality, '')) CONTAINS 'inexig'
  AND ct.contracting_org IS NOT NULL
  AND trim(ct.contracting_org) <> ''
  AND ct.object IS NOT NULL
  AND trim(ct.object) <> ''
  AND ct.date IS NOT NULL
  AND trim(ct.date) <> ''
WITH c,
     ct.contracting_org AS contracting_org,
     toLower(trim(ct.object)) AS object_key,
     collect(DISTINCT ct.contract_id) AS contract_ids,
     collect(DISTINCT b.bid_id) AS bid_ids,
     sum(coalesce(ct.value, 0.0)) AS group_total,
     min(ct.date) AS group_start,
     max(ct.date) AS group_end
WHERE size(contract_ids) >= toInteger($pattern_inexig_min_recurrence)
WITH c,
     collect(contract_ids) AS contract_id_groups,
     collect(bid_ids) AS bid_id_groups,
     sum(group_total) AS amount_total,
     min(group_start) AS window_start,
     max(group_end) AS window_end,
     count(*) AS recurring_groups
WITH c,
     amount_total,
     window_start,
     window_end,
     recurring_groups,
     reduce(flat = [], ids IN contract_id_groups | flat + ids) AS contract_ids,
     reduce(flat = [], ids IN bid_id_groups | flat + ids) AS bid_ids
WITH c,
     amount_total,
     window_start,
     window_end,
     recurring_groups,
     [x IN contract_ids WHERE x IS NOT NULL AND x <> ''] AS contract_ids,
     [x IN bid_ids WHERE x IS NOT NULL AND x <> ''] AS bid_ids,
     [x IN contract_ids + bid_ids WHERE x IS NOT NULL AND x <> ''] AS evidence_refs
WHERE size(evidence_refs) > 0
RETURN 'inexigibility_recurrence' AS pattern_id,
       c.cnpj AS cnpj,
       c.razao_social AS company_name,
       toFloat(recurring_groups + size(contract_ids)) AS risk_signal,
       amount_total AS amount_total,
       window_start AS window_start,
       window_end AS window_end,
       evidence_refs[0..toInteger($pattern_max_evidence_refs)] AS evidence_refs,
       size(evidence_refs) AS evidence_count
