from app.services.entity_extractor import extract_entities


def test_extract_entities_required_formats():
    text = """
    Email notes@example.test.
    Phone +1-555-019-2834 and backup (555) 013-4455.
    Dates 2026-08-15, 12/05/2026, and August 1, 2026.
    """
    entities = extract_entities(text)
    assert "notes@example.test" in [item.value for item in entities.emails]
    phones = [item.value for item in entities.phone_numbers]
    assert "+1-555-019-2834" in phones
    assert "(555) 013-4455" in phones
    dates = [item.value for item in entities.dates]
    assert "2026-08-15" in dates
    assert "12/05/2026" in dates
    assert "August 1, 2026" in dates
