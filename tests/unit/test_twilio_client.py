"""
Pruebas unitarias para TwilioClient.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from twilio.base.exceptions import TwilioRestException

from src.integrations.twilio_client import TwilioClient


class TestTwilioClient:
    """Pruebas para la clase TwilioClient."""

    @pytest.fixture
    def twilio_client(self, mock_env_vars):
        """Fixture para crear una instancia de TwilioClient."""
        with patch('src.integrations.twilio_client.Client') as mock_twilio:
            mock_client = Mock()
            mock_twilio.return_value = mock_client
            return TwilioClient()

    @pytest.fixture
    def sample_message_data(self):
        """Dados de exemplo para mensagem WhatsApp."""
        return {
            "to": "+5511999999999",
            "message": "Olá! Seu documento foi aprovado.",
            "media_url": None
        }

    @pytest.mark.asyncio
    async def test_send_whatsapp_message_success(self, twilio_client, sample_message_data):
        """Testa envio bem-sucedido de mensagem WhatsApp."""
        # Mock da resposta do Twilio
        mock_message = Mock()
        mock_message.sid = "SM123456789"
        mock_message.status = "sent"
        mock_message.error_code = None
        mock_message.error_message = None
        
        twilio_client.client.messages.create.return_value = mock_message
        
        result = await twilio_client.send_whatsapp_message(
            to=sample_message_data["to"],
            message=sample_message_data["message"]
        )
        
        assert result["success"] is True
        assert result["message_sid"] == "SM123456789"
        assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_whatsapp_message_with_media(self, twilio_client):
        """Testa envio bem-sucedido de mensagem WhatsApp com mídia."""
        mock_message = Mock()
        mock_message.sid = "SM123456789"
        mock_message.status = "sent"
        mock_message.error_code = None
        mock_message.error_message = None
        
        twilio_client.client.messages.create.return_value = mock_message
        
        result = await twilio_client.send_whatsapp_message(
            to="+5511999999999",
            message="Documento anexado",
            media_url="https://example.com/document.pdf"
        )
        
        assert result["success"] is True
        assert result["message_sid"] == "SM123456789"
        
        # Verifica se foi chamado com mídia
        call_args = twilio_client.client.messages.create.call_args
        assert "media_url" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_send_whatsapp_message_failure(self, twilio_client):
        """Testa falha no envio de mensagem WhatsApp."""
        # Mock de erro do Twilio
        twilio_client.client.messages.create.side_effect = TwilioRestException(
            status=400,
            uri="https://api.twilio.com/test",
            msg="Invalid phone number"
        )
        
        result = await twilio_client.send_whatsapp_message(
            to="invalid_number",
            message="Test message"
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "Invalid phone number" in result["error"]

    @pytest.mark.asyncio
    async def test_send_sms_message_success(self, twilio_client):
        """Testa envio bem-sucedido de SMS."""
        mock_message = Mock()
        mock_message.sid = "SM987654321"
        mock_message.status = "sent"
        mock_message.error_code = None
        mock_message.error_message = None
        
        twilio_client.client.messages.create.return_value = mock_message
        
        result = await twilio_client.send_sms_message(
            to="+5511999999999",
            message="Seu código de verificação é: 123456"
        )
        
        assert result["success"] is True
        assert result["message_sid"] == "SM987654321"
        assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_sms_message_failure(self, twilio_client):
        """Testa falha no envio de SMS."""
        twilio_client.client.messages.create.side_effect = TwilioRestException(
            status=400,
            uri="https://api.twilio.com/test",
            msg="Message body is required"
        )
        
        result = await twilio_client.send_sms_message(
            to="+5511999999999",
            message=""
        )
        
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_message_status_success(self, twilio_client):
        """Testa busca bem-sucedida de status de mensagem."""
        mock_message = Mock()
        mock_message.sid = "SM123456789"
        mock_message.status = "delivered"
        mock_message.error_code = None
        mock_message.error_message = None
        mock_message.date_sent = "2024-01-01T10:00:00Z"
        mock_message.date_updated = "2024-01-01T10:01:00Z"
        
        twilio_client.client.messages.get.return_value = mock_message
        
        result = await twilio_client.get_message_status("SM123456789")
        
        assert result["message_sid"] == "SM123456789"
        assert result["status"] == "delivered"
        assert result["error_code"] is None

    @pytest.mark.asyncio
    async def test_get_message_status_not_found(self, twilio_client):
        """Testa busca de mensagem não encontrada."""
        twilio_client.client.messages.get.side_effect = TwilioRestException(
            status=404,
            uri="https://api.twilio.com/test",
            msg="Message not found"
        )
        
        result = await twilio_client.get_message_status("SM_NONEXISTENT")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_send_notification_pendencia(self, twilio_client):
        """Testa envio de notificação de pendência."""
        mock_message = Mock()
        mock_message.sid = "SM123456789"
        mock_message.status = "sent"
        
        twilio_client.client.messages.create.return_value = mock_message
        
        result = await twilio_client.send_notification_pendencia(
            to="+5511999999999",
            company_name="Empresa Teste LTDA",
            missing_documents=["RG", "Comprovante de endereço"],
            case_id="CASE_123"
        )
        
        assert result["success"] is True
        assert result["message_sid"] == "SM123456789"
        
        # Verifica se a mensagem contém os dados esperados
        call_args = twilio_client.client.messages.create.call_args
        message_body = call_args.kwargs["body"]
        assert "Empresa Teste LTDA" in message_body
        assert "RG" in message_body
        assert "Comprovante de endereço" in message_body
        assert "CASE_123" in message_body

    @pytest.mark.asyncio
    async def test_send_notification_aprovacao(self, twilio_client):
        """Testa envio de notificação de aprovação."""
        mock_message = Mock()
        mock_message.sid = "SM123456789"
        mock_message.status = "sent"
        
        twilio_client.client.messages.create.return_value = mock_message
        
        result = await twilio_client.send_notification_aprovacao(
            to="+5511999999999",
            company_name="Empresa Teste LTDA",
            case_id="CASE_123"
        )
        
        assert result["success"] is True
        
        # Verifica se a mensagem contém os dados esperados
        call_args = twilio_client.client.messages.create.call_args
        message_body = call_args.kwargs["body"]
        assert "aprovado" in message_body.lower()
        assert "Empresa Teste LTDA" in message_body

    @pytest.mark.asyncio
    async def test_send_notification_rejeicao(self, twilio_client):
        """Testa envio de notificação de rejeição."""
        mock_message = Mock()
        mock_message.sid = "SM123456789"
        mock_message.status = "sent"
        
        twilio_client.client.messages.create.return_value = mock_message
        
        result = await twilio_client.send_notification_rejeicao(
            to="+5511999999999",
            company_name="Empresa Teste LTDA",
            reasons=["Documento ilegível", "Informações inconsistentes"],
            case_id="CASE_123"
        )
        
        assert result["success"] is True
        
        # Verifica se a mensagem contém os dados esperados
        call_args = twilio_client.client.messages.create.call_args
        message_body = call_args.kwargs["body"]
        assert "rejeitado" in message_body.lower()
        assert "Documento ilegível" in message_body
        assert "Informações inconsistentes" in message_body

    @pytest.mark.asyncio
    async def test_send_custom_message(self, twilio_client):
        """Testa envio de mensagem personalizada."""
        mock_message = Mock()
        mock_message.sid = "SM123456789"
        mock_message.status = "sent"
        
        twilio_client.client.messages.create.return_value = mock_message
        
        template_vars = {
            "company_name": "Empresa Teste LTDA",
            "case_id": "CASE_123",
            "deadline": "5 dias úteis"
        }
        
        result = await twilio_client.send_custom_message(
            to="+5511999999999",
            template="Olá {company_name}! Prazo para envio: {deadline}. Caso: {case_id}",
            template_vars=template_vars
        )
        
        assert result["success"] is True
        
        # Verifica se as variáveis foram substituídas
        call_args = twilio_client.client.messages.create.call_args
        message_body = call_args.kwargs["body"]
        assert "Empresa Teste LTDA" in message_body
        assert "5 dias úteis" in message_body
        assert "CASE_123" in message_body

    @pytest.mark.asyncio
    async def test_validate_phone_number_valid(self, twilio_client):
        """Testa validação de número de telefone válido."""
        valid_numbers = [
            "+5511999999999",
            "+551199999999",
            "5511999999999",
            "11999999999"
        ]
        
        for number in valid_numbers:
            assert twilio_client._validate_phone_number(number) is True

    @pytest.mark.asyncio
    async def test_validate_phone_number_invalid(self, twilio_client):
        """Testa validação de número de telefone inválido."""
        invalid_numbers = [
            "123",
            "abc123",
            "",
            None,
            "+55119999",  # Muito curto
            "+551199999999999999"  # Muito longo
        ]
        
        for number in invalid_numbers:
            assert twilio_client._validate_phone_number(number) is False

    def test_format_phone_number(self, twilio_client):
        """Testa formatação de número de telefone."""
        test_cases = [
            ("11999999999", "+5511999999999"),
            ("5511999999999", "+5511999999999"),
            ("+5511999999999", "+5511999999999"),
            ("(11) 99999-9999", "+5511999999999")
        ]
        
        for input_number, expected in test_cases:
            result = twilio_client._format_phone_number(input_number)
            assert result == expected

    def test_validate_message_content(self, twilio_client):
        """Testa validação de conteúdo de mensagem."""
        # Mensagem válida
        valid_message = "Esta é uma mensagem de teste válida."
        assert twilio_client._validate_message_content(valid_message) is True
        
        # Mensagem muito longa (> 1600 caracteres)
        long_message = "A" * 1601
        assert twilio_client._validate_message_content(long_message) is False
        
        # Mensagem vazia
        assert twilio_client._validate_message_content("") is False
        assert twilio_client._validate_message_content(None) is False

    def test_sanitize_message_content(self, twilio_client):
        """Testa sanitização de conteúdo de mensagem."""
        test_cases = [
            ("Mensagem normal", "Mensagem normal"),
            ("Mensagem\ncom\nquebras", "Mensagem com quebras"),
            ("Mensagem    com    espaços", "Mensagem com espaços"),
            ("Mensagem\tcom\ttabs", "Mensagem com tabs")
        ]
        
        for input_msg, expected in test_cases:
            result = twilio_client._sanitize_message_content(input_msg)
            assert result == expected

    @pytest.mark.asyncio
    async def test_send_bulk_messages_success(self, twilio_client):
        """Testa envio em lote bem-sucedido."""
        mock_message = Mock()
        mock_message.sid = "SM123456789"
        mock_message.status = "sent"
        
        twilio_client.client.messages.create.return_value = mock_message
        
        messages = [
            {"to": "+5511999999999", "message": "Mensagem 1"},
            {"to": "+5511888888888", "message": "Mensagem 2"},
            {"to": "+5511777777777", "message": "Mensagem 3"}
        ]
        
        results = await twilio_client.send_bulk_messages(messages)
        
        assert len(results) == 3
        assert all(result["success"] for result in results)
        assert twilio_client.client.messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_send_bulk_messages_partial_failure(self, twilio_client):
        """Testa envio em lote com falhas parciais."""
        def mock_create(**kwargs):
            if "999999999" in kwargs["to"]:
                # Sucesso para este número
                mock_message = Mock()
                mock_message.sid = "SM123456789"
                mock_message.status = "sent"
                return mock_message
            else:
                # Falha para outros números
                raise TwilioRestException(
                    status=400,
                    uri="https://api.twilio.com/test",
                    msg="Invalid number"
                )
        
        twilio_client.client.messages.create.side_effect = mock_create
        
        messages = [
            {"to": "+5511999999999", "message": "Mensagem 1"},  # Sucesso
            {"to": "+5511888888888", "message": "Mensagem 2"},  # Falha
        ]
        
        results = await twilio_client.send_bulk_messages(messages)
        
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False

    @pytest.mark.asyncio
    async def test_get_delivery_report(self, twilio_client):
        """Testa relatório de entrega de mensagens."""
        message_sids = ["SM123", "SM456", "SM789"]
        
        def mock_get(sid):
            mock_message = Mock()
            mock_message.sid = sid
            mock_message.status = "delivered" if sid == "SM123" else "failed"
            mock_message.error_code = None if sid == "SM123" else "30008"
            return mock_message
        
        twilio_client.client.messages.get.side_effect = mock_get
        
        report = await twilio_client.get_delivery_report(message_sids)
        
        assert len(report) == 3
        assert report[0]["status"] == "delivered"
        assert report[1]["status"] == "failed"
        assert report[2]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, twilio_client):
        """Testa controle de rate limiting."""
        # Simula rate limit do Twilio
        twilio_client.client.messages.create.side_effect = TwilioRestException(
            status=429,
            uri="https://api.twilio.com/test",
            msg="Too Many Requests"
        )
        
        result = await twilio_client.send_whatsapp_message(
            to="+5511999999999",
            message="Test message"
        )
        
        assert result["success"] is False
        assert "rate limit" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, twilio_client):
        """Testa tratamento de erro de conexão."""
        twilio_client.client.messages.create.side_effect = ConnectionError("Network error")
        
        result = await twilio_client.send_whatsapp_message(
            to="+5511999999999",
            message="Test message"
        )
        
        assert result["success"] is False
        assert "connection" in result["error"].lower()

    def test_build_whatsapp_number(self, twilio_client):
        """Testa construção de número WhatsApp."""
        phone_number = "+5511999999999"
        whatsapp_number = twilio_client._build_whatsapp_number(phone_number)
        
        assert whatsapp_number == "whatsapp:+5511999999999"

    def test_extract_error_details(self, twilio_client):
        """Testa extração de detalhes de erro."""
        twilio_error = TwilioRestException(
            status=400,
            uri="https://api.twilio.com/test",
            msg="Invalid phone number format"
        )
        
        error_details = twilio_client._extract_error_details(twilio_error)
        
        assert error_details["status_code"] == 400
        assert error_details["message"] == "Invalid phone number format"
        assert error_details["uri"] == "https://api.twilio.com/test"

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, twilio_client):
        """Testa mecanismo de retry."""
        call_count = 0
        
        def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TwilioRestException(
                    status=500,
                    uri="https://api.twilio.com/test",
                    msg="Internal Server Error"
                )
            else:
                mock_message = Mock()
                mock_message.sid = "SM123456789"
                mock_message.status = "sent"
                return mock_message
        
        twilio_client.client.messages.create.side_effect = mock_create
        
        result = await twilio_client.send_whatsapp_message_with_retry(
            to="+5511999999999",
            message="Test message",
            max_retries=3
        )
        
        assert result["success"] is True
        assert call_count == 3  # Falhou 2 vezes, sucesso na 3ª

    def test_message_template_rendering(self, twilio_client):
        """Testa renderização de templates de mensagem."""
        template = "Olá {name}! Seu pedido {order_id} está {status}."
        variables = {
            "name": "João",
            "order_id": "12345",
            "status": "aprovado"
        }
        
        rendered = twilio_client._render_template(template, variables)
        
        assert rendered == "Olá João! Seu pedido 12345 está aprovado."

    def test_message_template_missing_variables(self, twilio_client):
        """Testa template com variáveis ausentes."""
        template = "Olá {name}! Seu pedido {order_id} está {status}."
        variables = {
            "name": "João",
            "order_id": "12345"
            # status ausente
        }
        
        rendered = twilio_client._render_template(template, variables)
        
        # Deve manter a variável não substituída
        assert "{status}" in rendered
        assert "João" in rendered
        assert "12345" in rendered