MATCH (c:Company)
WHERE elementId(c) = $company_id
   OR c.cnpj = $company_identifier
   OR c.cnpj = $company_identifier_formatted
MATCH (c)-[:VENCEU]->(ct:Contract)
WHERE ct.contracting_org IS NOT NULL
  AND trim(ct.contracting_org) <> ''
  AND ct.value IS NOT NULL
WITH c, ct.contracting_org AS contracting_org, sum(coalesce(ct.value, 0.0)) AS company_org_total
CALL {
  WITH contracting_org
  MATCH (:Company)-[:VENCEU]->(org_ct:Contract)
  WHERE org_ct.contracting_org = contracting_org
    AND org_ct.value IS NOT NULL
  RETURN sum(coalesce(org_ct.value, 0.0)) AS org_total
}
WITH c, contracting_org, company_org_total, org_total
WHERE org_total > 0
  AND (company_org_total / org_total) >= toFloat($pattern_share_threshold)
WITH c, collect(DISTINCT contracting_org) AS risky_orgs
WHERE size(risky_orgs) > 0
MATCH (c)-[:VENCEU]->(risk_ct:Contract)
WHERE risk_ct.contracting_org IN risky_orgs
WITH c,
     risky_orgs,
     collect(DISTINCT risk_ct.contract_id) AS contract_ids,
     sum(coalesce(risk_ct.value, 0.0)) AS amount_total,
     min(risk_ct.date) AS window_start,
     max(risk_ct.date) AS window_end
WITH c,
     risky_orgs,
     amount_total,
     window_start,
     window_end,
     [x IN contract_ids WHERE x IS NOT NULL AND x <> ''] AS evidence_refs
WHERE size(evidence_refs) > 0
RETURN 'contract_concentration' AS pattern_id,
       c.cnpj AS cnpj,
       c.razao_social AS company_name,
       toFloat(size(risky_orgs) + size(evidence_refs)) AS risk_signal,
       amount_total AS amount_total,
       window_start AS window_start,
       window_end AS window_end,
       evidence_refs[0..toInteger($pattern_max_evidence_refs)] AS evidence_refs,
       size(evidence_refs) AS evidence_count
