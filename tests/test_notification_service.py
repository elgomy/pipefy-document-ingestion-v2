"""
Tests unitarios para el servicio de notificaciones WhatsApp.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.notification_service import (
    NotificationService,
    NotificationRecipient,
    NotificationContext,
    NotificationResult,
    NotificationType
)
from src.services.classification_service import (
    ClassificationResult,
    ClassificationType,
    DocumentAnalysis,
    DocumentType
)

class TestNotificationService:
    """Tests para el servicio de notificaciones."""
    
    @pytest.fixture
    def service(self):
        """Fixture del servicio de notificaciones."""
        with patch('src.services.notification_service.twilio_client') as mock_client:
            service = NotificationService()
            service.twilio_client = mock_client
            return service
    
    @pytest.fixture
    def sample_recipient(self):
        """Fixture de destinatario de prueba."""
        return NotificationRecipient(
            name="João Silva",
            phone_number="+5511999999999",
            role="gestor_comercial",
            is_active=True
        )
    
    @pytest.fixture
    def sample_context(self):
        """Fixture de contexto de notificación."""
        return NotificationContext(
            case_id="CASE-12345",
            company_name="Empresa Teste Ltda",
            cnpj="12.345.678/0001-99",
            analyst_name="Maria Santos"
        )
    
    @pytest.fixture
    def blocking_classification_result(self):
        """Fixture de resultado con pendencias bloqueantes."""
        return ClassificationResult(
            ClassificationType.PENDENCIA_BLOQUEANTE,
            0.85,
            "Documentos com pendências bloqueantes",
            [
                DocumentAnalysis(DocumentType.CARTAO_CNPJ, False, False, ["Ausente"], None),
                DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, True, False, ["Vencido"], 120)
            ],
            ["Cartão CNPJ ausente", "Contrato social vencido"],
            [],
            []
        )
    
    @pytest.fixture
    def approved_classification_result(self):
        """Fixture de resultado aprovado."""
        return ClassificationResult(
            ClassificationType.APROVADO,
            0.95,
            "Documentação aprovada",
            [
                DocumentAnalysis(DocumentType.CARTAO_CNPJ, True, True, [], 30),
                DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, True, True, [], 45)
            ],
            [],
            [],
            []
        )
    
    @pytest.fixture
    def non_blocking_classification_result(self):
        """Fixture de resultado com pendencias não bloqueantes."""
        return ClassificationResult(
            ClassificationType.PENDENCIA_NAO_BLOQUEANTE,
            0.75,
            "Documentação aprovada com observações",
            [
                DocumentAnalysis(DocumentType.CARTAO_CNPJ, False, False, ["Ausente"], None, True),
                DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, True, True, [], 45)
            ],
            [],
            ["Cartão CNPJ pode ser gerado automaticamente"],
            ["Gerar Cartão CNPJ"]
        )
    
    @pytest.mark.asyncio
    async def test_send_blocking_issues_notification_success(
        self, service, blocking_classification_result, sample_context, sample_recipient
    ):
        """Test envío exitoso de notificación de pendencias bloqueantes."""
        # Mock do cliente Twilio
        service.twilio_client.validate_phone_number.return_value = {
            "valid": True,
            "formatted_number": "+5511999999999"
        }
        service.twilio_client.send_blocking_issues_notification = AsyncMock(return_value={
            "success": True,
            "message_sid": "SM123456789",
            "status": "sent"
        })
        
        # Executar
        result = await service._send_blocking_issues_notification(
            blocking_classification_result,
            sample_context,
            sample_recipient
        )
        
        # Verificar
        assert result.success is True
        assert result.notification_type == NotificationType.BLOCKING_ISSUES
        assert result.message_sid == "SM123456789"
        assert result.recipient == sample_recipient
        
        # Verificar chamada ao cliente
        service.twilio_client.send_blocking_issues_notification.assert_called_once_with(
            to_number="+5511999999999",
            company_name="Empresa Teste Ltda",
            case_id="CASE-12345",
            blocking_issues=["Cartão CNPJ ausente", "Contrato social vencido"],
            cnpj="12.345.678/0001-99"
        )
    
    @pytest.mark.asyncio
    async def test_send_approval_notification_success(
        self, service, sample_context, sample_recipient
    ):
        """Test envío exitoso de notificación de aprobación."""
        # Mock do cliente Twilio
        service.twilio_client.validate_phone_number.return_value = {
            "valid": True,
            "formatted_number": "+5511999999999"
        }
        service.twilio_client.send_approval_notification = AsyncMock(return_value={
            "success": True,
            "message_sid": "SM987654321",
            "status": "sent"
        })
        
        # Executar
        result = await service._send_approval_notification(
            sample_context,
            sample_recipient
        )
        
        # Verificar
        assert result.success is True
        assert result.notification_type == NotificationType.APPROVAL
        assert result.message_sid == "SM987654321"
        
        # Verificar chamada ao cliente
        service.twilio_client.send_approval_notification.assert_called_once_with(
            to_number="+5511999999999",
            company_name="Empresa Teste Ltda",
            case_id="CASE-12345",
            cnpj="12.345.678/0001-99"
        )
    
    @pytest.mark.asyncio
    async def test_send_classification_notification_blocking(
        self, service, blocking_classification_result, sample_context, sample_recipient
    ):
        """Test envío de notificación basada en clasificación bloqueante."""
        # Mock do método interno
        service._send_blocking_issues_notification = AsyncMock(return_value=NotificationResult(
            success=True,
            notification_type=NotificationType.BLOCKING_ISSUES,
            recipient=sample_recipient,
            message_sid="SM123456789"
        ))
        
        # Executar
        result = await service.send_classification_notification(
            blocking_classification_result,
            sample_context,
            sample_recipient
        )
        
        # Verificar
        assert result.success is True
        assert result.notification_type == NotificationType.BLOCKING_ISSUES
        service._send_blocking_issues_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_classification_notification_approved(
        self, service, approved_classification_result, sample_context, sample_recipient
    ):
        """Test envío de notificación basada en clasificación aprovada."""
        # Mock do método interno
        service._send_approval_notification = AsyncMock(return_value=NotificationResult(
            success=True,
            notification_type=NotificationType.APPROVAL,
            recipient=sample_recipient,
            message_sid="SM987654321"
        ))
        
        # Executar
        result = await service.send_classification_notification(
            approved_classification_result,
            sample_context,
            sample_recipient
        )
        
        # Verificar
        assert result.success is True
        assert result.notification_type == NotificationType.APPROVAL
        service._send_approval_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_classification_notification_non_blocking(
        self, service, non_blocking_classification_result, sample_context, sample_recipient
    ):
        """Test envío de notificación para pendencias não bloqueantes."""
        # Mock do método interno
        service._send_non_blocking_issues_notification = AsyncMock(return_value=NotificationResult(
            success=True,
            notification_type=NotificationType.NON_BLOCKING_ISSUES,
            recipient=sample_recipient,
            message_sid="SM555666777"
        ))
        
        # Executar
        result = await service.send_classification_notification(
            non_blocking_classification_result,
            sample_context,
            sample_recipient
        )
        
        # Verificar
        assert result.success is True
        assert result.notification_type == NotificationType.NON_BLOCKING_ISSUES
        service._send_non_blocking_issues_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_invalid_phone(
        self, service, blocking_classification_result, sample_context
    ):
        """Test envío de notificación con número de teléfono inválido."""
        # Recipient com número inválido
        invalid_recipient = NotificationRecipient(
            name="João Silva",
            phone_number="123",  # Número muito curto
            role="gestor_comercial"
        )
        
        # Mock validação de telefone
        service.twilio_client.validate_phone_number.return_value = {
            "valid": False,
            "error": "Número muito curto"
        }
        
        # Executar
        result = await service._send_blocking_issues_notification(
            blocking_classification_result,
            sample_context,
            invalid_recipient
        )
        
        # Verificar
        assert result.success is False
        assert "Número de teléfono inválido" in result.error_message
    
    @pytest.mark.asyncio
    async def test_send_custom_notification(self, service, sample_recipient):
        """Test envío de notificación personalizada."""
        # Mock do cliente Twilio
        service.twilio_client.validate_phone_number.return_value = {
            "valid": True,
            "formatted_number": "+5511999999999"
        }
        service.twilio_client.send_whatsapp_message = AsyncMock(return_value={
            "success": True,
            "message_sid": "SM111222333",
            "status": "sent"
        })
        
        # Executar
        result = await service.send_custom_notification(
            sample_recipient,
            "Mensagem de teste personalizada",
            NotificationType.SYSTEM_ERROR
        )
        
        # Verificar
        assert result.success is True
        assert result.notification_type == NotificationType.SYSTEM_ERROR
        assert result.message_sid == "SM111222333"
        
        # Verificar chamada
        service.twilio_client.send_whatsapp_message.assert_called_once_with(
            to_number="+5511999999999",
            message="Mensagem de teste personalizada"
        )
    
    @pytest.mark.asyncio
    async def test_get_notification_status(self, service):
        """Test obtenção de status de notificação."""
        # Mock do cliente
        service.twilio_client.get_message_status = AsyncMock(return_value={
            "success": True,
            "message_sid": "SM123456789",
            "status": "delivered",
            "date_sent": "2024-06-15T14:30:00"
        })
        
        # Executar
        result = await service.get_notification_status("SM123456789")
        
        # Verificar
        assert result["success"] is True
        assert result["status"] == "delivered"
        service.twilio_client.get_message_status.assert_called_once_with("SM123456789")
    
    def test_generate_non_blocking_message(self, service):
        """Test geração de mensagem para pendencias não bloqueantes."""
        message = service._generate_non_blocking_message(
            company_name="Empresa Teste",
            case_id="CASE-123",
            non_blocking_issues=["Observação 1", "Observação 2"],
            auto_actions=["Gerar documento X", "Atualizar campo Y"],
            cnpj="12.345.678/0001-99"
        )
        
        # Verificar conteúdo
        assert "PENDÊNCIAS NÃO BLOQUEANTES" in message
        assert "Empresa Teste" in message
        assert "CASE-123" in message
        assert "12.345.678/0001-99" in message
        assert "Observação 1" in message
        assert "Gerar documento X" in message
        assert "Sistema de Triagem v2.0" in message
    
    def test_validate_recipient_valid(self, service, sample_recipient):
        """Test validação de destinatário válido."""
        # Mock validação de telefone
        service.twilio_client.validate_phone_number.return_value = {
            "valid": True,
            "formatted_number": "+5511999999999"
        }
        
        # Executar
        result = service.validate_recipient(sample_recipient)
        
        # Verificar
        assert result["valid"] is True
        assert result["formatted_phone"] == "+5511999999999"
    
    def test_validate_recipient_invalid_name(self, service):
        """Test validação de destinatário com nome inválido."""
        invalid_recipient = NotificationRecipient(
            name="",  # Nome vazio
            phone_number="+5511999999999",
            role="gestor_comercial"
        )
        
        # Executar
        result = service.validate_recipient(invalid_recipient)
        
        # Verificar
        assert result["valid"] is False
        assert "Nome do destinatário é obrigatório" in result["error"]
    
    def test_validate_recipient_invalid_phone(self, service):
        """Test validação de destinatário com telefone inválido."""
        invalid_recipient = NotificationRecipient(
            name="João Silva",
            phone_number="123",  # Telefone inválido
            role="gestor_comercial"
        )
        
        # Mock validação de telefone
        service.twilio_client.validate_phone_number.return_value = {
            "valid": False,
            "error": "Número muito curto"
        }
        
        # Executar
        result = service.validate_recipient(invalid_recipient)
        
        # Verificar
        assert result["valid"] is False
        assert "Número de telefone inválido" in result["error"]
    
    def test_validate_recipient_inactive(self, service):
        """Test validação de destinatário inativo."""
        inactive_recipient = NotificationRecipient(
            name="João Silva",
            phone_number="+5511999999999",
            role="gestor_comercial",
            is_active=False  # Inativo
        )
        
        # Executar
        result = service.validate_recipient(inactive_recipient)
        
        # Verificar
        assert result["valid"] is False
        assert "Destinatário está inativo" in result["error"]
    
    @pytest.mark.asyncio
    async def test_notification_service_error_handling(
        self, service, blocking_classification_result, sample_context, sample_recipient
    ):
        """Test manejo de errores en el servicio de notificaciones."""
        # Mock erro no cliente Twilio
        service.twilio_client.validate_phone_number.side_effect = Exception("Erro de conexão")
        
        # Executar
        result = await service._send_blocking_issues_notification(
            blocking_classification_result,
            sample_context,
            sample_recipient
        )
        
        # Verificar
        assert result.success is False
        assert "Error enviando notificación de pendencias bloqueantes" in result.error_message
        assert result.notification_type == NotificationType.BLOCKING_ISSUES
    
    def test_notification_types_enum(self):
        """Test enum de tipos de notificación."""
        assert NotificationType.BLOCKING_ISSUES.value == "blocking_issues"
        assert NotificationType.APPROVAL.value == "approval"
        assert NotificationType.NON_BLOCKING_ISSUES.value == "non_blocking_issues"
        assert NotificationType.SYSTEM_ERROR.value == "system_error"
    
    def test_notification_result_dataclass(self):
        """Test dataclass NotificationResult."""
        recipient = NotificationRecipient("Test", "+5511999999999")
        result = NotificationResult(
            success=True,
            notification_type=NotificationType.APPROVAL,
            recipient=recipient,
            message_sid="SM123",
            sent_at=datetime.now()
        )
        
        assert result.success is True
        assert result.notification_type == NotificationType.APPROVAL
        assert result.recipient.name == "Test"
        assert result.message_sid == "SM123"
        assert result.error_message is None
    
    def test_notification_context_dataclass(self):
        """Test dataclass NotificationContext."""
        context = NotificationContext(
            case_id="CASE-123",
            company_name="Test Company",
            cnpj="12.345.678/0001-99",
            analyst_name="Test Analyst"
        )
        
        assert context.case_id == "CASE-123"
        assert context.company_name == "Test Company"
        assert context.cnpj == "12.345.678/0001-99"
        assert context.analyst_name == "Test Analyst"
        assert context.classification_result is None
        assert context.additional_info is None 