## Requirements

### Requirement: Refresh selects topic articles within a window
The refresh pipeline SHALL load articles linked to the topic within a configurable time window when recomputing consensus.

#### Scenario: Load refresh window
- **WHEN** a topic refresh begins
- **THEN** the system SHALL load linked articles within the configured window

### Requirement: Consensus is recomputed and versioned
The refresh pipeline SHALL recompute the topic consensus title, summary, and reliability, and SHALL increment the consensus version for the topic.

#### Scenario: Consensus recompute
- **WHEN** a refresh completes for a topic
- **THEN** the system SHALL persist updated consensus fields and increment the consensus version

### Requirement: Topic embeddings are updated in Qdrant
The refresh pipeline SHALL update the topic embedding in Qdrant to match the latest consensus.

#### Scenario: Embedding update
- **WHEN** consensus recomputation finishes
- **THEN** the system SHALL upsert the topic embedding in Qdrant for that topic id

### Requirement: Consensus distance is backfilled after refresh
The refresh pipeline SHALL compute and persist `consensus_distance` for linked articles that are missing it or that have an older consensus version than the topic.

#### Scenario: Backfill missing consensus distance
- **WHEN** a topic refresh completes
- **THEN** the system SHALL backfill `consensus_distance` for linked articles missing a value

#### Scenario: Backfill stale consensus distance
- **WHEN** a topic refresh completes and linked articles have an older consensus version
- **THEN** the system SHALL recompute and update `consensus_distance` for those links

### Requirement: Refresh is idempotent and guarded
The refresh pipeline SHALL be idempotent per topic and MUST avoid repeated refreshes within a configurable cooldown window or when insufficient new evidence exists.

#### Scenario: Cooldown guard
- **WHEN** a refresh is requested within the cooldown window
- **THEN** the system SHALL skip recomputation for that topic

#### Scenario: Idempotent processing
- **WHEN** the same refresh request is processed more than once
- **THEN** the system SHALL not produce duplicate consensus versions or duplicate updates
