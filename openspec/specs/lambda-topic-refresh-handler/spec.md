## ADDED Requirements

### Requirement: Topic refresh worker exposes a Lambda SQS handler
The system SHALL expose `lambda_handler(event, context)` in `storydiff.topic_refresh.lambda_handler` that processes `topic.refresh` messages delivered by Lambda SQS event source mapping.

#### Scenario: Successful processing of a valid message
- **WHEN** Lambda delivers an SQS event containing one record with a valid `topic.refresh` payload (with `topic_id`)
- **THEN** the handler calls `process_topic_refresh_swallow` with the correct `topic_id` and returns `{"batchItemFailures": []}`

#### Scenario: Processing failure returns message to queue
- **WHEN** Lambda delivers a record and `process_topic_refresh_swallow` returns `{"ok": False, ...}`
- **THEN** the handler includes that record's `messageId` in `batchItemFailures`, causing only that message to be retried

### Requirement: Topic refresh handler implements partial batch failure reporting
The system SHALL return `{"batchItemFailures": [{"itemIdentifier": "<messageId>"}]}` for any record that fails, so that a single failure does not cause the entire batch to be retried.

#### Scenario: Exception during processing is caught
- **WHEN** `process_topic_refresh_swallow` raises an unhandled exception for a record
- **THEN** the handler catches it, logs the error, and adds the record's `messageId` to `batchItemFailures`

### Requirement: Invalid or malformed messages are treated as permanent failures
The system SHALL add malformed messages (invalid JSON, missing `topic_id`, wrong `event_type`) to `batchItemFailures` rather than silently discarding them, so they route to the dead-letter queue after the configured maximum receive count.

#### Scenario: Invalid JSON body
- **WHEN** a record body is not valid JSON
- **THEN** the handler adds its `messageId` to `batchItemFailures`

#### Scenario: Missing topic_id
- **WHEN** a record payload has `event_type: topic.refresh` but no `topic_id`
- **THEN** the handler adds its `messageId` to `batchItemFailures`

### Requirement: Existing polling worker entry point is unaffected
The system SHALL not modify `storydiff/topic_refresh/__main__.py` or `storydiff/topic_refresh/worker.py`.

#### Scenario: Local dev polling loop still works
- **WHEN** the worker is started with `python -m storydiff.topic_refresh`
- **THEN** it runs the long-polling loop as before
