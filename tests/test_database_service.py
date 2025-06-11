"""
Tests para el servicio de base de datos.
Adaptado para usar FAQ.pdf como knowledge base en lugar de checklist_config.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from src.services.database_service import (
    DatabaseService, 
    CaseTrackingRecord, 
    ProcessingLogRecord, 
    NotificationRecord
)

class TestDatabaseService:
    """Tests para DatabaseService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock del cliente Supabase."""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        return mock_client, mock_table
    
    @pytest.fixture
    def database_service(self, mock_supabase_client):
        """Instancia de DatabaseService con cliente mock."""
        mock_client, _ = mock_supabase_client
        with patch('src.services.database_service.create_client', return_value=mock_client):
            service = DatabaseService()
        return service
    
    # === TESTS DE CASE TRACKING ===
    
    @pytest.mark.asyncio
    async def test_create_case_tracking_success(self, database_service, mock_supabase_client):
        """Test crear tracking de caso exitoso."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"id": "test-uuid", "case_id": "CASE-001"}]
        mock_table.insert.return_value.execute.return_value = mock_execute
        
        # Crear record
        record = CaseTrackingRecord(
            case_id="CASE-001",
            company_name="Test Company",
            cnpj="12345678000195"
        )
        
        # Ejecutar
        result = await database_service.create_case_tracking(record)
        
        # Verificar
        assert result["case_id"] == "CASE-001"
        mock_table.insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_case_tracking_success(self, database_service, mock_supabase_client):
        """Test actualizar tracking de caso exitoso."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"case_id": "CASE-001", "processing_status": "completed"}]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        updates = {"processing_status": "completed"}
        result = await database_service.update_case_tracking("CASE-001", updates)
        
        # Verificar
        assert result["processing_status"] == "completed"
        mock_table.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_case_tracking_found(self, database_service, mock_supabase_client):
        """Test obtener tracking de caso existente."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"case_id": "CASE-001", "company_name": "Test Company"}]
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.get_case_tracking("CASE-001")
        
        # Verificar
        assert result is not None
        assert result["case_id"] == "CASE-001"
    
    @pytest.mark.asyncio
    async def test_get_case_tracking_not_found(self, database_service, mock_supabase_client):
        """Test obtener tracking de caso no existente."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = []
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.get_case_tracking("CASE-999")
        
        # Verificar
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_cases_by_status(self, database_service, mock_supabase_client):
        """Test listar casos por status."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [
            {"case_id": "CASE-001", "processing_status": "pending"},
            {"case_id": "CASE-002", "processing_status": "pending"}
        ]
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.list_cases_by_status("pending")
        
        # Verificar
        assert len(result) == 2
        assert all(case["processing_status"] == "pending" for case in result)
    
    # === TESTS DE PROCESSING LOGS ===
    
    @pytest.mark.asyncio
    async def test_add_processing_log_success(self, database_service, mock_supabase_client):
        """Test agregar log de procesamiento exitoso."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"id": "log-uuid", "case_id": "CASE-001"}]
        mock_table.insert.return_value.execute.return_value = mock_execute
        
        # Crear record
        record = ProcessingLogRecord(
            case_id="CASE-001",
            log_level="INFO",
            component="triagem_service",
            message="Procesamiento iniciado"
        )
        
        # Ejecutar
        result = await database_service.add_processing_log(record)
        
        # Verificar
        assert result["case_id"] == "CASE-001"
        mock_table.insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_case_logs(self, database_service, mock_supabase_client):
        """Test obtener logs de caso."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [
            {"case_id": "CASE-001", "log_level": "INFO", "message": "Log 1"},
            {"case_id": "CASE-001", "log_level": "ERROR", "message": "Log 2"}
        ]
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.get_case_logs("CASE-001")
        
        # Verificar
        assert len(result) == 2
        assert all(log["case_id"] == "CASE-001" for log in result)
    
    @pytest.mark.asyncio
    async def test_get_case_logs_with_level_filter(self, database_service, mock_supabase_client):
        """Test obtener logs de caso con filtro de nivel."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"case_id": "CASE-001", "log_level": "ERROR", "message": "Error log"}]
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.get_case_logs("CASE-001", "ERROR")
        
        # Verificar
        assert len(result) == 1
        assert result[0]["log_level"] == "ERROR"
    
    # === TESTS DE NOTIFICATION HISTORY ===
    
    @pytest.mark.asyncio
    async def test_add_notification_record_success(self, database_service, mock_supabase_client):
        """Test registrar notificación exitoso."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"id": "notif-uuid", "case_id": "CASE-001"}]
        mock_table.insert.return_value.execute.return_value = mock_execute
        
        # Crear record
        record = NotificationRecord(
            case_id="CASE-001",
            notification_type="blocking_issues",
            recipient_name="Test User",
            recipient_phone="+5511999999999",
            message_content="Test message"
        )
        
        # Ejecutar
        result = await database_service.add_notification_record(record)
        
        # Verificar
        assert result["case_id"] == "CASE-001"
        mock_table.insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_notification_status(self, database_service, mock_supabase_client):
        """Test actualizar status de notificación."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"id": "notif-uuid", "delivery_status": "delivered"}]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.update_notification_status(
            "notif-uuid", 
            "delivered", 
            datetime.now()
        )
        
        # Verificar
        assert result["delivery_status"] == "delivered"
        mock_table.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_case_notifications(self, database_service, mock_supabase_client):
        """Test obtener notificaciones de caso."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [
            {"case_id": "CASE-001", "notification_type": "blocking_issues"},
            {"case_id": "CASE-001", "notification_type": "approval"}
        ]
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.get_case_notifications("CASE-001")
        
        # Verificar
        assert len(result) == 2
        assert all(notif["case_id"] == "CASE-001" for notif in result)
    
    # === TESTS DE SYSTEM CONFIG ===
    
    @pytest.mark.asyncio
    async def test_get_system_config_found(self, database_service, mock_supabase_client):
        """Test obtener configuración existente."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"config_value": {"test": "value"}}]
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.get_system_config("test_config")
        
        # Verificar
        assert result == {"test": "value"}
    
    @pytest.mark.asyncio
    async def test_get_system_config_not_found(self, database_service, mock_supabase_client):
        """Test obtener configuración no existente."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = []
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.get_system_config("nonexistent_config")
        
        # Verificar
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_system_config(self, database_service, mock_supabase_client):
        """Test actualizar configuración del sistema."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"config_key": "test_config", "config_value": {"updated": "value"}}]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.update_system_config(
            "test_config", 
            {"updated": "value"}
        )
        
        # Verificar
        assert result["config_value"] == {"updated": "value"}
        mock_table.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_notification_recipients(self, database_service, mock_supabase_client):
        """Test obtener destinatarios de notificaciones."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{
            "config_value": [
                {"name": "User 1", "phone": "+5511111111111", "is_active": True},
                {"name": "User 2", "phone": "+5511222222222", "is_active": False},
                {"name": "User 3", "phone": "+5511333333333", "is_active": True}
            ]
        }]
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.get_notification_recipients()
        
        # Verificar
        assert len(result) == 2  # Solo los activos
        assert all(r["is_active"] for r in result)
    
    # === TESTS DE UTILITY METHODS ===
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, database_service, mock_supabase_client):
        """Test health check exitoso."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"count": 1}]
        mock_table.select.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.health_check()
        
        # Verificar
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, database_service, mock_supabase_client):
        """Test health check con fallo."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock para lanzar excepción
        mock_table.select.return_value.execute.side_effect = Exception("Connection error")
        
        # Ejecutar
        result = await database_service.health_check()
        
        # Verificar
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cleanup_old_logs(self, database_service, mock_supabase_client):
        """Test limpieza de logs antiguos."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock
        mock_execute = Mock()
        mock_execute.data = [{"id": "1"}, {"id": "2"}]  # 2 registros eliminados
        mock_table.delete.return_value.lt.return_value.execute.return_value = mock_execute
        
        # Ejecutar
        result = await database_service.cleanup_old_logs(30)
        
        # Verificar
        assert result == 2
        mock_table.delete.assert_called_once()
    
    # === TESTS DE DATACLASSES ===
    
    def test_case_tracking_record_creation(self):
        """Test creación de CaseTrackingRecord."""
        record = CaseTrackingRecord(
            case_id="CASE-001",
            company_name="Test Company",
            cnpj="12345678000195"
        )
        
        assert record.case_id == "CASE-001"
        assert record.company_name == "Test Company"
        assert record.cnpj == "12345678000195"
        assert record.processing_status == "pending"  # Default value
    
    def test_processing_log_record_creation(self):
        """Test creación de ProcessingLogRecord."""
        record = ProcessingLogRecord(
            case_id="CASE-001",
            log_level="INFO",
            component="test_component",
            message="Test message"
        )
        
        assert record.case_id == "CASE-001"
        assert record.log_level == "INFO"
        assert record.component == "test_component"
        assert record.message == "Test message"
    
    def test_notification_record_creation(self):
        """Test creación de NotificationRecord."""
        record = NotificationRecord(
            case_id="CASE-001",
            notification_type="blocking_issues",
            recipient_name="Test User",
            recipient_phone="+5511999999999",
            message_content="Test message"
        )
        
        assert record.case_id == "CASE-001"
        assert record.notification_type == "blocking_issues"
        assert record.recipient_name == "Test User"
        assert record.recipient_phone == "+5511999999999"
        assert record.message_content == "Test message"
        assert record.delivery_status == "sent"  # Default value
    
    # === TESTS DE ERROR HANDLING ===
    
    @pytest.mark.asyncio
    async def test_create_case_tracking_error(self, database_service, mock_supabase_client):
        """Test error al crear tracking de caso."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock para lanzar excepción
        mock_table.insert.return_value.execute.side_effect = Exception("Database error")
        
        # Crear record
        record = CaseTrackingRecord(case_id="CASE-001")
        
        # Ejecutar y verificar excepción
        with pytest.raises(Exception, match="Database error"):
            await database_service.create_case_tracking(record)
    
    @pytest.mark.asyncio
    async def test_get_system_config_error(self, database_service, mock_supabase_client):
        """Test error al obtener configuración."""
        _, mock_table = mock_supabase_client
        
        # Configurar mock para lanzar excepción
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception("Database error")
        
        # Ejecutar y verificar excepción
        with pytest.raises(Exception, match="Database error"):
            await database_service.get_system_config("test_config")