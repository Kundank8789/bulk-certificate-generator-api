from pathlib import Path
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from .config import settings
from .database import Base, engine, get_db
from .models import GenerationJob, Certificate
from .schemas import GenerationRequest, JobCreatedResponse, JobResponse, CertificateResponse
from .services.processor import process_job

Base.metadata.create_all(bind=engine)
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Bulk Certificate Generator API",
    version="1.0.0",
    description="Bulk certificate generation with job tracking and failure isolation.",
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/jobs", response_model=JobCreatedResponse, status_code=202)
def create_job(
    payload: GenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = GenerationJob(total=len(payload.recipients), status="PENDING")
    db.add(job)
    db.flush()

    for recipient in payload.recipients:
        db.add(Certificate(
            job_id=job.id,
            recipient_name=recipient.name,
            recipient_email=str(recipient.email),
            course_name=recipient.course_name,
            status="PENDING",
        ))

    db.commit()
    background_tasks.add_task(process_job, job.id)

    return JobCreatedResponse(job_id=job.id, status=job.status, total=job.total)

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(GenerationJob)
        .options(selectinload(GenerationJob.certificates))
        .where(GenerationJob.id == job_id)
    )
    job = db.execute(stmt).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    certificates = [
        CertificateResponse(
            id=c.id,
            recipient_name=c.recipient_name,
            recipient_email=c.recipient_email,
            course_name=c.course_name,
            status=c.status,
            file_url=f"/api/certificates/{c.id}/download" if c.file_path else None,
            error_message=c.error_message,
        )
        for c in job.certificates
    ]

    return JobResponse(
        id=job.id,
        status=job.status,
        total=job.total,
        successful=job.successful,
        failed=job.failed,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        certificates=certificates,
    )

@app.get("/api/jobs/{job_id}/certificates", response_model=list[CertificateResponse])
def list_certificates(job_id: int, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    certs = db.scalars(select(Certificate).where(Certificate.job_id == job_id)).all()
    return [
        CertificateResponse(
            id=c.id,
            recipient_name=c.recipient_name,
            recipient_email=c.recipient_email,
            course_name=c.course_name,
            status=c.status,
            file_url=f"/api/certificates/{c.id}/download" if c.file_path else None,
            error_message=c.error_message,
        ) for c in certs
    ]

@app.get("/api/certificates/{certificate_id}/download")
def download_certificate(certificate_id: int, db: Session = Depends(get_db)):
    cert = db.get(Certificate, certificate_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if cert.status != "SUCCESS" or not cert.file_path or not Path(cert.file_path).exists():
        raise HTTPException(status_code=409, detail="Certificate is not available")
    return FileResponse(cert.file_path, media_type="application/pdf", filename=Path(cert.file_path).name)
