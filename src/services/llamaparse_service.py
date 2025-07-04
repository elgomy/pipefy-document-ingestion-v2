import os
from dotenv import load_dotenv
load_dotenv()  # Carga las variables del archivo .env
import tempfile
import logging
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
import httpx
from llama_cloud_services import LlamaParse
import asyncio

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
        # Limpiar extensión del archivo
        url_without_params = request.file_url.split('?')[0]
        extension = "." + url_without_params.split('.')[-1] if '.' in url_without_params else ".pdf"
        # Descargar archivo temporalmente
        async with httpx.AsyncClient() as client:
            response = await client.get(request.file_url)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp_file:
                tmp_file.write(response.content)
                tmp_file_path = tmp_file.name
        parser = LlamaParse(
            api_key=LLAMA_CLOUD_API_KEY,
            num_workers=1,
            verbose=True,
            language=request.language
        )
        # Parsear
        result = await parser.aparse(tmp_file_path)
        if request.result_as_markdown:
            markdown_documents = result.get_markdown_documents(split_by_page=True)
            parsed_content = "\n\n---\n\n".join([doc.text for doc in markdown_documents if hasattr(doc, 'text') and doc.text])
        else:
            text_documents = result.get_text_documents(split_by_page=False)
            parsed_content = "\n\n---\n\n".join([doc for doc in text_documents if doc])
        os.remove(tmp_file_path)
        return {
            "parsed_content": parsed_content,
            "parsing_status": "completed" if parsed_content else "empty",
            "parsing_error": None if parsed_content else "No se extrajo contenido textual",
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

# Función de prueba directa con la URL problemática
async def test_llamaparse_with_url():
    test_url = "https://aguoqgqbdbyipztgrmbd.supabase.co/storage/v1/object/public/documents/1130856215/4-CONTRATOSOCIAL.pdf?"
    request = DocumentParsingRequest(file_url=test_url, parsing_preset="balanced", language="es", result_as_markdown=True)
    result = await parse_document_with_llamaparse(request)
    print("Resultado de parseo:")
    print(result)

if __name__ == "__main__":
    asyncio.run(test_llamaparse_with_url()) 