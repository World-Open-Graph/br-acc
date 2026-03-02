CREATE (i:Investigation {
  id: $id,
  title: $title,
  description: $description,
  created_at: datetime(),
  updated_at: datetime(),
  share_token: null
})
WITH i
MATCH (u:User {id: $user_id})
CREATE (u)-[:OWNS]->(i)
RETURN i.id AS id,
       i.title AS title,
       i.description AS description,
       i.created_at AS created_at,
       i.updated_at AS updated_at,
       i.share_token AS share_token,
       [] AS entity_ids
