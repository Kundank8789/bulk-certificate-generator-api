from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from ..config import settings
from ..database import SessionLocal
from ..models import GenerationJob, Certificate
from .certificate import generate_certificate

def process_job(job_id: int) -> None:
    db: Session = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            return
        job.status = "PROCESSING"
        db.commit()

        for cert in job.certificates:
            try:
                safe_name = "".join(ch if ch.isalnum() else "_" for ch in cert.recipient_name)
                output = Path(settings.storage_dir) / str(job.id) / f"{cert.id}_{safe_name}.pdf"
                generate_certificate(output, cert.recipient_name, cert.course_name)
                cert.status = "SUCCESS"
                cert.file_path = str(output)
                job.successful += 1
            except Exception as exc:
                cert.status = "FAILED"
                cert.error_message = str(exc)
                job.failed += 1
            db.commit()

        job.status = "COMPLETED" if job.failed == 0 else ("PARTIAL" if job.successful else "FAILED")
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
