"""
Pruebas unitarias para ErrorNotificationService.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.services.error_notification_service import ErrorNotificationService


class TestErrorNotificationService:
    """Pruebas para la clase ErrorNotificationService."""

    @pytest.fixture
    def error_notification_service(self, mock_env_vars):
        """Fixture para crear una instancia de ErrorNotificationService."""
        with patch('src.services.error_notification_service.TwilioClient') as mock_twilio, \
             patch('src.services.error_notification_service.DatabaseService') as mock_db:
            
            mock_twilio_instance = Mock()
            mock_db_instance = Mock()
            mock_twilio.return_value = mock_twilio_instance
            mock_db.return_value = mock_db_instance
            
            service = ErrorNotificationService()
            service.twilio_client = mock_twilio_instance
            service.database_service = mock_db_instance
            
            return service

    @pytest.fixture
    def sample_error_data(self):
        """Dados de exemplo para erro."""
        return {
            "error_type": "API_ERROR",
            "severity": "HIGH",
            "api_name": "CNPJ_API",
            "error_message": "Connection timeout",
            "context": {
                "cnpj": "11.222.333/0001-81",
                "case_id": "CASE_123",
                "retry_count": 3
            },
            "timestamp": datetime.now().isoformat(),
            "should_retry": False
        }

    @pytest.mark.asyncio
    async def test_notify_error_critical_severity(self, error_notification_service, sample_error_data):
        """Testa notificação de erro com severidade crítica."""
        sample_error_data["severity"] = "CRITICAL"
        
        # Mock do envio de notificação
        error_notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": True,
            "message_sid": "SM123456789"
        }
        
        # Mock do log no banco
        error_notification_service.database_service.add_processing_log.return_value = {
            "id": "log_123"
        }
        
        result = await error_notification_service.notify_error(sample_error_data)
        
        assert result["notification_sent"] is True
        assert result["message_sid"] == "SM123456789"
        
        # Verifica se foi chamado o Twilio
        error_notification_service.twilio_client.send_whatsapp_message.assert_called_once()
        
        # Verifica se foi logado no banco
        error_notification_service.database_service.add_processing_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_error_low_severity_no_notification(self, error_notification_service, sample_error_data):
        """Testa que erros de baixa severidade não geram notificação."""
        sample_error_data["severity"] = "LOW"
        
        result = await error_notification_service.notify_error(sample_error_data)
        
        assert result["notification_sent"] is False
        assert result["reason"] == "Severity too low for notification"
        
        # Verifica que não foi chamado o Twilio
        error_notification_service.twilio_client.send_whatsapp_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_error_rate_limited(self, error_notification_service, sample_error_data):
        """Testa rate limiting de notificações."""
        # Simula que já foi enviada uma notificação recentemente
        with patch.object(error_notification_service, '_is_rate_limited', return_value=True):
            result = await error_notification_service.notify_error(sample_error_data)
            
            assert result["notification_sent"] is False
            assert result["reason"] == "Rate limited"

    @pytest.mark.asyncio
    async def test_notify_error_twilio_failure(self, error_notification_service, sample_error_data):
        """Testa falha no envio via Twilio."""
        sample_error_data["severity"] = "CRITICAL"
        
        # Mock de falha no Twilio
        error_notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": False,
            "error": "Invalid phone number"
        }
        
        result = await error_notification_service.notify_error(sample_error_data)
        
        assert result["notification_sent"] is False
        assert "Invalid phone number" in result["error"]

    @pytest.mark.asyncio
    async def test_notify_api_outage(self, error_notification_service):
        """Testa notificação de indisponibilidade de API."""
        outage_data = {
            "api_name": "CNPJ_API",
            "error_count": 10,
            "time_window": "5 minutes",
            "last_error": "Connection refused",
            "affected_cases": ["CASE_123", "CASE_124", "CASE_125"]
        }
        
        error_notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": True,
            "message_sid": "SM987654321"
        }
        
        result = await error_notification_service.notify_api_outage(outage_data)
        
        assert result["success"] is True
        assert result["message_sid"] == "SM987654321"
        
        # Verifica se a mensagem contém informações da indisponibilidade
        call_args = error_notification_service.twilio_client.send_whatsapp_message.call_args
        message = call_args.kwargs["message"]
        assert "CNPJ_API" in message
        assert "10" in message
        assert "5 minutes" in message

    @pytest.mark.asyncio
    async def test_notify_system_recovery(self, error_notification_service):
        """Testa notificação de recuperação do sistema."""
        recovery_data = {
            "api_name": "CNPJ_API",
            "downtime_duration": "15 minutes",
            "recovery_time": datetime.now().isoformat(),
            "pending_cases": 5
        }
        
        error_notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": True,
            "message_sid": "SM111222333"
        }
        
        result = await error_notification_service.notify_system_recovery(recovery_data)
        
        assert result["success"] is True
        
        # Verifica se a mensagem contém informações da recuperação
        call_args = error_notification_service.twilio_client.send_whatsapp_message.call_args
        message = call_args.kwargs["message"]
        assert "recuperado" in message.lower()
        assert "CNPJ_API" in message
        assert "15 minutes" in message

    @pytest.mark.asyncio
    async def test_send_daily_error_summary(self, error_notification_service):
        """Testa envio de resumo diário de erros."""
        summary_data = {
            "date": "2024-01-01",
            "total_errors": 25,
            "critical_errors": 3,
            "high_errors": 8,
            "medium_errors": 10,
            "low_errors": 4,
            "top_apis": [
                {"api": "CNPJ_API", "errors": 15},
                {"api": "PIPEFY_API", "errors": 7},
                {"api": "TWILIO_API", "errors": 3}
            ],
            "resolved_issues": 20,
            "pending_issues": 5
        }
        
        error_notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": True,
            "message_sid": "SM444555666"
        }
        
        result = await error_notification_service.send_daily_error_summary(summary_data)
        
        assert result["success"] is True
        
        # Verifica se a mensagem contém estatísticas
        call_args = error_notification_service.twilio_client.send_whatsapp_message.call_args
        message = call_args.kwargs["message"]
        assert "25" in message  # Total de erros
        assert "CNPJ_API" in message  # API com mais erros

    @pytest.mark.asyncio
    async def test_notify_circuit_breaker_opened(self, error_notification_service):
        """Testa notificação de circuit breaker aberto."""
        circuit_data = {
            "api_name": "CNPJ_API",
            "failure_threshold": 5,
            "failure_count": 5,
            "timeout_duration": "30 seconds",
            "last_error": "Connection timeout"
        }
        
        error_notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": True,
            "message_sid": "SM777888999"
        }
        
        result = await error_notification_service.notify_circuit_breaker_opened(circuit_data)
        
        assert result["success"] is True
        
        # Verifica se a mensagem contém informações do circuit breaker
        call_args = error_notification_service.twilio_client.send_whatsapp_message.call_args
        message = call_args.kwargs["message"]
        assert "circuit breaker" in message.lower()
        assert "CNPJ_API" in message
        assert "30 seconds" in message

    @pytest.mark.asyncio
    async def test_notify_circuit_breaker_closed(self, error_notification_service):
        """Testa notificação de circuit breaker fechado."""
        circuit_data = {
            "api_name": "CNPJ_API",
            "recovery_time": datetime.now().isoformat(),
            "test_requests_successful": 3
        }
        
        error_notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": True,
            "message_sid": "SM000111222"
        }
        
        result = await error_notification_service.notify_circuit_breaker_closed(circuit_data)
        
        assert result["success"] is True
        
        # Verifica se a mensagem contém informações da recuperação
        call_args = error_notification_service.twilio_client.send_whatsapp_message.call_args
        message = call_args.kwargs["message"]
        assert "recuperado" in message.lower()
        assert "CNPJ_API" in message

    def test_format_error_message_api_error(self, error_notification_service, sample_error_data):
        """Testa formatação de mensagem para erro de API."""
        message = error_notification_service._format_error_message(sample_error_data)
        
        assert "🚨 ERRO CRÍTICO" in message or "⚠️ ERRO" in message
        assert "CNPJ_API" in message
        assert "Connection timeout" in message
        assert "CASE_123" in message

    def test_format_error_message_database_error(self, error_notification_service):
        """Testa formatação de mensagem para erro de banco."""
        error_data = {
            "error_type": "DATABASE_ERROR",
            "severity": "HIGH",
            "api_name": "SUPABASE",
            "error_message": "Connection pool exhausted",
            "context": {"table": "case_tracking", "operation": "insert"},
            "timestamp": datetime.now().isoformat()
        }
        
        message = error_notification_service._format_error_message(error_data)
        
        assert "banco de dados" in message.lower()
        assert "SUPABASE" in message
        assert "Connection pool exhausted" in message

    def test_determine_notification_priority(self, error_notification_service):
        """Testa determinação de prioridade de notificação."""
        test_cases = [
            ("CRITICAL", True),
            ("HIGH", True),
            ("MEDIUM", False),
            ("LOW", False)
        ]
        
        for severity, should_notify in test_cases:
            result = error_notification_service._should_send_notification(severity)
            assert result == should_notify

    def test_is_rate_limited(self, error_notification_service):
        """Testa verificação de rate limiting."""
        api_name = "CNPJ_API"
        
        # Primeira chamada - não deve estar limitada
        assert error_notification_service._is_rate_limited(api_name) is False
        
        # Registra uma notificação
        error_notification_service._record_notification(api_name)
        
        # Segunda chamada imediata - deve estar limitada
        assert error_notification_service._is_rate_limited(api_name) is True

    def test_record_notification(self, error_notification_service):
        """Testa registro de notificação."""
        api_name = "CNPJ_API"
        
        # Registra notificação
        error_notification_service._record_notification(api_name)
        
        # Verifica se foi registrada
        assert api_name in error_notification_service.notification_history
        assert len(error_notification_service.notification_history[api_name]) == 1

    def test_cleanup_old_notifications(self, error_notification_service):
        """Testa limpeza de notificações antigas."""
        api_name = "CNPJ_API"
        
        # Adiciona notificação antiga (mais de 1 hora)
        old_time = datetime.now() - timedelta(hours=2)
        error_notification_service.notification_history[api_name] = [old_time]
        
        # Adiciona notificação recente
        recent_time = datetime.now() - timedelta(minutes=10)
        error_notification_service.notification_history[api_name].append(recent_time)
        
        # Executa limpeza
        error_notification_service._cleanup_old_notifications()
        
        # Verifica se apenas a notificação recente permanece
        assert len(error_notification_service.notification_history[api_name]) == 1
        assert error_notification_service.notification_history[api_name][0] == recent_time

    def test_get_notification_recipients(self, error_notification_service):
        """Testa obtenção de destinatários de notificação."""
        recipients = error_notification_service._get_notification_recipients()
        
        assert isinstance(recipients, list)
        assert len(recipients) > 0
        # Verifica se contém números de telefone válidos
        for recipient in recipients:
            assert recipient.startswith("+55") or recipient.startswith("55")

    def test_validate_error_data(self, error_notification_service, sample_error_data):
        """Testa validação de dados de erro."""
        # Dados válidos
        assert error_notification_service._validate_error_data(sample_error_data) is True
        
        # Dados inválidos - campos obrigatórios ausentes
        invalid_data = {
            "error_type": "API_ERROR"
            # severity ausente
        }
        assert error_notification_service._validate_error_data(invalid_data) is False

    @pytest.mark.asyncio
    async def test_batch_notify_errors(self, error_notification_service):
        """Testa notificação em lote de erros."""
        errors = [
            {
                "error_type": "API_ERROR",
                "severity": "CRITICAL",
                "api_name": "CNPJ_API",
                "error_message": "Error 1"
            },
            {
                "error_type": "API_ERROR", 
                "severity": "HIGH",
                "api_name": "PIPEFY_API",
                "error_message": "Error 2"
            }
        ]
        
        error_notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": True,
            "message_sid": "SM123456789"
        }
        
        results = await error_notification_service.batch_notify_errors(errors)
        
        assert len(results) == 2
        assert all(result["notification_sent"] for result in results)

    @pytest.mark.asyncio
    async def test_get_error_statistics(self, error_notification_service):
        """Testa obtenção de estatísticas de erro."""
        # Mock do banco de dados
        error_notification_service.database_service.get_error_statistics.return_value = {
            "total_errors": 100,
            "critical_errors": 5,
            "high_errors": 15,
            "apis_with_errors": ["CNPJ_API", "PIPEFY_API"],
            "most_common_error": "Connection timeout"
        }
        
        stats = await error_notification_service.get_error_statistics()
        
        assert stats["total_errors"] == 100
        assert stats["critical_errors"] == 5
        assert "CNPJ_API" in stats["apis_with_errors"]

    def test_format_api_outage_message(self, error_notification_service):
        """Testa formatação de mensagem de indisponibilidade."""
        outage_data = {
            "api_name": "CNPJ_API",
            "error_count": 10,
            "time_window": "5 minutes",
            "affected_cases": ["CASE_123", "CASE_124"]
        }
        
        message = error_notification_service._format_api_outage_message(outage_data)
        
        assert "indisponível" in message.lower()
        assert "CNPJ_API" in message
        assert "10" in message
        assert "5 minutes" in message

    def test_format_recovery_message(self, error_notification_service):
        """Testa formatação de mensagem de recuperação."""
        recovery_data = {
            "api_name": "CNPJ_API",
            "downtime_duration": "15 minutes",
            "pending_cases": 5
        }
        
        message = error_notification_service._format_recovery_message(recovery_data)
        
        assert "recuperado" in message.lower()
        assert "CNPJ_API" in message
        assert "15 minutes" in message
        assert "5" in message

    @pytest.mark.asyncio
    async def test_emergency_notification(self, error_notification_service):
        """Testa notificação de emergência."""
        emergency_data = {
            "title": "Sistema Crítico Indisponível",
            "description": "Falha total no sistema de processamento",
            "severity": "EMERGENCY",
            "affected_services": ["Document Processing", "CNPJ Validation"],
            "estimated_recovery": "30 minutes"
        }
        
        error_notification_service.twilio_client.send_whatsapp_message.return_value = {
            "success": True,
            "message_sid": "SM_EMERGENCY"
        }
        
        result = await error_notification_service.send_emergency_notification(emergency_data)
        
        assert result["success"] is True
        
        # Verifica se a mensagem contém informações de emergência
        call_args = error_notification_service.twilio_client.send_whatsapp_message.call_args
        message = call_args.kwargs["message"]
        assert "🚨" in message  # Emoji de emergência
        assert "EMERGÊNCIA" in message.upper()
        assert "Sistema Crítico Indisponível" in message