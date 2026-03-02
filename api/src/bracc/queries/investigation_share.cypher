MATCH (u:User {id: $user_id})-[:OWNS]->(i:Investigation {id: $id})
SET i.share_token = $share_token,
    i.updated_at = datetime()
RETURN i.id AS id,
       i.share_token AS share_token
