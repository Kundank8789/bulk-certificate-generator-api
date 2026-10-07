import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Certificate
from app.services import processor


client = TestClient(app)


def wait_for_completion(job_id: int):
    for _ in range(30):
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200

        data = response.json()

        if data["status"] in {"COMPLETED", "PARTIAL", "FAILED"}:
            return data

        time.sleep(0.1)

    raise AssertionError("Job did not finish in time")


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_job():
    payload = {
        "recipients": [
            {
                "name": "Kundan Kumar",
                "email": "kundan@example.com",
                "course_name": "Backend Engineering",
            }
        ]
    }

    response = client.post("/api/jobs", json=payload)

    assert response.status_code == 202

    data = response.json()

    assert "job_id" in data
    assert data["status"] == "PENDING"
    assert data["total"] == 1


def test_validation():
    response = client.post(
        "/api/jobs",
        json={"recipients": []},
    )

    assert response.status_code == 422


def test_job_generation_and_status():
    payload = {
        "recipients": [
            {
                "name": "Kundan Kumar",
                "email": "kundan@example.com",
                "course_name": "Backend Engineering",
            },
            {
                "name": "Aman Sharma",
                "email": "aman@example.com",
                "course_name": "FastAPI Development",
            },
        ]
    }

    response = client.post("/api/jobs", json=payload)

    assert response.status_code == 202

    job_id = response.json()["job_id"]

    data = wait_for_completion(job_id)

    assert data["status"] == "COMPLETED"
    assert data["total"] == 2
    assert data["successful"] == 2
    assert data["failed"] == 0

    for certificate in data["certificates"]:
        assert certificate["status"] == "SUCCESS"
        assert certificate["file_url"] is not None


def test_certificate_retrieval():
    payload = {
        "recipients": [
            {
                "name": "Kundan Kumar",
                "email": "kundan@example.com",
                "course_name": "Backend Engineering",
            }
        ]
    }

    response = client.post("/api/jobs", json=payload)

    job_id = response.json()["job_id"]

    data = wait_for_completion(job_id)

    certificate_id = data["certificates"][0]["id"]

    response = client.get(
        f"/api/certificates/{certificate_id}/download"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_missing_job():
    response = client.get("/api/jobs/999999")

    assert response.status_code == 404


def test_individual_certificate_failure(monkeypatch):
    original_generate = processor.generate_certificate

    def fake_generate(output_path, recipient_name, course_name):
        if recipient_name == "Bad Recipient":
            raise RuntimeError("Simulated certificate generation failure")

        return original_generate(
            output_path,
            recipient_name,
            course_name,
        )

    monkeypatch.setattr(
        processor,
        "generate_certificate",
        fake_generate,
    )

    payload = {
        "recipients": [
            {
                "name": "Good Recipient",
                "email": "good@example.com",
                "course_name": "Backend Engineering",
            },
            {
                "name": "Bad Recipient",
                "email": "bad@example.com",
                "course_name": "Backend Engineering",
            },
        ]
    }

    response = client.post("/api/jobs", json=payload)

    assert response.status_code == 202

    job_id = response.json()["job_id"]

    data = wait_for_completion(job_id)

    assert data["status"] == "PARTIAL"
    assert data["total"] == 2
    assert data["successful"] == 1
    assert data["failed"] == 1

    statuses = {
        certificate["recipient_name"]: certificate["status"]
        for certificate in data["certificates"]
    }

    assert statuses["Good Recipient"] == "SUCCESS"
    assert statuses["Bad Recipient"] == "FAILED"