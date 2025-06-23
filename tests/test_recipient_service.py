"""
Tests unitarios para el servicio de gestión de destinatarios.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import UUID
from datetime import datetime

from src.services.recipient_service import RecipientService
from src.services.notification_service import NotificationRecipient

class TestRecipientService:
    """Tests para el servicio de gestión de destinatarios."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Fixture del cliente Supabase mock."""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        return mock_client, mock_table
    
    @pytest.fixture
    def service(self, mock_supabase_client):
        """Fixture del servicio de gestión de destinatarios."""
        client, _ = mock_supabase_client
        with patch('src.services.recipient_service.twilio_client') as mock_twilio:
            service = RecipientService(client)
            service.twilio_client = mock_twilio
            return service
    
    @pytest.fixture
    def sample_recipient_data(self):
        """Fixture de datos de destinatario de prueba."""
        return {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "João Silva",
            "phone_number": "+5511999999999",
            "role": "gestor_comercial",
            "company_name": "Empresa Test",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    
    @pytest.mark.asyncio
    async def test_create_recipient_success(self, service, mock_supabase_client, sample_recipient_data):
        """Test creación exitosa de destinatario."""
        _, mock_table = mock_supabase_client
        
        # Mock validación de teléfono
        service.twilio_client.validate_phone_number.return_value = True
        
        # Mock respuesta de Supabase
        mock_execute = Mock()
        mock_execute.data = [sample_recipient_data]
        mock_table.insert.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await service.create_recipient({
            "name": "João Silva",
            "phone_number": "+5511999999999",
            "role": "gestor_comercial",
            "company_name": "Empresa Test"
        })
        
        # Verificar
        assert result == sample_recipient_data
        service.twilio_client.validate_phone_number.assert_called_once_with("+5511999999999")
        mock_table.insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_recipient_invalid_phone(self, service):
        """Test creación de destinatario con teléfono inválido."""
        # Mock validación de teléfono
        service.twilio_client.validate_phone_number.return_value = False
        
        # Ejecutar y verificar
        with pytest.raises(ValueError, match="Número de teléfono inválido"):
            await service.create_recipient({
                "name": "João Silva",
                "phone_number": "123",  # Número inválido
                "role": "gestor_comercial"
            })
    
    @pytest.mark.asyncio
    async def test_get_recipient_success(self, service, mock_supabase_client, sample_recipient_data):
        """Test obtención exitosa de destinatario."""
        _, mock_table = mock_supabase_client
        
        # Mock respuesta de Supabase
        mock_execute = Mock()
        mock_execute.data = [sample_recipient_data]
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await service.get_recipient(UUID(sample_recipient_data["id"]))
        
        # Verificar
        assert result == sample_recipient_data
        mock_table.select.assert_called_once_with("*")
        mock_table.select.return_value.eq.assert_called_once_with("id", sample_recipient_data["id"])
    
    @pytest.mark.asyncio
    async def test_get_recipient_not_found(self, service, mock_supabase_client):
        """Test obtención de destinatario inexistente."""
        _, mock_table = mock_supabase_client
        
        # Mock respuesta vacía de Supabase
        mock_execute = Mock()
        mock_execute.data = []
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await service.get_recipient(UUID("123e4567-e89b-12d3-a456-426614174000"))
        
        # Verificar
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_recipients_success(self, service, mock_supabase_client, sample_recipient_data):
        """Test listado exitoso de destinatarios."""
        _, mock_table = mock_supabase_client
        
        # Mock respuesta de Supabase
        mock_execute = Mock()
        mock_execute.data = [sample_recipient_data]
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await service.list_recipients(active_only=True)
        
        # Verificar
        assert result == [sample_recipient_data]
        mock_table.select.assert_called_once_with("*")
        mock_table.select.return_value.eq.assert_called_once_with("is_active", True)
    
    @pytest.mark.asyncio
    async def test_update_recipient_success(self, service, mock_supabase_client, sample_recipient_data):
        """Test actualización exitosa de destinatario."""
        _, mock_table = mock_supabase_client
        
        # Mock respuesta de Supabase
        mock_execute = Mock()
        mock_execute.data = [sample_recipient_data]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Datos de actualización
        updates = {
            "name": "João Silva Jr",
            "company_name": "Nueva Empresa"
        }
        
        # Ejecutar
        result = await service.update_recipient(UUID(sample_recipient_data["id"]), updates)
        
        # Verificar
        assert result == sample_recipient_data
        mock_table.update.assert_called_once()
        mock_table.update.return_value.eq.assert_called_once_with("id", sample_recipient_data["id"])
    
    @pytest.mark.asyncio
    async def test_update_recipient_with_phone(self, service, mock_supabase_client, sample_recipient_data):
        """Test actualización de destinatario con nuevo teléfono."""
        _, mock_table = mock_supabase_client
        
        # Mock validación de teléfono
        service.twilio_client.validate_phone_number.return_value = True
        
        # Mock respuesta de Supabase
        mock_execute = Mock()
        mock_execute.data = [sample_recipient_data]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Datos de actualización
        updates = {
            "phone_number": "+5511888888888"
        }
        
        # Ejecutar
        result = await service.update_recipient(UUID(sample_recipient_data["id"]), updates)
        
        # Verificar
        assert result == sample_recipient_data
        service.twilio_client.validate_phone_number.assert_called_once_with("+5511888888888")
    
    @pytest.mark.asyncio
    async def test_delete_recipient_success(self, service, mock_supabase_client):
        """Test eliminación exitosa de destinatario."""
        _, mock_table = mock_supabase_client
        
        # Mock respuesta de Supabase
        mock_execute = Mock()
        mock_execute.data = [{"id": "123"}]  # Cualquier dato indica éxito
        mock_table.delete.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await service.delete_recipient(UUID("123e4567-e89b-12d3-a456-426614174000"))
        
        # Verificar
        assert result is True
        mock_table.delete.assert_called_once()
        mock_table.delete.return_value.eq.assert_called_once_with(
            "id", "123e4567-e89b-12d3-a456-426614174000"
        )
    
    @pytest.mark.asyncio
    async def test_get_recipients_by_role(self, service, mock_supabase_client, sample_recipient_data):
        """Test obtención de destinatarios por rol."""
        _, mock_table = mock_supabase_client
        
        # Mock respuesta de Supabase
        mock_execute = Mock()
        mock_execute.data = [sample_recipient_data]
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await service.get_recipients_by_role("gestor_comercial", active_only=True)
        
        # Verificar
        assert result == [sample_recipient_data]
        mock_table.select.assert_called_once_with("*")
        mock_table.select.return_value.eq.assert_called_once_with("role", "gestor_comercial")
    
    @pytest.mark.asyncio
    async def test_get_recipients_by_company(self, service, mock_supabase_client, sample_recipient_data):
        """Test obtención de destinatarios por empresa."""
        _, mock_table = mock_supabase_client
        
        # Mock respuesta de Supabase
        mock_execute = Mock()
        mock_execute.data = [sample_recipient_data]
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await service.get_recipients_by_company("Empresa Test", active_only=True)
        
        # Verificar
        assert result == [sample_recipient_data]
        mock_table.select.assert_called_once_with("*")
        mock_table.select.return_value.eq.assert_called_once_with("company_name", "Empresa Test")
    
    def test_to_notification_recipient(self, service, sample_recipient_data):
        """Test conversión a NotificationRecipient."""
        # Ejecutar
        result = service.to_notification_recipient(sample_recipient_data)
        
        # Verificar
        assert isinstance(result, NotificationRecipient)
        assert result.name == sample_recipient_data["name"]
        assert result.phone_number == sample_recipient_data["phone_number"]
        assert result.role == sample_recipient_data["role"]
        assert result.is_active == sample_recipient_data["is_active"] 