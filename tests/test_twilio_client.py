"""
Tests unitarios para el cliente de Twilio WhatsApp.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from twilio.base.exceptions import TwilioException

from src.integrations.twilio_client import TwilioClient, TwilioAPIError

class TestTwilioClient:
    """Tests para el cliente de Twilio."""
    
    @pytest.fixture
    def mock_twilio_client(self):
        """Fixture del cliente Twilio mockeado."""
        with patch('src.integrations.twilio_client.Client') as mock_client_class:
            with patch('src.integrations.twilio_client.settings') as mock_settings:
                # Configurar settings mock
                mock_settings.TWILIO_ACCOUNT_SID = "test_account_sid"
                mock_settings.TWILIO_AUTH_TOKEN = "test_auth_token"
                mock_settings.TWILIO_WHATSAPP_NUMBER = "+17245586619"
                
                # Configurar cliente mock
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                # Crear instancia del cliente
                client = TwilioClient()
                client.client = mock_client
                
                return client, mock_client
    
    @pytest.mark.asyncio
    async def test_send_whatsapp_message_success(self, mock_twilio_client):
        """Test envío exitoso de mensaje WhatsApp."""
        client, mock_client = mock_twilio_client
        
        # Mock da resposta do Twilio
        mock_message = Mock()
        mock_message.sid = "SM123456789"
        mock_message.status = "sent"
        mock_client.messages.create.return_value = mock_message
        
        # Executar
        result = await client.send_whatsapp_message(
            to_number="+5511999999999",
            message="Teste de mensagem"
        )
        
        # Verificar
        assert result["success"] is True
        assert result["message_sid"] == "SM123456789"
        assert result["status"] == "sent"
        assert result["to_number"] == "+5511999999999"
        assert result["message_body"] == "Teste de mensagem"
        assert result["error_code"] is None
        
        # Verificar chamada ao Twilio
        mock_client.messages.create.assert_called_once_with(
            body="Teste de mensagem",
            from_="whatsapp:+17245586619",
            to="whatsapp:+5511999999999"
        )
    
    @pytest.mark.asyncio
    async def test_send_whatsapp_message_with_media(self, mock_twilio_client):
        """Test envío de mensaje WhatsApp com media."""
        client, mock_client = mock_twilio_client
        
        # Mock da resposta do Twilio
        mock_message = Mock()
        mock_message.sid = "SM987654321"
        mock_message.status = "sent"
        mock_client.messages.create.return_value = mock_message
        
        # Executar
        result = await client.send_whatsapp_message(
            to_number="+5511999999999",
            message="Mensagem com media",
            media_url="https://example.com/image.jpg"
        )
        
        # Verificar
        assert result["success"] is True
        assert result["message_sid"] == "SM987654321"
        
        # Verificar chamada com media
        mock_client.messages.create.assert_called_once_with(
            body="Mensagem com media",
            from_="whatsapp:+17245586619",
            to="whatsapp:+5511999999999",
            media_url=["https://example.com/image.jpg"]
        )
    
    @pytest.mark.asyncio
    async def test_send_whatsapp_message_format_number(self, mock_twilio_client):
        """Test formatação automática de número de telefone."""
        client, mock_client = mock_twilio_client
        
        # Mock da resposta do Twilio
        mock_message = Mock()
        mock_message.sid = "SM111222333"
        mock_message.status = "sent"
        mock_client.messages.create.return_value = mock_message
        
        # Executar com número sem +
        result = await client.send_whatsapp_message(
            to_number="5511999999999",  # Sem +
            message="Teste formatação"
        )
        
        # Verificar
        assert result["success"] is True
        assert result["to_number"] == "+5511999999999"  # Deve adicionar +
        
        # Verificar chamada com número formatado
        mock_client.messages.create.assert_called_once_with(
            body="Teste formatação",
            from_="whatsapp:+17245586619",
            to="whatsapp:+5511999999999"
        )
    
    @pytest.mark.asyncio
    async def test_send_whatsapp_message_twilio_error(self, mock_twilio_client):
        """Test manejo de erro do Twilio."""
        client, mock_client = mock_twilio_client
        
        # Mock erro do Twilio
        twilio_error = TwilioException("Invalid phone number")
        twilio_error.code = 21211
        mock_client.messages.create.side_effect = twilio_error
        
        # Executar
        result = await client.send_whatsapp_message(
            to_number="+5511999999999",
            message="Teste erro"
        )
        
        # Verificar
        assert result["success"] is False
        assert result["status"] == "failed"
        assert result["error_code"] == 21211
        assert "Invalid phone number" in result["error_message"]
        assert result["message_sid"] is None
    
    @pytest.mark.asyncio
    async def test_send_whatsapp_message_generic_error(self, mock_twilio_client):
        """Test manejo de erro genérico."""
        client, mock_client = mock_twilio_client
        
        # Mock erro genérico
        mock_client.messages.create.side_effect = Exception("Erro de conexão")
        
        # Executar
        result = await client.send_whatsapp_message(
            to_number="+5511999999999",
            message="Teste erro genérico"
        )
        
        # Verificar
        assert result["success"] is False
        assert result["status"] == "failed"
        assert result["error_code"] == "UNKNOWN_ERROR"
        assert "Erro de conexão" in result["error_message"]
    
    @pytest.mark.asyncio
    async def test_send_blocking_issues_notification(self, mock_twilio_client):
        """Test envío de notificación de pendencias bloqueantes."""
        client, mock_client = mock_twilio_client
        
        # Mock da resposta do Twilio
        mock_message = Mock()
        mock_message.sid = "SM444555666"
        mock_message.status = "sent"
        mock_client.messages.create.return_value = mock_message
        
        # Executar
        result = await client.send_blocking_issues_notification(
            to_number="+5511999999999",
            company_name="Empresa Teste",
            case_id="CASE-123",
            blocking_issues=["Documento A ausente", "Documento B vencido"],
            cnpj="12.345.678/0001-99"
        )
        
        # Verificar
        assert result["success"] is True
        assert result["message_sid"] == "SM444555666"
        
        # Verificar que a mensagem foi criada
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        
        # Verificar conteúdo da mensagem
        message_body = call_args["body"]
        assert "PENDÊNCIAS BLOQUEANTES DETECTADAS" in message_body
        assert "Empresa Teste" in message_body
        assert "CASE-123" in message_body
        assert "12.345.678/0001-99" in message_body
        assert "Documento A ausente" in message_body
        assert "Documento B vencido" in message_body
    
    @pytest.mark.asyncio
    async def test_send_approval_notification(self, mock_twilio_client):
        """Test envío de notificación de aprobación."""
        client, mock_client = mock_twilio_client
        
        # Mock da resposta do Twilio
        mock_message = Mock()
        mock_message.sid = "SM777888999"
        mock_message.status = "sent"
        mock_client.messages.create.return_value = mock_message
        
        # Executar
        result = await client.send_approval_notification(
            to_number="+5511999999999",
            company_name="Empresa Aprovada",
            case_id="CASE-456",
            cnpj="98.765.432/0001-11"
        )
        
        # Verificar
        assert result["success"] is True
        assert result["message_sid"] == "SM777888999"
        
        # Verificar conteúdo da mensagem
        call_args = mock_client.messages.create.call_args[1]
        message_body = call_args["body"]
        assert "DOCUMENTAÇÃO APROVADA" in message_body
        assert "Empresa Aprovada" in message_body
        assert "CASE-456" in message_body
        assert "98.765.432/0001-11" in message_body
    
    @pytest.mark.asyncio
    async def test_get_message_status_success(self, mock_twilio_client):
        """Test obtenção de status de mensagem."""
        client, mock_client = mock_twilio_client
        
        # Mock da resposta do Twilio
        mock_message = Mock()
        mock_message.sid = "SM123456789"
        mock_message.status = "delivered"
        mock_message.date_created = None
        mock_message.date_sent = None
        mock_message.date_updated = None
        mock_message.error_code = None
        mock_message.error_message = None
        mock_message.price = "0.005"
        mock_message.price_unit = "USD"
        
        mock_client.messages.return_value.fetch.return_value = mock_message
        
        # Executar
        result = await client.get_message_status("SM123456789")
        
        # Verificar
        assert result["success"] is True
        assert result["message_sid"] == "SM123456789"
        assert result["status"] == "delivered"
        assert result["price"] == "0.005"
        assert result["price_unit"] == "USD"
        
        # Verificar chamada
        mock_client.messages.assert_called_once_with("SM123456789")
    
    @pytest.mark.asyncio
    async def test_get_message_status_error(self, mock_twilio_client):
        """Test erro ao obter status de mensagem."""
        client, mock_client = mock_twilio_client
        
        # Mock erro do Twilio
        mock_client.messages.return_value.fetch.side_effect = TwilioException("Message not found")
        
        # Executar
        result = await client.get_message_status("SM_INVALID")
        
        # Verificar
        assert result["success"] is False
        assert "Message not found" in result["error"]
    
    def test_generate_blocking_issues_message(self, mock_twilio_client):
        """Test geração de mensagem para pendencias bloqueantes."""
        client, _ = mock_twilio_client
        
        # Executar
        message = client._generate_blocking_issues_message(
            company_name="Empresa Teste",
            case_id="CASE-789",
            blocking_issues=["Issue 1", "Issue 2", "Issue 3"],
            cnpj="11.222.333/0001-44"
        )
        
        # Verificar conteúdo
        assert "🚫 *PENDÊNCIAS BLOQUEANTES DETECTADAS*" in message
        assert "Empresa Teste" in message
        assert "CASE-789" in message
        assert "11.222.333/0001-44" in message
        assert "Issue 1" in message
        assert "Issue 2" in message
        assert "Issue 3" in message
        assert "Sistema de Triagem v2.0" in message
    
    def test_generate_blocking_issues_message_many_issues(self, mock_twilio_client):
        """Test geração de mensagem com muitas pendencias (limitação)."""
        client, _ = mock_twilio_client
        
        # Criar lista com muitas pendencias
        many_issues = [f"Issue {i}" for i in range(10)]
        
        # Executar
        message = client._generate_blocking_issues_message(
            company_name="Empresa Teste",
            case_id="CASE-999",
            blocking_issues=many_issues
        )
        
        # Verificar limitação a 5 pendencias (índices 0-4)
        assert "Issue 0" in message
        assert "Issue 4" in message
        assert "Issue 5" not in message  # Não deve aparecer
        assert "... e mais 5 pendências" in message
    
    def test_generate_approval_message(self, mock_twilio_client):
        """Test geração de mensagem de aprobación."""
        client, _ = mock_twilio_client
        
        # Executar
        message = client._generate_approval_message(
            company_name="Empresa Aprovada",
            case_id="CASE-APPROVED",
            cnpj="55.666.777/0001-88"
        )
        
        # Verificar conteúdo
        assert "✅ *DOCUMENTAÇÃO APROVADA*" in message
        assert "Empresa Aprovada" in message
        assert "CASE-APPROVED" in message
        assert "55.666.777/0001-88" in message
        assert "Documentação aprovada para prosseguimento" in message
        assert "Sistema de Triagem v2.0" in message
    
    def test_validate_phone_number_valid_brazilian(self, mock_twilio_client):
        """Test validação de número brasileiro válido."""
        client, _ = mock_twilio_client
        
        # Testar diferentes formatos
        test_cases = [
            "+5511999999999",
            "5511999999999", 
            "11999999999",
            "21987654321"
        ]
        
        for phone in test_cases:
            result = client.validate_phone_number(phone)
            assert result["valid"] is True
            assert result["formatted_number"].startswith("+55")
            assert result["original_number"] == phone
    
    def test_validate_phone_number_invalid_short(self, mock_twilio_client):
        """Test validação de número muito curto."""
        client, _ = mock_twilio_client
        
        result = client.validate_phone_number("123")
        
        assert result["valid"] is False
        assert "Número muito curto" in result["error"]
    
    def test_validate_phone_number_invalid_long(self, mock_twilio_client):
        """Test validação de número muito longo."""
        client, _ = mock_twilio_client
        
        result = client.validate_phone_number("1234567890123456")  # 16 dígitos
        
        assert result["valid"] is False
        assert "Número muito longo" in result["error"]
    
    def test_validate_phone_number_with_special_chars(self, mock_twilio_client):
        """Test validação de número com caracteres especiais."""
        client, _ = mock_twilio_client
        
        result = client.validate_phone_number("(11) 99999-9999")
        
        assert result["valid"] is True
        assert result["formatted_number"] == "+5511999999999"
    
    def test_validate_phone_number_error_handling(self, mock_twilio_client):
        """Test manejo de erro na validação."""
        client, _ = mock_twilio_client
        
        # Simular erro interno
        with patch('builtins.filter', side_effect=Exception("Erro interno")):
            result = client.validate_phone_number("+5511999999999")
            
            assert result["valid"] is False
            assert "Erro interno" in result["error"]
    
    def test_twilio_client_initialization_error(self):
        """Test erro na inicialização do cliente."""
        with patch('src.integrations.twilio_client.Client', side_effect=Exception("Credenciais inválidas")):
            with patch('src.integrations.twilio_client.settings') as mock_settings:
                mock_settings.TWILIO_ACCOUNT_SID = "invalid"
                mock_settings.TWILIO_AUTH_TOKEN = "invalid"
                mock_settings.TWILIO_WHATSAPP_NUMBER = "+17245586619"
                
                with pytest.raises(TwilioAPIError) as exc_info:
                    TwilioClient()
                
                assert "Error de inicialización" in str(exc_info.value)
    
    def test_blocking_issues_message_without_cnpj(self, mock_twilio_client):
        """Test geração de mensagem sem CNPJ."""
        client, _ = mock_twilio_client
        
        message = client._generate_blocking_issues_message(
            company_name="Empresa Sem CNPJ",
            case_id="CASE-NO-CNPJ",
            blocking_issues=["Issue 1"],
            cnpj=None  # Sem CNPJ
        )
        
        # Verificar que não menciona CNPJ
        assert "Empresa Sem CNPJ" in message
        assert "CASE-NO-CNPJ" in message
        assert "CNPJ:" not in message
    
    def test_approval_message_without_cnpj(self, mock_twilio_client):
        """Test geração de mensagem de aprobación sem CNPJ."""
        client, _ = mock_twilio_client
        
        message = client._generate_approval_message(
            company_name="Empresa Aprovada",
            case_id="CASE-APPROVED",
            cnpj=None  # Sem CNPJ
        )
        
        # Verificar que não menciona CNPJ
        assert "Empresa Aprovada" in message
        assert "CASE-APPROVED" in message
        assert "CNPJ:" not in message 