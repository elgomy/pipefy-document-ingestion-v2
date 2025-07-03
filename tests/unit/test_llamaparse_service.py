import os
import pytest
import asyncio
from src.services.llamaparse_service import parse_document_with_llamaparse, DocumentParsingRequest

@pytest.mark.asyncio
async def test_parse_document_with_llamaparse_real_pdf():
    # Usar la URL pública de Supabase
    file_url = "https://aguoqgqbdbyipztgrmbd.supabase.co/storage/v1/object/public/documents/1131156124/2-ContratoSocial_12.2021.pdf"
    request = DocumentParsingRequest(
        file_url=file_url,
        parsing_preset="fast",
        language="es",
        result_as_markdown=True
    )
    result = await parse_document_with_llamaparse(request)
    assert result["parsing_status"] == "completed", f"Estado inesperado: {result}"
    assert result["parsed_content"], "El contenido parseado está vacío"
    print("Contenido parseado (primeros 500 caracteres):", result["parsed_content"][:500]) 