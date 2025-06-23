"""
Tests para el servicio CNPJ.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile

from src.services.cnpj_service import CNPJService, CNPJServiceError
from src.integrations.cnpj_client import CNPJData, CNPJAPIError

# Datos de prueba
MOCK_CNPJ = "11.222.333/0001-81"
MOCK_CNPJ_CLEAN = "12345678000190"

@pytest.fixture
def mock_supabase_client():
    """Mock del cliente Supabase."""
    mock_client = MagicMock()
    mock_client.storage = MagicMock()
    mock_client.storage.from_ = MagicMock()
    mock_client.storage.from_.return_value.upload = AsyncMock(return_value={"path": "cards/test.pdf"})
    mock_client.storage.from_.return_value.list = AsyncMock(return_value=[{"name": "test.pdf"}])
    mock_client.storage.from_.return_value.get_public_url = MagicMock(return_value="https://test.com/cards/test.pdf")
    return mock_client

@pytest.fixture
def mock_cnpj_client():
    """Mock del cliente CNPJ."""
    mock_client = MagicMock()
    mock_client.get_cnpj_data = AsyncMock(return_value=CNPJData(
        cnpj=MOCK_CNPJ,
        razao_social="EMPRESA TESTE LTDA",
        nome_fantasia="Empresa Teste",
        situacao_cadastral="ATIVA",
        uf="SP",
        municipio="SAO PAULO",
        endereco_completo="RUA DAS FLORES, 123",
        telefone="(11) 1234-5678",
        api_source="Mock"
    ))
    return mock_client

@pytest.fixture
def cnpj_service(mock_supabase_client, mock_cnpj_client):
    """Fixture del servicio CNPJ."""
    return CNPJService(
        supabase_client=mock_supabase_client,
        cnpj_client=mock_cnpj_client
    )

@pytest.mark.asyncio
async def test_get_cached_data_hit(cnpj_service):
    """Test de obtención de datos cacheados (hit)."""
    # Configurar mock
    mock_data = {
        "cnpj": MOCK_CNPJ,
        "razao_social": "Empresa Test",
        "cached_at": datetime.now().isoformat()
    }
    mock_select = AsyncMock(return_value=MagicMock(data=[mock_data]))
    cnpj_service.client.table.return_value.select.return_value.eq.return_value.execute = mock_select
    
    # Ejecutar
    result = await cnpj_service._get_cached_data(MOCK_CNPJ)
    
    # Verificar
    assert result == mock_data
    cnpj_service.client.table.return_value.select.return_value.eq.assert_called_once_with("cnpj", MOCK_CNPJ)

@pytest.mark.asyncio
async def test_get_cached_data_expired(cnpj_service):
    """Test de obtención de datos cacheados (expirado)."""
    # Configurar mock
    expired_data = {
        "cnpj": MOCK_CNPJ,
        "razao_social": "Empresa Test",
        "cached_at": (datetime.now() - timedelta(hours=25)).isoformat()
    }
    
    # Mock para select
    mock_select = AsyncMock(return_value=MagicMock(data=[expired_data]))
    cnpj_service.client.table.return_value.select.return_value.eq.return_value.execute = mock_select
    
    # Mock para delete
    mock_delete = AsyncMock()
    cnpj_service.client.table.return_value.delete.return_value.eq.return_value.execute = mock_delete
    
    # Ejecutar
    result = await cnpj_service._get_cached_data(MOCK_CNPJ)
    
    # Verificar
    assert result is None
    cnpj_service.client.table.return_value.select.return_value.eq.assert_called_once_with("cnpj", MOCK_CNPJ)
    cnpj_service.client.table.return_value.delete.return_value.eq.assert_called_once_with("cnpj", MOCK_CNPJ)

@pytest.mark.asyncio
async def test_cache_data(cnpj_service):
    """Test de almacenamiento en caché."""
    # Datos de prueba
    cnpj_data = CNPJData(
        cnpj=MOCK_CNPJ,
        razao_social="EMPRESA TESTE LTDA",
        nome_fantasia="Empresa Teste",
        situacao_cadastral="ATIVA",
        uf="SP",
        municipio="SAO PAULO",
        endereco_completo="RUA DAS FLORES, 123",
        telefone="(11) 1234-5678",
        api_source="Mock"
    )
    
    # Mock para upsert
    mock_upsert = AsyncMock()
    cnpj_service.client.table.return_value.upsert.return_value.execute = mock_upsert
    
    # Ejecutar
    await cnpj_service._cache_data(cnpj_data)
    
    # Verificar
    cnpj_service.client.table.return_value.upsert.assert_called_once()
    args = cnpj_service.client.table.return_value.upsert.call_args[0][0]
    assert args["cnpj"] == MOCK_CNPJ
    assert args["razao_social"] == "EMPRESA TESTE LTDA"
    assert "cached_at" in args

@pytest.mark.asyncio
async def test_get_cnpj_data_cached(cnpj_service):
    """Test de obtención de datos CNPJ (cacheado)."""
    # Configurar mock de caché
    mock_data = {
        "cnpj": MOCK_CNPJ,
        "razao_social": "Empresa Test",
        "cached_at": datetime.now().isoformat()
    }
    mock_select = AsyncMock(return_value=MagicMock(data=[mock_data]))
    cnpj_service.client.table.return_value.select.return_value.eq.return_value.execute = mock_select
    
    # Ejecutar
    result = await cnpj_service.get_cnpj_data(MOCK_CNPJ)
    
    # Verificar
    assert result.cnpj == MOCK_CNPJ
    assert result.razao_social == "Empresa Test"
    cnpj_service.client.table.return_value.select.return_value.eq.assert_called_once_with("cnpj", MOCK_CNPJ)
    cnpj_service.cnpj_client.get_cnpj_data.assert_not_called()

@pytest.mark.asyncio
async def test_get_cnpj_data_fresh(cnpj_service):
    """Test de obtención de datos CNPJ (fresco)."""
    # Configurar mock de caché vacío
    mock_select = AsyncMock(return_value=MagicMock(data=[]))
    cnpj_service.client.table.return_value.select.return_value.eq.return_value.execute = mock_select
    
    # Configurar mock de upsert
    mock_upsert = AsyncMock()
    cnpj_service.client.table.return_value.upsert.return_value.execute = mock_upsert
    
    # Ejecutar
    result = await cnpj_service.get_cnpj_data(MOCK_CNPJ)
    
    # Verificar
    assert result.cnpj == MOCK_CNPJ
    assert result.razao_social == "EMPRESA TESTE LTDA"
    cnpj_service.client.table.return_value.select.return_value.eq.assert_called_once_with("cnpj", MOCK_CNPJ)
    cnpj_service.cnpj_client.get_cnpj_data.assert_called_once_with(MOCK_CNPJ)

@pytest.mark.asyncio
async def test_generate_cnpj_card_new(cnpj_service):
    """Test de generación de cartón CNPJ (nuevo)."""
    # Configurar mock de cartón existente
    mock_select = AsyncMock(return_value=MagicMock(data=[]))
    cnpj_service.client.table.return_value.select.return_value.eq.return_value.execute = mock_select
    
    # Configurar mock de datos CNPJ
    mock_cnpj_data = CNPJData(
        cnpj=MOCK_CNPJ,
        razao_social="EMPRESA TESTE LTDA",
        nome_fantasia="Empresa Teste",
        situacao_cadastral="ATIVA",
        uf="SP",
        municipio="SAO PAULO",
        endereco_completo="RUA DAS FLORES, 123",
        telefone="(11) 1234-5678",
        api_source="Mock"
    )
    cnpj_service.get_cnpj_data = AsyncMock(return_value=mock_cnpj_data)
    
    # Configurar mock de descarga PDF
    pdf_content = b"%PDF-1.4\n..."  # Contenido mínimo de PDF
    pdf_info = {
        "success": True,
        "file_size_bytes": len(pdf_content),
        "api_source": "Mock",
        "content": pdf_content
    }
    cnpj_service.cnpj_client.download_cnpj_certificate_pdf = AsyncMock(return_value=pdf_info)
    
    # Configurar mock de Supabase Storage
    storage_mock = MagicMock()
    storage_mock.upload = AsyncMock(return_value={"path": "cards/test.pdf"})
    storage_mock.get_public_url = MagicMock(return_value="http://test.com/cards/test.pdf")
    cnpj_service.client.storage.from_ = MagicMock(return_value=storage_mock)
    
    # Configurar mock de base de datos
    mock_upsert = AsyncMock()
    cnpj_service.client.table.return_value.upsert.return_value.execute = mock_upsert
    
    # Ejecutar
    result = await cnpj_service.generate_cnpj_card(MOCK_CNPJ)
    
    # Verificar
    assert result["success"]
    assert result["public_url"] == "http://test.com/cards/test.pdf"
    assert result["file_size_bytes"] == len(pdf_content)
    assert result["api_source"] == "Mock"
    
    # Verificar llamadas
    cnpj_service.get_cnpj_data.assert_called_once_with(MOCK_CNPJ)
    cnpj_service.cnpj_client.download_cnpj_certificate_pdf.assert_called_once_with(MOCK_CNPJ)
    storage_mock.upload.assert_called_once()
    storage_mock.get_public_url.assert_called_once()
    cnpj_service.client.table.return_value.upsert.assert_called_once()

@pytest.mark.asyncio
async def test_generate_cnpj_card_existing(cnpj_service):
    """Test de generación de cartón CNPJ (existente)."""
    # Configurar mock de cartón existente
    mock_data = {
        "cnpj": MOCK_CNPJ,
        "razao_social": "EMPRESA TESTE LTDA",
        "public_url": "http://test.com/cards/test.pdf",
        "file_size_bytes": 1000,
        "api_source": "Mock",
        "generated_at": datetime.now().isoformat()
    }
    mock_select = AsyncMock(return_value=MagicMock(data=[mock_data]))
    cnpj_service.client.table.return_value.select.return_value.eq.return_value.execute = mock_select
    
    # Ejecutar
    result = await cnpj_service.get_cnpj_card(MOCK_CNPJ)
    
    # Verificar
    assert result == mock_data
    cnpj_service.client.table.return_value.select.return_value.eq.assert_called_once_with("cnpj", MOCK_CNPJ)

@pytest.mark.asyncio
async def test_list_cnpj_cards(cnpj_service):
    """Test de listado de cartones CNPJ."""
    # Configurar mock de conteo
    mock_count = AsyncMock(return_value=MagicMock(count=10))
    cnpj_service.client.table.return_value.select.return_value.execute = mock_count
    
    # Configurar mock de registros
    mock_data = [
        {
            "cnpj": MOCK_CNPJ,
            "public_url": "http://test.com/card.pdf",
            "file_size_bytes": 1000,
            "api_source": "Mock",
            "generated_at": datetime.now().isoformat()
        }
    ]
    mock_select = AsyncMock(return_value=MagicMock(data=mock_data))
    cnpj_service.client.table.return_value.select.return_value.order.return_value.range.return_value.execute = mock_select
    
    # Ejecutar
    result = await cnpj_service.list_cnpj_cards(page=1, per_page=10)
    
    # Verificar
    assert result["total"] == 10
    assert len(result["items"]) == 1
    assert result["items"][0]["cnpj"] == MOCK_CNPJ
    assert result["items"][0]["public_url"] == "http://test.com/card.pdf"

class TestCNPJService:
    @pytest.fixture
    def valid_cnpj(self):
        return "11.222.333/0001-81"
        
    @pytest.fixture
    def sample_cnpj_data(self):
        return CNPJData(
            cnpj="11.222.333/0001-81",
            razao_social="EMPRESA TESTE LTDA",
            nome_fantasia="Empresa Teste",
            situacao_cadastral="ATIVA",
            uf="SP",
            municipio="SAO PAULO",
            endereco_completo="RUA DAS FLORES, 123",
            telefone="(11) 1234-5678",
            email="contato@empresateste.com.br",
            data_situacao_cadastral="2020-01-01",
            api_source="brasilapi"
        )
    
    @pytest.fixture
    def mock_supabase_client(self):
        mock_client = MagicMock()
        
        # Mock para tabla cnpj_data_cache
        mock_client.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
            return_value=MagicMock(data=[])
        )
        mock_client.table.return_value.upsert.return_value.execute = AsyncMock()
        mock_client.table.return_value.delete.return_value.eq.return_value.execute = AsyncMock()
        
        # Mock para storage
        mock_client.storage.from_.return_value.upload = AsyncMock(
            return_value={"path": "cards/test.pdf"}
        )
        mock_client.storage.from_.return_value.get_public_url = MagicMock(
            return_value="https://test.com/cards/test.pdf"
        )
        
        return mock_client
    
    @pytest.fixture
    def mock_cnpj_client(self, sample_cnpj_data):
        mock_client = MagicMock()
        mock_client.get_cnpj_data = AsyncMock(return_value=sample_cnpj_data)
        mock_client.download_cnpj_certificate_pdf = AsyncMock(
            return_value={"file_size_bytes": 12345}
        )
        return mock_client
    
    @pytest.fixture
    def service(self, mock_supabase_client, mock_cnpj_client):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CNPJService(mock_supabase_client, mock_cnpj_client)
            service.base_dir = Path(temp_dir)
            service.cache_dir = service.base_dir / "cache"
            service.cards_dir = service.base_dir / "cards"
            service.cache_dir.mkdir(parents=True, exist_ok=True)
            service.cards_dir.mkdir(parents=True, exist_ok=True)
            yield service
    
    async def test_get_cnpj_data_no_cache(self, service, valid_cnpj, sample_cnpj_data):
        """Prueba obtener datos de CNPJ sin caché."""
        result = await service.get_cnpj_data(valid_cnpj)
        assert result == sample_cnpj_data
        service.cnpj_client.get_cnpj_data.assert_called_once_with(valid_cnpj)
    
    async def test_get_cnpj_data_with_cache(self, service, valid_cnpj, sample_cnpj_data):
        """Prueba obtener datos de CNPJ desde caché."""
        # Configurar mock para devolver datos cacheados
        cached_data = {
            "cnpj": sample_cnpj_data.cnpj,
            "razao_social": sample_cnpj_data.razao_social,
            "nome_fantasia": sample_cnpj_data.nome_fantasia,
            "situacao_cadastral": sample_cnpj_data.situacao_cadastral,
            "data_situacao_cadastral": sample_cnpj_data.data_situacao_cadastral,
            "endereco_completo": sample_cnpj_data.endereco_completo,
            "telefone": sample_cnpj_data.telefone,
            "email": sample_cnpj_data.email,
            "api_source": sample_cnpj_data.api_source,
            "cached_at": datetime.now().isoformat()
        }
        
        service.client.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
            return_value=MagicMock(data=[cached_data])
        )
        
        result = await service.get_cnpj_data(valid_cnpj)
        assert result.cnpj == sample_cnpj_data.cnpj
        assert result.razao_social == sample_cnpj_data.razao_social
        service.cnpj_client.get_cnpj_data.assert_not_called()
    
    async def test_get_cnpj_data_expired_cache(self, service, valid_cnpj, sample_cnpj_data):
        """Prueba obtener datos de CNPJ con caché expirado."""
        # Configurar mock para devolver datos cacheados expirados
        cached_data = {
            "cnpj": sample_cnpj_data.cnpj,
            "razao_social": sample_cnpj_data.razao_social,
            "nome_fantasia": sample_cnpj_data.nome_fantasia,
            "situacao_cadastral": sample_cnpj_data.situacao_cadastral,
            "data_situacao_cadastral": sample_cnpj_data.data_situacao_cadastral,
            "endereco_completo": sample_cnpj_data.endereco_completo,
            "telefone": sample_cnpj_data.telefone,
            "email": sample_cnpj_data.email,
            "api_source": sample_cnpj_data.api_source,
            "cached_at": (datetime.now() - timedelta(hours=25)).isoformat()
        }
        
        service.client.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
            return_value=MagicMock(data=[cached_data])
        )
        
        result = await service.get_cnpj_data(valid_cnpj)
        assert result == sample_cnpj_data
        service.cnpj_client.get_cnpj_data.assert_called_once_with(valid_cnpj)
    
    async def test_generate_cnpj_card(self, service, valid_cnpj, sample_cnpj_data):
        """Prueba generar cartón CNPJ."""
        result = await service.generate_cnpj_card(valid_cnpj)
        
        assert result["success"] is True
        assert result["cnpj"] == valid_cnpj
        assert result["razao_social"] == sample_cnpj_data.razao_social
        assert result["public_url"] == "https://test.com/cards/test.pdf"
        assert result["file_size_bytes"] == 12345
        assert "generated_at" in result
        assert result["api_source"] == sample_cnpj_data.api_source
        
        service.cnpj_client.get_cnpj_data.assert_called_once_with(valid_cnpj)
        service.cnpj_client.download_cnpj_certificate_pdf.assert_called_once_with(valid_cnpj)
    
    async def test_get_cnpj_card(self, service, valid_cnpj, sample_cnpj_data):
        """Prueba obtener cartón CNPJ existente."""
        # Configurar mock para devolver datos del cartón
        card_data = {
            "cnpj": valid_cnpj,
            "razao_social": sample_cnpj_data.razao_social,
            "public_url": "https://test.com/cards/test.pdf",
            "file_size_bytes": 12345,
            "generated_at": datetime.now().isoformat(),
            "api_source": sample_cnpj_data.api_source
        }
        
        service.client.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
            return_value=MagicMock(data=[card_data])
        )
        
        result = await service.get_cnpj_card(valid_cnpj)
        
        assert result["success"] is True
        assert result["cnpj"] == valid_cnpj
        assert result["razao_social"] == sample_cnpj_data.razao_social
        assert result["public_url"] == "https://test.com/cards/test.pdf"
        assert result["file_size_bytes"] == 12345
        assert "generated_at" in result
        assert result["api_source"] == sample_cnpj_data.api_source
    
    async def test_list_cnpj_cards(self, service, valid_cnpj, sample_cnpj_data):
        """Prueba listar cartones CNPJ."""
        # Configurar mock para devolver lista de cartones
        cards = [{
            "cnpj": valid_cnpj,
            "razao_social": sample_cnpj_data.razao_social,
            "public_url": "https://test.com/cards/test.pdf",
            "file_size_bytes": 12345,
            "generated_at": datetime.now().isoformat(),
            "api_source": sample_cnpj_data.api_source
        }]
        
        service.client.table.return_value.select.return_value.execute = AsyncMock(
            return_value=MagicMock(count=1)
        )
        service.client.table.return_value.select.return_value.order.return_value.range.return_value.execute = AsyncMock(
            return_value=MagicMock(data=cards)
        )
        
        result = await service.list_cnpj_cards()
        
        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["cnpj"] == valid_cnpj
        assert result["metadata"]["total"] == 1
        assert result["metadata"]["limit"] == 100
        assert result["metadata"]["offset"] == 0 