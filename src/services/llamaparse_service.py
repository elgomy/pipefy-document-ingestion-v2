import os
import tempfile
import logging
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, validator
import httpx
from llama_cloud_services import LlamaParse

logger = logging.getLogger(__name__)

# Usar SOLO esta variable de entorno
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

ParsingPreset = Literal["fast", "balanced", "premium"]

class DocumentParsingRequest(BaseModel):
    file_url: str = Field(..., description="URL del archivo a procesar")
    parsing_preset: ParsingPreset = Field("balanced", description="Preset de parseo: fast, balanced o premium")
    language: str = Field("es", description="Idioma del documento (ISO 639-1)")
    result_as_markdown: bool = Field(True, description="Retornar resultado como Markdown")

async def parse_document_with_llamaparse(request: DocumentParsingRequest) -> Dict[str, Any]:
    if not LLAMA_CLOUD_API_KEY:
        logger.error("LLAMA_CLOUD_API_KEY no está configurada. El parseo estará deshabilitado.")
        return {
            "parsed_content": None,
            "parsing_status": "disabled",
            "parsing_error": "LLAMA_CLOUD_API_KEY no configurada",
            "confidence_score": 0.0
        }
    try:
        parser = LlamaParse(
            api_key=LLAMA_CLOUD_API_KEY,
            parsing_mode=request.parsing_preset,
            result_type="markdown" if request.result_as_markdown else "text",
            language=request.language
        )
        # Descargar archivo temporalmente
        async with httpx.AsyncClient() as client:
            response = await client.get(request.file_url)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(response.content)
                tmp_file_path = tmp_file.name
        # Parsear
        result = await parser.aparse(tmp_file_path)
        markdown_documents = result.get_markdown_documents()
        parsed_content = markdown_documents[0].text if markdown_documents else ""
        os.remove(tmp_file_path)
        return {
            "parsed_content": parsed_content,
            "parsing_status": "completed",
            "parsing_error": None,
            "confidence_score": 1.0 if parsed_content else 0.0
        }
    except Exception as e:
        logger.error(f"Error en parseo con LlamaParse: {e}")
        return {
            "parsed_content": None,
            "parsing_status": "error",
            "parsing_error": str(e),
            "confidence_score": 0.0
        } 