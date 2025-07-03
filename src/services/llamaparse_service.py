"""
Enhanced LlamaParse Service
Combina lo mejor de ambas implementaciones:
- Integración automática en el flujo de backend
- Configuración flexible con presets
- Validación robusta con Pydantic
- Manejo robusto de errores y archivos temporales
"""
import os
import tempfile
import logging
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, validator
import httpx
from llama_parse import LlamaParse

logger = logging.getLogger(__name__)

# Tipos de preset permitidos
ParsingPreset = Literal["simple", "detailed"]

class DocumentParsingRequest(BaseModel):
    """Esquema de validación para solicitudes de parsing"""
    file_url: str = Field(..., description="URL del documento a parsear")
    file_name: str = Field(..., description="Nombre del archivo")
    parsing_preset: ParsingPreset = Field(default="simple", description="Preset de parsing ('simple' o 'detailed')")
    parsing_instructions: Optional[str] = Field(default=None, description="Instrucciones específicas para el parsing")
    language: str = Field(default="pt", description="Idioma del documento (código ISO 639-1)")
    result_as_markdown: bool = Field(default=True, description="Retornar resultado como Markdown")

    @validator('file_url')
    def validate_file_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('file_url debe ser una URL válida')
        return v

    @validator('language')
    def validate_language(cls, v):
        # Normalizar idioma
        if v.lower() in ['por', 'portuguese']:
            return 'pt'
        return v.lower()

class DocumentParsingResponse(BaseModel):
    """Esquema de respuesta del parsing"""
    success: bool
    parsed_content: Optional[str] = None
    confidence_score: float = 0.0
    parsing_status: str = "pending"
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class EnhancedLlamaParseService:
    """Servicio mejorado de LlamaParse con características avanzadas"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LLAMAPARSE_API_KEY")
        if not self.api_key:
            raise ValueError("LLAMAPARSE_API_KEY no configurada")
        
        logger.info("EnhancedLlamaParseService inicializado correctamente")

    async def _download_file_from_url(self, file_url: str) -> str:
        """
        Descarga un archivo de URL a un archivo temporal con manejo robusto
        Adoptado de la implementación de referencia
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Descargando archivo desde: {file_url}")
                response = await client.get(file_url)
                response.raise_for_status()
                
                # Extraer extensión limpiando parámetros de consulta
                url_without_params = file_url.split('?')[0]
                possible_extension = ""
                if '.' in url_without_params.split('/')[-1]:
                    possible_extension = "." + url_without_params.split('/')[-1].split('.')[-1]
                
                # Crear archivo temporal
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix=possible_extension, 
                    mode='wb'
                )
                temp_file.write(response.content)
                temp_file.close()
                
                logger.info(f"Archivo descargado exitosamente a: {temp_file.name}")
                return temp_file.name
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Error HTTP {e.response.status_code} al descargar {file_url}"
            logger.error(f"{error_msg}: {e.response.text}")
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Error de conexión al descargar {file_url}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error inesperado al descargar {file_url}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    def _get_parser_instance(
        self, 
        preset: ParsingPreset, 
        language: str, 
        result_as_markdown: bool,
        parsing_instructions: Optional[str] = None
    ) -> LlamaParse:
        """
        Configura y retorna una instancia del parser LlamaParse
        con configuración basada en preset
        """
        # Mapear preset a configuración
        if preset == "detailed":
            parsing_instruction = parsing_instructions or "Extraer todo el contenido del documento incluyendo tablas, metadatos y estructura detallada."
        else:  # simple
            parsing_instruction = parsing_instructions or "Extraer el contenido principal del documento de forma clara y concisa."
        
        try:
            parser = LlamaParse(
                api_key=self.api_key,
                result_type="markdown" if result_as_markdown else "text",
                language=language,
                parsing_instruction=parsing_instruction,
                verbose=True
            )
            logger.info(f"Parser LlamaParse configurado - Preset: {preset}, Idioma: {language}")
            return parser
        except Exception as e:
            logger.error(f"Error al configurar parser LlamaParse: {str(e)}")
            raise

    def _calculate_confidence_score(
        self, 
        parsed_content: str, 
        file_name: str,
        preset: ParsingPreset
    ) -> float:
        """
        Calcula una puntuación de confianza mejorada basada en múltiples factores
        """
        if not parsed_content or len(parsed_content.strip()) < 10:
            return 0.0
        
        # Factores de confianza
        content_length_score = min(0.4, len(parsed_content) / 2500)  # Máximo 0.4
        
        # Bonus por estructura (headers, listas, etc.)
        structure_indicators = ['#', '*', '-', '|', '\n\n']
        structure_score = min(0.3, sum(parsed_content.count(indicator) for indicator in structure_indicators) / 50)
        
        # Bonus por preset detallado
        preset_bonus = 0.1 if preset == "detailed" else 0.05
        
        # Penalty por contenido muy corto
        length_penalty = 0.0 if len(parsed_content) > 100 else -0.2
        
        # Bonus por tipo de archivo
        file_extension = file_name.lower().split('.')[-1] if '.' in file_name else ''
        format_bonus = {
            'pdf': 0.15,
            'docx': 0.10,
            'doc': 0.05,
            'txt': 0.05
        }.get(file_extension, 0.0)
        
        confidence = content_length_score + structure_score + preset_bonus + length_penalty + format_bonus
        return round(min(1.0, max(0.0, confidence)), 3)

    async def parse_document_enhanced(
        self,
        file_url: str,
        file_name: str,
        parsing_preset: ParsingPreset = "simple",
        parsing_instructions: Optional[str] = None,
        language: str = "pt",
        result_as_markdown: bool = True
    ) -> DocumentParsingResponse:
        """
        Parsea un documento con configuración avanzada y manejo robusto de errores
        """
        # Validar entrada
        try:
            request = DocumentParsingRequest(
                file_url=file_url,
                file_name=file_name,
                parsing_preset=parsing_preset,
                parsing_instructions=parsing_instructions,
                language=language,
                result_as_markdown=result_as_markdown
            )
        except Exception as e:
            logger.error(f"Error de validación: {str(e)}")
            return DocumentParsingResponse(
                success=False,
                error=f"Error de validación: {str(e)}",
                parsing_status="failed"
            )

        temp_file_path = None
        
        try:
            logger.info(f"Iniciando parsing mejorado - Archivo: {file_name}, Preset: {parsing_preset}")
            
            # Descargar archivo
            temp_file_path = await self._download_file_from_url(request.file_url)
            
            # Configurar parser
            parser = self._get_parser_instance(
                preset=request.parsing_preset,
                language=request.language,
                result_as_markdown=request.result_as_markdown,
                parsing_instructions=request.parsing_instructions
            )
            
            # Realizar parsing
            logger.info("Ejecutando parsing con LlamaParse...")
            documents = await parser.aload_data(temp_file_path)
            
            if not documents:
                logger.warning("LlamaParse no retornó documentos")
                return DocumentParsingResponse(
                    success=False,
                    error="No se pudieron extraer documentos del archivo",
                    parsing_status="failed"
                )
            
            # Combinar contenido
            parsed_content = "\n\n---\n\n".join([doc.text for doc in documents if doc.text])
            
            if not parsed_content or len(parsed_content.strip()) < 10:
                logger.warning("Contenido parseado muy corto o vacío")
                return DocumentParsingResponse(
                    success=False,
                    error="El contenido extraído está vacío o es muy corto",
                    parsing_status="failed"
                )
            
            # Calcular puntuación de confianza
            confidence_score = self._calculate_confidence_score(
                parsed_content, 
                file_name, 
                request.parsing_preset
            )
            
            # Metadatos adicionales
            metadata = {
                "preset_used": request.parsing_preset,
                "language": request.language,
                "document_count": len(documents),
                "content_length": len(parsed_content),
                "has_instructions": bool(request.parsing_instructions)
            }
            
            logger.info(
                f"Parsing completado exitosamente - "
                f"Confianza: {confidence_score}, "
                f"Longitud: {len(parsed_content)} chars"
            )
            
            return DocumentParsingResponse(
                success=True,
                parsed_content=parsed_content,
                confidence_score=confidence_score,
                parsing_status="completed",
                metadata=metadata
            )
            
        except Exception as e:
            error_msg = f"Error durante el parsing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return DocumentParsingResponse(
                success=False,
                error=error_msg,
                parsing_status="failed"
            )
            
        finally:
            # Limpiar archivo temporal
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    logger.info(f"Archivo temporal eliminado: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar archivo temporal {temp_file_path}: {str(e)}")

# Función de conveniencia para mantener compatibilidad con código existente
async def parse_document_with_llamaparse(file_url: str, file_name: str) -> dict:
    """
    Función de compatibilidad que mantiene la interfaz original
    pero usa el servicio mejorado internamente
    """
    service = EnhancedLlamaParseService()
    
    # Determinar preset basado en el tipo de archivo
    file_extension = file_name.lower().split('.')[-1] if '.' in file_name else ''
    preset = "detailed" if file_extension in ['pdf', 'docx'] else "simple"
    
    # Instrucciones específicas basadas en el contexto del proyecto
    instructions = (
        "Extraer toda la información relevante del documento incluyendo: "
        "datos de empresa, información legal, contratos, tablas de datos, "
        "fechas importantes, y cualquier información que pueda ser útil "
        "para análisis de cumplimiento y triagem."
    )
    
    result = await service.parse_document_enhanced(
        file_url=file_url,
        file_name=file_name,
        parsing_preset=preset,
        parsing_instructions=instructions,
        language="pt"
    )
    
    # Convertir a formato esperado por el código existente
    return {
        "success": result.success,
        "parsed_content": result.parsed_content,
        "confidence_score": result.confidence_score,
        "parsing_status": result.parsing_status,
        "error": result.error,
        "metadata": result.metadata
    } 