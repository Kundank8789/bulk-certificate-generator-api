# Bulk Certificate Generator API

A backend assignment implementation that accepts a bulk list of recipients, generates certificates from one predefined template, tracks job progress, isolates individual failures, and exposes generated certificates for retrieval.

## Assignment coverage

- Python + FastAPI
- Relational database via SQLAlchemy
- Bulk generation in one request
- Input validation with Pydantic
- Job status/progress tracking
- Individual certificate status
- Individual failure isolation
- PDF certificate generation
- Certificate retrieval
- Automated tests
- OpenAPI/Swagger documentation

The assignment explicitly requires bulk processing, validation, job tracking, retrieval, and handling a failure without unnecessarily stopping other valid certificates. It also requires tests for job creation, validation, generation, status/progress, individual failure, and retrieval.

## Architecture

`POST /api/jobs` validates and stores the job and recipients, then schedules background processing.

The processor generates each PDF independently. A failure marks only that certificate as `FAILED`; the remaining certificates continue. The final job status is:

- `COMPLETED`: all certificates succeeded
- `PARTIAL`: some succeeded and some failed
- `FAILED`: all failed

## Project structure

```text
app/
  main.py
  config.py
  database.py
  models.py
  schemas.py
  services/
    certificate.py
    processor.py
tests/
  test_api.py
storage/
  certificates/
```

## Setup

Python 3.11+ recommended.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

Open Swagger:

`http://127.0.0.1:8000/docs`

## API

### Create generation job

`POST /api/jobs`

Example:

```json
{
  "recipients": [
    {
      "name": "Kundan Kumar",
      "email": "kundan@example.com",
      "course_name": "Backend Engineering"
    },
    {
      "name": "Aman Sharma",
      "email": "aman@example.com",
      "course_name": "Backend Engineering"
    }
  ]
}
```

Response:

```json
{
  "job_id": 1,
  "status": "PENDING",
  "total": 2
}
```

### Check job

`GET /api/jobs/{job_id}`

The response includes total, successful, failed, overall status, and per-certificate status.

### List certificates

`GET /api/jobs/{job_id}/certificates`

### Download

`GET /api/certificates/{certificate_id}/download`

## Tests

```bash
pytest -q
```

## Database

SQLite is the default so the project runs immediately. The application reads `DATABASE_URL`, so PostgreSQL can be used without changing the application code.

Example:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/certificates
```

For PostgreSQL, install the appropriate psycopg package.

## Design decisions

### Background processing

FastAPI `BackgroundTasks` is used for the assignment implementation because the API should return a job ID immediately rather than making the client wait for every PDF. For production at larger scale, the processor can be moved to Celery/RQ/Dramatiq with Redis or another queue.

### Failure isolation

Each certificate is generated inside its own try/except block. A single bad recipient or generation failure does not stop valid recipients.

### Storage

Generated PDFs are stored under `storage/certificates/{job_id}`. A production deployment could replace local storage with S3-compatible object storage.

## Future scope

- Redis + Celery worker queue
- PostgreSQL in production
- S3/object storage
- Authentication and authorization
- Signed download URLs
- Configurable certificate templates
- Email delivery
- Retry failed certificates
- Pagination for very large jobs
- Docker and CI/CD
