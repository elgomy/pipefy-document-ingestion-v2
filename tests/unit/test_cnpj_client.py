"""
Pruebas unitarias para CNPJClient.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import aiohttp
import json

from src.integrations.cnpj_client import CNPJClient, CNPJAPIError, CNPJData


class TestCNPJClient:
    """Pruebas para la clase CNPJClient."""

    @pytest.fixture
    def cnpj_client(self):
        """Fixture para crear una instancia de CNPJClient."""
        return CNPJClient(timeout=10)

    @pytest.fixture
    def mock_cnpj_response(self, sample_cnpj_data):
        """Mock de respuesta de la API de CNPJ."""
        return {
            "cnpj": sample_cnpj_data["cnpj"],
            "razao_social": sample_cnpj_data["razao_social"],
            "nome_fantasia": sample_cnpj_data["nome_fantasia"],
            "situacao_cadastral": sample_cnpj_data["situacao_cadastral"],
            "endereco": sample_cnpj_data["endereco"],
            "telefone": sample_cnpj_data["telefone"],
            "email": sample_cnpj_data["email"],
            "atividade_principal": sample_cnpj_data["atividade_principal"],
            "data_abertura": sample_cnpj_data["data_abertura"]
        }

    def test_init(self, cnpj_client):
        """Testa a inicialização do cliente."""
        assert cnpj_client.timeout == 10
        assert cnpj_client.brasil_api_url == "https://brasilapi.com.br/api/cnpj/v1"
        assert cnpj_client.cnpj_ws_url == "https://www.cnpj.ws/cnpj"
        assert cnpj_client.cnpja_api_url == "https://api.cnpja.com/rfb/certificate"

    def test_clean_cnpj(self, cnpj_client):
        """Testa a limpeza de CNPJ."""
        test_cases = [
            ("11.222.333/0001-81", "11222333000181"),
            ("11222333000181", "11222333000181"),
            ("11 222 333 0001 81", "11222333000181"),
            ("11-222-333-0001-81", "11222333000181"),
            ("", ""),
        ]
        
        for input_cnpj, expected in test_cases:
            result = cnpj_client._clean_cnpj(input_cnpj)
            assert result == expected

    def test_format_cnpj(self, cnpj_client):
        """Testa a formatação de CNPJ."""
        test_cases = [
            ("11222333000181", "11.222.333/0001-81"),
            ("14616875000127", "14.616.875/0001-27"),
        ]
        
        for input_cnpj, expected in test_cases:
            result = cnpj_client._format_cnpj(input_cnpj)
            assert result == expected

    def test_format_cnpj_invalid_length(self, cnpj_client):
        """Testa formatação com CNPJ de tamanho inválido."""
        with pytest.raises(ValueError, match="CNPJ deve ter exatamente 14 dígitos"):
            cnpj_client._format_cnpj("123")

    def test_validate_cnpj_valid(self, cnpj_client, valid_cnpj_numbers):
        """Testa validação de CNPJs válidos."""
        for cnpj in valid_cnpj_numbers:
            result = cnpj_client._validate_cnpj(cnpj)
            assert result is True

    def test_validate_cnpj_invalid(self, cnpj_client, invalid_cnpj_numbers):
        """Testa validação de CNPJs inválidos."""
        for cnpj in invalid_cnpj_numbers:
            result = cnpj_client._validate_cnpj(cnpj)
            assert result is False

    def test_validate_cnpj_edge_cases(self, cnpj_client):
        """Testa casos extremos de validação."""
        edge_cases = [
            "123",  # Muito curto
            "123456789012345",  # Muito longo
            "abcdefghijklmn",  # Não numérico
        ]
        
        for cnpj in edge_cases:
            result = cnpj_client._validate_cnpj(cnpj)
            assert result is False

    @pytest.mark.asyncio
    async def test_get_cnpj_data_success_brasil_api(self, cnpj_client, mock_cnpj_response):
        """Testa consulta bem-sucedida via BrasilAPI."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock da resposta da API
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_cnpj_response)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await cnpj_client.get_cnpj_data("11.222.333/0001-81")
            
            assert isinstance(result, CNPJData)
            assert result.cnpj == "11.222.333/0001-81"
            assert result.razao_social == "EMPRESA TESTE LTDA"
            assert result.api_source == "BrasilAPI"

    @pytest.mark.asyncio
    async def test_get_cnpj_data_fallback_to_cnpj_ws(self, cnpj_client, mock_cnpj_response):
        """Testa fallback para CNPJ.ws quando BrasilAPI falha."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Primeira chamada (BrasilAPI) falha
            mock_response_fail = AsyncMock()
            mock_response_fail.status = 500
            
            # Segunda chamada (CNPJ.ws) sucede
            mock_response_success = AsyncMock()
            mock_response_success.status = 200
            mock_response_success.json = AsyncMock(return_value=mock_cnpj_response)
            
            mock_get.return_value.__aenter__.side_effect = [
                mock_response_fail,
                mock_response_success
            ]
            
            result = await cnpj_client.get_cnpj_data("11.222.333/0001-81")
            
            assert isinstance(result, CNPJData)
            assert result.api_source == "CNPJ.ws"

    @pytest.mark.asyncio
    async def test_get_cnpj_data_fallback_to_mock(self, cnpj_client):
        """Testa fallback para dados mock quando todas as APIs falham."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Ambas as chamadas falham
            mock_response_fail = AsyncMock()
            mock_response_fail.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response_fail
            
            result = await cnpj_client.get_cnpj_data("11.222.333/0001-81")
            
            assert isinstance(result, CNPJData)
            assert result.api_source == "Mock"
            assert result.razao_social == "EMPRESA TESTE LTDA"

    @pytest.mark.asyncio
    async def test_get_cnpj_data_invalid_cnpj(self, cnpj_client):
        """Testa erro com CNPJ inválido."""
        with pytest.raises(CNPJAPIError, match="CNPJ inválido"):
            await cnpj_client.get_cnpj_data("00.000.000/0000-00")

    @pytest.mark.asyncio
    async def test_get_cnpj_data_timeout(self, cnpj_client):
        """Testa timeout na consulta."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()
            
            result = await cnpj_client.get_cnpj_data("11.222.333/0001-81")
            
            # Deve retornar dados mock em caso de timeout
            assert isinstance(result, CNPJData)
            assert result.api_source == "Mock"

    @pytest.mark.asyncio
    async def test_generate_cnpj_card(self, cnpj_client, sample_cnpj_data):
        """Testa geração de cartão CNPJ."""
        with patch.object(cnpj_client, 'get_cnpj_data') as mock_get_data:
            mock_get_data.return_value = CNPJData(**sample_cnpj_data)
            
            result = await cnpj_client.generate_cnpj_card("11.222.333/0001-81")
            
            assert "cnpj" in result
            assert "razao_social" in result
            assert "endereco_completo" in result
            assert result["cnpj"] == "11.222.333/0001-81"
            assert result["razao_social"] == "EMPRESA TESTE LTDA"

    @pytest.mark.asyncio
    async def test_download_cnpj_certificate_pdf_success(self, cnpj_client, sample_pdf_content):
        """Testa download bem-sucedido de certificado PDF."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=sample_pdf_content)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await cnpj_client.download_cnpj_certificate_pdf("11.222.333/0001-81")
            
            assert result == sample_pdf_content

    @pytest.mark.asyncio
    async def test_download_cnpj_certificate_pdf_fallback_mock(self, cnpj_client):
        """Testa fallback para PDF mock quando API falha."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with patch.object(cnpj_client, '_generate_mock_pdf') as mock_generate:
                mock_pdf = b"mock_pdf_content"
                mock_generate.return_value = mock_pdf
                
                result = await cnpj_client.download_cnpj_certificate_pdf("11.222.333/0001-81")
                
                assert result == mock_pdf
                mock_generate.assert_called_once_with("11.222.333/0001-81")

    @pytest.mark.asyncio
    async def test_download_cnpj_certificate_pdf_invalid_cnpj(self, cnpj_client):
        """Testa erro com CNPJ inválido no download."""
        with pytest.raises(CNPJAPIError, match="CNPJ inválido"):
            await cnpj_client.download_cnpj_certificate_pdf("00.000.000/0000-00")

    def test_generate_mock_pdf(self, cnpj_client):
        """Testa geração de PDF mock."""
        result = cnpj_client._generate_mock_pdf("11.222.333/0001-81")
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert b"PDF" in result  # Verifica se é um PDF válido

    def test_cnpj_data_dataclass(self, sample_cnpj_data):
        """Testa a criação do dataclass CNPJData."""
        cnpj_data = CNPJData(**sample_cnpj_data)
        
        assert cnpj_data.cnpj == "11.222.333/0001-81"
        assert cnpj_data.razao_social == "EMPRESA TESTE LTDA"
        assert cnpj_data.situacao_cadastral == "ATIVA"
        assert isinstance(cnpj_data.consulted_at, datetime)

    def test_cnpj_api_error(self):
        """Testa a exceção CNPJAPIError."""
        error = CNPJAPIError("Test error", 500, "TestAPI")
        
        assert str(error) == "Test error"
        assert error.status_code == 500
        assert error.api_name == "TestAPI"

    @pytest.mark.asyncio
    async def test_session_management(self, cnpj_client):
        """Testa o gerenciamento de sessão HTTP."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Simula uma chamada que usa a sessão
            with patch.object(cnpj_client, 'get_cnpj_data') as mock_get_data:
                mock_get_data.return_value = CNPJData(
                    cnpj="11.222.333/0001-81",
                    razao_social="Test",
                    consulted_at=datetime.now()
                )
                
                await cnpj_client.get_cnpj_data("11.222.333/0001-81")
                
                # Verifica se a sessão foi criada com timeout correto
                mock_session_class.assert_called_with(
                    timeout=aiohttp.ClientTimeout(total=10)
                )

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, cnpj_client):
        """Testa requisições concorrentes."""
        cnpjs = ["11.222.333/0001-81", "14.616.875/0001-27"]
        
        with patch.object(cnpj_client, 'get_cnpj_data') as mock_get_data:
            mock_get_data.side_effect = [
                CNPJData(cnpj=cnpj, razao_social=f"Empresa {i}", consulted_at=datetime.now())
                for i, cnpj in enumerate(cnpjs)
            ]
            
            # Executa requisições concorrentes
            tasks = [cnpj_client.get_cnpj_data(cnpj) for cnpj in cnpjs]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 2
            assert all(isinstance(result, CNPJData) for result in results)

    def test_cnpj_validation_algorithm(self, cnpj_client):
        """Testa o algoritmo de validação de CNPJ em detalhes."""
        # CNPJ conhecido válido: 11.222.333/0001-81
        cnpj = "11222333000181"
        
        # Testa o cálculo manual dos dígitos verificadores
        digits = [int(d) for d in cnpj[:12]]
        
        # Primeiro dígito verificador
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum1 = sum(d * w for d, w in zip(digits, weights1))
        remainder1 = sum1 % 11
        digit1 = 0 if remainder1 < 2 else 11 - remainder1
        
        # Segundo dígito verificador
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum2 = sum(d * w for d, w in zip(digits + [digit1], weights2))
        remainder2 = sum2 % 11
        digit2 = 0 if remainder2 < 2 else 11 - remainder2
        
        # Verifica se os dígitos calculados coincidem com os do CNPJ
        assert digit1 == 8
        assert digit2 == 1
        
        # Verifica se a função de validação retorna True
        assert cnpj_client._validate_cnpj(cnpj) is True 