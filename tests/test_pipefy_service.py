"""
Tests unitarios para el servicio de Pipefy.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.pipefy_service import PipefyService
from src.integrations.pipefy_client import PipefyAPIError

class TestPipefyService:
    """Tests para el servicio de alto nivel de Pipefy."""
    
    @pytest.fixture
    def pipefy_service(self):
        """Fixture que retorna una instancia del servicio Pipefy."""
        return PipefyService()
    
    @pytest.fixture
    def mock_move_result(self):
        """Mock de resultado exitoso de movimiento."""
        return {
            "success": True,
            "card_id": "123456",
            "new_phase_id": "338000018",
            "new_phase_name": "Aprovado",
            "updated_at": "2024-01-15T10:30:00Z",
            "classification": "Aprovado"
        }
    
    @pytest.fixture
    def mock_update_result(self):
        """Mock de resultado exitoso de actualización."""
        return {
            "success": True,
            "card_id": "123456",
            "field_id": "informe_triagem_crewai",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    
    @pytest.mark.asyncio
    async def test_process_triagem_result_success(self, pipefy_service, mock_move_result, mock_update_result):
        """Test procesamiento exitoso de resultado de triagem."""
        with patch.object(pipefy_service.client, 'move_card_by_classification', return_value=mock_move_result) as mock_move, \
             patch.object(pipefy_service.client, 'update_card_field', return_value=mock_update_result) as mock_update:
            
            result = await pipefy_service.process_triagem_result(
                "123456", 
                "Aprovado", 
                "# Informe de Triagem\n\nDocumentação aprovada."
            )
            
            assert result["success"] is True
            assert result["card_id"] == "123456"
            assert result["classification"] == "Aprovado"
            assert len(result["operations"]) == 2
            assert result["operations"][0]["type"] == "move_card"
            assert result["operations"][1]["type"] == "update_field"
            assert len(result["errors"]) == 0
            
            mock_move.assert_called_once_with("123456", "Aprovado")
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_triagem_result_move_error(self, pipefy_service, mock_update_result):
        """Test manejo de error en movimiento de card."""
        with patch.object(pipefy_service.client, 'move_card_by_classification', side_effect=PipefyAPIError("API Error")) as mock_move, \
             patch.object(pipefy_service.client, 'update_card_field', return_value=mock_update_result) as mock_update:
            
            result = await pipefy_service.process_triagem_result(
                "123456", 
                "Aprovado", 
                "# Informe de Triagem\n\nDocumentação aprovada."
            )
            
            assert result["success"] is False
            assert len(result["errors"]) == 1
            assert "Error de API Pipefy" in result["errors"][0]
            
            mock_move.assert_called_once_with("123456", "Aprovado")
            mock_update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_triagem_result_invalid_classification(self, pipefy_service):
        """Test manejo de clasificación inválida."""
        with patch.object(pipefy_service.client, 'move_card_by_classification', side_effect=ValueError("Invalid classification")) as mock_move:
            
            result = await pipefy_service.process_triagem_result(
                "123456", 
                "InvalidClassification", 
                "# Informe de Triagem\n\nClasificación inválida."
            )
            
            assert result["success"] is False
            assert len(result["errors"]) == 1
            assert "Error de validación" in result["errors"][0]
            
            mock_move.assert_called_once_with("123456", "InvalidClassification")
    
    @pytest.mark.asyncio
    async def test_move_card_to_phase_success(self, pipefy_service, mock_move_result):
        """Test movimiento exitoso de card a fase específica."""
        with patch.object(pipefy_service.client, 'move_card_to_phase', return_value=mock_move_result) as mock_move:
            
            result = await pipefy_service.move_card_to_phase("123456", "338000018")
            
            assert result["success"] is True
            assert result["card_id"] == "123456"
            assert result["new_phase_id"] == "338000018"
            
            mock_move.assert_called_once_with("123456", "338000018")
    
    @pytest.mark.asyncio
    async def test_update_card_informe_success(self, pipefy_service, mock_update_result):
        """Test actualización exitosa de informe."""
        with patch.object(pipefy_service.client, 'update_card_field', return_value=mock_update_result) as mock_update:
            
            result = await pipefy_service.update_card_informe("123456", "# Test Report")
            
            assert result["success"] is True
            assert result["card_id"] == "123456"
            
            mock_update.assert_called_once_with("123456", "informe_triagem_crewai", "# Test Report")
    
    @pytest.mark.asyncio
    async def test_get_card_status_success(self, pipefy_service):
        """Test obtención exitosa de estado de card."""
        mock_card_info = {
            "id": "123456",
            "title": "Test Card",
            "current_phase": {"id": "338000017", "name": "Pendências Documentais"}
        }
        
        with patch.object(pipefy_service.client, 'get_card_info', return_value=mock_card_info) as mock_get:
            
            result = await pipefy_service.get_card_status("123456")
            
            assert result["id"] == "123456"
            assert result["title"] == "Test Card"
            
            mock_get.assert_called_once_with("123456")
    
    @pytest.mark.asyncio
    async def test_validate_card_exists_true(self, pipefy_service):
        """Test validación de card existente."""
        mock_card_info = {"id": "123456", "title": "Test Card"}
        
        with patch.object(pipefy_service.client, 'get_card_info', return_value=mock_card_info) as mock_get:
            
            result = await pipefy_service.validate_card_exists("123456")
            
            assert result is True
            mock_get.assert_called_once_with("123456")
    
    @pytest.mark.asyncio
    async def test_validate_card_exists_false(self, pipefy_service):
        """Test validación de card inexistente."""
        with patch.object(pipefy_service.client, 'get_card_info', side_effect=PipefyAPIError("Card not found")) as mock_get:
            
            result = await pipefy_service.validate_card_exists("123456")
            
            assert result is False
            mock_get.assert_called_once_with("123456")
    
    @pytest.mark.asyncio
    async def test_validate_card_exists_unexpected_error(self, pipefy_service):
        """Test validación con error inesperado."""
        with patch.object(pipefy_service.client, 'get_card_info', side_effect=Exception("Unexpected error")) as mock_get:
            
            result = await pipefy_service.validate_card_exists("123456")
            
            assert result is False
            mock_get.assert_called_once_with("123456")
    
    @pytest.mark.asyncio
    async def test_process_triagem_result_all_classifications(self, pipefy_service, mock_update_result):
        """Test procesamiento con todas las clasificaciones válidas."""
        classifications = ["Aprovado", "Pendencia_Bloqueante", "Pendencia_NaoBloqueante"]
        
        for classification in classifications:
            mock_move_result = {
                "success": True,
                "card_id": "123456",
                "new_phase_id": "338000018",
                "new_phase_name": "Test Phase",
                "classification": classification
            }
            
            with patch.object(pipefy_service.client, 'move_card_by_classification', return_value=mock_move_result) as mock_move, \
                 patch.object(pipefy_service.client, 'update_card_field', return_value=mock_update_result) as mock_update:
                
                result = await pipefy_service.process_triagem_result(
                    "123456", 
                    classification, 
                    f"# Informe para {classification}"
                )
                
                assert result["success"] is True
                assert result["classification"] == classification
                mock_move.assert_called_once_with("123456", classification)
                mock_update.assert_called_once()