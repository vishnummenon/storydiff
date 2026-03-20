## Requirements

### Requirement: Candidate topics are retrieved from Qdrant
The system SHALL query Qdrant for the top-N candidate topics for an analyzed article using the article embedding. The value of N MUST be configurable.

#### Scenario: Candidate retrieval
- **WHEN** an article analysis completes with an embedding
- **THEN** the system SHALL request the top-N topic candidates from Qdrant using that embedding

### Requirement: Candidate scoring uses required signals
The system SHALL compute a composite score for each candidate topic using vector similarity, entity overlap, category match, time proximity, topic recency, and source diversity. The weights for each signal MUST be configurable.

#### Scenario: Multi-signal scoring
- **WHEN** candidate topics are retrieved for an article
- **THEN** the system SHALL compute a score using all required signals with configured weights

### Requirement: Assignment or new topic creation is thresholded
The system SHALL assign the article to the highest-scoring candidate when the score is at or above the assignment threshold. If no candidate meets the threshold, the system SHALL create a new topic and link the article to it.

#### Scenario: Assign to existing topic
- **WHEN** the best candidate score meets or exceeds the assignment threshold
- **THEN** the system SHALL link the article to that topic

#### Scenario: Create a new topic
- **WHEN** no candidate meets the assignment threshold
- **THEN** the system SHALL create a new topic and link the article to it

### Requirement: Article-topic linkage is persisted with consensus distance
The system SHALL persist the article-topic link and update article/topic fields required by Phase 3. If the topic has a current consensus embedding, the system SHALL compute and store `consensus_distance` for the link; otherwise the field MUST be stored as null and eligible for backfill.

#### Scenario: Persist link with consensus distance
- **WHEN** an article is linked to a topic with a consensus embedding
- **THEN** the system SHALL store the link and the computed `consensus_distance`

#### Scenario: Persist link without consensus distance
- **WHEN** an article is linked to a topic without a consensus embedding
- **THEN** the system SHALL store the link with `consensus_distance` set to null

### Requirement: Topic refresh is triggered for new evidence
The system SHALL emit a `topic.refresh` event when an article is linked to a topic or when a new topic is created.

#### Scenario: Refresh event on assignment
- **WHEN** an article is linked to an existing topic
- **THEN** the system SHALL emit a `topic.refresh` event for that topic

#### Scenario: Refresh event on new topic
- **WHEN** a new topic is created
- **THEN** the system SHALL emit a `topic.refresh` event for that topic
