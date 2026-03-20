## ADDED Requirements

### Requirement: Topic embeddings are updated on consensus refresh
The system SHALL upsert the topic embedding point in `topic_embeddings` whenever a topic consensus is refreshed.

#### Scenario: Refresh writes topic embeddings
- **WHEN** a topic consensus refresh completes
- **THEN** the system SHALL upsert the topic's embedding in `topic_embeddings` using the configured point id strategy

### Requirement: Topic retrieval uses the topic embeddings collection
The system SHALL query the `topic_embeddings` collection to retrieve candidate topics for assignment.

#### Scenario: Candidate retrieval from topic embeddings
- **WHEN** candidate topics are requested for article assignment
- **THEN** the system SHALL query `topic_embeddings` for the top-N nearest topics
