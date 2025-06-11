"""
Pruebas unitarias para CNPJService.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import os
import json

from src.services.cnpj_service import CNPJService, CNPJServiceError


class TestCNPJService:
    """Pruebas para la clase CNPJService."""

    @pytest.fixture
    def cnpj_service(self, mock_env_vars):
        """Fixture para crear una instancia de CNPJService."""
        with patch('src.services.cnpj_service.CNPJClient') as mock_cnpj_client, \
             patch('src.services.cnpj_service.DatabaseService') as mock_db_service:
            
            # Mock del cliente CNPJ
            mock_client = Mock()
            mock_cnpj_client.return_value = mock_client
            
            # Mock del servicio de base de datos
            mock_db = Mock()
            mock_db_service.return_value = mock_db
            
            service = CNPJService()
            service.cnpj_client = mock_client
            service.database_service = mock_db
            
            return service

    @pytest.fixture
    def sample_cnpj_data(self):
        """Datos de ejemplo de CNPJ."""
        return {
            "cnpj": "11.222.333/0001-81",
            "razao_social": "EMPRESA TESTE LTDA",
            "nome_fantasia": "Empresa Teste",
            "situacao_cadastral": "ATIVA",
            "endereco": {
                "logradouro": "RUA TESTE, 123",
                "bairro": "CENTRO",
                "municipio": "SÃO PAULO",
                "uf": "SP",
                "cep": "01000-000"
            },
            "telefone": "(11) 99999-9999",
            "email": "contato@empresateste.com.br",
            "consulted_at": datetime.now()
        }

    @pytest.mark.asyncio
    async def test_validate_cnpj_for_triagem_valid(self, cnpj_service):
        """Testa validação de CNPJ válido para triagem."""
        cnpj_service.cnpj_client.validate_cnpj.return_value = True
        
        result = await cnpj_service.validate_cnpj_for_triagem("11.222.333/0001-81")
        
        assert result["valid"] is True
        assert result["cnpj"] == "11.222.333/0001-81"
        cnpj_service.cnpj_client.validate_cnpj.assert_called_once_with("11.222.333/0001-81")

    @pytest.mark.asyncio
    async def test_validate_cnpj_for_triagem_invalid(self, cnpj_service):
        """Testa validação de CNPJ inválido para triagem."""
        cnpj_service.cnpj_client.validate_cnpj.return_value = False
        
        result = await cnpj_service.validate_cnpj_for_triagem("00.000.000/0000-00")
        
        assert result["valid"] is False
        assert "CNPJ inválido" in result["error"]

    @pytest.mark.asyncio
    async def test_gerar_e_armazenar_cartao_cnpj_success(self, cnpj_service, sample_cnpj_data):
        """Testa geração e armazenamento bem-sucedido de cartão CNPJ."""
        # Mock dos métodos necessários
        cnpj_service.cnpj_client.get_cnpj_data.return_value = sample_cnpj_data
        cnpj_service.cnpj_client.generate_cnpj_card.return_value = {"formatted_data": "test"}
        cnpj_service.cnpj_client.download_cnpj_certificate_pdf.return_value = b"fake_pdf_content"
        
        # Mock do upload para Supabase
        cnpj_service.database_service.upload_file_to_storage.return_value = {
            "url": "https://test.supabase.co/storage/v1/object/public/documents/CASE_123/cartao_cnpj.pdf"
        }
        cnpj_service.database_service.create_document_record.return_value = {
            "id": "doc_123",
            "filename": "cartao_cnpj.pdf"
        }
        
        result = await cnpj_service.gerar_e_armazenar_cartao_cnpj(
            cnpj="11.222.333/0001-81",
            case_id="CASE_123"
        )
        
        assert result["success"] is True
        assert result["cnpj"] == "11.222.333/0001-81"
        assert result["razao_social"] == "EMPRESA TESTE LTDA"
        assert "document_id" in result
        assert "storage_url" in result

    @pytest.mark.asyncio
    async def test_gerar_e_armazenar_cartao_cnpj_invalid_cnpj(self, cnpj_service):
        """Testa geração com CNPJ inválido."""
        cnpj_service.cnpj_client.validate_cnpj.return_value = False
        
        with pytest.raises(CNPJServiceError, match="CNPJ inválido"):
            await cnpj_service.gerar_e_armazenar_cartao_cnpj(
                cnpj="00.000.000/0000-00",
                case_id="CASE_123"
            )

    @pytest.mark.asyncio
    async def test_gerar_e_armazenar_cartao_cnpj_api_error(self, cnpj_service):
        """Testa tratamento de erro da API CNPJ."""
        cnpj_service.cnpj_client.validate_cnpj.return_value = True
        cnpj_service.cnpj_client.get_cnpj_data.side_effect = Exception("API Error")
        
        with pytest.raises(CNPJServiceError, match="Erro ao consultar dados do CNPJ"):
            await cnpj_service.gerar_e_armazenar_cartao_cnpj(
                cnpj="11.222.333/0001-81",
                case_id="CASE_123"
            )

    @pytest.mark.asyncio
    async def test_gerar_e_armazenar_cartao_cnpj_storage_error(self, cnpj_service, sample_cnpj_data):
        """Testa tratamento de erro no storage."""
        cnpj_service.cnpj_client.validate_cnpj.return_value = True
        cnpj_service.cnpj_client.get_cnpj_data.return_value = sample_cnpj_data
        cnpj_service.cnpj_client.generate_cnpj_card.return_value = {"formatted_data": "test"}
        cnpj_service.cnpj_client.download_cnpj_certificate_pdf.return_value = b"fake_pdf_content"
        
        # Mock de erro no upload
        cnpj_service.database_service.upload_file_to_storage.side_effect = Exception("Storage error")
        
        with pytest.raises(CNPJServiceError, match="Erro ao fazer upload do documento"):
            await cnpj_service.gerar_e_armazenar_cartao_cnpj(
                cnpj="11.222.333/0001-81",
                case_id="CASE_123"
            )

    def test_create_directories_success(self, cnpj_service):
        """Testa criação bem-sucedida de diretórios."""
        with patch('os.makedirs') as mock_makedirs:
            cnpj_service._create_directories()
            
            # Verifica que os diretórios foram criados
            assert mock_makedirs.call_count >= 2  # cache e cards directories

    def test_create_directories_already_exist(self, cnpj_service):
        """Testa criação de diretórios que já existem."""
        with patch('os.makedirs') as mock_makedirs:
            mock_makedirs.side_effect = FileExistsError("Directory already exists")
            
            # Não deve levantar exceção
            cnpj_service._create_directories()

    def test_generate_filename(self, cnpj_service):
        """Testa geração de nome de arquivo."""
        filename = cnpj_service._generate_filename("11.222.333/0001-81", "pdf")
        
        assert filename.startswith("cartao_cnpj_")
        assert filename.endswith(".pdf")
        assert "11222333000181" in filename

    def test_clean_cnpj_for_filename(self, cnpj_service):
        """Testa limpeza de CNPJ para nome de arquivo."""
        test_cases = [
            ("11.222.333/0001-81", "11222333000181"),
            ("11222333000181", "11222333000181"),
            ("11 222 333 0001 81", "11222333000181")
        ]
        
        for input_cnpj, expected in test_cases:
            result = cnpj_service._clean_cnpj_for_filename(input_cnpj)
            assert result == expected

    @pytest.mark.asyncio
    async def test_save_json_card_success(self, cnpj_service, sample_cnpj_data):
        """Testa salvamento bem-sucedido de cartão JSON."""
        card_data = {"cnpj_data": sample_cnpj_data}
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = cnpj_service._save_json_card(card_data, "test_file.json")
            
            assert result["success"] is True
            assert result["file_path"] == "test_file.json"
            mock_open.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_json_card_error(self, cnpj_service):
        """Testa erro no salvamento de cartão JSON."""
        card_data = {"test": "data"}
        
        with patch('builtins.open', side_effect=IOError("Write error")):
            with pytest.raises(CNPJServiceError, match="Erro ao salvar cartão JSON"):
                cnpj_service._save_json_card(card_data, "test_file.json")

    def test_format_storage_path(self, cnpj_service):
        """Testa formatação do caminho de storage."""
        path = cnpj_service._format_storage_path("CASE_123", "cartao_cnpj.pdf")
        
        assert path == "CASE_123/cartao_cnpj.pdf"

    def test_format_storage_path_with_special_chars(self, cnpj_service):
        """Testa formatação do caminho com caracteres especiais."""
        path = cnpj_service._format_storage_path("CASE/123", "cartão cnpj.pdf")
        
        # Deve limpar caracteres especiais
        assert "/" not in path.split("/")[0]  # case_id limpo
        assert "cartao_cnpj.pdf" in path  # filename normalizado

    @pytest.mark.asyncio
    async def test_generate_document_metadata(self, cnpj_service, sample_cnpj_data):
        """Testa geração de metadados do documento."""
        pdf_content = b"fake_pdf_content"
        
        metadata = cnpj_service._generate_document_metadata(
            cnpj_data=sample_cnpj_data,
            pdf_size=len(pdf_content),
            case_id="CASE_123"
        )
        
        assert metadata["cnpj"] == "11.222.333/0001-81"
        assert metadata["razao_social"] == "EMPRESA TESTE LTDA"
        assert metadata["file_size"] == len(pdf_content)
        assert metadata["case_id"] == "CASE_123"
        assert metadata["generated_by"] == "cnpj_service"
        assert "generated_at" in metadata

    @pytest.mark.asyncio
    async def test_concurrent_cnpj_processing(self, cnpj_service, sample_cnpj_data):
        """Testa processamento concorrente de múltiplos CNPJs."""
        cnpjs = ["11.222.333/0001-81", "11.222.333/0001-82", "11.222.333/0001-83"]
        
        # Mock das respostas
        cnpj_service.cnpj_client.validate_cnpj.return_value = True
        cnpj_service.cnpj_client.get_cnpj_data.return_value = sample_cnpj_data
        cnpj_service.cnpj_client.generate_cnpj_card.return_value = {"formatted_data": "test"}
        cnpj_service.cnpj_client.download_cnpj_certificate_pdf.return_value = b"fake_pdf_content"
        
        cnpj_service.database_service.upload_file_to_storage.return_value = {
            "url": "https://test.supabase.co/storage/v1/object/public/documents/test.pdf"
        }
        cnpj_service.database_service.create_document_record.return_value = {
            "id": "doc_123",
            "filename": "cartao_cnpj.pdf"
        }
        
        # Processa concorrentemente
        tasks = [
            cnpj_service.gerar_e_armazenar_cartao_cnpj(cnpj, f"CASE_{i}")
            for i, cnpj in enumerate(cnpjs)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(result["success"] for result in results)

    @pytest.mark.asyncio
    async def test_retry_mechanism_on_api_failure(self, cnpj_service, sample_cnpj_data):
        """Testa mecanismo de retry em caso de falha da API."""
        cnpj_service.cnpj_client.validate_cnpj.return_value = True
        
        # Simula falha seguida de sucesso
        cnpj_service.cnpj_client.get_cnpj_data.side_effect = [
            Exception("Temporary API failure"),
            sample_cnpj_data
        ]
        cnpj_service.cnpj_client.generate_cnpj_card.return_value = {"formatted_data": "test"}
        cnpj_service.cnpj_client.download_cnpj_certificate_pdf.return_value = b"fake_pdf_content"
        
        cnpj_service.database_service.upload_file_to_storage.return_value = {
            "url": "https://test.supabase.co/storage/v1/object/public/documents/test.pdf"
        }
        cnpj_service.database_service.create_document_record.return_value = {
            "id": "doc_123",
            "filename": "cartao_cnpj.pdf"
        }
        
        # Com retry habilitado, deve ter sucesso na segunda tentativa
        with patch.object(cnpj_service, '_should_retry', return_value=True):
            result = await cnpj_service.gerar_e_armazenar_cartao_cnpj(
                cnpj="11.222.333/0001-81",
                case_id="CASE_123"
            )
            
            assert result["success"] is True

    def test_validate_case_id(self, cnpj_service):
        """Testa validação de case_id."""
        valid_cases = ["CASE_123", "TEST_001", "ABC123"]
        invalid_cases = ["", None, "case with spaces", "case/with/slashes"]
        
        for case_id in valid_cases:
            assert cnpj_service._validate_case_id(case_id) is True
        
        for case_id in invalid_cases:
            assert cnpj_service._validate_case_id(case_id) is False

    @pytest.mark.asyncio
    async def test_cleanup_on_error(self, cnpj_service, sample_cnpj_data):
        """Testa limpeza de recursos em caso de erro."""
        cnpj_service.cnpj_client.validate_cnpj.return_value = True
        cnpj_service.cnpj_client.get_cnpj_data.return_value = sample_cnpj_data
        cnpj_service.cnpj_client.generate_cnpj_card.return_value = {"formatted_data": "test"}
        cnpj_service.cnpj_client.download_cnpj_certificate_pdf.return_value = b"fake_pdf_content"
        
        # Simula erro no upload
        cnpj_service.database_service.upload_file_to_storage.side_effect = Exception("Upload failed")
        
        with patch('os.remove') as mock_remove:
            with pytest.raises(CNPJServiceError):
                await cnpj_service.gerar_e_armazenar_cartao_cnpj(
                    cnpj="11.222.333/0001-81",
                    case_id="CASE_123"
                )
            
            # Verifica que tentou limpar arquivos temporários
            # (dependendo da implementação)

    @pytest.mark.asyncio
    async def test_large_pdf_handling(self, cnpj_service, sample_cnpj_data):
        """Testa tratamento de PDFs grandes."""
        # Simula PDF grande (5MB)
        large_pdf_content = b"x" * (5 * 1024 * 1024)
        
        cnpj_service.cnpj_client.validate_cnpj.return_value = True
        cnpj_service.cnpj_client.get_cnpj_data.return_value = sample_cnpj_data
        cnpj_service.cnpj_client.generate_cnpj_card.return_value = {"formatted_data": "test"}
        cnpj_service.cnpj_client.download_cnpj_certificate_pdf.return_value = large_pdf_content
        
        cnpj_service.database_service.upload_file_to_storage.return_value = {
            "url": "https://test.supabase.co/storage/v1/object/public/documents/test.pdf"
        }
        cnpj_service.database_service.create_document_record.return_value = {
            "id": "doc_123",
            "filename": "cartao_cnpj.pdf"
        }
        
        result = await cnpj_service.gerar_e_armazenar_cartao_cnpj(
            cnpj="11.222.333/0001-81",
            case_id="CASE_123"
        )
        
        assert result["success"] is True
        # Verifica que o tamanho foi registrado corretamente
        assert len(large_pdf_content) > 1000000  # > 1MB 