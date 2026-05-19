# tests/test_analysis.py
import pytest
from pdflinkcheck.validate import validate_pdf  # Adjust based on actual internal API

def test_tem_om_link_integrity(get_test_pdf):
    pdf_path = get_test_pdf("temOM.pdf")
    
    # Run your core processing or CLI invocation programmatically
    results = validate_pdf(pdf_path, engine="pypdf") # Use pypdf to avoid AGPL dependency in core tests
    
    assert results is not None
    assert results.broken_links_count == 0
