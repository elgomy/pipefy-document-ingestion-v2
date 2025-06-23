#!/usr/bin/env python3
"""
Pipefy Document Ingestion Service v2.0 - Backend API Completo
ENFOQUE HÍBRIDO INTELIGENTE: Este servicio contiene TODA la lógica de negocio.
El agente CrewAI solo llama a endpoints simples de este backend.

Responsabilidades:
- Procesamiento de documentos de Pipefy
- Integración con APIs externas (CNPJá, Twilio, etc.)
- Gestión de Supabase Storage y Database
- Orquestación de flujos de trabajo
- Manejo de errores y métricas
- Comunicación HTTP con CrewAI
"""

import os
import asyncio
import tempfile
import httpx
import logging
import hmac
import hashlib
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any, Union
from fastapi import FastAPI, HTTPException, Request, Header, BackgroundTasks
from pydantic import BaseModel, field_validator, model_validator
from supabase import create_client, Client
from dotenv import load_dotenv
import json
from datetime import datetime

# Importar el sistema de error handling y métricas
from src.utils.error_handler import with_error_handling
from src.services.metrics_service import MetricsService

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variables de entorno - Configuración centralizada
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_STORAGE_BUCKET_NAME = os.getenv("SUPABASE_STORAGE_BUCKET_NAME", "documents")
PIPEFY_TOKEN = os.getenv("PIPEFY_TOKEN")
PIPEFY_WEBHOOK_SECRET = os.getenv("PIPEFY_WEBHOOK_SECRET")

# URLs de servicios
CREWAI_SERVICE_URL = os.getenv("CREWAI_SERVICE_URL", "https://pipefy-crewai-analysis-v2.onrender.com")

# Integración con APIs externas
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
CNPJA_API_KEY = os.getenv("CNPJA_API_KEY")

# IDs de fases de Pipefy
PHASE_ID_TRIAGEM = "338000020"  # Triagem Documentos AI
PHASE_ID_PENDENCIAS = os.getenv("PHASE_ID_PENDENCIAS")
PHASE_ID_EMITIR_DOCS = os.getenv("PHASE_ID_EMITIR_DOCS")
PHASE_ID_APROVADO = os.getenv("PHASE_ID_APROVADO")

# Constantes de API
PIPEFY_API_URL = "https://api.pipefy.com/graphql"

# Cliente Supabase global
supabase_client: Optional[Client] = None
metrics_service: Optional[MetricsService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação FastAPI."""
    global supabase_client, metrics_service
    
    # Startup
    logger.info("🚀 Iniciando Pipefy Document Ingestion Service v2.0...")
    
    # Validar variables críticas
    required_vars = [
        "SUPABASE_URL", "SUPABASE_ANON_KEY", "PIPEFY_TOKEN"
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"ERRO: Variables de entorno faltantes: {', '.join(missing_vars)}")
        raise RuntimeError(f"Configuración incompleta: {', '.join(missing_vars)}")
    
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("✅ Cliente Supabase inicializado com sucesso.")
        
        # Inicializar servicio de métricas
        metrics_service = MetricsService()
        logger.info("✅ Servicio de métricas inicializado.")
        
    except Exception as e:
        logger.error(f"ERRO ao inicializar servicios: {e}")
        raise RuntimeError(f"Falha na inicialização: {e}")
    
    logger.info(f"🔗 Servicio CrewAI configurado en: {CREWAI_SERVICE_URL}")
    
    yield
    
    # Shutdown
    logger.info("INFO: Encerrando Pipefy Document Ingestion Service...")

app = FastAPI(
    lifespan=lifespan, 
    title="Pipefy Document Ingestion Service v2.0",
    description="Backend API completo para procesamiento de documentos con enfoque híbrido inteligente"
)

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class PipefyCard(BaseModel):
    model_config = {"extra": "allow"}
    
    id: str
    title: Optional[str] = None
    current_phase: Optional[Dict[str, Any]] = None
    pipe: Optional[Dict[str, Any]] = None
    fields: Optional[List[Dict[str, Any]]] = None
    
    @model_validator(mode='before')
    @classmethod
    def convert_id_to_string(cls, data):
        if isinstance(data, dict) and 'id' in data:
            data['id'] = str(data['id'])
        return data

class PipefyEventData(BaseModel):
    model_config = {"extra": "allow"}
    card: PipefyCard
    action: Optional[str] = None

class PipefyWebhookPayload(BaseModel):
    model_config = {"extra": "allow"}
    data: PipefyEventData

class PipefyAttachment(BaseModel):
    name: str
    path: str

class CrewAIAnalysisRequest(BaseModel):
    case_id: str
    documents: List[Dict[str, Any]]
    checklist_url: str
    current_date: str
    pipe_id: Optional[str] = None

class SupabaseWebhookPayload(BaseModel):
    """Modelo para el payload del webhook de Supabase"""
    type: str  # INSERT, UPDATE, DELETE
    table: str
    schema: str
    record: Optional[Dict[str, Any]] = None
    old_record: Optional[Dict[str, Any]] = None

# ============================================================================
# HERRAMIENTAS SIMPLES PARA EL AGENTE CREWAI
# ============================================================================

class ClienteEnriquecimentoRequest(BaseModel):
    """Request para enriquecimiento de datos de cliente"""
    cnpj: str
    case_id: str

class ClienteEnriquecimentoResponse(BaseModel):
    """Response del enriquecimiento de datos de cliente"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str

@app.post("/api/v1/cliente/enriquecer", response_model=ClienteEnriquecimentoResponse)
async def enriquecer_cliente_api(request: ClienteEnriquecimentoRequest) -> ClienteEnriquecimentoResponse:
    """
    HERRAMIENTA SIMPLE PARA EL AGENTE: Enriquece datos de cliente con CNPJ
    
    Este endpoint encapsula TODA la lógica de:
    - Llamar a CNPJá API
    - Llamar a BrasilAPI como fallback
    - Generar tarjeta CNPJ
    - Almacenar en Supabase
    
    El agente solo necesita llamar a este endpoint con un CNPJ.
    """
    try:
        logger.info(f"🔍 Iniciando enriquecimiento de cliente para CNPJ: {request.cnpj}")
        
        # Llamar a la función de enriquecimiento completo
        success = await gerar_e_armazenar_cartao_cnpj(request.case_id, request.cnpj)
        
        if success:
            return ClienteEnriquecimentoResponse(
                success=True,
                message=f"Cliente enriquecido exitosamente para CNPJ: {request.cnpj}"
            )
        else:
            return ClienteEnriquecimentoResponse(
                success=False,
                message=f"Error al enriquecer cliente para CNPJ: {request.cnpj}"
            )
            
    except Exception as e:
        logger.error(f"❌ Error en enriquecimiento de cliente: {e}")
        return ClienteEnriquecimentoResponse(
            success=False,
            message=f"Error interno: {str(e)}"
        )

# ============================================================================
# FUNCIONES DE NEGOCIO (MOVIDAS DESDE APP.PY RAÍZ)
# ============================================================================

@with_error_handling(api_name="pipefy", max_retries=3, base_delay=2, max_delay=30)
async def validate_pipefy_webhook_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """
    Valida la firma del webhook de Pipefy usando HMAC-SHA256.
    """
    if not secret:
        logger.warning("⚠️ PIPEFY_WEBHOOK_SECRET não configurado. Validação de assinatura desabilitada.")
        return True
    
    if not signature:
        logger.error("❌ Header X-Pipefy-Signature ausente")
        return False
    
    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        is_valid = hmac.compare_digest(signature, expected_signature)
        
        if is_valid:
            logger.info("✅ Assinatura do webhook Pipefy validada com sucesso")
        else:
            logger.error(f"❌ Assinatura inválida. Esperado: {expected_signature[:10]}..., Recebido: {signature[:10]}...")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"❌ Erro ao validar assinatura do webhook: {e}")
        return False

@with_error_handling(api_name="pipefy", max_retries=3, base_delay=2, max_delay=30)
async def get_pipefy_field_id_for_informe_crewai(card_id: str) -> Optional[str]:
    """
    Detecta automáticamente el field_id del campo 'Informe CrewAI' en Pipefy.
    """
    if not PIPEFY_TOKEN:
        logger.error("❌ PIPEFY_TOKEN não configurado")
        return None
    
    query = """
    query GetCard($cardId: ID!) {
        card(id: $cardId) {
            id
            title
            current_phase {
                id
                name
                fields {
                    id
                    label
                    type
                }
            }
            fields {
                name
                value
                field {
                    id
                    label
                    type
                }
            }
        }
    }
    """
    
    variables = {"cardId": card_id}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                PIPEFY_API_URL,
                json={"query": query, "variables": variables},
                headers={"Authorization": f"Bearer {PIPEFY_TOKEN}"}
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"❌ Error en GraphQL: {data['errors']}")
                return None
            
            card_data = data.get("data", {}).get("card")
            if not card_data:
                logger.error(f"❌ Card {card_id} não encontrado")
                return None
            
            # Buscar en campos existentes del card
            card_fields = card_data.get("fields", [])
            for field in card_fields:
                field_info = field.get("field", {})
                if field_info.get("label") == "Informe CrewAI":
                    field_id = field_info.get("id")
                    logger.info(f"✅ Campo 'Informe CrewAI' encontrado con field_id: {field_id}")
                    return field_id
            
            # Buscar en campos de la fase actual
            current_phase = card_data.get("current_phase", {})
            phase_fields = current_phase.get("fields", [])
            for field in phase_fields:
                if field.get("label") == "Informe CrewAI":
                    field_id = field.get("id")
                    logger.info(f"✅ Campo 'Informe CrewAI' encontrado en fase con field_id: {field_id}")
                    return field_id
            
            logger.warning(f"⚠️ Campo 'Informe CrewAI' não encontrado para card {card_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar field_id: {e}")
            return None

# ============================================================================
# ENDPOINTS BÁSICOS
# ============================================================================

@app.get("/")
async def root():
    """Endpoint raíz del servicio"""
    return {
        "service": "Pipefy Document Ingestion Service v2.0",
        "status": "running",
        "architecture": "Enfoque Híbrido Inteligente",
        "description": "Backend API completo que encapsula toda la lógica de negocio"
    }

@app.get("/health")
async def health_check():
    """Health check del servicio"""
    try:
        # Verificar conexión a Supabase
        if supabase_client:
            # Test básico de conexión
            test_response = supabase_client.table("documents").select("count", count="exact").limit(1).execute()
            supabase_status = "connected"
        else:
            supabase_status = "disconnected"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "supabase": supabase_status,
                "crewai_url": CREWAI_SERVICE_URL
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))