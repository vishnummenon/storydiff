## ADDED Requirements

### Requirement: Analysis worker exposes a Lambda SQS handler
The system SHALL expose `lambda_handler(event, context)` in `storydiff.analysis.lambda_handler` that processes `article.analyze` messages delivered by Lambda SQS event source mapping.

#### Scenario: Successful processing of a valid message
- **WHEN** Lambda delivers an SQS event containing one record with a valid `article.analyze` payload (with `article_id`)
- **THEN** the handler calls `process_article_analysis_swallow` with the correct `article_id` and returns `{"batchItemFailures": []}`

#### Scenario: Processing failure returns message to queue
- **WHEN** Lambda delivers a record and `process_article_analysis_swallow` returns `{"ok": False, ...}`
- **THEN** the handler includes that record's `messageId` in `batchItemFailures`, causing only that message to be retried

### Requirement: Analysis handler implements partial batch failure reporting
The system SHALL return `{"batchItemFailures": [{"itemIdentifier": "<messageId>"}]}` for any record that fails processing, so that a single failure does not cause the entire batch to be retried.

#### Scenario: One failure in a multi-record batch
- **WHEN** a batch of two records is delivered and the second fails
- **THEN** only the second record's `messageId` appears in `batchItemFailures`
- **THEN** the first record is not retried

#### Scenario: Exception during processing is caught
- **WHEN** `process_article_analysis_swallow` raises an unhandled exception for a record
- **THEN** the handler catches it, logs the error, and adds the record's `messageId` to `batchItemFailures`

### Requirement: Invalid or malformed messages are treated as permanent failures
The system SHALL add malformed messages (invalid JSON, missing `article_id`, wrong `event_type`) to `batchItemFailures` rather than silently discarding them, so they route to the dead-letter queue after the configured maximum receive count.

#### Scenario: Invalid JSON body
- **WHEN** a record body is not valid JSON
- **THEN** the handler adds its `messageId` to `batchItemFailures`

#### Scenario: Missing article_id
- **WHEN** a record payload has `event_type: article.analyze` but no `article_id`
- **THEN** the handler adds its `messageId` to `batchItemFailures`

### Requirement: Existing polling worker entry point is unaffected
The system SHALL not modify `storydiff/analysis/__main__.py` or `storydiff/analysis/worker.py`.

#### Scenario: Local dev polling loop still works
- **WHEN** the worker is started with `python -m storydiff.analysis`
- **THEN** it runs the long-polling loop as before
