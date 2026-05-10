import pytest
from sqlalchemy import select

from app.models.mandant import Mandant
from app.services.invoice_sequence import (
    allocate_invoice_number,
    get_or_create_sequence,
)


@pytest.fixture
async def mandant_id(db_session):
    result = await db_session.execute(select(Mandant).limit(1))
    mandant = result.scalar_one_or_none()
    if mandant:
        return mandant.id
    m = Mandant(name="SeqTest GmbH", skr_variant="skr03")
    db_session.add(m)
    await db_session.flush()
    return m.id


async def test_sequence_allocates_first_number(db_session, mandant_id):
    num = await allocate_invoice_number(db_session, mandant_id)
    assert num.startswith("RE-")
    assert num.endswith("-001")


async def test_sequence_increments(db_session, mandant_id):
    first = await allocate_invoice_number(db_session, mandant_id)
    second = await allocate_invoice_number(db_session, mandant_id)
    assert first.endswith("-001")
    assert second.endswith("-002")


async def test_sequence_year_rollover(db_session, mandant_id):
    seq = await get_or_create_sequence(db_session, mandant_id)
    seq.last_reset_year = 2000  # simulate old year
    seq.next_number = 99
    await db_session.flush()

    num = await allocate_invoice_number(db_session, mandant_id)
    assert num.endswith("-001"), f"Expected reset to 001 but got {num}"


async def test_sequence_no_year_reset(db_session, mandant_id):
    seq = await get_or_create_sequence(db_session, mandant_id)
    seq.year_reset = False
    seq.next_number = 1
    await db_session.flush()

    num = await allocate_invoice_number(db_session, mandant_id)
    assert "-2026-" not in num
    assert num == "RE-001"
