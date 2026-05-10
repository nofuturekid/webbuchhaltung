import base64
import json

from anthropic import APIConnectionError, AsyncAnthropic, AuthenticationError

from app.config import settings
from app.errors import LLMExtractionError
from app.schemas.document import ExtractionResult

SYSTEM_PROMPT = """You are an accounting assistant. Extract information from the document and return ONLY valid JSON with these fields:
{
  "vendor_name": "string or null",
  "document_date": "YYYY-MM-DD or null",
  "total_amount_cents": integer_or_null,
  "vat_amount_cents": integer_or_null,
  "suggested_debit_account": "4-digit SKR number or null",
  "suggested_credit_account": "4-digit SKR number or null",
  "booking_text": "max 60 chars description or null",
  "confidence_score": float_0_to_1
}
Do not include any other text outside the JSON."""


async def extract_document(
    file_content: bytes,
    mime_type: str,
    known_accounts: list[str],
) -> ExtractionResult:
    """Call the Anthropic API to extract accounting data from a document."""
    if settings.anthropic_api_key is None:
        raise LLMExtractionError("ANTHROPIC_API_KEY is not configured.")

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    encoded = base64.b64encode(file_content).decode()
    if mime_type == "application/pdf":
        content_block: dict = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": encoded,
            },
        }
    else:
        content_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": encoded,
            },
        }

    accounts_hint = (
        f"\nKnown accounts for this client: {', '.join(known_accounts[:30])}"
    )

    try:
        response = await client.messages.create(
            model="claude-opus-4-7",
            max_tokens=512,
            system=SYSTEM_PROMPT + accounts_hint,
            messages=[{"role": "user", "content": [content_block]}],
        )
    except (APIConnectionError, AuthenticationError) as exc:
        raise LLMExtractionError(str(exc)) from exc

    text = response.content[0].text if response.content else ""
    try:
        data = json.loads(text)
        return ExtractionResult(**data)
    except (json.JSONDecodeError, ValueError):
        return ExtractionResult()
