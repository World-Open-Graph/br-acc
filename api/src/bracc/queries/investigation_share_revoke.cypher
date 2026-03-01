MATCH (u:User {id: $user_id})-[:OWNS]->(i:Investigation {id: $id})
SET i.share_token = null,
    i.share_expires_at = null,
    i.updated_at = datetime()
RETURN 1 AS updated
