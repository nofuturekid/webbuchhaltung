import io
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError

try:
    from schwifty import IBAN as SchwiftyIBAN

    _SCHWIFTY_AVAILABLE = True
except ImportError:
    _SCHWIFTY_AVAILABLE = False


@dataclass
class SEPAPaymentInstruction:
    vendor_name: str
    vendor_iban: str
    vendor_bic: str | None
    amount_cents: int
    currency: str
    remittance_info: str  # max 140 chars
    end_to_end_id: str  # max 35 chars


def _validate_iban(iban: str) -> str:
    """Basic structural validation. Uses schwifty if available."""
    iban = iban.replace(" ", "").upper()
    if len(iban) < 15 or len(iban) > 34:
        raise ValueError(f"Invalid IBAN length: {iban}")
    if _SCHWIFTY_AVAILABLE:
        try:
            SchwiftyIBAN(iban)
        except Exception as e:
            raise ValueError(f"Invalid IBAN {iban}: {e}") from e
    return iban


def generate_sepa_pain_001(
    mandant_name: str,
    mandant_iban: str,
    mandant_bic: str,
    execution_date: date,
    payments: list[SEPAPaymentInstruction],
    message_id: str | None = None,
) -> bytes:
    """Generate SEPA Credit Transfer pain.001.003.03 XML.

    Uses stdlib xml.etree.ElementTree (no lxml required for generation).
    Returns UTF-8 encoded XML bytes.
    """
    if not payments:
        raise ValueError("No payments provided.")

    mandant_iban = _validate_iban(mandant_iban)
    if message_id is None:
        message_id = str(uuid.uuid4())[:35]

    ns = "urn:iso:std:iso:20022:tech:xsd:pain.001.003.03"

    def el(tag: str, text: str | None = None) -> ET.Element:
        e = ET.Element(tag)
        if text is not None:
            e.text = text
        return e

    root = ET.Element(f"{{{ns}}}Document")
    cstmr_cdt = ET.SubElement(root, f"{{{ns}}}CstmrCdtTrfInitn")

    # GroupHeader
    grp_hdr = ET.SubElement(cstmr_cdt, f"{{{ns}}}GrpHdr")
    grp_hdr.append(el(f"{{{ns}}}MsgId", message_id))
    grp_hdr.append(
        el(
            f"{{{ns}}}CreDtTm",
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        )
    )
    grp_hdr.append(el(f"{{{ns}}}NbOfTxs", str(len(payments))))
    ctrl_sum = sum(p.amount_cents for p in payments)
    grp_hdr.append(el(f"{{{ns}}}CtrlSum", f"{Decimal(ctrl_sum) / 100:.2f}"))
    initg_pty = ET.SubElement(grp_hdr, f"{{{ns}}}InitgPty")
    initg_pty.append(el(f"{{{ns}}}Nm", mandant_name[:70]))

    # One PaymentInformation block
    pmt_inf = ET.SubElement(cstmr_cdt, f"{{{ns}}}PmtInf")
    pmt_inf.append(el(f"{{{ns}}}PmtInfId", f"PMT-{message_id[:30]}"))
    pmt_inf.append(el(f"{{{ns}}}PmtMtd", "TRF"))
    pmt_inf.append(el(f"{{{ns}}}NbOfTxs", str(len(payments))))
    pmt_inf.append(el(f"{{{ns}}}CtrlSum", f"{Decimal(ctrl_sum) / 100:.2f}"))
    pmt_tp_inf = ET.SubElement(pmt_inf, f"{{{ns}}}PmtTpInf")
    svc_lvl = ET.SubElement(pmt_tp_inf, f"{{{ns}}}SvcLvl")
    svc_lvl.append(el(f"{{{ns}}}Cd", "SEPA"))
    pmt_inf.append(el(f"{{{ns}}}ReqdExctnDt", execution_date.isoformat()))
    dbtr = ET.SubElement(pmt_inf, f"{{{ns}}}Dbtr")
    dbtr.append(el(f"{{{ns}}}Nm", mandant_name[:70]))
    dbtr_acct = ET.SubElement(pmt_inf, f"{{{ns}}}DbtrAcct")
    dbtr_acct_id = ET.SubElement(dbtr_acct, f"{{{ns}}}Id")
    dbtr_acct_id.append(el(f"{{{ns}}}IBAN", mandant_iban))
    dbtr_agt = ET.SubElement(pmt_inf, f"{{{ns}}}DbtrAgt")
    fin_instn_id = ET.SubElement(dbtr_agt, f"{{{ns}}}FinInstnId")
    fin_instn_id.append(el(f"{{{ns}}}BIC", mandant_bic))

    for pmt in payments:
        cdt_trf = ET.SubElement(pmt_inf, f"{{{ns}}}CdtTrfTxInf")
        pmt_id = ET.SubElement(cdt_trf, f"{{{ns}}}PmtId")
        pmt_id.append(el(f"{{{ns}}}EndToEndId", pmt.end_to_end_id[:35]))
        amt = ET.SubElement(cdt_trf, f"{{{ns}}}Amt")
        instd_amt = ET.SubElement(amt, f"{{{ns}}}InstdAmt")
        instd_amt.set("Ccy", pmt.currency)
        instd_amt.text = f"{Decimal(pmt.amount_cents) / 100:.2f}"
        if pmt.vendor_bic:
            cdtr_agt = ET.SubElement(cdt_trf, f"{{{ns}}}CdtrAgt")
            fi = ET.SubElement(cdtr_agt, f"{{{ns}}}FinInstnId")
            fi.append(el(f"{{{ns}}}BIC", pmt.vendor_bic))
        cdtr = ET.SubElement(cdt_trf, f"{{{ns}}}Cdtr")
        cdtr.append(el(f"{{{ns}}}Nm", pmt.vendor_name[:70]))
        cdtr_acct = ET.SubElement(cdt_trf, f"{{{ns}}}CdtrAcct")
        cdtr_acct_id = ET.SubElement(cdtr_acct, f"{{{ns}}}Id")
        cdtr_acct_id.append(el(f"{{{ns}}}IBAN", _validate_iban(pmt.vendor_iban)))
        rmt_inf = ET.SubElement(cdt_trf, f"{{{ns}}}RmtInf")
        rmt_inf.append(el(f"{{{ns}}}Ustrd", pmt.remittance_info[:140]))

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    buf = io.BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue()


async def build_sepa_batch_for_due_invoices(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    due_on_or_before: date,
    mandant_name: str,
    mandant_iban: str,
    mandant_bic: str,
) -> tuple[bytes, list[uuid.UUID]]:
    """Collect posted vendor invoices due by the given date and generate SEPA XML."""
    from sqlalchemy import select

    from app.models.vendor import Vendor, VendorInvoice

    invoices = (
        (
            await session.execute(
                select(VendorInvoice).where(
                    VendorInvoice.mandant_id == mandant_id,
                    VendorInvoice.status == "posted",
                    VendorInvoice.due_date <= due_on_or_before,
                )
            )
        )
        .scalars()
        .all()
    )

    if not invoices:
        raise ConflictError("No due invoices found for the given date.")

    payments: list[SEPAPaymentInstruction] = []
    invoice_ids: list[uuid.UUID] = []

    for inv in invoices:
        vendor = (
            await session.execute(select(Vendor).where(Vendor.id == inv.vendor_id))
        ).scalar_one()
        if not vendor.bank_iban:
            raise ConflictError(f"Vendor {vendor.name} has no IBAN configured.")
        payments.append(
            SEPAPaymentInstruction(
                vendor_name=vendor.name,
                vendor_iban=vendor.bank_iban,
                vendor_bic=vendor.bank_bic,
                amount_cents=inv.amount_cents,
                currency=inv.currency,
                remittance_info=f"RE {inv.invoice_number}"[:140],
                end_to_end_id=f"INV-{str(inv.id)[:30]}"[:35],
            )
        )
        invoice_ids.append(inv.id)

    xml_bytes = generate_sepa_pain_001(
        mandant_name=mandant_name,
        mandant_iban=mandant_iban,
        mandant_bic=mandant_bic,
        execution_date=due_on_or_before,
        payments=payments,
    )
    return xml_bytes, invoice_ids
