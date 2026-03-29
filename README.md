# StoryDiff

StoryDiff is a multi-source narrative variance analyzer. It ingests news articles from curated publishers, clusters them into time-aware topic groups using AI, computes narrative variance metrics per article, and serves the results through read-optimized APIs consumed by a Next.js web frontend.

The core insight is that different outlets covering the same story frame it differently. StoryDiff surfaces those differences — measuring consensus distance, framing polarity, source diversity, and novel claims — so readers can see not just *what* is being reported, but *how* and *from what angle*.

---

## What It Does

1. **Ingests** article metadata via a REST endpoint (idempotent, deduplicated)
2. **Analyzes** each article asynchronously using a LangGraph AI pipeline: embedding, category classification, entity extraction, topic assignment, summarization, and variance scoring
3. **Clusters** articles into topics and maintains versioned consensus summaries that evolve as new articles arrive
4. **Exposes** read-optimized APIs for browsing topics by category, viewing publisher leaderboards, and searching across the corpus
5. **Renders** all of the above in a server-side-rendered Next.js web app

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python 3.11+) |
| AI Orchestration | LangGraph with Postgres checkpointing |
| LLM | Ollama (default: `llama3.1:8b`) or OpenAI |
| Embeddings | Ollama `all-minilm` (384-d) or Sentence Transformers |
| Primary Database | PostgreSQL 16 |
| Vector Store | Qdrant |
| Message Queue | AWS SQS (LocalStack for local dev) |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Observability | Netra (OpenTelemetry auto-instrumentation) |
| LLM Evaluation | DeepEval (offline, LLM-as-judge) |
| Package Manager (Python) | uv |

---

## Repository Structure

```
storydiff/
├── backend/          # FastAPI app + workers (Python package: storydiff)
│   ├── src/storydiff/
│   │   ├── ingestion/      # POST /ingest handler, dedupe, SQS publisher
│   │   ├── analysis/       # LangGraph article analysis worker
│   │   ├── topic_refresh/  # LangGraph topic consensus worker
│   │   ├── core_api/       # Read endpoints (feed, topics, media, search)
│   │   ├── db/             # SQLAlchemy models + session
│   │   └── qdrant/         # Collection setup + payload definitions
│   ├── alembic/            # Database migrations
│   └── tests/
├── web/              # Next.js 15 frontend (App Router)
│   └── app/
│       ├── page.tsx              # Feed (categories + topic tiles)
│       ├── topics/[topicId]/     # Topic detail + timeline
│       ├── media/                # Publisher leaderboard + detail
│       └── search/               # Keyword/semantic/hybrid search
├── architecture/     # Detailed design documentation (HLD, schema, API contract)
├── scripts/          # localstack-init-sqs.sh
└── docker-compose.yml
```

---

## Prerequisites

- **Docker** and **Docker Compose** — for local Postgres, Qdrant, and SQS (LocalStack)
- **[uv](https://docs.astral.sh/uv/)** — Python package manager (`pip install uv` or `brew install uv`)
- **Node.js 18+** and **npm** — for the frontend
- **[Ollama](https://ollama.com/)** — for local LLM and embeddings (or an OpenAI API key)
- **AWS CLI** — to create LocalStack SQS queues (only needed once)

---

## Setup

### 1. Start Local Infrastructure

From the repository root:

```bash
docker compose up -d
```

This starts:
- **PostgreSQL 16** on `localhost:5434` (user: `postgres`, password: `postgres`, db: `storydiff`)
- **Qdrant** REST API on `http://localhost:6333`, gRPC on `6334`
- **LocalStack** (SQS only) on `http://localhost:4566`

Create the SQS queues (once per machine):

```bash
chmod +x scripts/localstack-init-sqs.sh
./scripts/localstack-init-sqs.sh
```

The script prints the queue URLs. You'll need them in the next step.

### 2. Configure the Backend

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` and fill in:

```env
# Postgres (matches Docker Compose defaults)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/storydiff

# SQS (paste URLs from the localstack-init-sqs.sh output)
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
SQS_ARTICLE_INGESTED_QUEUE_URL=<printed by init script>
SQS_ARTICLE_ANALYZE_QUEUE_URL=<printed by init script>
SQS_TOPIC_REFRESH_QUEUE_URL=<printed by init script>

# Qdrant (matches Docker Compose defaults)
QDRANT_URL=http://localhost:6333
EMBEDDING_VECTOR_SIZE=384

# LLM — Ollama (default) or OpenAI
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_MODEL=llama3.1:8b
EMBEDDING_BACKEND=ollama
OLLAMA_EMBEDDING_MODEL=all-minilm
```

For OpenAI instead of Ollama:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 3. Install Backend Dependencies and Run Migrations

```bash
cd backend
uv venv
uv sync --group dev
uv run alembic upgrade head
```

### 4. Pull Ollama Models (if using Ollama)

```bash
ollama pull llama3.1:8b
ollama pull all-minilm
```

### 5. Configure and Install the Frontend

```bash
cd web
npm install
cp .env.example .env.local   # defaults already match local FastAPI
```

No changes to `.env.local` are needed for local dev; it defaults to `http://127.0.0.1:8000`.

---

## Running

Open separate terminals for each process:

**API server:**
```bash
cd backend
uv run uvicorn storydiff.main:app --reload --host 127.0.0.1 --port 8000
```

**Article analysis worker** (consumes `article.analyze` from SQS):
```bash
cd backend
uv run python -m storydiff.analysis
```

**Topic refresh worker** (consumes `topic.refresh` from SQS):
```bash
cd backend
uv run python -m storydiff.topic_refresh
```

**Web frontend:**
```bash
cd web
npm run dev
```

The app is now accessible at `http://localhost:3000`. The API is at `http://localhost:8000`.

---

## API Overview

All read endpoints return a common envelope `{ data, meta, error }`. Full request/response examples are in `architecture/api_contract.md`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/ingest` | Ingest an article (idempotent) |
| `GET` | `/api/v1/categories` | List active categories |
| `GET` | `/api/v1/feed` | Category-wise topic tiles (homepage) |
| `GET` | `/api/v1/topics/{topicId}` | Topic detail with articles and scores |
| `GET` | `/api/v1/topics/{topicId}/timeline` | Topic version history |
| `GET` | `/api/v1/media` | Publisher leaderboard |
| `GET` | `/api/v1/media/{mediaId}` | Publisher detail and breakdown |
| `GET` | `/api/v1/search` | Keyword, semantic, or hybrid search (`?q=...&mode=keyword\|semantic\|hybrid`) |
| `GET` | `/health` | Service health check |

---

## How the AI Pipeline Works

When an article is ingested it is immediately persisted and a job is queued. No AI runs in the request path.

The **analysis worker** picks up the job and runs a LangGraph pipeline:

1. **Embed** the article title + text
2. **Store** the vector in Qdrant
3. **Classify** the category using an LLM
4. **Extract** named entities
5. **Retrieve** candidate topic clusters from Qdrant by vector similarity
6. **Assign** the article to the best matching topic (or create a new one) using a multi-factor score: vector similarity, entity overlap, category match, and publish-time proximity
7. **Summarize** the article
8. **Score** narrative variance metrics (see below)
9. **Persist** everything to Postgres
10. **Trigger** a topic refresh if the topic changed materially

The **topic refresh worker** recomputes the topic's consensus title and summary using an LLM, versions the state in `topic_versions`, updates the topic embedding in Qdrant, and backfills `consensus_distance` on all linked articles.

### Narrative Variance Scores

| Score | Meaning |
|-------|---------|
| **Consensus Distance** | Semantic distance from the topic cluster. Higher = more divergent from the dominant narrative. |
| **Framing Polarity** | Tone and framing intensity relative to cluster norm. |
| **Source Diversity** | Breadth of perspectives and actors cited. Higher = broader sourcing. |
| **Novel Claim** | How much the article emphasizes claims not yet common in the cluster. Higher = more distinctive. |
| **Reliability** | System confidence in the analysis quality (not article truthfulness). Factors in topic size, source count, text availability, and assignment confidence. |

---

## Testing

Unit tests (dedupe, SQS mocking) run without a database. Integration tests require the Docker Compose Postgres.

```bash
cd backend

# Run all tests (DB-dependent tests auto-skip if unreachable)
uv run pytest

# Run against Docker Compose Postgres
export TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5434/storydiff
uv run pytest

# Run a single test file
uv run pytest tests/path/to/test_file.py
```

Frontend linting:
```bash
cd web
npm run lint
```

### LLM Evaluation (DeepEval)

The `backend/tests/eval/` directory contains an offline evaluation suite for the AI pipeline, powered by [DeepEval](https://github.com/confident-ai/deepeval). These tests are **excluded from the standard `pytest` run** and must be invoked explicitly. They call the real LLM and use OpenAI (`gpt-4o-mini`) as an LLM judge, so they incur API costs.

```bash
cd backend
export OPENAI_API_KEY=sk-...   # required for DeepEval judge
uv run pytest tests/eval/ -v   # run all eval tests
uv run pytest tests/eval/test_consensus.py -v  # run a single flow
```

| Test file | AI flow evaluated | Metrics |
|-----------|-------------------|---------|
| `test_classify.py` | Category classification | Exact-match accuracy, GEval (category appropriateness) |
| `test_entities.py` | Entity extraction | GEval (completeness + no hallucinated entities) |
| `test_summary_scores.py` | Article summary + variance scores | SummarizationMetric, HallucinationMetric, GEval (score range validity) |
| `test_consensus.py` | Consensus summary (RAG) | FaithfulnessMetric, AnswerRelevancyMetric, GEval (neutrality) |

Each test file contains hardcoded synthetic article fixtures. The LLM provider for the system under test is controlled by `LLM_PROVIDER` (same as the analysis worker); the judge LLM is always OpenAI.

---

## Observability (Netra)

StoryDiff integrates [Netra](https://getnetra.ai/) for production observability. When `NETRA_API_KEY` is set, Netra auto-instruments LangGraph nodes, LLM calls, Qdrant queries, SQS operations, SQLAlchemy queries, and FastAPI requests — no manual span creation required.

To enable, add to `backend/.env`:

```env
NETRA_API_KEY=your-api-key-here
```

Netra is initialized at startup in three entry points:
- **API server** (`storydiff/main.py`) — service name `storydiff-api`
- **Analysis worker** (`storydiff/analysis/worker.py`) — service name `storydiff-analysis-worker`
- **Topic refresh worker** (`storydiff/topic_refresh/worker.py`) — service name `storydiff-topic-refresh-worker`

When `NETRA_API_KEY` is absent or empty, Netra is not loaded and the application runs normally with no overhead.

---

## Database Migrations

```bash
cd backend

# Apply all migrations
uv run alembic upgrade head

# Roll back to empty state
uv run alembic downgrade base
```

After changing `pyproject.toml` dependencies, refresh the lockfile and commit it:

```bash
uv lock
```

---

## Stopping / Resetting

Stop the Docker services:

```bash
docker compose down
```

Wipe all local data (Postgres, Qdrant, LocalStack) and start fresh:

```bash
docker compose down -v
```

---

## Deployment

Production runs on AWS Lambda (backend) and Vercel (frontend). The deploy pipeline is fully automated via GitHub Actions — every push to `main` builds Docker images, runs database migrations, and updates the Lambda functions.

### Prerequisites

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured with credentials that have IAM, Lambda, ECR, SQS, and SSM permissions
- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.6
- [uv](https://docs.astral.sh/uv/) (for local dev)

### One-time Bootstrap

**1. Create the Terraform state bucket**

```bash
aws s3 mb s3://storydiff-tf-state --region us-east-1
```

**2. Provision ECR repositories first** (needed before images can be pushed)

```bash
cd infra
terraform init
terraform apply -target=aws_ecr_repository.repos
```

**3. Push initial images** (trigger the GitHub Actions deploy workflow, or push manually)

The deploy workflow will push the first real images. Lambda functions are created with a `:latest` placeholder and will only work after images are pushed.

**4. Provision remaining infrastructure**

```bash
terraform apply
```

This creates: Lambda functions, SQS queues + DLQs, IAM roles, SSM parameter placeholders.

**5. Populate SSM secrets**

After `terraform apply`, fill in the real values for each parameter:

```bash
aws ssm put-parameter --name "/storydiff/database-url" \
  --value "postgresql+psycopg://user:pass@host:5432/storydiff" \
  --type SecureString --overwrite

aws ssm put-parameter --name "/storydiff/openai-api-key" \
  --value "sk-..." --type SecureString --overwrite

aws ssm put-parameter --name "/storydiff/qdrant-url" \
  --value "https://xxx.qdrant.io" --type SecureString --overwrite

aws ssm put-parameter --name "/storydiff/qdrant-api-key" \
  --value "..." --type SecureString --overwrite

# Use the queue URLs from `terraform output`
aws ssm put-parameter --name "/storydiff/sqs-article-analyze-queue-url" \
  --value "$(terraform output -raw article_analyze_queue_url)" \
  --type SecureString --overwrite

aws ssm put-parameter --name "/storydiff/sqs-topic-refresh-queue-url" \
  --value "$(terraform output -raw topic_refresh_queue_url)" \
  --type SecureString --overwrite
```

**6. Add GitHub repository secrets**

In your GitHub repo → Settings → Secrets → Actions, add:

| Secret | Value |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | AWS access key for the deploy IAM user |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_REGION` | e.g. `us-east-1` |
| `ECR_REGISTRY` | ECR registry URL (e.g. `123456789.dkr.ecr.us-east-1.amazonaws.com`) |

**7. Connect Vercel to this repo**

In [Vercel](https://vercel.com), import this repository, set the root directory to `web/`, and add the environment variable:

```
BACKEND_URL=<value of `terraform output api_function_url`>
```

### Ongoing Workflow

After bootstrap, everything is automated:

- **Push to `dev`** → runs backend CI (lint + test) and frontend CI (lint + build)
- **Push to `main`** → runs CI, then builds Docker images, runs Alembic migrations, and deploys all three Lambda functions
- **Vercel** auto-deploys the frontend on every push to `main`

### Running Migrations Manually

```bash
aws lambda invoke \
  --function-name storydiff-api \
  --payload '{"action":"migrate"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json && cat /tmp/response.json
```

---

## Architecture Documentation

The `architecture/` directory contains detailed design specifications:

| File | Contents |
|------|---------|
| `hld.md` | Full high-level design, principles, component responsibilities, build phases |
| `db_schema.md` | Table definitions, indexes, Qdrant payload fields |
| `api_contract.md` | Complete API spec with request/response examples for every endpoint |
| `score_semantics.md` | Interpretation guide for all five variance scores |
| `events.md` | SQS event payload definitions |
| `graph.md` | LangGraph output schemas for both workers |
| `build_order.md` | Phased implementation roadmap |
