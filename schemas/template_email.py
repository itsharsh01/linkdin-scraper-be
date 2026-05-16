from pydantic import BaseModel, EmailStr, Field


class SendTemplateEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str = Field(
        default="Harsh Gupta – AI/ML Engineer | Open to Opportunities",
        max_length=998,
    )
    attach_resume: bool = True


class SendTemplateEmailResponse(BaseModel):
    to_email: EmailStr
    subject: str
    message: str = "Template email sent successfully."
