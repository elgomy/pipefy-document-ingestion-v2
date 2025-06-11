"""
Pruebas unitarias para PipefyClient.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
import json

from src.integrations.pipefy_client import PipefyClient


class TestPipefyClient:
    """Pruebas para la clase PipefyClient."""

    @pytest.fixture
    def pipefy_client(self, mock_env_vars):
        """Fixture para crear una instancia de PipefyClient."""
        return PipefyClient()

    @pytest.fixture
    def sample_card_data(self):
        """Datos de ejemplo para card de Pipefy."""
        return {
            "id": "123456789",
            "title": "Empresa Teste LTDA - 11.222.333/0001-81",
            "fields": [
                {"field_id": "cnpj", "value": "11.222.333/0001-81"},
                {"field_id": "razao_social", "value": "EMPRESA TESTE LTDA"},
                {"field_id": "status", "value": "pending"}
            ],
            "attachments": [
                {
                    "id": "att_123",
                    "name": "rg_frente.pdf",
                    "url": "https://example.com/file1.pdf"
                },
                {
                    "id": "att_124", 
                    "name": "comprovante_endereco.pdf",
                    "url": "https://example.com/file2.pdf"
                }
            ]
        }

    @pytest.fixture
    def sample_pipe_data(self):
        """Dados de exemplo para pipe de Pipefy."""
        return {
            "id": "pipe_123",
            "name": "Triagem de Documentos",
            "phases": [
                {"id": "phase_1", "name": "Pendente"},
                {"id": "phase_2", "name": "Em Análise"},
                {"id": "phase_3", "name": "Aprovado"}
            ]
        }

    @pytest.mark.asyncio
    async def test_get_card_success(self, pipefy_client, sample_card_data):
        """Testa busca bem-sucedida de card."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"card": sample_card_data}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.get_card("123456789")
            
            assert result["id"] == sample_card_data["id"]
            assert result["title"] == sample_card_data["title"]
            assert len(result["fields"]) == 3

    @pytest.mark.asyncio
    async def test_get_card_not_found(self, pipefy_client):
        """Testa busca de card não encontrado."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"card": None}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.get_card("999999999")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_card_api_error(self, pipefy_client):
        """Testa erro de API ao buscar card."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value="Bad Request")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception, match="Erro na API do Pipefy"):
                await pipefy_client.get_card("123456789")

    @pytest.mark.asyncio
    async def test_update_card_success(self, pipefy_client):
        """Testa atualização bem-sucedida de card."""
        update_data = {
            "status": "approved",
            "classification": "APROVADO",
            "confidence": 0.95
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"updateCard": {"card": {"id": "123456789"}}}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.update_card("123456789", update_data)
            
            assert result["success"] is True
            assert result["card_id"] == "123456789"

    @pytest.mark.asyncio
    async def test_update_card_failure(self, pipefy_client):
        """Testa falha na atualização de card."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value="Validation Error")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception, match="Erro na API do Pipefy"):
                await pipefy_client.update_card("123456789", {"invalid": "data"})

    @pytest.mark.asyncio
    async def test_move_card_to_phase_success(self, pipefy_client):
        """Testa movimentação bem-sucedida de card para fase."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"moveCardToPhase": {"card": {"id": "123456789"}}}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.move_card_to_phase("123456789", "phase_approved")
            
            assert result["success"] is True
            assert result["card_id"] == "123456789"

    @pytest.mark.asyncio
    async def test_get_pipe_cards_success(self, pipefy_client, sample_card_data):
        """Testa busca bem-sucedida de cards de um pipe."""
        cards_data = [sample_card_data, {**sample_card_data, "id": "987654321"}]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"pipe": {"cards": {"edges": [{"node": card} for card in cards_data]}}}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.get_pipe_cards("pipe_123")
            
            assert len(result) == 2
            assert result[0]["id"] == "123456789"
            assert result[1]["id"] == "987654321"

    @pytest.mark.asyncio
    async def test_get_pipe_cards_empty(self, pipefy_client):
        """Testa busca de cards em pipe vazio."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"pipe": {"cards": {"edges": []}}}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.get_pipe_cards("pipe_empty")
            
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_create_card_success(self, pipefy_client):
        """Testa criação bem-sucedida de card."""
        card_data = {
            "pipe_id": "pipe_123",
            "title": "Novo Card Teste",
            "fields": [
                {"field_id": "cnpj", "field_value": "11.222.333/0001-81"},
                {"field_id": "razao_social", "field_value": "EMPRESA TESTE LTDA"}
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"createCard": {"card": {"id": "new_card_123"}}}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.create_card(card_data)
            
            assert result["success"] is True
            assert result["card_id"] == "new_card_123"

    @pytest.mark.asyncio
    async def test_upload_attachment_success(self, pipefy_client, sample_pdf_content):
        """Testa upload bem-sucedido de anexo."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"createPresignedUrl": {"url": "https://upload.url", "headers": {}}}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Mock do upload para S3
            with patch('aiohttp.ClientSession.put') as mock_put:
                mock_put_response = Mock()
                mock_put_response.status = 200
                mock_put.return_value.__aenter__.return_value = mock_put_response
                
                result = await pipefy_client.upload_attachment(
                    card_id="123456789",
                    filename="test.pdf",
                    file_content=sample_pdf_content
                )
                
                assert result["success"] is True
                assert "attachment_id" in result

    @pytest.mark.asyncio
    async def test_upload_attachment_failure(self, pipefy_client, sample_pdf_content):
        """Testa falha no upload de anexo."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value="Upload Error")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception, match="Erro na API do Pipefy"):
                await pipefy_client.upload_attachment(
                    card_id="123456789",
                    filename="test.pdf",
                    file_content=sample_pdf_content
                )

    @pytest.mark.asyncio
    async def test_download_attachment_success(self, pipefy_client):
        """Testa download bem-sucedido de anexo."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=b"PDF content")
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.download_attachment("https://example.com/file.pdf")
            
            assert result == b"PDF content"

    @pytest.mark.asyncio
    async def test_download_attachment_failure(self, pipefy_client):
        """Testa falha no download de anexo."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 404
            mock_response.text = AsyncMock(return_value="Not Found")
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception, match="Erro ao baixar anexo"):
                await pipefy_client.download_attachment("https://example.com/nonexistent.pdf")

    @pytest.mark.asyncio
    async def test_get_pipe_info_success(self, pipefy_client, sample_pipe_data):
        """Testa busca bem-sucedida de informações do pipe."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"pipe": sample_pipe_data}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.get_pipe_info("pipe_123")
            
            assert result["id"] == sample_pipe_data["id"]
            assert result["name"] == sample_pipe_data["name"]
            assert len(result["phases"]) == 3

    @pytest.mark.asyncio
    async def test_search_cards_by_field_success(self, pipefy_client, sample_card_data):
        """Testa busca bem-sucedida de cards por campo."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"pipe": {"cards": {"edges": [{"node": sample_card_data}]}}}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.search_cards_by_field(
                pipe_id="pipe_123",
                field_id="cnpj",
                field_value="11.222.333/0001-81"
            )
            
            assert len(result) == 1
            assert result[0]["id"] == sample_card_data["id"]

    @pytest.mark.asyncio
    async def test_delete_card_success(self, pipefy_client):
        """Testa exclusão bem-sucedida de card."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"deleteCard": {"success": True}}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.delete_card("123456789")
            
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_add_comment_success(self, pipefy_client):
        """Testa adição bem-sucedida de comentário."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"createComment": {"comment": {"id": "comment_123"}}}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await pipefy_client.add_comment("123456789", "Comentário de teste")
            
            assert result["success"] is True
            assert result["comment_id"] == "comment_123"

    def test_build_graphql_query(self, pipefy_client):
        """Testa construção de query GraphQL."""
        query = pipefy_client._build_card_query("123456789")
        
        assert "card(id: 123456789)" in query
        assert "id" in query
        assert "title" in query
        assert "fields" in query

    def test_format_card_fields(self, pipefy_client):
        """Testa formatação de campos de card."""
        fields_data = [
            {"field_id": "cnpj", "value": "11.222.333/0001-81"},
            {"field_id": "razao_social", "value": "EMPRESA TESTE LTDA"}
        ]
        
        formatted = pipefy_client._format_card_fields(fields_data)
        
        assert formatted["cnpj"] == "11.222.333/0001-81"
        assert formatted["razao_social"] == "EMPRESA TESTE LTDA"

    def test_validate_card_data(self, pipefy_client):
        """Testa validação de dados de card."""
        valid_data = {
            "pipe_id": "pipe_123",
            "title": "Teste",
            "fields": [{"field_id": "test", "field_value": "value"}]
        }
        
        invalid_data = {
            "title": "Teste"
            # pipe_id ausente
        }
        
        assert pipefy_client._validate_card_data(valid_data) is True
        assert pipefy_client._validate_card_data(invalid_data) is False

    @pytest.mark.asyncio
    async def test_connection_timeout(self, pipefy_client):
        """Testa timeout de conexão."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = aiohttp.ClientTimeout()
            
            with pytest.raises(Exception, match="Timeout"):
                await pipefy_client.get_card("123456789")

    @pytest.mark.asyncio
    async def test_connection_error(self, pipefy_client):
        """Testa erro de conexão."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = aiohttp.ClientConnectionError()
            
            with pytest.raises(Exception, match="Erro de conexão"):
                await pipefy_client.get_card("123456789")

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, pipefy_client):
        """Testa tratamento de rate limit."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 429
            mock_response.text = AsyncMock(return_value="Rate limit exceeded")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception, match="Rate limit"):
                await pipefy_client.get_card("123456789")

    @pytest.mark.asyncio
    async def test_authentication_error(self, pipefy_client):
        """Testa erro de autenticação."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value="Unauthorized")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception, match="Erro de autenticação"):
                await pipefy_client.get_card("123456789")

    @pytest.mark.asyncio
    async def test_batch_update_cards(self, pipefy_client):
        """Testa atualização em lote de cards."""
        cards_data = [
            {"card_id": "123", "status": "approved"},
            {"card_id": "456", "status": "rejected"}
        ]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": {"updateCard": {"card": {"id": "123"}}}
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            results = await pipefy_client.batch_update_cards(cards_data)
            
            assert len(results) == 2
            assert all(result["success"] for result in results)

    def test_headers_configuration(self, pipefy_client):
        """Testa configuração de headers."""
        headers = pipefy_client._get_headers()
        
        assert "Authorization" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"