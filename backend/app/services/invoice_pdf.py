from pathlib import Path

from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _format_cents(cents: int | None) -> str:
    """Format an integer cent value as a German-locale currency string."""
    if cents is None:
        return "0,00 €"
    formatted = f"{cents / 100:,.2f} €"
    # Convert US locale separators to German: 1,234.56 → 1.234,56
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def render_invoice_pdf(
    invoice: object,
    mandant: object,
    customer: object,
    line_items: list[dict],
    template_settings: object,
) -> bytes:
    """Render an invoice as a PDF byte string using WeasyPrint.

    Args:
        invoice: Invoice ORM instance (or duck-typed object).
        mandant: Mandant ORM instance with name, iban, bic, etc.
        customer: Customer ORM instance.
        line_items: List of dicts with position, description, quantity,
                    unit, unit_price_cents, vat_rate, net_total_cents,
                    vat_amount_cents.
        template_settings: InvoiceTemplate ORM instance (or duck-typed).

    Returns:
        PDF bytes.
    """
    env = SandboxedEnvironment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    tmpl = env.get_template("invoice_layout_a.html")

    # Aggregate VAT amounts by rate for the totals section
    vat_buckets: dict[str, dict] = {}
    for item in line_items:
        key = str(item["vat_rate"])
        if key not in vat_buckets:
            vat_buckets[key] = {"rate": item["vat_rate"], "net": 0, "vat": 0}
        vat_buckets[key]["net"] += item.get("net_total_cents") or 0
        vat_buckets[key]["vat"] += item.get("vat_amount_cents") or 0

    ctx = {
        "invoice": invoice,
        "mandant": mandant,
        "customer": customer,
        "line_items": line_items,
        "template": template_settings,
        "vat_buckets": list(vat_buckets.values()),
        "fmt": _format_cents,
    }
    html = tmpl.render(**ctx)

    try:
        import weasyprint  # imported lazily so tests without weasyprint can still import this module

        return weasyprint.HTML(string=html).write_pdf()  # type: ignore[no-any-return]
    except Exception as exc:
        raise RuntimeError(f"PDF rendering failed: {exc}") from exc
