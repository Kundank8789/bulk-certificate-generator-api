from pydantic import BaseModel, EmailStr, Field, ConfigDict

class Recipient(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    course_name: str = Field(min_length=2, max_length=200)

class GenerationRequest(BaseModel):
    recipients: list[Recipient] = Field(min_length=1, max_length=5000)

class CertificateResponse(BaseModel):
    id: int
    recipient_name: str
    recipient_email: str
    course_name: str
    status: str
    file_url: str | None = None
    error_message: str | None = None
    model_config = ConfigDict(from_attributes=True)

class JobResponse(BaseModel):
    id: int
    status: str
    total: int
    successful: int
    failed: int
    created_at: str
    completed_at: str | None = None
    certificates: list[CertificateResponse] = []

class JobCreatedResponse(BaseModel):
    job_id: int
    status: str
    total: int
