import pytest
import io
import os
from backend.monolith.main import extract_text

def test_extract_txt():
    content = b"This is a simple text file."
    result = extract_text(content, "txt")
    assert result == "This is a simple text file."

def test_extract_unsupported():
    content = b"some content"
    with pytest.raises(ValueError) as excinfo:
        extract_text(content, "exe")
    assert "Unsupported file type: exe" in str(excinfo.value)

# Note: Testing PDF and DOCX would require actual binary content 
# from those file formats, which we can mock if needed, 
# or use small sample files.
# For now, let's just ensure the structure handles them correctly.

def test_extract_pdf_call_structure():
    # We mock PdfReader to see if it's called
    from unittest.mock import patch, MagicMock
    
    with patch("backend.monolith.main.PdfReader") as mock_pdf:
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF Content"
        mock_reader.pages = [mock_page]
        mock_pdf.return_value = mock_reader
        
        content = b"%PDF-1.4 mock content"
        result = extract_text(content, "pdf")
        
        assert result == "PDF Content\n"
        mock_pdf.assert_called_once()

def test_extract_docx_call_structure():
    from unittest.mock import patch, MagicMock
    
    with patch("backend.monolith.main.docx.Document") as mock_doc:
        mock_document = MagicMock()
        mock_para = MagicMock()
        mock_para.text = "Docx Content"
        mock_document.paragraphs = [mock_para]
        mock_doc.return_value = mock_document
        
        content = b"mock docx content"
        result = extract_text(content, "docx")
        
        assert result == "Docx Content"
        mock_doc.assert_called_once()
