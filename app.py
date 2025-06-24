#!/usr/bin/env python3
"""
Servicio de Ingestión de Documentos - Versión HTTP Directa
Se enfoca únicamente en procesar documentos de Pipefy y almacenarlos en Supabase.
Usa comunicación HTTP directa con el servicio CrewAI.
MANTIENE LA MODULARIDAD: Cada servicio tiene su responsabilidad específica.
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

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_STORAGE_BUCKET_NAME = os.getenv("SUPABASE_STORAGE_BUCKET_NAME", "documents")
PIPEFY_TOKEN = os.getenv("PIPEFY_TOKEN")
PIPEFY_WEBHOOK_SECRET = os.getenv("PIPEFY_WEBHOOK_SECRET")

# 🔗 COMUNICACIÓN HTTP DIRECTA - URL del servicio CrewAI
CREWAI_SERVICE_URL = os.getenv("CREWAI_SERVICE_URL", "https://pipefy-crewai-analysis-modular.onrender.com")

# 🆕 NUEVAS VARIABLES PARA INTEGRACIÓN SEGÚN PRD
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "+17245586619")
CNPJA_API_KEY = os.getenv("CNPJA_API_KEY")

# 🎯 IDs DE FASES DE PIPEFY SEGÚN PRD
PHASE_ID_TRIAGEM = "338000020"  # Triagem Documentos AI
PHASE_ID_PENDENCIAS = "338000017"  # Pendências Documentais
PHASE_ID_EMITIR_DOCS = "338000019"  # Emitir documentos
PHASE_ID_APROVADO = "338000018"  # Aprovado

# 📋 CONSTANTES DE PIPEFY API
PIPEFY_API_URL = "https://api.pipefy.com/graphql"

# Cliente Supabase global
supabase_client: Optional[Client] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação FastAPI."""
    global supabase_client
    
    # Startup
    logger.info("🚀 Iniciando Servicio de Ingestión de Documentos (HTTP Directo)...")
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("ERRO: Variáveis SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórias.")
        raise RuntimeError("Configuração Supabase incompleta.")
    
    if not PIPEFY_TOKEN:
        logger.error("ERRO: Variável PIPEFY_TOKEN é obrigatória.")
        raise RuntimeError("Token Pipefy não configurado.")
    
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("✅ Cliente Supabase inicializado com sucesso.")
    except Exception as e:
        logger.error(f"ERRO ao inicializar cliente Supabase: {e}")
        raise RuntimeError(f"Falha na inicialização do Supabase: {e}")
    
    logger.info(f"🔗 Servicio CrewAI configurado en: {CREWAI_SERVICE_URL}")
    
    yield
    
    # Shutdown
    logger.info("INFO: Encerrando Servicio de Ingestión de Documentos...")

app = FastAPI(
    lifespan=lifespan, 
    title="Document Ingestion Service - HTTP Direct",
    description="Servicio modular para ingestión de documentos con comunicación HTTP directa"
)

# Modelos Pydantic
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

# 🔗 Modelo para comunicación HTTP directa con CrewAI
class CrewAIAnalysisRequest(BaseModel):
    case_id: str
    documents: List[Dict[str, Any]]
    checklist_url: str
    current_date: str
    pipe_id: Optional[str] = None

# 📋 Modelos para Webhook de Supabase
class SupabaseWebhookPayload(BaseModel):
    """Modelo para el payload del webhook de Supabase"""
    type: str  # INSERT, UPDATE, DELETE
    table: str
    schema: str
    record: Optional[Dict[str, Any]] = None
    old_record: Optional[Dict[str, Any]] = None

# 🔐 Función para validar webhook secret de Pipefy
def validate_pipefy_webhook_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """
    Valida la firma del webhook de Pipefy usando HMAC-SHA256.
    
    Args:
        payload_body: Cuerpo raw del webhook en bytes
        signature: Firma recibida en el header X-Pipefy-Signature
        secret: Secret configurado en Pipefy
    
    Returns:
        bool: True si la firma es válida, False en caso contrario
    """
    if not secret:
        logger.warning("⚠️ PIPEFY_WEBHOOK_SECRET não configurado. Validação de assinatura desabilitada.")
        return True  # Si no hay secret configurado, permitir el webhook
    
    if not signature:
        logger.error("❌ Header X-Pipefy-Signature ausente")
        return False
    
    try:
        # Pipefy usa HMAC-SHA256 y envía la firma como hex
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        # Comparar de forma segura
        is_valid = hmac.compare_digest(signature, expected_signature)
        
        if is_valid:
            logger.info("✅ Assinatura do webhook Pipefy validada com sucesso")
        else:
            logger.error(f"❌ Assinatura inválida. Esperado: {expected_signature[:10]}..., Recebido: {signature[:10]}...")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"❌ Erro ao validar assinatura do webhook: {e}")
        return False

# 🔍 Función para detectar automáticamente el field_id de Pipefy
async def get_pipefy_field_id_for_informe_crewai(card_id: str) -> Optional[str]:
    """
    Detecta automáticamente el field_id del campo 'Informe CrewAI' en Pipefy.
    MEJORADO: Maneja el comportamiento específico de Pipefy donde los campos
    solo aparecen en la API cuando tienen algún valor asignado.
    
    Args:
        card_id: ID del card de Pipefy
    
    Returns:
        str: field_id si se encuentra, None en caso contrario
    """
    if not PIPEFY_TOKEN:
        logger.error("ERRO: Token Pipefy não configurado.")
        return None
    
    query = """
    query GetCardFields($cardId: ID!) {
        card(id: $cardId) {
            id
            title
            current_phase {
                id
                name
            }
            fields {
                field {
                    id
                    label
                    type
                }
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
                logger.error(f"ERRO GraphQL ao buscar campos: {data['errors']}")
                return None
            
            card_data = data.get("data", {}).get("card")
            if not card_data:
                logger.warning(f"Card {card_id} não encontrado.")
                return None
            
            # Obtener información de la fase actual
            current_phase = card_data.get("current_phase", {})
            phase_id = current_phase.get("id")
            phase_name = current_phase.get("name", "Desconhecida")
            
            logger.info(f"📍 Card {card_id} está na fase: {phase_name} (ID: {phase_id})")
            
            fields = card_data.get("fields", [])
            logger.info(f"📋 Total de campos encontrados: {len(fields)}")
            
            # Buscar por nome exato "Informe CrewAI"
            for field in fields:
                field_info = field.get("field", {})
                field_label = field_info.get("label", "").strip()
                field_name = field.get("name", "").strip()
                
                # Verificar coincidencia exacta con "Informe CrewAI"
                if field_label == "Informe CrewAI" or field_name == "Informe CrewAI":
                    field_id = field_info.get("id")
                    logger.info(f"✅ Campo 'Informe CrewAI' encontrado: ID {field_id}")
                    logger.info(f"   - Label: '{field_label}'")
                    logger.info(f"   - Name: '{field_name}'")
                    logger.info(f"   - Type: {field_info.get('type')}")
                    return field_id
            
            # Si no se encuentra con nombre exacto, buscar por palabras clave
            target_keywords = [
                "informe crewai",
                "informe crew ai", 
                "crewai informe",
                "crew ai informe"
            ]
            
            for field in fields:
                field_info = field.get("field", {})
                field_label = field_info.get("label", "").lower()
                field_name = field.get("name", "").lower()
                
                for keyword in target_keywords:
                    if keyword in field_label or keyword in field_name:
                        field_id = field_info.get("id")
                        logger.info(f"✅ Campo encontrado por keyword '{keyword}': ID {field_id}")
                        logger.info(f"   - Label: '{field_info.get('label')}'")
                        logger.info(f"   - Name: '{field.get('name')}'")
                        return field_id
            
            # COMPORTAMIENTO ESPECÍFICO DE PIPEFY: Los campos sin valor no aparecen en la API
            logger.warning(f"⚠️ Campo 'Informe CrewAI' não encontrado no card {card_id}")
            logger.warning(f"🔍 IMPORTANTE: En Pipefy, los campos solo aparecen en la API cuando tienen algún valor")
            logger.info(f"📋 Campos disponibles en el card (solo los que tienen valor):")
            for field in fields:
                field_info = field.get("field", {})
                field_value = field.get("value", "")
                logger.info(f"   - '{field.get('name')}' (Label: '{field_info.get('label')}', ID: {field_info.get('id')}, Value: '{field_value[:50]}...')")
            
            # Retornar información de la fase para crear el campo si es necesario
            return {"phase_id": phase_id, "phase_name": phase_name, "field_not_found": True}
            
    except Exception as e:
        logger.error(f"ERRO ao buscar field_id para card {card_id}: {e}")
        return None

# 🆕 Función para crear campo "Informe CrewAI" en una fase específica
async def create_informe_crewai_field_in_phase(phase_id: str) -> Optional[str]:
    """
    Crea el campo 'Informe CrewAI' en una fase específica de Pipefy.
    
    Args:
        phase_id: ID de la fase donde crear el campo
    
    Returns:
        str: field_id del campo creado, None si falla
    """
    if not PIPEFY_TOKEN:
        logger.error("ERRO: Token Pipefy não configurado.")
        return None
    
    mutation = """
    mutation CreateInformeCrewAIField($phaseId: ID!) {
        createPhaseField(input: {
            phase_id: $phaseId,
            type: "long_text",
            label: "Informe CrewAI",
            description: "Informe generado automáticamente por CrewAI con análisis de documentos",
            required: false,
            editable: true
        }) {
            phase_field {
                id
                label
                type
                description
            }
        }
    }
    """
    
    variables = {"phaseId": phase_id}
    headers = {
        "Authorization": f"Bearer {PIPEFY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": mutation,
        "variables": variables
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.pipefy.com/graphql", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"ERRO GraphQL ao criar campo: {data['errors']}")
                return None
            
            result = data.get("data", {}).get("createPhaseField", {})
            phase_field = result.get("phase_field", {})
            
            if phase_field and phase_field.get("id"):
                field_id = phase_field.get("id")
                logger.info(f"✅ Campo 'Informe CrewAI' criado com sucesso!")
                logger.info(f"   - Field ID: {field_id}")
                logger.info(f"   - Label: {phase_field.get('label')}")
                logger.info(f"   - Type: {phase_field.get('type')}")
                logger.info(f"   - Phase ID: {phase_id}")
                return field_id
            else:
                logger.error(f"❌ Resposta inesperada ao criar campo: {result}")
                return None
                
    except Exception as e:
        logger.error(f"❌ Erro ao criar campo 'Informe CrewAI' na fase {phase_id}: {e}")
        return None

# 🔄 Función para asignar valor inicial al campo recién creado
async def initialize_field_with_placeholder(card_id: str, field_id: str) -> bool:
    """
    Asigna un valor inicial al campo para que aparezca en futuras consultas de la API.
    Esto es necesario debido al comportamiento específico de Pipefy.
    
    Args:
        card_id: ID del card
        field_id: ID del campo a inicializar
    
    Returns:
        bool: True si la inicialización fue exitosa
    """
    placeholder_value = "🔄 Inicializando campo... El informe se actualizará automáticamente."
    
    mutation = """
    mutation {
        updateCardField(input: {card_id: %s, field_id: "%s", new_value: "%s"}) {
            card {
                id
                title
            }
        }
    }
    """ % (card_id, field_id, placeholder_value)
    
    headers = {
        "Authorization": f"Bearer {PIPEFY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {"query": mutation}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.pipefy.com/graphql", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"ERRO ao inicializar campo: {data['errors']}")
                return False
            
            result = data.get("data", {}).get("updateCardField", {})
            if result and result.get("card"):
                logger.info(f"✅ Campo inicializado com placeholder para aparecer na API")
                return True
            else:
                logger.error(f"❌ Falha ao inicializar campo com placeholder")
                return False
                
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar campo: {e}")
        return False

# 📝 Función para actualizar campo específico en Pipefy (VERSIÓN DEFINITIVA CON FIELD_ID FIJO)
async def update_pipefy_informe_crewai_field(card_id: str, informe_content: str) -> bool:
    """
    Actualiza el campo 'Informe CrewAI' en Pipefy usando el field_id fijo descubierto.
    
    SOLUCIÓN DEFINITIVA:
    - Field ID fijo: "informe_crewai_2" (descubierto mediante query pipe.start_form_fields)
    - Sintaxis oficial: updateCardField con card_id, field_id, new_value
    - Sin búsquedas dinámicas ni creación de campos
    
    Args:
        card_id: ID del card de Pipefy
        informe_content: Contenido del informe a actualizar
    
    Returns:
        bool: True si la actualización fue exitosa, False en caso contrario
    """
    try:
        logger.info(f"🔄 Actualizando campo 'Informe CrewAI' para card: {card_id}")
        logger.info(f"📝 Field ID fijo: informe_crewai_2")
        
        # Field ID fijo descubierto por el usuario
        field_id = "informe_crewai_2"
        
        # Escapar contenido para GraphQL
        escaped_content = informe_content.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
        
        # Sintaxis oficial de Pipefy
        mutation = """
        mutation {
            updateCardField(input: {card_id: %s, field_id: "%s", new_value: "%s"}) {
                card {
                    id
                    title
                }
            }
        }
        """ % (card_id, field_id, escaped_content)
        
        headers = {
            "Authorization": f"Bearer {PIPEFY_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {"query": mutation}
        
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.pipefy.com/graphql", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"❌ Erro GraphQL ao atualizar campo: {data['errors']}")
                return False
            
            result = data.get("data", {}).get("updateCardField", {})
            card_info = result.get("card", {})
            
            if card_info and card_info.get("id"):
                logger.info(f"✅ Campo 'Informe CrewAI' atualizado com sucesso!")
                logger.info(f"   - Card ID: {card_info.get('id')}")
                logger.info(f"   - Card Title: {card_info.get('title')}")
                logger.info(f"   - Field ID: {field_id}")
                logger.info(f"   - Conteúdo: {informe_content[:100]}...")
                logger.info(f"   - Estratégia: Field ID fijo + sintaxis oficial")
                return True
            else:
                logger.error(f"❌ Resposta inesperada da mutação: {result}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar campo 'Informe CrewAI': {e}")
        return False

# Funciones auxiliares (iguales al original)
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

# 🔗 COMUNICACIÓN HTTP DIRECTA CON CREWAI
async def call_crewai_analysis_service(case_id: str, documents: List[Dict], checklist_url: str, pipe_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Llama directamente al servicio CrewAI para análisis de documentos.
    MANTIENE LA MODULARIDAD: Solo llama al servicio, no guarda en Supabase.
    El módulo CrewAI se encarga de guardar el informe en la tabla informe_cadastro.
    
    MEJORADO: Maneja cold starts y timeouts de Render.
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
        
        # MEJORADO: Primero verificar que el servicio esté despierto
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
                
                # Procesar resultado completo
                if result.get("status") == "completed" and "analysis_result" in result:
                    analysis_result = result["analysis_result"]
                    summary_report = analysis_result.get("summary_report", "")
                    
                    # MODULARIDAD: Solo el módulo CrewAI guarda en Supabase
                    # Este módulo solo se encarga de la comunicación con Pipefy
                    logger.info(f"💾 Informe guardado por módulo CrewAI en tabla informe_cadastro")
                    
                    # 🆕 NUEVA LÓGICA: Verificar si hay respuesta JSON estructurada para orquestación
                    structured_response = analysis_result.get("structured_response")
                    if structured_response and isinstance(structured_response, dict):
                        logger.info(f"🎯 Resposta JSON estruturada detectada - Executando orquestrador")
                        
                        # Executar orquestrador com a resposta estruturada
                        orchestration_result = await handle_crewai_analysis_result(case_id, structured_response)
                        
                        return {
                            "status": "success_with_orchestration",
                            "crewai_response": result,
                            "orchestration_result": orchestration_result,
                            "supabase_saved_by_crewai": True,
                            "communication": "http_direct_sync_with_orchestration",
                            "risk_score": analysis_result.get("risk_score"),
                            "summary_report": summary_report,
                            "architecture": "modular_separation_v2"
                        }
                    else:
                        # LÓGICA ANTERIOR: Solo actualizar campo Informe CrewAI (compatibilidad)
                        logger.info(f"📝 Resposta não estruturada - Usando lógica anterior")
                        pipefy_updated = False
                        if summary_report:
                            logger.info(f"📝 Actualizando campo 'Informe CrewAI' en Pipefy para case_id: {case_id}")
                            pipefy_updated = await update_pipefy_informe_crewai_field(case_id, summary_report)
                            
                            if pipefy_updated:
                                logger.info(f"✅ Campo 'Informe CrewAI' actualizado exitosamente para case_id: {case_id}")
                            else:
                                logger.warning(f"⚠️ No se pudo actualizar campo 'Informe CrewAI' para case_id: {case_id}")
                        
                        return {
                            "status": "success",
                            "crewai_response": result,
                            "supabase_saved_by_crewai": True,  # Guardado por el módulo CrewAI
                            "pipefy_updated": pipefy_updated,
                            "communication": "http_direct_sync",
                            "risk_score": analysis_result.get("risk_score"),
                            "summary_report": summary_report,
                            "architecture": "modular_separation"
                        }
                else:
                    logger.warning(f"⚠️ Respuesta CrewAI incompleta para case_id: {case_id}")
                    return {
                        "status": "partial_success",
                        "crewai_response": result,
                        "communication": "http_direct_sync"
                    }
            elif response.status_code == 502:
                logger.error(f"🛌 Servicio CrewAI está dormido (502 Bad Gateway) - Reintentando en 30 segundos...")
                
                # RETRY PARA COLD STARTS: Esperar y reintentar una vez
                await asyncio.sleep(30)
                logger.info("🔄 Reintentando llamada a CrewAI después de cold start...")
                
                async with httpx.AsyncClient(timeout=900.0) as retry_client:
                    retry_response = await retry_client.post(
                        f"{CREWAI_SERVICE_URL}/analyze/sync",
                        json=analysis_request.model_dump()
                    )
                    
                    if retry_response.status_code == 200:
                        result = retry_response.json()
                        logger.info(f"✅ Análisis CrewAI completado exitosamente en reintento para case_id: {case_id}")
                        
                        if result.get("status") == "completed" and "analysis_result" in result:
                            analysis_result = result["analysis_result"]
                            summary_report = analysis_result.get("summary_report", "")
                            
                            logger.info(f"💾 Informe guardado por módulo CrewAI en tabla informe_cadastro")
                            
                            # 🆕 NUEVA LÓGICA: Verificar si hay respuesta JSON estructurada para orquestación (retry)
                            structured_response = analysis_result.get("structured_response")
                            if structured_response and isinstance(structured_response, dict):
                                logger.info(f"🎯 Resposta JSON estruturada detectada no retry - Executando orquestrador")
                                
                                # Executar orquestrador com a resposta estruturada
                                orchestration_result = await handle_crewai_analysis_result(case_id, structured_response)
                                
                                return {
                                    "status": "success_after_retry_with_orchestration",
                                    "crewai_response": result,
                                    "orchestration_result": orchestration_result,
                                    "supabase_saved_by_crewai": True,
                                    "communication": "http_direct_sync_retry_with_orchestration",
                                    "risk_score": analysis_result.get("risk_score"),
                                    "summary_report": summary_report,
                                    "architecture": "modular_separation_v2",
                                    "cold_start_handled": True
                                }
                            else:
                                # LÓGICA ANTERIOR: Solo actualizar campo Informe CrewAI (compatibilidad retry)
                                logger.info(f"📝 Resposta não estruturada no retry - Usando lógica anterior")
                                pipefy_updated = False
                                if summary_report:
                                    logger.info(f"📝 Actualizando campo 'Informe CrewAI' en Pipefy para case_id: {case_id}")
                                    pipefy_updated = await update_pipefy_informe_crewai_field(case_id, summary_report)
                                
                                return {
                                    "status": "success_after_retry",
                                    "crewai_response": result,
                                    "supabase_saved_by_crewai": True,
                                    "pipefy_updated": pipefy_updated,
                                    "communication": "http_direct_sync_retry",
                                    "risk_score": analysis_result.get("risk_score"),
                                    "summary_report": summary_report,
                                    "architecture": "modular_separation",
                                    "cold_start_handled": True
                                }
                    
                    logger.error(f"❌ Reintento falló: {retry_response.status_code} - {retry_response.text}")
                    return {
                        "status": "error_after_retry",
                        "error": f"CrewAI service error after retry: {retry_response.status_code}",
                        "details": retry_response.text,
                        "communication": "http_direct_sync_retry_failed"
                    }
            else:
                logger.error(f"❌ Error en servicio CrewAI: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "error": f"CrewAI service error: {response.status_code}",
                    "details": response.text,
                    "communication": "http_direct_sync"
                }
                
    except httpx.TimeoutException:
        logger.error(f"⏰ Timeout al llamar al servicio CrewAI para case_id: {case_id}")
        logger.error("💡 Esto puede indicar que el servicio está en cold start. Considera usar el endpoint asíncrono.")
        return {
            "status": "timeout",
            "error": "CrewAI service timeout - posible cold start",
            "communication": "http_direct_sync",
            "suggestion": "El servicio puede estar dormido. Reintenta en unos minutos."
        }
    except Exception as e:
        logger.error(f"❌ Error al llamar al servicio CrewAI: {e}")
        return {
            "status": "error",
            "error": str(e),
            "communication": "http_direct_sync"
        }

# 🆕 FUNCIONES DE INTEGRACIÓN SEGÚN PRD

async def move_pipefy_card_to_phase(card_id: str, phase_id: str) -> bool:
    """
    Mueve un card de Pipefy a una nueva fase usando la API GraphQL.
    
    Args:
        card_id: ID del card a mover
        phase_id: ID de la fase destino
    
    Returns:
        bool: True si el movimiento fue exitoso, False en caso contrario
    """
    if not PIPEFY_TOKEN:
        logger.error("❌ Token Pipefy não configurado para mover card")
        return False
    
    mutation = """
    mutation MoveCardToPhase($cardId: ID!, $phaseId: ID!) {
        moveCardToPhase(input: {card_id: $cardId, destination_phase_id: $phaseId}) {
            card {
                id
                current_phase {
                    id
                    name
                }
            }
        }
    }
    """
    
    variables = {
        "cardId": card_id,
        "phaseId": phase_id
    }
    
    headers = {
        "Authorization": f"Bearer {PIPEFY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": mutation,
        "variables": variables
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(PIPEFY_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"❌ Erro GraphQL ao mover card {card_id}: {data['errors']}")
                return False
            
            move_result = data.get("data", {}).get("moveCardToPhase")
            if move_result and move_result.get("card"):
                new_phase = move_result["card"]["current_phase"]
                logger.info(f"✅ Card {card_id} movido para fase: {new_phase['name']} (ID: {new_phase['id']})")
                return True
            else:
                logger.error(f"❌ Resposta inesperada ao mover card {card_id}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Erro ao mover card {card_id} para fase {phase_id}: {e}")
        return False

async def get_manager_phone_for_card(card_id: str) -> Optional[str]:
    """
    Obtém o número de telefone do gestor comercial responsável pelo card.
    Por enquanto retorna um número fixo para testes, pero puede ser expandido
    para buscar em campos do card ou base de dados.
    
    Args:
        card_id: ID do card
    
    Returns:
        str: Número de telefone do gestor ou None se não encontrado
    """
    # TODO: Implementar lógica para buscar o telefone real do gestor
    # Pode ser um campo no card ou uma consulta à base de dados
    
    # Por enquanto, usar número de teste
    test_manager_phone = "+5531999999999"  # Substituir por lógica real
    
    logger.info(f"📞 Número do gestor para card {card_id}: {test_manager_phone}")
    return test_manager_phone

async def send_whatsapp_notification(card_id: str, relatorio_detalhado: str) -> bool:
    """
    Envia notificação via WhatsApp usando Twilio para pendências bloqueantes.
    
    Args:
        card_id: ID do card com pendência
        relatorio_detalhado: Relatório detalhado da pendência
    
    Returns:
        bool: True se a notificação foi enviada com sucesso
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.error("❌ Credenciais Twilio não configuradas")
        return False
    
    try:
        # Importar Twilio apenas quando necessário
        from twilio.rest import Client
        
        # Obter número do gestor
        manager_phone = await get_manager_phone_for_card(card_id)
        if not manager_phone:
            logger.error(f"❌ Número do gestor não encontrado para card {card_id}")
            return False
        
        # Criar cliente Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Preparar mensagem
        message_body = (
            f"🚨 *Pendência Crítica no Pipefy!*\n\n"
            f"📋 Card: https://app.pipefy.com/open-cards/{card_id}\n\n"
            f"📄 *Resumo da Pendência:*\n{relatorio_detalhado[:300]}...\n\n"
            f"⚡ *Ação Necessária:* Verifique o card para detalhes e providencie a documentação necessária.\n\n"
            f"🤖 Mensagem automática do sistema de triagem documental."
        )
        
        # Enviar mensagem
        message = client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            body=message_body,
            to=f"whatsapp:{manager_phone}"
        )
        
        logger.info(f"✅ Notificação WhatsApp enviada com sucesso para {manager_phone}")
        logger.info(f"📱 SID da mensagem: {message.sid}")
        return True
        
    except ImportError:
        logger.error("❌ Biblioteca Twilio não instalada. Execute: pip install twilio")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao enviar notificação WhatsApp: {e}")
        return False

async def gerar_e_armazenar_cartao_cnpj(case_id: str, cnpj: str) -> bool:
    """
    Gera Cartão CNPJ via API CNPJá e armazena no Supabase Storage.
    
    Args:
        case_id: ID do caso
        cnpj: CNPJ para gerar o cartão
    
    Returns:
        bool: True se o documento foi gerado e armazenado com sucesso
    """
    if not CNPJA_API_KEY:
        logger.error("❌ API Key CNPJá não configurada")
        return False
    
    if not supabase_client:
        logger.error("❌ Cliente Supabase não inicializado")
        return False
    
    try:
        # Limpar CNPJ (remover caracteres especiais)
        cnpj_clean = ''.join(filter(str.isdigit, cnpj))
        
        if len(cnpj_clean) != 14:
            logger.error(f"❌ CNPJ inválido: {cnpj}")
            return False
        
        logger.info(f"🏭 Gerando Cartão CNPJ para {cnpj_clean} no caso {case_id}")
        
        # Chamar API CNPJá
        headers = {
            'Authorization': f'Bearer {CNPJA_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        url = f'https://api.cnpja.com/rfb/certificate?taxId={cnpj_clean}&pages=REGISTRATION'
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            # Verificar se a resposta é um PDF
            content_type = response.headers.get('content-type', '')
            if 'application/pdf' not in content_type:
                logger.error(f"❌ Resposta da API CNPJá não é um PDF: {content_type}")
                return False
            
            pdf_content = response.content
            logger.info(f"✅ PDF do Cartão CNPJ obtido com sucesso ({len(pdf_content)} bytes)")
            
            # Definir caminho no storage
            file_path = f"{case_id}/cartao_cnpj_gerado.pdf"
            
            # Upload para Supabase Storage
            def sync_upload():
                return supabase_client.storage.from_(SUPABASE_STORAGE_BUCKET_NAME).upload(
                    file_path, 
                    pdf_content,
                    file_options={"content-type": "application/pdf"}
                )
            
            upload_result = await asyncio.to_thread(sync_upload)
            
            if upload_result:
                logger.info(f"✅ Cartão CNPJ armazenado em: {file_path}")
                
                # Obter URL pública do arquivo
                def sync_get_public_url():
                    return supabase_client.storage.from_(SUPABASE_STORAGE_BUCKET_NAME).get_public_url(file_path)
                
                public_url = await asyncio.to_thread(sync_get_public_url)
                
                # Registrar documento na base de dados
                await register_document_in_db(
                    case_id=case_id,
                    document_name="cartao_cnpj_gerado.pdf",
                    document_tag="cartao_cnpj",
                    file_url=public_url
                )
                
                logger.info(f"✅ Cartão CNPJ gerado e registrado com sucesso para caso {case_id}")
                return True
            else:
                logger.error(f"❌ Falha no upload do Cartão CNPJ para caso {case_id}")
                return False
                
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Erro HTTP na API CNPJá: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao gerar Cartão CNPJ: {e}")
        return False

async def handle_crewai_analysis_result(card_id: str, crew_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orquestador principal que processa o resultado do análise CrewAI e executa as ações correspondentes.
    Implementa a lógica de decisão baseada no status_geral conforme definido no PRD.
    
    Args:
        card_id: ID do card no Pipefy
        crew_response: Resposta JSON estruturada do CrewAI
    
    Returns:
        Dict com o resultado das ações executadas
    """
    try:
        # Extrair dados da resposta CrewAI (formato real)
        status_geral = crew_response.get("status_geral")
        resumo_analise = crew_response.get("resumo_analise", "")
        pendencias = crew_response.get("pendencias", [])
        documentos_analisados = crew_response.get("documentos_analisados", [])
        proximos_passos = crew_response.get("proximos_passos", [])
        recomendacoes = crew_response.get("recomendacoes", "")
        
        # Gerar relatório detalhado formatado em Markdown baseado nos dados do CrewAI
        relatorio_detalhado = f"""# 📋 Relatório de Análise Documental

## 📊 Status Geral: {status_geral}

## 📝 Resumo da Análise
{resumo_analise}

## 📄 Documentos Analisados
"""
        
        for doc in documentos_analisados:
            nome = doc.get("nome", "N/A")
            status_doc = doc.get("status", "N/A")
            observacoes = doc.get("observacoes", "")
            relatorio_detalhado += f"- **{nome}**: {status_doc}\n"
            if observacoes:
                relatorio_detalhado += f"  - {observacoes}\n"
        
        if pendencias:
            relatorio_detalhado += "\n## ⚠️ Pendências Identificadas\n"
            for pendencia in pendencias:
                tipo = pendencia.get("tipo", "N/A")
                categoria = pendencia.get("categoria", "N/A")
                descricao = pendencia.get("descricao", "")
                acao_requerida = pendencia.get("acao_requerida", "")
                prazo_sugerido = pendencia.get("prazo_sugerido", "")
                
                relatorio_detalhado += f"### {categoria} ({tipo})\n"
                relatorio_detalhado += f"**Descrição:** {descricao}\n\n"
                relatorio_detalhado += f"**Ação Requerida:** {acao_requerida}\n\n"
                if prazo_sugerido:
                    relatorio_detalhado += f"**Prazo Sugerido:** {prazo_sugerido}\n\n"
        
        if proximos_passos:
            relatorio_detalhado += "\n## 🎯 Próximos Passos\n"
            for i, passo in enumerate(proximos_passos, 1):
                relatorio_detalhado += f"{i}. {passo}\n"
        
        if recomendacoes:
            relatorio_detalhado += f"\n## 💡 Recomendações\n{recomendacoes}\n"
        
        # Extrair ações requeridas das pendências para compatibilidade
        acoes_requeridas = []
        for pendencia in pendencias:
            acao_requerida = pendencia.get("acao_requerida", "")
            if "cartão cnpj" in acao_requerida.lower() or "cnpj" in acao_requerida.lower():
                # Tentar extrair CNPJ do resumo ou buscar en documentos analisados
                cnpj_extraido = None
                # Lógica básica para extrair CNPJ (pode ser melhorada)
                import re
                cnpj_pattern = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}'
                texto_completo = f"{resumo_analise} {relatorio_detalhado}"
                cnpj_matches = re.findall(cnpj_pattern, texto_completo)
                if cnpj_matches:
                    cnpj_extraido = cnpj_matches[0].replace('.', '').replace('/', '').replace('-', '')
                
                acoes_requeridas.append({
                    "item": "Cartão CNPJ",
                    "acao": "GERAR_DOCUMENTO_VIA_API",
                    "parametros": {"cnpj": cnpj_extraido}
                })
        
        logger.info(f"🎯 Processando resultado CrewAI para card {card_id}")
        logger.info(f"📊 Status Geral: {status_geral}")
        logger.info(f"📋 Ações Requeridas: {len(acoes_requeridas)}")
        
        # Resultado das ações executadas
        result = {
            "card_id": card_id,
            "status_geral": status_geral,
            "actions_executed": [],
            "success": True,
            "errors": []
        }
        
        # 1. Sempre atualizar o campo Informe CrewAI com o relatório detalhado
        logger.info(f"📝 Atualizando campo 'Informe CrewAI' no card {card_id}")
        informe_updated = await update_pipefy_informe_crewai_field(card_id, relatorio_detalhado)
        
        if informe_updated:
            result["actions_executed"].append("informe_updated")
            logger.info(f"✅ Campo 'Informe CrewAI' atualizado com sucesso")
        else:
            result["errors"].append("failed_to_update_informe")
            logger.error(f"❌ Falha ao atualizar campo 'Informe CrewAI'")
        
        # 2. Executar ações baseadas no status_geral
        if status_geral == "Pendencia_Bloqueante":
            logger.info(f"🚨 Processando PENDÊNCIA BLOQUEANTE para card {card_id}")
            
            # Mover card para fase "Pendências Documentais"
            moved = await move_pipefy_card_to_phase(card_id, PHASE_ID_PENDENCIAS)
            if moved:
                result["actions_executed"].append("moved_to_pendencias")
                logger.info(f"✅ Card movido para fase 'Pendências Documentais'")
            else:
                result["errors"].append("failed_to_move_to_pendencias")
                logger.error(f"❌ Falha ao mover card para 'Pendências Documentais'")
            
            # Enviar notificação WhatsApp para gestor
            whatsapp_sent = await send_whatsapp_notification(card_id, relatorio_detalhado)
            if whatsapp_sent:
                result["actions_executed"].append("whatsapp_notification_sent")
                logger.info(f"✅ Notificação WhatsApp enviada ao gestor")
            else:
                result["errors"].append("failed_to_send_whatsapp")
                logger.error(f"❌ Falha ao enviar notificação WhatsApp")
        
        elif status_geral == "Pendencia_NaoBloqueante":
            logger.info(f"⚠️ Processando PENDÊNCIA NÃO BLOQUEANTE para card {card_id}")
            
            # Executar ações automáticas para pendências não bloqueantes
            for acao in acoes_requeridas:
                item = acao.get("item", "")
                acao_tipo = acao.get("acao", "")
                parametros = acao.get("parametros", {})
                
                logger.info(f"🔧 Executando ação: {acao_tipo} para item: {item}")
                
                if acao_tipo == "GERAR_DOCUMENTO_VIA_API" and "Cartão CNPJ" in item:
                    cnpj = parametros.get("cnpj")
                    if cnpj:
                        logger.info(f"🏢 Gerando Cartão CNPJ para CNPJ: {cnpj}")
                        cartao_gerado = await gerar_e_armazenar_cartao_cnpj(card_id, cnpj)
                        if cartao_gerado:
                            result["actions_executed"].append("cartao_cnpj_generated")
                            logger.info(f"✅ Cartão CNPJ gerado e armazenado automaticamente")
                        else:
                            result["errors"].append("failed_to_generate_cartao_cnpj")
                            logger.error(f"❌ Falha ao gerar Cartão CNPJ para CNPJ: {cnpj}")
                    else:
                        logger.warning(f"⚠️ CNPJ não fornecido para geração de Cartão CNPJ")
                        logger.info(f"🔍 Tentando extrair CNPJ do texto da pendência...")
                        import re
                        cnpj_pattern = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}'
                        cnpj_matches = re.findall(cnpj_pattern, acao.get("descricao", ""))
                        if cnpj_matches:
                            cnpj_extraido = cnpj_matches[0].replace('.', '').replace('/', '').replace('-', '')
                            logger.info(f"🎯 CNPJ extraído da descrição: {cnpj_extraido}")
                            cartao_gerado = await gerar_e_armazenar_cartao_cnpj(card_id, cnpj_extraido)
                            if cartao_gerado:
                                result["actions_executed"].append("cartao_cnpj_generated")
                                logger.info(f"✅ Cartão CNPJ gerado com CNPJ extraído")
                            else:
                                result["errors"].append("failed_to_generate_cartao_cnpj")
                                logger.error(f"❌ Falha ao gerar Cartão CNPJ com CNPJ extraído")
                        else:
                            logger.warning(f"❌ Não foi possível extrair CNPJ para geração do cartão")
                
                elif acao_tipo == "NOTIFICAR_EQUIPE_CADASTRO":
                    # Por enquanto, o movimento do card serve como notificação
                    logger.info(f"📢 Notificação para equipe de cadastro: {item}")
                    result["actions_executed"].append("team_notification_logged")
                
                elif acao_tipo == "SOLICITAR_AO_GESTOR":
                    # Ação que será tratada pelo movimento para fase de pendências
                    logger.info(f"👤 Solicitação ao gestor: {item}")
                    result["actions_executed"].append("manager_request_logged")
            
            # Mover card para fase "Emitir documentos"
            moved = await move_pipefy_card_to_phase(card_id, PHASE_ID_EMITIR_DOCS)
            if moved:
                result["actions_executed"].append("moved_to_emitir_docs")
                logger.info(f"✅ Card movido para fase 'Emitir documentos'")
            else:
                result["errors"].append("failed_to_move_to_emitir_docs")
                logger.error(f"❌ Falha ao mover card para 'Emitir documentos'")
        
        elif status_geral == "Aprovado":
            logger.info(f"✅ Processando APROVAÇÃO para card {card_id}")
            
            # Atualizar campo com mensagem de aprovação
            aprovacao_message = "✅ **DOCUMENTAÇÃO APROVADA**\n\nTodos os documentos estão em conformidade com o checklist. O caso seguirá para a próxima etapa de análise de risco."
            informe_aprovacao = await update_pipefy_informe_crewai_field(card_id, aprovacao_message)
            
            if informe_aprovacao:
                result["actions_executed"].append("approval_message_updated")
                logger.info(f"✅ Mensagem de aprovação atualizada")
            
            # Mover card para fase "Aprovado"
            moved = await move_pipefy_card_to_phase(card_id, PHASE_ID_APROVADO)
            if moved:
                result["actions_executed"].append("moved_to_aprovado")
                logger.info(f"✅ Card movido para fase 'Aprovado'")
            else:
                result["errors"].append("failed_to_move_to_aprovado")
                logger.error(f"❌ Falha ao mover card para 'Aprovado'")
        
        else:
            logger.error(f"❌ Status geral desconhecido: '{status_geral}' para card {card_id}")
            result["success"] = False
            result["errors"].append(f"unknown_status: {status_geral}")
        
        # Determinar sucesso geral
        if result["errors"]:
            result["success"] = False
            logger.warning(f"⚠️ Processamento concluído com erros para card {card_id}: {result['errors']}")
        else:
            logger.info(f"✅ Processamento concluído com sucesso para card {card_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro crítico no orquestrador para card {card_id}: {e}")
        return {
            "card_id": card_id,
            "success": False,
            "error": str(e),
            "actions_executed": [],
            "errors": ["critical_orchestrator_error"]
        }

# --- Endpoint Principal ---
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
        
        logger.info(f"📥 Webhook Pipefy recebido. Payload length: {len(raw_body_str)}")
        
        # 🔐 VALIDAR WEBHOOK SECRET
        if not validate_pipefy_webhook_signature(raw_body, x_pipefy_signature, PIPEFY_WEBHOOK_SECRET):
            logger.error("❌ Assinatura do webhook Pipefy inválida")
            raise HTTPException(status_code=401, detail="Assinatura do webhook inválida")
        
        # Parsear JSON manualmente
        try:
            payload_data = json.loads(raw_body_str)
        except json.JSONDecodeError as e:
            logger.error(f"ERRO: JSON inválido recebido: {e}")
            raise HTTPException(status_code=400, detail="JSON inválido")
        
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

        # 🎯 FILTRAR POR FASE 338000020 (Triagem Documentos AI)
        current_phase = card.get('current_phase')
        if not current_phase or not isinstance(current_phase, dict):
            # Intentar enriquecer el payload consultando la API de Pipefy
            logger.warning(f"⚠️ Card {card_id_str} sem informação de fase atual. Tentando enriquecer via API Pipefy...")
            try:
                from src.integrations.pipefy_client import pipefy_client
                card_info = await pipefy_client.get_card_info(card_id_str)
                if card_info and isinstance(card_info, dict) and card_info.get('current_phase'):
                    card['current_phase'] = card_info['current_phase']
                    current_phase = card['current_phase']
                    logger.info(f"✅ Fase atual obtida via API: {current_phase}")
                else:
                    logger.warning(f"⚠️ Card {card_id_str} ainda sem informação de fase após consulta à API. Ignorando webhook.")
                    return {
                        "status": "ignored",
                        "reason": "no_current_phase_info",
                        "card_id": card_id_str,
                        "message": "Webhook ignorado - sem informação de fase atual (mesmo após consulta à API)"
                    }
            except Exception as e:
                logger.error(f"❌ Erro ao consultar API Pipefy para card {card_id_str}: {e}")
                return {
                    "status": "ignored",
                    "reason": "no_current_phase_info_api_error",
                    "card_id": card_id_str,
                    "message": f"Webhook ignorado - erro ao consultar API Pipefy: {e}"
                }
        
        current_phase_id = str(current_phase.get('id', ''))
        current_phase_name = current_phase.get('name', 'Unknown')
        
        logger.info(f"📍 Fase atual do card: {current_phase_name} (ID: {current_phase_id})")
        
        # Verificar se está na fase de triagem (338000020)
        if current_phase_id != PHASE_ID_TRIAGEM:
            logger.info(f"⏭️ Card {card_id_str} não está na fase de triagem (ID: {current_phase_id}). Webhook ignorado.")
            return {
                "status": "ignored",
                "reason": "not_triagem_phase",
                "card_id": card_id_str,
                "current_phase_id": current_phase_id,
                "current_phase_name": current_phase_name,
                "expected_phase_id": PHASE_ID_TRIAGEM,
                "message": f"Webhook ignorado - card não está na fase de triagem. Fase atual: {current_phase_name}"
            }
        
        logger.info(f"✅ Card {card_id_str} está na fase de triagem. Iniciando processamento...")

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

# 🔔 WEBHOOK SUPABASE - Endpoint para recibir notificaciones de nuevos informes
@app.post('/webhook/supabase')
async def supabase_webhook(request: Request):
    """
    Webhook que recibe notificaciones de Supabase cuando se inserta un nuevo informe.
    VERSIÓN COMPLETA: Ejecuta toda la lógica de negocio incluyendo movimiento de cards y generación de cartão CNPJ.
    """
    try:
        data = await request.json()
        logger.info(f"📨 Webhook Supabase recebido: {json.dumps(data, indent=2)}")
        
        # Verificar que es un INSERT en la tabla informe_cadastro
        if data.get('type') != 'INSERT' or data.get('table') != 'informe_cadastro':
            logger.info(f"⏭️ Webhook ignorado - Tipo: {data.get('type')}, Tabla: {data.get('table')}")
            return {"status": "ignored", "reason": "not_informe_insert"}
        
        record = data.get('record', {})
        case_id = record.get('case_id')
        informe_json_str = record.get('informe')
        status = record.get('status')
        
        if not case_id or not informe_json_str:
            logger.warning(f"⚠️ Webhook com dados incompletos - case_id: {case_id}, informe presente: {bool(informe_json_str)}")
            raise HTTPException(status_code=400, detail="case_id ou informe ausente")
        
        logger.info(f"🎯 Processando informe completo para case_id: {case_id}")
        logger.info(f"   - Status: {status}")
        logger.info(f"   - Tamanho do informe: {len(informe_json_str)} caracteres")
        
        # Parsear el JSON del informe para obtener la estructura completa
        try:
            informe_data = json.loads(informe_json_str)
            logger.info(f"📊 Informe parseado - Status geral: {informe_data.get('status_geral')}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao parsear JSON do informe: {e}")
            raise HTTPException(status_code=400, detail="JSON do informe inválido")
        
        # Ejecutar el orquestrador principal de forma asíncrona
        async def process_complete_workflow():
            try:
                logger.info(f"🚀 Iniciando fluxo completo para case_id: {case_id}")
                
                # 1. Executar orquestrador principal com todos os dados do CrewAI
                orchestrator_result = await handle_crewai_analysis_result(case_id, informe_data)
                
                if orchestrator_result.get("success"):
                    logger.info(f"✅ Fluxo completo executado com sucesso para case_id: {case_id}")
                    logger.info(f"🎯 Ações executadas: {orchestrator_result.get('actions_executed', [])}")
                else:
                    logger.error(f"❌ Fluxo completo falhou para case_id: {case_id}")
                    logger.error(f"❌ Erros: {orchestrator_result.get('errors', [])}")
                    
            except Exception as e:
                logger.error(f"❌ Erro no fluxo completo para case_id {case_id}: {e}")
        
        # Executar em background
        asyncio.create_task(process_complete_workflow())
        
        return {
            "status": "success", 
            "message": "Webhook processado - fluxo completo iniciado",
            "case_id": case_id,
            "strategy": "complete_workflow_orchestrator",
            "informe_status": informe_data.get('status_geral', 'unknown')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no webhook Supabase: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Agregar endpoint alternativo para el webhook
@app.post('/webhook/supabase/informe-created')
async def supabase_informe_created_webhook(request: Request):
    """
    Endpoint alternativo para el webhook de Supabase - redirige al principal.
    """
    logger.info("🔄 Webhook alternativo recebido - redirecionando para principal")
    return await supabase_webhook(request)

@app.post("/test/check-and-move-card")
async def test_check_and_move_card(card_id: str):
    """
    Endpoint de prueba para verificar la fase actual del card y moverlo si es necesario.
    Útil para testing del nuevo sistema de manejo de fases.
    """
    try:
        logger.info(f"🧪 Test: Verificando fase y movimiento para card {card_id}")
        
        # Verificar fase actual y mover si es necesario
        phase_info = await get_card_current_phase_and_move_if_needed(card_id)
        
        if "error" in phase_info:
            raise HTTPException(
                status_code=500, 
                detail=f"Error al verificar fase del card: {phase_info}"
            )
        
        return {
            "status": "success",
            "message": f"Verificación de fase completada para card {card_id}",
            "phase_info": phase_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ERRO en test endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/test/update-pipefy-with-phase-handling")
async def test_update_pipefy_with_phase_handling(
    case_id: str,
    informe_content: str
):
    """
    Endpoint de prueba para actualizar el campo Informe CrewAI con manejo automático de fases.
    Incluye verificación de fase, movimiento si es necesario, y actualización del campo.
    """
    try:
        logger.info(f"🧪 Test: Actualización completa con manejo de fases para case_id {case_id}")
        
        success = await update_pipefy_informe_crewai_field(case_id, informe_content)
        
        if success:
            return {
                "status": "success",
                "message": f"Campo actualizado exitosamente con manejo de fases para case_id {case_id}",
                "case_id": case_id,
                "feature": "automatic_phase_handling"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Error al actualizar campo con manejo de fases para case_id {case_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ERRO en test endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/test/update-form-field")
async def test_update_form_field(request: Request):
    """
    Endpoint de prueba para verificar la actualización de campos en formulario.
    CORREGIDO: Usa la sintaxis correcta de updateCardField de Pipefy.
    """
    try:
        data = await request.json()
        card_id = data.get('card_id')
        test_content = data.get('test_content', f'🧪 Prueba de campo en formulario - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        if not card_id:
            raise HTTPException(status_code=400, detail="card_id es requerido")
        
        logger.info(f"🧪 Prueba de actualización de campo en formulario para card: {card_id}")
        
        # Ejecutar actualización usando la función corregida
        success = await update_pipefy_informe_crewai_field(card_id, test_content)
        
        if success:
            return {
                "success": True,
                "card_id": card_id,
                "test_content": test_content,
                "strategy": "form_field_direct_corrected",
                "message": "Campo actualizado exitosamente con sintaxis corregida"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="Error al actualizar campo con sintaxis corregida"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en prueba de campo en formulario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/test/robust-field-handling")
async def test_robust_field_handling(request: Request):
    """
    Endpoint de prueba para la funcionalidad robusta de manejo de campos Pipefy.
    
    FUNCIONALIDAD:
    - Detecta si el campo 'Informe CrewAI' existe (tiene valor)
    - Si no existe, lo crea automáticamente en la fase actual
    - Inicializa con placeholder para que aparezca en la API
    - Actualiza con el contenido real del informe
    
    SOLUCIONA: El comportamiento específico de Pipefy donde los campos
    solo aparecen en la API cuando tienen algún valor asignado.
    """
    try:
        data = await request.json()
        card_id = data.get('card_id')
        test_content = data.get('test_content', f'🧪 Prueba robusta de campo Pipefy - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        if not card_id:
            raise HTTPException(status_code=400, detail="card_id es requerido")
        
        logger.info(f"🧪 PRUEBA ROBUSTA: Manejo de campos Pipefy para card: {card_id}")
        logger.info(f"🎯 OBJETIVO: Solucionar comportamiento donde campos sin valor no aparecen en API")
        
        # Ejecutar actualización robusta
        success = await update_pipefy_informe_crewai_field(card_id, test_content)
        
        if success:
            return {
                "success": True,
                "card_id": card_id,
                "test_content": test_content,
                "strategy": "robust_field_handling",
                "features": [
                    "Detección automática de campos existentes",
                    "Creación automática si no existe",
                    "Inicialización con placeholder",
                    "Actualización con contenido real",
                    "Manejo del comportamiento específico de Pipefy"
                ],
                "message": "Campo manejado exitosamente con estrategia robusta"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="Error en manejo robusto de campo"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en prueba robusta: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/test/field-detection/{card_id}")
async def test_field_detection(card_id: str):
    """
    Endpoint para probar solo la detección de campos sin actualizar nada.
    Útil para debugging y entender el comportamiento de Pipefy.
    """
    try:
        logger.info(f"🔍 PRUEBA DE DETECCIÓN: Analizando campos del card {card_id}")
        
        # Solo detectar, no actualizar
        field_result = await get_pipefy_field_id_for_informe_crewai(card_id)
        
        if isinstance(field_result, str):
            return {
                "field_found": True,
                "field_id": field_result,
                "card_id": card_id,
                "message": "Campo 'Informe CrewAI' encontrado exitosamente",
                "behavior": "Campo tiene valor y aparece en la API"
            }
        elif isinstance(field_result, dict) and field_result.get("field_not_found"):
            return {
                "field_found": False,
                "phase_id": field_result.get("phase_id"),
                "phase_name": field_result.get("phase_name"),
                "card_id": card_id,
                "message": "Campo 'Informe CrewAI' no encontrado",
                "behavior": "Campo no tiene valor y no aparece en la API",
                "solution": "Necesita creación automática o asignación de valor inicial"
            }
        else:
            return {
                "field_found": False,
                "error": "Error inesperado en detección",
                "card_id": card_id,
                "result": field_result
            }
        
    except Exception as e:
        logger.error(f"❌ Error en detección de campo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/")
async def root():
    return {
        "service": "Document Ingestion Service - HTTP Direct",
        "description": "Servicio modular para ingestión de documentos con comunicación HTTP directa",
        "architecture": "modular",
        "communication": "http_direct",
        "crewai_service": CREWAI_SERVICE_URL
    }

@app.get("/health")
async def health_check():
    """Endpoint de verificação de saúde con estado del servicio CrewAI."""
    
    # Verificar estado del servicio CrewAI
    crewai_status = "unknown"
    crewai_response_time = None
    
    try:
        start_time = datetime.now()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CREWAI_SERVICE_URL}/health")
            end_time = datetime.now()
            crewai_response_time = (end_time - start_time).total_seconds()
            
            if response.status_code == 200:
                crewai_status = "healthy"
            else:
                crewai_status = f"unhealthy_status_{response.status_code}"
    except httpx.TimeoutException:
        crewai_status = "timeout"
    except Exception as e:
        crewai_status = f"error_{str(e)[:50]}"
    
    return {
        "status": "healthy",
        "service": "document_ingestion_service",
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_SERVICE_KEY),
        "pipefy_configured": bool(PIPEFY_TOKEN),
        "storage_bucket": SUPABASE_STORAGE_BUCKET_NAME,
        "crewai_service": CREWAI_SERVICE_URL,
        "crewai_status": crewai_status,
        "crewai_response_time_seconds": crewai_response_time,
        "architecture": "modular_http_direct",
        "communication": "http_direct",
        "cold_start_handling": "enabled"
    }

# 🧪 Función para detectar la fase actual del card y moverlo si es necesario
# NOTA: Mantenida para compatibilidad, pero no necesaria con la nueva estrategia
async def get_card_current_phase_and_move_if_needed(card_id: str) -> Dict[str, Any]:
    """
    Detecta la fase actual del card y lo mueve a la fase de destino si es necesario.
    OBSOLETA: No necesaria con campos en formulario, pero mantenida para compatibilidad.
    """
    # Función mantenida para compatibilidad pero no usada en la nueva estrategia
    return {"status": "not_needed", "message": "Campo en formulario - no requiere movimiento de fase"}

# 🧪 ENDPOINT DE PRUEBA - Para probar el orquestador directamente
@app.post("/test/orchestrator")
async def test_orchestrator(request: Request):
    """
    Endpoint de prueba para probar el orquestador handle_crewai_analysis_result directamente.
    Permite simular diferentes respuestas JSON del CrewAI para validar el flujo completo.
    """
    try:
        data = await request.json()
        card_id = data.get('card_id')
        
        if not card_id:
            raise HTTPException(status_code=400, detail="card_id es requerido")
        
        # Respuesta de prueba por defecto o personalizada
        test_crew_response = data.get('crew_response', {
            "status_geral": "Pendencia_NaoBloqueante",
            "relatorio_detalhado": "## Relatório de Análise Documental\n\n**Status:** Pendência Não Bloqueante\n\n### Documentos Analisados:\n- ✅ Contrato Social: Presente e válido\n- ⚠️ Cartão CNPJ: Ausente ou desatualizado\n\n### Ações Requeridas:\n- Gerar novo Cartão CNPJ via API\n\n### Observações:\n- Documentação principal está em conformidade\n- Pendência pode ser resolvida automaticamente",
            "acoes_requeridas": [
                {
                    "item": "Cartão CNPJ",
                    "acao": "GERAR_DOCUMENTO_VIA_API",
                    "parametros": {
                        "cnpj": "12345678000195",
                        "detalhes": "Cartão CNPJ ausente ou com mais de 90 dias"
                    }
                }
            ]
        })
        
        logger.info(f"🧪 TESTE ORQUESTRADOR: Executando para card {card_id}")
        logger.info(f"📋 Resposta simulada: {test_crew_response.get('status_geral')}")
        
        # Executar orquestrador
        orchestration_result = await handle_crewai_analysis_result(card_id, test_crew_response)
        
        return {
            "success": True,
            "card_id": card_id,
            "test_crew_response": test_crew_response,
            "orchestration_result": orchestration_result,
            "message": "Teste do orquestrador executado com sucesso",
            "endpoint": "test_orchestrator"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no teste do orquestrador: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/test/robust-field-handling")
async def test_robust_field_handling(request: Request):
    """
    Endpoint de prueba para la funcionalidad robusta de manejo de campos Pipefy.
    
    FUNCIONALIDAD:
    - Detecta si el campo 'Informe CrewAI' existe (tiene valor)
    - Si no existe, lo crea automáticamente en la fase actual
    - Inicializa con placeholder para que aparezca en la API
    - Actualiza con el contenido real del informe
    
    SOLUCIONA: El comportamiento específico de Pipefy donde los campos
    solo aparecen en la API cuando tienen algún valor asignado.
    """
    try:
        data = await request.json()
        card_id = data.get('card_id')
        test_content = data.get('test_content', f'🧪 Prueba robusta de campo Pipefy - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        if not card_id:
            raise HTTPException(status_code=400, detail="card_id es requerido")
        
        logger.info(f"🧪 PRUEBA ROBUSTA: Manejo de campos Pipefy para card: {card_id}")
        logger.info(f"🎯 OBJETIVO: Solucionar comportamiento donde campos sin valor no aparecen en API")
        
        # Ejecutar actualización robusta
        success = await update_pipefy_informe_crewai_field(card_id, test_content)
        
        if success:
            return {
                "success": True,
                "card_id": card_id,
                "test_content": test_content,
                "strategy": "robust_field_handling",
                "features": [
                    "Detección automática de campos existentes",
                    "Creación automática si no existe",
                    "Inicialización con placeholder",
                    "Actualización con contenido real",
                    "Manejo del comportamiento específico de Pipefy"
                ],
                "message": "Campo manejado exitosamente con estrategia robusta"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="Error en manejo robusto de campo"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en prueba robusta: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# 🧪 ENDPOINT DE PRUEBA - Escenarios predefinidos del orquestador
@app.post("/test/orchestrator-scenarios")
async def test_orchestrator_scenarios(request: Request):
    """
    Endpoint de prueba con escenarios predefinidos para el orquestador.
    Permite probar los 3 flujos principales: Aprovado, Pendencia_Bloqueante, Pendencia_NaoBloqueante.
    """
    try:
        data = await request.json()
        card_id = data.get('card_id')
        scenario = data.get('scenario', 'pendencia_nao_bloqueante')
        
        if not card_id:
            raise HTTPException(status_code=400, detail="card_id es requerido")
        
        # Escenarios predefinidos
        scenarios = {
            "aprovado": {
                "status_geral": "Aprovado",
                "relatorio_detalhado": "## ✅ DOCUMENTAÇÃO APROVADA\n\n### Análise Completa:\n- ✅ Contrato Social: Válido e atualizado\n- ✅ Cartão CNPJ: Presente e dentro da validade\n- ✅ Documentos dos sócios: Completos e legíveis\n- ✅ Procuração: Assinada e reconhecida\n\n### Conclusão:\nToda a documentação está em conformidade com o checklist. O caso pode prosseguir para a próxima etapa de análise de risco.",
                "acoes_requeridas": []
            },
            "pendencia_bloqueante": {
                "status_geral": "Pendencia_Bloqueante",
                "relatorio_detalhado": "## 🚨 PENDÊNCIA CRÍTICA DETECTADA\n\n### Problemas Identificados:\n- ❌ Contrato Social: SEM NÚMERO DE REGISTRO na Junta Comercial\n- ❌ RG do sócio: Documento ilegível\n- ⚠️ Procuração: Falta reconhecimento de firma\n\n### Ação Necessária:\n**URGENTE:** Gestor comercial deve entrar em contato com o cliente para providenciar:\n1. Contrato Social com registro válido\n2. RG legível do sócio principal\n3. Procuração com firma reconhecida\n\n### Impacto:\nEsses documentos são obrigatórios e impedem o prosseguimento do processo.",
                "acoes_requeridas": [
                    {
                        "item": "Contrato Social",
                        "acao": "SOLICITAR_AO_GESTOR",
                        "parametros": {
                            "detalhes": "Documento sem número de registro na Junta Comercial"
                        }
                    },
                    {
                        "item": "RG do sócio",
                        "acao": "SOLICITAR_AO_GESTOR",
                        "parametros": {
                            "detalhes": "Documento ilegível, necessário nova cópia"
                        }
                    }
                ]
            },
            "pendencia_nao_bloqueante": {
                "status_geral": "Pendencia_NaoBloqueante",
                "relatorio_detalhado": "## ⚠️ PENDÊNCIAS NÃO CRÍTICAS\n\n### Documentos Principais:\n- ✅ Contrato Social: Válido e registrado\n- ✅ Documentos dos sócios: Completos\n- ✅ Procuração: Válida\n\n### Pendências Identificadas:\n- ⚠️ Cartão CNPJ: Ausente ou desatualizado (>90 dias)\n- ⚠️ Certidão Simplificada: Necessária devido à idade do contrato\n\n### Ações Automáticas:\n- 🤖 Cartão CNPJ será gerado automaticamente via API\n- 📋 Equipe de cadastro será notificada para emitir Certidão Simplificada\n\n### Status:\nDocumentação principal aprovada. Pendências serão resolvidas internamente.",
                "acoes_requeridas": [
                    {
                        "item": "Cartão CNPJ",
                        "acao": "GERAR_DOCUMENTO_VIA_API",
                        "parametros": {
                            "cnpj": "12345678000195",
                            "detalhes": "Cartão CNPJ ausente ou com mais de 90 dias"
                        }
                    },
                    {
                        "item": "Certidão Simplificada",
                        "acao": "NOTIFICAR_EQUIPE_CADASTRO",
                        "parametros": {
                            "detalhes": "Contrato Social com mais de 3 anos, necessária certidão atualizada"
                        }
                    }
                ]
            }
        }
        
        if scenario not in scenarios:
            raise HTTPException(
                status_code=400, 
                detail=f"Scenario inválido. Opções: {list(scenarios.keys())}"
            )
        
        test_crew_response = scenarios[scenario]
        
        logger.info(f"🧪 TESTE CENÁRIO: {scenario.upper()} para card {card_id}")
        logger.info(f"📋 Status: {test_crew_response.get('status_geral')}")
        
        # Executar orquestrador
        orchestration_result = await handle_crewai_analysis_result(card_id, test_crew_response)
        
        return {
            "success": True,
            "card_id": card_id,
            "scenario": scenario,
            "test_crew_response": test_crew_response,
            "orchestration_result": orchestration_result,
            "message": f"Cenário '{scenario}' executado com sucesso",
            "available_scenarios": list(scenarios.keys()),
            "endpoint": "test_orchestrator_scenarios"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no teste de cenários: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/test/robust-field-handling")
async def test_robust_field_handling(request: Request):
    """
    Endpoint de prueba para la funcionalidad robusta de manejo de campos Pipefy.
    
    FUNCIONALIDAD:
    - Detecta si el campo 'Informe CrewAI' existe (tiene valor)
    - Si no existe, lo crea automáticamente en la fase actual
    - Inicializa con placeholder para que aparezca en la API
    - Actualiza con el contenido real del informe
    
    SOLUCIONA: El comportamiento específico de Pipefy donde los campos
    solo aparecen en la API cuando tienen algún valor asignado.
    """
    try:
        data = await request.json()
        card_id = data.get('card_id')
        test_content = data.get('test_content', f'🧪 Prueba robusta de campo Pipefy - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        if not card_id:
            raise HTTPException(status_code=400, detail="card_id es requerido")
        
        logger.info(f"🧪 PRUEBA ROBUSTA: Manejo de campos Pipefy para card: {card_id}")
        logger.info(f"🎯 OBJETIVO: Solucionar comportamiento donde campos sin valor no aparecen en API")
        
        # Ejecutar actualización robusta
        success = await update_pipefy_informe_crewai_field(card_id, test_content)
        
        if success:
            return {
                "success": True,
                "card_id": card_id,
                "test_content": test_content,
                "strategy": "robust_field_handling",
                "features": [
                    "Detección automática de campos existentes",
                    "Creación automática si no existe",
                    "Inicialización con placeholder",
                    "Actualización con contenido real",
                    "Manejo del comportamiento específico de Pipefy"
                ],
                "message": "Campo manejado exitosamente con estrategia robusta"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="Error en manejo robusto de campo"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en prueba robusta: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)