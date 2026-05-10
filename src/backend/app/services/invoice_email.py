import base64
import hashlib
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from cryptography.fernet import Fernet

from app.errors import EmailSendError
from app.models.invoice import Invoice
from app.models.mandant import Mandant


def _fernet(secret_key: str) -> Fernet:
    """Derive a Fernet cipher from an arbitrary secret key using SHA-256."""
    key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest())
    return Fernet(key)


def encrypt_smtp_password(plain: str, secret_key: str) -> str:
    """Encrypt an SMTP password for storage using the application secret key."""
    return _fernet(secret_key).encrypt(plain.encode()).decode()


def decrypt_smtp_password(encrypted: str, secret_key: str) -> str:
    """Decrypt a stored SMTP password."""
    return _fernet(secret_key).decrypt(encrypted.encode()).decode()


def send_invoice_email(
    invoice: Invoice,
    mandant: Mandant,
    pdf_bytes: bytes,
    secret_key: str,
    override_email: str | None = None,
) -> None:
    """Send an invoice PDF via SMTP using mandant's configured mail settings.

    Args:
        invoice: Invoice ORM instance — must have invoice_number attribute.
        mandant: Mandant ORM instance — must have smtp_host, smtp_port, smtp_user,
                 smtp_password, smtp_from, smtp_from_name, name attributes.
        pdf_bytes: The rendered PDF byte string.
        secret_key: Application secret key for decrypting smtp_password.
        override_email: If provided, overrides the default recipient address.

    Raises:
        EmailSendError: If SMTP connection or authentication fails.
    """
    recipient = override_email
    if not recipient:
        raise EmailSendError("No recipient email address available.")

    smtp_password = ""
    if mandant.smtp_password:
        smtp_password = decrypt_smtp_password(mandant.smtp_password, secret_key)

    salutation = mandant.email_salutation or "Sehr geehrte Damen und Herren,"
    closing = mandant.email_closing or "Mit freundlichen Grüßen"
    body = (
        f"{salutation}\n\n"
        f"anbei erhalten Sie Rechnung {invoice.invoice_number} im Anhang.\n\n"
        f"{closing}\n{mandant.name}"
    )

    sender_name = mandant.smtp_from_name or mandant.name
    sender_addr = mandant.smtp_from or ""

    msg = MIMEMultipart("mixed")
    msg["From"] = f"{sender_name} <{sender_addr}>"
    msg["To"] = recipient
    msg["Subject"] = f"Rechnung {invoice.invoice_number}"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header(
        "Content-Disposition",
        "attachment",
        filename=f"{invoice.invoice_number}.pdf",
    )
    msg.attach(pdf_part)

    smtp_host = mandant.smtp_host
    smtp_port = mandant.smtp_port or 587
    smtp_user = mandant.smtp_user

    if not smtp_host:
        raise EmailSendError("SMTP host is not configured for this mandant.")

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(sender_addr, [recipient], msg.as_string())
    except smtplib.SMTPException as exc:
        raise EmailSendError(str(exc)) from exc
