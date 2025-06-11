"""
Pruebas unitarias para NotificationService.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.notification_service import NotificationService


class TestNotificationService:
    """Pruebas para la clase NotificationService."""

    @pytest.fixture
    def notification_service(self, mock_env_vars, mock_twilio_client):
        """Fixture para crear una instancia de NotificationService."""
        with patch('src.services.notification_service.TwilioClient', return_value=mock_twilio_client):
            return NotificationService()

    @pytest.mark.asyncio
    async def test_send_blocking_issues_notification_success(self, notification_service, sample_notification_data):
        """Testa envio bem-sucedido de notificação de pendências."""
        result = await notification_service.send_blocking_issues_notification(
            recipient_name=sample_notification_data["recipient_name"],
            recipient_phone=sample_notification_data["recipient_phone"],
            company_name=sample_notification_data["company_name"],
            case_id=sample_notification_data["case_id"],
            cnpj=sample_notification_data["cnpj"],
            blocking_issues=sample_notification_data["blocking_issues"]
        )
        
        assert result["success"] is True
        assert "message_sid" in result

    @pytest.mark.asyncio
    async def test_send_blocking_issues_notification_failure(self, notification_service, sample_notification_data):
        """Testa falha no envio de notificação."""
        # Configura o mock para falhar
        notification_service.twilio_client.send_blocking_issues_notification.return_value = {
            "success": False,
            "error": "Failed to send message"
        }
        
        result = await notification_service.send_blocking_issues_notification(
            recipient_name=sample_notification_data["recipient_name"],
            recipient_phone=sample_notification_data["recipient_phone"],
            company_name=sample_notification_data["company_name"],
            case_id=sample_notification_data["case_id"],
            cnpj=sample_notification_data["cnpj"],
            blocking_issues=sample_notification_data["blocking_issues"]
        )
        
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_send_approval_notification(self, notification_service):
        """Testa envio de notificação de aprovação."""
        result = await notification_service.send_approval_notification(
            recipient_name="João Silva",
            recipient_phone="+5511999999999",
            company_name="Empresa Teste LTDA",
            case_id="CASE_123"
        )
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_rejection_notification(self, notification_service):
        """Testa envio de notificação de rejeição."""
        result = await notification_service.send_rejection_notification(
            recipient_name="João Silva",
            recipient_phone="+5511999999999",
            company_name="Empresa Teste LTDA",
            case_id="CASE_123",
            rejection_reasons=["Documento suspeito", "Informações inconsistentes"]
        )
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_custom_message(self, notification_service):
        """Testa envio de mensagem personalizada."""
        custom_message = "Esta é uma mensagem personalizada de teste."
        
        result = await notification_service.send_custom_message(
            recipient_phone="+5511999999999",
            message=custom_message
        )
        
        assert result["success"] is True

    def test_format_blocking_issues_message(self, notification_service, sample_notification_data):
        """Testa formatação de mensagem de pendências."""
        message = notification_service._format_blocking_issues_message(
            recipient_name=sample_notification_data["recipient_name"],
            company_name=sample_notification_data["company_name"],
            case_id=sample_notification_data["case_id"],
            cnpj=sample_notification_data["cnpj"],
            blocking_issues=sample_notification_data["blocking_issues"]
        )
        
        assert sample_notification_data["recipient_name"] in message
        assert sample_notification_data["company_name"] in message
        assert sample_notification_data["case_id"] in message
        assert sample_notification_data["cnpj"] in message
        
        for issue in sample_notification_data["blocking_issues"]:
            assert issue in message

    def test_format_approval_message(self, notification_service):
        """Testa formatação de mensagem de aprovação."""
        message = notification_service._format_approval_message(
            recipient_name="João Silva",
            company_name="Empresa Teste LTDA",
            case_id="CASE_123"
        )
        
        assert "João Silva" in message
        assert "Empresa Teste LTDA" in message
        assert "CASE_123" in message
        assert "aprovado" in message.lower()

    def test_format_rejection_message(self, notification_service):
        """Testa formatação de mensagem de rejeição."""
        rejection_reasons = ["Documento suspeito", "Informações inconsistentes"]
        
        message = notification_service._format_rejection_message(
            recipient_name="João Silva",
            company_name="Empresa Teste LTDA",
            case_id="CASE_123",
            rejection_reasons=rejection_reasons
        )
        
        assert "João Silva" in message
        assert "Empresa Teste LTDA" in message
        assert "CASE_123" in message
        assert "rejeitado" in message.lower()
        
        for reason in rejection_reasons:
            assert reason in message

    def test_validate_phone_number_valid(self, notification_service):
        """Testa validação de números de telefone válidos."""
        valid_phones = [
            "+5511999999999",
            "+551199999999",
            "+5511999999999",
            "5511999999999"
        ]
        
        for phone in valid_phones:
            assert notification_service._validate_phone_number(phone) is True

    def test_validate_phone_number_invalid(self, notification_service):
        """Testa validação de números de telefone inválidos."""
        invalid_phones = [
            "123",
            "invalid_phone",
            "",
            None,
            "+123",
            "11999999999"  # Sem código do país
        ]
        
        for phone in invalid_phones:
            assert notification_service._validate_phone_number(phone) is False

    @pytest.mark.asyncio
    async def test_send_notification_with_invalid_phone(self, notification_service):
        """Testa envio com número de telefone inválido."""
        result = await notification_service.send_custom_message(
            recipient_phone="invalid_phone",
            message="Test message"
        )
        
        assert result["success"] is False
        assert "Número de telefone inválido" in result["error"]

    @pytest.mark.asyncio
    async def test_send_notification_with_empty_message(self, notification_service):
        """Testa envio com mensagem vazia."""
        result = await notification_service.send_custom_message(
            recipient_phone="+5511999999999",
            message=""
        )
        
        assert result["success"] is False
        assert "Mensagem não pode estar vazia" in result["error"]

    @pytest.mark.asyncio
    async def test_notification_retry_mechanism(self, notification_service):
        """Testa mecanismo de retry em caso de falha."""
        # Simula falha seguida de sucesso
        notification_service.twilio_client.send_whatsapp_message.side_effect = [
            {"success": False, "error": "Temporary failure"},
            {"success": True, "message_sid": "test_sid"}
        ]
        
        result = await notification_service.send_custom_message(
            recipient_phone="+5511999999999",
            message="Test message"
        )
        
        # Deve ter tentado duas vezes e sucedido na segunda
        assert result["success"] is True
        assert notification_service.twilio_client.send_whatsapp_message.call_count == 2

    @pytest.mark.asyncio
    async def test_notification_max_retries_exceeded(self, notification_service):
        """Testa quando o máximo de tentativas é excedido."""
        # Simula falhas consecutivas
        notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": False,
            "error": "Persistent failure"
        }
        
        result = await notification_service.send_custom_message(
            recipient_phone="+5511999999999",
            message="Test message"
        )
        
        assert result["success"] is False
        assert "Máximo de tentativas excedido" in result["error"]

    def test_message_length_validation(self, notification_service):
        """Testa validação do comprimento da mensagem."""
        # Mensagem muito longa (> 1600 caracteres)
        long_message = "A" * 1601
        
        is_valid = notification_service._validate_message_length(long_message)
        assert is_valid is False
        
        # Mensagem de tamanho válido
        valid_message = "A" * 1000
        is_valid = notification_service._validate_message_length(valid_message)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_send_notification_with_long_message(self, notification_service):
        """Testa envio com mensagem muito longa."""
        long_message = "A" * 1601
        
        result = await notification_service.send_custom_message(
            recipient_phone="+5511999999999",
            message=long_message
        )
        
        assert result["success"] is False
        assert "Mensagem muito longa" in result["error"]

    def test_sanitize_message_content(self, notification_service):
        """Testa sanitização do conteúdo da mensagem."""
        test_cases = [
            ("Mensagem normal", "Mensagem normal"),
            ("Mensagem com\nemojis 😀", "Mensagem com\nemojis 😀"),
            ("Mensagem com caracteres especiais: @#$%", "Mensagem com caracteres especiais: @#$%"),
        ]
        
        for input_message, expected in test_cases:
            result = notification_service._sanitize_message(input_message)
            assert result == expected

    @pytest.mark.asyncio
    async def test_notification_logging(self, notification_service, caplog):
        """Testa logging das notificações."""
        import logging
        
        with caplog.at_level(logging.INFO):
            await notification_service.send_custom_message(
                recipient_phone="+5511999999999",
                message="Test message"
            )
            
            assert "Enviando notificação" in caplog.text
            assert "+5511999999999" in caplog.text

    @pytest.mark.asyncio
    async def test_notification_error_logging(self, notification_service, caplog):
        """Testa logging de erros nas notificações."""
        import logging
        
        # Configura falha
        notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": False,
            "error": "Test error"
        }
        
        with caplog.at_level(logging.ERROR):
            await notification_service.send_custom_message(
                recipient_phone="+5511999999999",
                message="Test message"
            )
            
            assert "Erro ao enviar notificação" in caplog.text
            assert "Test error" in caplog.text

    def test_format_phone_number(self, notification_service):
        """Testa formatação de números de telefone."""
        test_cases = [
            ("5511999999999", "+5511999999999"),
            ("+5511999999999", "+5511999999999"),
            ("11999999999", "+5511999999999"),  # Adiciona código do país
        ]
        
        for input_phone, expected in test_cases:
            result = notification_service._format_phone_number(input_phone)
            assert result == expected

    @pytest.mark.asyncio
    async def test_batch_notifications(self, notification_service):
        """Testa envio de notificações em lote."""
        recipients = [
            {"phone": "+5511999999999", "name": "João"},
            {"phone": "+5511888888888", "name": "Maria"},
            {"phone": "+5511777777777", "name": "Pedro"}
        ]
        
        results = await notification_service.send_batch_notifications(
            recipients=recipients,
            message_template="Olá {name}, sua solicitação foi processada.",
            case_id="BATCH_001"
        )
        
        assert len(results) == 3
        assert all(result["success"] for result in results)

    @pytest.mark.asyncio
    async def test_notification_rate_limiting(self, notification_service):
        """Testa limitação de taxa de envio."""
        # Simula múltiplas notificações rápidas
        tasks = []
        for i in range(10):
            task = notification_service.send_custom_message(
                recipient_phone=f"+551199999999{i}",
                message=f"Message {i}"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Todas devem ter sido enviadas (rate limiting interno do Twilio)
        assert len(results) == 10
        assert all(result["success"] for result in results)

    def test_message_template_rendering(self, notification_service):
        """Testa renderização de templates de mensagem."""
        template = "Olá {name}, sua empresa {company} tem pendências no caso {case_id}."
        variables = {
            "name": "João Silva",
            "company": "Empresa Teste LTDA",
            "case_id": "CASE_123"
        }
        
        result = notification_service._render_message_template(template, variables)
        
        assert "João Silva" in result
        assert "Empresa Teste LTDA" in result
        assert "CASE_123" in result
        assert "{" not in result  # Não deve ter variáveis não substituídas 