"""
Tests unitarios para el cliente de Pipefy.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.integrations.pipefy_client import PipefyClient, PipefyAPIError

class TestPipefyClient:
    """Tests para el cliente GraphQL de Pipefy."""
    
    @pytest.fixture
    def pipefy_client(self):
        """Fixture que retorna una instancia del cliente Pipefy."""
        return PipefyClient()
    
    @pytest.fixture
    def mock_successful_move_response(self):
        """Mock de respuesta exitosa para movimiento de card."""
        return {
            "data": {
                "moveCardToPhase": {
                    "card": {
                        "id": "123456",
                        "title": "Test Card",
                        "current_phase": {
                            "id": "338000018",
                            "name": "Aprovado"
                        },
                        "updated_at": "2024-01-15T10:30:00Z"
                    },
                    "success": True
                }
            }
        }
    
    @pytest.fixture
    def mock_successful_update_response(self):
        """Mock de respuesta exitosa para actualización de campo."""
        return {
            "data": {
                "updateCardField": {
                    "card": {
                        "id": "123456",
                        "title": "Test Card",
                        "updated_at": "2024-01-15T10:30:00Z"
                    },
                    "success": True
                }
            }
        }
    
    @pytest.fixture
    def mock_card_info_response(self):
        """Mock de respuesta para información de card."""
        return {
            "data": {
                "card": {
                    "id": "123456",
                    "title": "Test Card",
                    "current_phase": {
                        "id": "338000017",
                        "name": "Pendências Documentais"
                    },
                    "pipe": {
                        "id": "789",
                        "name": "Test Pipe"
                    },
                    "created_at": "2024-01-15T09:00:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_move_card_to_phase_success(self, pipefy_client, mock_successful_move_response):
        """Test movimiento exitoso de card a fase."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_successful_move_response
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await pipefy_client.move_card_to_phase("123456", "338000018")
            
            assert result["success"] is True
            assert result["card_id"] == "123456"
            assert result["new_phase_id"] == "338000018"
            assert result["new_phase_name"] == "Aprovado"
    
    @pytest.mark.asyncio
    async def test_move_card_to_phase_graphql_error(self, pipefy_client):
        """Test manejo de errores GraphQL."""
        error_response = {
            "errors": [{"message": "Card not found"}]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = error_response
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            with pytest.raises(PipefyAPIError, match="Error GraphQL en Pipefy"):
                await pipefy_client.move_card_to_phase("123456", "338000018")
    
    @pytest.mark.asyncio
    async def test_move_card_to_phase_http_error(self, pipefy_client):
        """Test manejo de errores HTTP."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPStatusError("401", request=None, response=mock_response)
            )
            
            with pytest.raises(PipefyAPIError, match="Error HTTP al mover card"):
                await pipefy_client.move_card_to_phase("123456", "338000018")
    
    @pytest.mark.asyncio
    async def test_move_card_to_phase_timeout(self, pipefy_client):
        """Test manejo de timeout."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Request timeout")
            )
            
            with pytest.raises(PipefyAPIError, match="Timeout al mover card"):
                await pipefy_client.move_card_to_phase("123456", "338000018")
    
    @pytest.mark.asyncio
    async def test_update_card_field_success(self, pipefy_client, mock_successful_update_response):
        """Test actualización exitosa de campo."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_successful_update_response
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await pipefy_client.update_card_field("123456", "informe_crewai_2", "Test report")
            
            assert result["success"] is True
            assert result["card_id"] == "123456"
            assert result["field_id"] == "informe_crewai_2"
    
    @pytest.mark.asyncio
    async def test_get_card_info_success(self, pipefy_client, mock_card_info_response):
        """Test obtención exitosa de información de card."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_card_info_response
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await pipefy_client.get_card_info("123456")
            
            assert result["id"] == "123456"
            assert result["title"] == "Test Card"
            assert result["current_phase"]["name"] == "Pendências Documentais"
    
    @pytest.mark.asyncio
    async def test_move_card_by_classification_aprovado(self, pipefy_client, mock_successful_move_response):
        """Test movimiento por clasificación - Aprovado."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_successful_move_response
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await pipefy_client.move_card_by_classification("123456", "Aprovado")
            
            assert result["success"] is True
            assert result["classification"] == "Aprovado"
            assert result["new_phase_id"] == "338000018"
    
    @pytest.mark.asyncio
    async def test_move_card_by_classification_invalid(self, pipefy_client):
        """Test movimiento por clasificación inválida."""
        with pytest.raises(ValueError, match="Clasificación inválida"):
            await pipefy_client.move_card_by_classification("123456", "InvalidClassification")
    
    def test_classification_mapping(self, pipefy_client):
        """Test que el mapeo de clasificaciones sea correcto."""
        # Este test verifica que las constantes estén correctamente configuradas
        from src.config import settings
        
        assert settings.PHASE_ID_APROVADO == "338000018"
        assert settings.PHASE_ID_PENDENCIAS == "338000017"
        assert settings.PHASE_ID_EMITIR_DOCS == "338000019"