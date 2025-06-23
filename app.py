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
import httpx
import tempfile
import os
import asyncio

# Importar el sistema de error handling y métricas
from src.utils.error_handler import with_error_handling
from src.services.metrics_service import MetricsService

# Importar funciones de negocio
from src.services.triagem_service import gerar_e_armazenar_cartao_cnpj

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
# FUNCIONES AUXILIARES PARA WEBHOOK
# ============================================================================

async def get_pipefy_card_attachments(card_id: str) -> List[PipefyAttachment]:
    """Obtém anexos de um card do Pipefy via GraphQL."""
    if not PIPEFY_TOKEN:
        logger.error("ERRO: Token Pipefy não configurado.")
        return []
    
    query = """
    query GetCardAttachments($cardId: ID!) {
        card(id: $cardId) {
            id
            title
            fields {
                name
                value
            }
        }
    }
    """
    
    variables = {"cardId": card_id}
    headers = {
        "Authorization": f"Bearer {PIPEFY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": query,
        "variables": variables
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.pipefy.com/graphql", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"ERRO GraphQL Pipefy: {data['errors']}")
                return []
            
            card_data = data.get("data", {}).get("card")
            if not card_data:
                logger.warning(f"ALERTA: Card {card_id} não encontrado ou sem dados.")
                return []
            
            attachments = []
            fields = card_data.get("fields", [])
            
            for field in fields:
                field_value = field.get("value", "")
                if field_value and isinstance(field_value, str):
                    try:
                        import json
                        urls = json.loads(field_value)
                        if isinstance(urls, list):
                            for url in urls:
                                if isinstance(url, str) and url.startswith("http"):
                                    filename = url.split("/")[-1].split("?")[0]
                                    if not filename or filename == "":
                                        filename = f"{field.get('name', 'documento')}.pdf"
                                    
                                    attachments.append(PipefyAttachment(
                                        name=filename,
                                        path=url
                                    ))
                    except (json.JSONDecodeError, TypeError):
                        if field_value.startswith("http"):
                            filename = field_value.split("/")[-1].split("?")[0]
                            if not filename or filename == "":
                                filename = f"{field.get('name', 'documento')}.pdf"
                            
                            attachments.append(PipefyAttachment(
                                name=filename,
                                path=field_value
                            ))
            
            logger.info(f"INFO: {len(attachments)} anexos encontrados para card {card_id}.")
            return attachments
            
    except Exception as e:
        logger.error(f"ERRO ao buscar anexos do card {card_id}: {e}")
        return []

async def download_file_to_temp(url: str, original_filename: str) -> Optional[str]:
    """Baixa um arquivo de uma URL para um arquivo temporário."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{original_filename}") as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            logger.info(f"INFO: Arquivo '{original_filename}' baixado para: {temp_file_path}")
            return temp_file_path
            
    except Exception as e:
        logger.error(f"ERRO ao baixar arquivo '{original_filename}' de {url}: {e}")
        return None

async def upload_to_supabase_storage_async(local_file_path: str, case_id: str, original_filename: str) -> Optional[str]:
    """Faz upload de um arquivo local para o Supabase Storage."""
    if not supabase_client:
        logger.error("ERRO: Cliente Supabase não inicializado.")
        return None
    
    try:
        storage_path = f"{case_id}/{original_filename}"
        
        def sync_upload_and_get_url():
            with open(local_file_path, 'rb') as file:
                upload_response = supabase_client.storage.from_(SUPABASE_STORAGE_BUCKET_NAME).upload(
                    storage_path, file, file_options={"upsert": "true"}
                )
                
                if hasattr(upload_response, 'error') and upload_response.error:
                    raise Exception(f"Erro no upload: {upload_response.error}")
                
                public_url_response = supabase_client.storage.from_(SUPABASE_STORAGE_BUCKET_NAME).get_public_url(storage_path)
                return public_url_response
        
        public_url = await asyncio.to_thread(sync_upload_and_get_url)
        
        # Limpar arquivo temporário
        try:
            os.unlink(local_file_path)
        except:
            pass
        
        logger.info(f"INFO: Upload concluído para '{original_filename}'. URL: {public_url}")
        return public_url
        
    except Exception as e:
        logger.error(f"ERRO no upload de '{original_filename}': {e}")
        try:
            os.unlink(local_file_path)
        except:
            pass
        return None

async def determine_document_tag(filename: str, card_fields: Optional[List[Dict]] = None) -> str:
    """Determina a tag do documento baseada no nome do arquivo."""
    filename_lower = filename.lower()
    
    tag_keywords = {
        "contrato_social": ["contrato", "social", "estatuto"],
        "comprovante_residencia": ["comprovante", "residencia", "endereco"],
        "documento_identidade": ["rg", "identidade", "cnh"],
        "declaracao_impostos": ["declaracao", "imposto", "ir"],
        "certificado_registro": ["certificado", "registro"],
        "procuracao": ["procuracao"],
        "balanco_patrimonial": ["balanco", "patrimonial", "demonstracao"],
        "faturamento": ["faturamento", "receita"]
    }
    
    for tag, keywords in tag_keywords.items():
        if any(keyword in filename_lower for keyword in keywords):
            return tag
    
    return "outro_documento"

async def register_document_in_db(case_id: str, document_name: str, document_tag: str, file_url: str, pipe_id: Optional[str] = None):
    """Registra um documento na tabela 'documents' do Supabase."""
    if not supabase_client:
        logger.error("ERRO: Cliente Supabase não inicializado.")
        return False
    
    try:
        data_to_insert = {
            "case_id": case_id,
            "name": document_name,
            "document_tag": document_tag,
            "file_url": file_url,
            "status": "uploaded"
        }
        
        if pipe_id:
            data_to_insert["pipe_id"] = pipe_id
            logger.info(f"INFO: Registrando documento con pipe_id: {pipe_id}")
        
        response = await asyncio.to_thread(
            supabase_client.table("documents").upsert(data_to_insert, on_conflict="case_id, name").execute
        )
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"ERRO Supabase DB (upsert) para {document_name}: {response.error.message}")
            return False
        if response.data:
            logger.info(f"INFO: Documento '{document_name}' registrado/atualizado no DB para case_id '{case_id}'.")
            return True
        logger.warning(f"AVISO: Upsert do documento '{document_name}' no DB não retornou dados nem erro explícito.")
        return False
    except Exception as e:
        logger.error(f"ERRO ao registrar documento '{document_name}' no Supabase DB: {e}")
        return False

async def get_checklist_url_from_supabase(config_name: str = "checklist_cadastro_pj") -> str:
    """Obtém a URL do checklist da tabela checklist_config."""
    if not supabase_client:
        logger.warning("AVISO: Cliente Supabase não inicializado para buscar checklist. Usando URL padrão.")
        return "https://aguoqgqbdbyipztgrmbd.supabase.co/storage/v1/object/public/checklist/checklist.pdf"
    
    try:
        logger.info(f"INFO: Buscando URL do checklist '{config_name}' de checklist_config...")
        
        def sync_get_checklist_url():
            return supabase_client.table("checklist_config").select("checklist_url").eq("config_name", config_name).single().execute()
        
        response = await asyncio.to_thread(sync_get_checklist_url)

        if response.data and response.data.get("checklist_url"):
            checklist_url = response.data["checklist_url"]
            logger.info(f"INFO: URL do checklist obtida: {checklist_url}")
            return checklist_url
        else:
            logger.warning(f"AVISO: URL do checklist '{config_name}' não encontrada. Usando URL padrão.")
            return "https://aguoqgqbdbyipztgrmbd.supabase.co/storage/v1/object/public/checklist/checklist.pdf"
            
    except Exception as e:
        logger.warning(f"AVISO: Erro ao buscar URL do checklist '{config_name}': {e}. Usando URL padrão.")
        return "https://aguoqgqbdbyipztgrmbd.supabase.co/storage/v1/object/public/checklist/checklist.pdf"

async def call_crewai_analysis_service(case_id: str, documents: List[Dict], checklist_url: str, pipe_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Llama directamente al servicio CrewAI para análisis de documentos.
    MANTIENE LA MODULARIDAD: Solo llama al servicio, no guarda en Supabase.
    El módulo CrewAI se encarga de guardar el informe en la tabla informe_cadastro.
    """
    try:
        # Preparar payload para CrewAI
        analysis_request = CrewAIAnalysisRequest(
            case_id=case_id,
            documents=documents,
            checklist_url=checklist_url,
            current_date=datetime.now().strftime('%Y-%m-%d'),
            pipe_id=pipe_id
        )
        
        logger.info(f"🔗 Llamando al servicio CrewAI para case_id: {case_id}")
        logger.info(f"📄 Documentos a analizar: {len(documents)}")
        logger.info(f"🎯 URL CrewAI: {CREWAI_SERVICE_URL}/analyze/sync")
        
        # Verificar que el servicio esté despierto
        logger.info("🏥 Verificando estado del servicio CrewAI...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as health_client:
                health_response = await health_client.get(f"{CREWAI_SERVICE_URL}/health")
                if health_response.status_code == 200:
                    logger.info("✅ Servicio CrewAI está activo")
                else:
                    logger.warning(f"⚠️ Servicio CrewAI respondió con status: {health_response.status_code}")
        except Exception as health_error:
            logger.warning(f"⚠️ No se pudo verificar estado del servicio: {health_error}")
        
        # Llamada HTTP directa al servicio CrewAI con timeout extendido para cold starts
        logger.info("🚀 Iniciando análisis CrewAI (puede tardar si el servicio estaba dormido)...")
        
        # TIMEOUT AUMENTADO: 15 minutos para manejar cold starts + análisis completo
        async with httpx.AsyncClient(timeout=900.0) as client:  
            response = await client.post(
                f"{CREWAI_SERVICE_URL}/analyze/sync",
                json=analysis_request.model_dump()
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Análisis CrewAI completado exitosamente para case_id: {case_id}")
                return {
                    "status": "success",
                    "crewai_response": result,
                    "communication": "http_direct_sync"
                }
            else:
                logger.error(f"❌ Error en servicio CrewAI: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "error": f"CrewAI service error: {response.status_code}",
                    "details": response.text
                }
                
    except httpx.TimeoutException:
        logger.error(f"⏰ Timeout al llamar al servicio CrewAI para case_id: {case_id}")
        return {
            "status": "timeout",
            "error": "CrewAI service timeout - posible cold start"
        }
    except Exception as e:
        logger.error(f"❌ Error al llamar al servicio CrewAI: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

# ============================================================================
# WEBHOOK PRINCIPAL DE PIPEFY
# ============================================================================

@app.post("/webhook/pipefy")
async def handle_pipefy_webhook(request: Request, background_tasks: BackgroundTasks, x_pipefy_signature: Optional[str] = Header(None)):
    """
    Recebe webhooks do Pipefy, processa anexos, armazena no Supabase e chama CrewAI diretamente.
    VERSIÓN HTTP DIRECTA: Mantiene modularidad pero usa comunicación HTTP directa.
    """
    try:
        # Capturar el cuerpo raw sin Pydantic
        raw_body = await request.body()
        raw_body_str = raw_body.decode('utf-8', errors='ignore')
        
        # Parsear JSON manualmente
        try:
            payload_data = json.loads(raw_body_str)
        except json.JSONDecodeError as e:
            logger.error(f"ERRO: JSON inválido recebido: {e}")
            raise HTTPException(status_code=400, detail="JSON inválido")
        
        logger.info(f"📥 Webhook Pipefy recebido. Payload length: {len(raw_body_str)}")
        
        # Validar estructura básica manualmente
        if not isinstance(payload_data, dict):
            logger.error("ERRO: Payload não é um objeto JSON válido")
            raise HTTPException(status_code=400, detail="Payload deve ser um objeto JSON")
        
        data = payload_data.get('data')
        if not data or not isinstance(data, dict):
            logger.error("ERRO: Campo 'data' ausente ou inválido")
            raise HTTPException(status_code=400, detail="Campo 'data' obrigatório")
        
        card = data.get('card')
        if not card or not isinstance(card, dict):
            logger.error("ERRO: Campo 'card' ausente ou inválido")
            raise HTTPException(status_code=400, detail="Campo 'card' obrigatório")
        
        # Extrair e convertir card_id
        card_id_raw = card.get('id')
        if card_id_raw is None:
            logger.error("ERRO: Campo 'card.id' ausente")
            raise HTTPException(status_code=400, detail="Campo 'card.id' obrigatório")
        
        card_id_str = str(card_id_raw)
        logger.info(f"📋 Processando card_id: {card_id_str}")
        
        # Extraer pipe_id si está disponible
        pipe_id = None
        if 'pipe' in card and isinstance(card['pipe'], dict):
            pipe_id = card['pipe'].get('id')
            if pipe_id:
                pipe_id = str(pipe_id)
                logger.info(f"🔗 Pipe ID encontrado: {pipe_id}")
        
        # Extraer action si existe
        action = data.get('action', 'unknown')
        logger.info(f"⚡ Ação: {action}")

        # Procesar documentos anexos del card
        attachments_from_pipefy = await get_pipefy_card_attachments(card_id_str)
        processed_documents: List[Dict[str, Any]] = []

        if not attachments_from_pipefy:
            logger.info(f"📄 Nenhum anexo encontrado para o card {card_id_str}.")
        else:
            logger.info(f"📄 {len(attachments_from_pipefy)} anexos encontrados para o card {card_id_str}.")
            for att in attachments_from_pipefy:
                logger.info(f"⬇️ Processando anexo: {att.name}...")
                
                temp_file = await download_file_to_temp(att.path, att.name)
                if temp_file:
                    storage_url = await upload_to_supabase_storage_async(temp_file, card_id_str, att.name)
                    if storage_url:
                        document_tag = await determine_document_tag(att.name)
                        success_db = await register_document_in_db(card_id_str, att.name, document_tag, storage_url, pipe_id)
                        if success_db:
                            processed_documents.append({
                                "name": att.name,
                                "file_url": storage_url,
                                "document_tag": document_tag
                            })
                        else:
                            logger.warning(f"⚠️ Falha ao fazer upload do anexo '{att.name}' para Supabase Storage.")
                else:
                    logger.warning(f"⚠️ Falha ao baixar o anexo '{att.name}' do Pipefy.")
        
        logger.info(f"✅ {len(processed_documents)} documentos processados com sucesso.")

        # Obtener URL del checklist
        logger.info("🔍 Buscando URL do checklist...")
        checklist_url = await get_checklist_url_from_supabase()
        logger.info(f"📋 URL do checklist: {checklist_url}")
        
        # 🔗 LLAMADA HTTP DIRECTA A CREWAI (en background para no bloquear respuesta)
        background_tasks.add_task(
            call_crewai_analysis_service,
            card_id_str,
            processed_documents,
            checklist_url,
            pipe_id
        )

        logger.info(f"🚀 Tarea CrewAI programada en background para case_id: {card_id_str}")
        logger.info(f"📊 Resumen del procesamiento:")
        logger.info(f"   - Card ID: {card_id_str}")
        logger.info(f"   - Pipe ID: {pipe_id}")
        logger.info(f"   - Documentos procesados: {len(processed_documents)}")
        logger.info(f"   - Checklist URL: {checklist_url}")
        logger.info(f"   - Servicio CrewAI: {CREWAI_SERVICE_URL}")

        return {
            "status": "success",
            "message": f"Webhook para card {card_id_str} processado. {len(processed_documents)} documentos processados.",
            "service": "document_ingestion_service",
            "card_id": card_id_str,
            "pipe_id": pipe_id,
            "documents_processed": len(processed_documents),
            "crewai_analysis": "initiated_in_background",
            "architecture": "modular_http_direct",
            "communication": "http_direct",
            "cold_start_handling": "enabled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ERRO inesperado no webhook: {e}")
        import traceback
        logger.error(f"TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# ============================================================================
# FUNCIONES DE NEGOCIO (MOVIDAS DESDE APP.PY RAÍZ)
# ============================================================================

@with_error_handling(api_name="pipefy")
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

@with_error_handling(api_name="pipefy")
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