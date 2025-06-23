"""
Configuración de pytest y fixtures comunes para las pruebas.
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List
from src.integrations.cnpj_client import CNPJData
from src.services.cnpj_service import CNPJService

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Fixtures para configuración de pruebas
@pytest.fixture(scope="session")
def event_loop():
    """Crea un event loop para toda la sesión de pruebas."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_env_vars():
    """Mock de variables de entorno para pruebas."""
    env_vars = {
        'PIPEFY_API_TOKEN': 'test_pipefy_token',
        'TWILIO_ACCOUNT_SID': 'test_twilio_sid',
        'TWILIO_AUTH_TOKEN': 'test_twilio_token',
        'TWILIO_WHATSAPP_NUMBER': '+1234567890',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_ANON_KEY': 'test_supabase_key',
        'CNPJA_API_KEY': 'test_cnpja_key',
        'ANTHROPIC_API_KEY': 'test_anthropic_key',
        'PERPLEXITY_API_KEY': 'test_perplexity_key'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture
def mock_supabase_client():
    """Mock del cliente Supabase."""
    mock_client = Mock()
    mock_client.storage = Mock()
    mock_client.storage.from_ = Mock()
    mock_client.storage.from_.return_value.upload = AsyncMock(return_value={"path": "cards/test.pdf"})
    mock_client.storage.from_.return_value.list = AsyncMock(return_value=[{"name": "test.pdf"}])
    mock_client.storage.from_.return_value.get_public_url = Mock(return_value="https://test.com/cards/test.pdf")
    return mock_client

@pytest.fixture
def mock_cnpj_client():
    """Mock del cliente CNPJ."""
    mock_client = Mock()
    mock_client.get_cnpj_data = AsyncMock(return_value=CNPJData(
        cnpj="11.222.333/0001-81",
        razao_social="EMPRESA TESTE LTDA",
        nome_fantasia="Empresa Teste",
        situacao_cadastral="ATIVA",
        uf="SP",
        municipio="SAO PAULO",
        endereco_completo="RUA DAS FLORES, 123",
        telefone="(11) 1234-5678",
        api_source="test",
        consulted_at=datetime.now()
    ))
    mock_client.generate_cnpj_card = AsyncMock(return_value={
        "cnpj": "11.222.333/0001-81",
        "razao_social": "EMPRESA TESTE LTDA",
        "situacao_cadastral": "ATIVA",
        "generated_at": datetime.now().isoformat()
    })
    return mock_client

@pytest.fixture
def cnpj_service(mock_supabase_client, mock_cnpj_client, tmp_path):
    """Crea una instancia del servicio CNPJ para pruebas."""
    service = CNPJService(mock_supabase_client)
    service.cnpj_client = mock_cnpj_client
    service.cache_dir = tmp_path / "cache"
    service.cards_dir = tmp_path / "cards"
    return service

@pytest.fixture
def valid_cnpj():
    """CNPJ válido para pruebas."""
    return "11.222.333/0001-81"

@pytest.fixture
def sample_cnpj_data():
    """Datos de muestra de CNPJ."""
    return CNPJData(
        cnpj="11.222.333/0001-81",
        razao_social="EMPRESA TESTE LTDA",
        nome_fantasia="Empresa Teste",
        situacao_cadastral="ATIVA",
        uf="SP",
        municipio="SAO PAULO",
        endereco_completo="RUA DAS FLORES, 123, CENTRO, SAO PAULO - SP",
        telefone="(11) 3333-4444",
        api_source="Mock",
        consulted_at=datetime.now()
    )

@pytest.fixture
def sample_pipefy_card():
    """Dados de exemplo para card do Pipefy."""
    return {
        "id": "123456789",
        "title": "Teste Card",
        "current_phase": {
            "id": "phase_1",
            "name": "Análise Inicial"
        },
        "fields": [
            {
                "field": {
                    "id": "field_1",
                    "label": "Nome da Empresa"
                },
                "value": "Empresa Teste LTDA"
            },
            {
                "field": {
                    "id": "field_2", 
                    "label": "CNPJ"
                },
                "value": "11.222.333/0001-81"
            }
        ]
    }

@pytest.fixture
def sample_classification_result():
    """Resultado de exemplo para classificação de documentos."""
    return {
        "classification": "APROVADO",
        "confidence": 0.95,
        "missing_documents": [],
        "blocking_issues": [],
        "recommendations": [
            "Todos os documentos estão em conformidade",
            "Processo pode prosseguir para próxima fase"
        ],
        "document_analysis": {
            "total_documents": 5,
            "approved_documents": 5,
            "pending_documents": 0,
            "rejected_documents": 0
        }
    }

@pytest.fixture
def sample_notification_data():
    """Dados de exemplo para notificações."""
    return {
        "recipient_name": "João Silva",
        "recipient_phone": "+5511999999999",
        "company_name": "Empresa Teste LTDA",
        "case_id": "CASE_123",
        "cnpj": "11.222.333/0001-81",
        "blocking_issues": [
            "Documento de identidade em baixa qualidade",
            "Comprovante de endereço desatualizado"
        ]
    }

@pytest.fixture
def mock_database_service():
    """Mock do serviço de banco de dados."""
    mock_service = Mock()
    mock_service.create_case_tracking = AsyncMock(return_value={"id": "test_id"})
    mock_service.update_case_tracking = AsyncMock(return_value={"id": "test_id"})
    mock_service.get_case_tracking = AsyncMock(return_value=None)
    mock_service.add_processing_log = AsyncMock(return_value={"id": "log_id"})
    mock_service.upload_file_to_storage = AsyncMock(return_value={"url": "test_url"})
    mock_service.create_document_record = AsyncMock(return_value={"id": "doc_id"})
    return mock_service

@pytest.fixture
def mock_pipefy_client():
    """Mock do cliente Pipefy."""
    mock_client = Mock()
    mock_client.move_card_to_phase = AsyncMock(return_value={"success": True})
    mock_client.update_card_field = AsyncMock(return_value={"success": True})
    mock_client.get_card_info = AsyncMock(return_value={"id": "123"})
    mock_client.move_card_by_classification = AsyncMock(return_value={"success": True})
    return mock_client

@pytest.fixture
def mock_twilio_client():
    """Mock do cliente Twilio."""
    mock_client = Mock()
    mock_client.send_whatsapp_message = AsyncMock(return_value={
        "success": True,
        "message_sid": "test_sid"
    })
    mock_client.send_blocking_issues_notification = AsyncMock(return_value={
        "success": True,
        "message_sid": "test_sid"
    })
    return mock_client

@pytest.fixture
def mock_error_handler():
    """Mock do error handler."""
    mock_handler = Mock()
    mock_handler.log_error = Mock()
    mock_handler.get_error_stats = Mock(return_value={
        "total_errors": 0,
        "apis": {},
        "error_types": {}
    })
    mock_handler.should_retry = Mock(return_value=False)
    mock_handler._is_circuit_breaker_open = Mock(return_value=False)
    return mock_handler

# Fixtures para dados de teste específicos
@pytest.fixture
def valid_cnpj_numbers():
    """Lista de CNPJs válidos para testes."""
    return [
        "11.222.333/0001-81",
        "11222333000181",
        "14.616.875/0001-27",
        "14616875000127"
    ]

@pytest.fixture
def invalid_cnpj_numbers():
    """Lista de CNPJs inválidos para testes."""
    return [
        "00.000.000/0000-00",
        "11.111.111/1111-11",
        "123.456.789/0001-00",
        "invalid_cnpj",
        "",
        None
    ]

@pytest.fixture
def sample_pdf_content():
    """Conteúdo de PDF de exemplo para testes."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF"

@pytest.fixture
def sample_error_scenarios():
    """Escenarios de error para pruebas."""
    return {
        "timeout_error": {
            "exception": asyncio.TimeoutError("Request timeout"),
            "expected_type": "timeout",
            "expected_severity": "medium"
        },
        "auth_error": {
            "exception": Exception("401 Unauthorized"),
            "expected_type": "authentication_error",
            "expected_severity": "high"
        },
        "server_error": {
            "exception": Exception("500 Internal Server Error"),
            "expected_type": "server_error", 
            "expected_severity": "high"
        }
    } 