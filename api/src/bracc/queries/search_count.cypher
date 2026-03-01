CALL db.index.fulltext.queryNodes("entity_search", $query)
YIELD node, score
WITH node, score, labels(node) AS node_labels
WHERE NONE(label IN node_labels WHERE label IN ['User', 'Investigation', 'Annotation', 'Tag'])
  AND (NOT $hide_person_entities OR NONE(label IN node_labels WHERE label IN ['Person', 'Partner']))
  AND ($entity_type IS NULL
       OR ANY(label IN node_labels WHERE toLower(label) = $entity_type))
RETURN count(node) AS total
