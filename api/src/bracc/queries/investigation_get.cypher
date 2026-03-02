MATCH (u:User {id: $user_id})-[:OWNS]->(i:Investigation {id: $id})
OPTIONAL MATCH (i)-[:INCLUDES]->(e)
WITH i, collect(coalesce(e.cpf, e.cnpj, e.contract_id, e.sanction_id, e.amendment_id, e.cnes_code, e.finance_id, e.embargo_id, e.school_id, e.convenio_id, e.stats_id, elementId(e))) AS eids
RETURN i.id AS id,
       i.title AS title,
       i.description AS description,
       i.created_at AS created_at,
       i.updated_at AS updated_at,
       i.share_token AS share_token,
       [x IN eids WHERE x IS NOT NULL] AS entity_ids
