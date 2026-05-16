from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse

from schemas.template_email import SendTemplateEmailRequest, SendTemplateEmailResponse
from services.template_email import load_email_template_html, send_template_html_email

router = APIRouter(tags=["template-email"])


@router.get("/preview/email-template", include_in_schema=False)
def preview_email_template() -> HTMLResponse:
    """Open in browser: http://127.0.0.1:8000/preview/email-template"""
    return HTMLResponse(load_email_template_html(strip_toolbar=False))


@router.post("/email/send-template", response_model=SendTemplateEmailResponse)
def send_portfolio_template_email(payload: SendTemplateEmailRequest) -> SendTemplateEmailResponse:
    try:
        send_template_html_email(
            to_email=str(payload.to_email),
            subject=payload.subject,
            attach_resume=payload.attach_resume,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {exc}",
        ) from exc

    return SendTemplateEmailResponse(to_email=payload.to_email, subject=payload.subject)
