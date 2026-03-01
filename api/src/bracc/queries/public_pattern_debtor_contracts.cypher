MATCH (c:Company)
WHERE elementId(c) = $company_id
   OR c.cnpj = $company_identifier
   OR c.cnpj = $company_identifier_formatted
CALL {
  WITH c
  MATCH (c)-[:DEVE]->(debt:Finance)
  WHERE debt.type = 'divida_ativa'
  RETURN collect(DISTINCT debt.finance_id) AS debt_ids,
         sum(coalesce(debt.value, 0.0)) AS debt_total,
         min(debt.date) AS debt_start,
         max(debt.date) AS debt_end
}
CALL {
  WITH c
  MATCH (c)-[:VENCEU]->(ct:Contract)
  RETURN collect(DISTINCT ct.contract_id) AS contract_ids,
         sum(coalesce(ct.value, 0.0)) AS contract_total,
         min(ct.date) AS contract_start,
         max(ct.date) AS contract_end
}
WITH c,
     [x IN debt_ids WHERE x IS NOT NULL AND x <> ''] AS debt_ids,
     [x IN contract_ids WHERE x IS NOT NULL AND x <> ''] AS contract_ids,
     coalesce(contract_total, 0.0) AS contract_total,
     coalesce(debt_total, 0.0) AS debt_total,
     [d IN [debt_start, contract_start] WHERE d IS NOT NULL AND d <> ''] AS starts,
     [d IN [debt_end, contract_end] WHERE d IS NOT NULL AND d <> ''] AS ends
WITH c,
     debt_ids,
     contract_ids,
     contract_total + debt_total AS amount_total,
     CASE
       WHEN size(starts) = 0 THEN NULL
       ELSE reduce(min_date = starts[0], item IN starts |
         CASE WHEN item < min_date THEN item ELSE min_date END
       )
     END AS window_start,
     CASE
       WHEN size(ends) = 0 THEN NULL
       ELSE reduce(max_date = ends[0], item IN ends |
         CASE WHEN item > max_date THEN item ELSE max_date END
       )
     END AS window_end
WITH c,
     amount_total,
     window_start,
     window_end,
     debt_ids,
     contract_ids,
     [x IN debt_ids + contract_ids WHERE x IS NOT NULL AND x <> ''] AS evidence_refs
WHERE size(debt_ids) > 0
  AND size(contract_ids) > 0
  AND size(evidence_refs) > 0
RETURN 'debtor_contracts' AS pattern_id,
       c.cnpj AS cnpj,
       c.razao_social AS company_name,
       toFloat(size(debt_ids) + size(contract_ids)) AS risk_signal,
       amount_total AS amount_total,
       window_start AS window_start,
       window_end AS window_end,
       evidence_refs[0..toInteger($pattern_max_evidence_refs)] AS evidence_refs,
       size(evidence_refs) AS evidence_count
