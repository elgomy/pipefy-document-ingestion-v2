"""
Pruebas unitarias para DatabaseService.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

from src.services.database_service import DatabaseService


class TestDatabaseService:
    """Pruebas para la clase DatabaseService."""

    @pytest.fixture
    def database_service(self, mock_env_vars):
        """Fixture para crear una instancia de DatabaseService."""
        with patch('src.services.database_service.create_client') as mock_create_client:
            mock_client = Mock()
            mock_create_client.return_value = mock_client
            return DatabaseService()

    @pytest.fixture
    def sample_case_data(self):
        """Datos de ejemplo para caso de tracking."""
        return {
            "case_id": "CASE_123",
            "company_name": "Empresa Teste LTDA",
            "cnpj": "11.222.333/0001-81",
            "status": "pending",
            "classification": "PENDENCIA_BLOQUEANTE",
            "confidence": 0.85,
            "missing_documents": ["Comprovante de endereço"],
            "blocking_issues": ["Documento de identidade em baixa qualidade"],
            "recommendations": ["Solicitar nova foto do RG"]
        }

    @pytest.fixture
    def sample_document_data(self):
        """Dados de exemplo para documento."""
        return {
            "case_id": "CASE_123",
            "filename": "cartao_cnpj.pdf",
            "file_type": "application/pdf",
            "file_size": 77308,
            "storage_path": "CASE_123/cartao_cnpj.pdf",
            "metadata": {
                "cnpj": "11.222.333/0001-81",
                "razao_social": "EMPRESA TESTE LTDA",
                "generated_by": "cnpj_service"
            }
        }

    @pytest.mark.asyncio
    async def test_create_case_tracking_success(self, database_service, sample_case_data):
        """Testa criação bem-sucedida de tracking de caso."""
        # Mock da resposta do Supabase
        mock_response = Mock()
        mock_response.data = [{"id": "test_id", **sample_case_data}]
        mock_response.count = None
        database_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response
        
        result = await database_service.create_case_tracking(sample_case_data)
        
        assert result["id"] == "test_id"
        assert result["case_id"] == sample_case_data["case_id"]

    @pytest.mark.asyncio
    async def test_create_case_tracking_failure(self, database_service, sample_case_data):
        """Testa falha na criação de tracking de caso."""
        # Mock de erro do Supabase
        database_service.supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await database_service.create_case_tracking(sample_case_data)

    @pytest.mark.asyncio
    async def test_update_case_tracking_success(self, database_service):
        """Testa atualização bem-sucedida de tracking de caso."""
        update_data = {
            "status": "approved",
            "classification": "APROVADO",
            "confidence": 0.95
        }
        
        mock_response = Mock()
        mock_response.data = [{"id": "test_id", **update_data}]
        mock_response.count = None
        database_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await database_service.update_case_tracking("CASE_123", update_data)
        
        assert result["status"] == "approved"
        assert result["classification"] == "APROVADO"

    @pytest.mark.asyncio
    async def test_get_case_tracking_found(self, database_service, sample_case_data):
        """Testa busca bem-sucedida de tracking de caso."""
        mock_response = Mock()
        mock_response.data = [sample_case_data]
        mock_response.count = None
        database_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await database_service.get_case_tracking("CASE_123")
        
        assert result is not None
        assert result["case_id"] == "CASE_123"

    @pytest.mark.asyncio
    async def test_get_case_tracking_not_found(self, database_service):
        """Testa busca de tracking de caso não encontrado."""
        mock_response = Mock()
        mock_response.data = []
        mock_response.count = None
        database_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await database_service.get_case_tracking("CASE_NONEXISTENT")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_add_processing_log_success(self, database_service):
        """Testa adição bem-sucedida de log de processamento."""
        log_data = {
            "case_id": "CASE_123",
            "step": "document_classification",
            "status": "completed",
            "details": {"classification": "APROVADO"},
            "execution_time": 2.5
        }
        
        mock_response = Mock()
        mock_response.data = [{"id": "log_id", **log_data}]
        mock_response.count = None
        database_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response
        
        result = await database_service.add_processing_log(
            case_id=log_data["case_id"],
            step=log_data["step"],
            status=log_data["status"],
            details=log_data["details"],
            execution_time=log_data["execution_time"]
        )
        
        assert result["id"] == "log_id"
        assert result["step"] == "document_classification"

    @pytest.mark.asyncio
    async def test_upload_file_to_storage_success(self, database_service, sample_pdf_content):
        """Testa upload bem-sucedido de arquivo para storage."""
        mock_response = Mock()
        mock_response.json.return_value = {"Key": "test_key"}
        database_service.supabase.storage.from_.return_value.upload.return_value = mock_response
        
        result = await database_service.upload_file_to_storage(
            bucket_name="documents",
            file_path="CASE_123/test.pdf",
            file_content=sample_pdf_content,
            content_type="application/pdf"
        )
        
        assert "url" in result
        assert "CASE_123/test.pdf" in result["url"]

    @pytest.mark.asyncio
    async def test_upload_file_to_storage_failure(self, database_service, sample_pdf_content):
        """Testa falha no upload de arquivo para storage."""
        database_service.supabase.storage.from_.return_value.upload.side_effect = Exception("Upload failed")
        
        with pytest.raises(Exception, match="Upload failed"):
            await database_service.upload_file_to_storage(
                bucket_name="documents",
                file_path="CASE_123/test.pdf",
                file_content=sample_pdf_content,
                content_type="application/pdf"
            )

    @pytest.mark.asyncio
    async def test_create_document_record_success(self, database_service, sample_document_data):
        """Testa criação bem-sucedida de registro de documento."""
        mock_response = Mock()
        mock_response.data = [{"id": "doc_id", **sample_document_data}]
        mock_response.count = None
        database_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response
        
        result = await database_service.create_document_record(sample_document_data)
        
        assert result["id"] == "doc_id"
        assert result["filename"] == sample_document_data["filename"]

    @pytest.mark.asyncio
    async def test_get_case_documents_success(self, database_service):
        """Testa busca bem-sucedida de documentos de um caso."""
        mock_documents = [
            {
                "id": "doc1",
                "filename": "rg_frente.pdf",
                "file_type": "application/pdf",
                "case_id": "CASE_123"
            },
            {
                "id": "doc2", 
                "filename": "comprovante_endereco.pdf",
                "file_type": "application/pdf",
                "case_id": "CASE_123"
            }
        ]
        
        mock_response = Mock()
        mock_response.data = mock_documents
        mock_response.count = None
        database_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await database_service.get_case_documents("CASE_123")
        
        assert len(result) == 2
        assert result[0]["filename"] == "rg_frente.pdf"
        assert result[1]["filename"] == "comprovante_endereco.pdf"

    @pytest.mark.asyncio
    async def test_get_case_documents_empty(self, database_service):
        """Testa busca de documentos para caso sem documentos."""
        mock_response = Mock()
        mock_response.data = []
        mock_response.count = None
        database_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await database_service.get_case_documents("CASE_EMPTY")
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_delete_document_success(self, database_service):
        """Testa exclusão bem-sucedida de documento."""
        mock_response = Mock()
        mock_response.data = [{"id": "doc_id"}]
        mock_response.count = None
        database_service.supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response
        
        # Mock para exclusão do storage
        database_service.supabase.storage.from_.return_value.remove.return_value = Mock()
        
        result = await database_service.delete_document("doc_id", "documents/CASE_123/test.pdf")
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_processing_logs_success(self, database_service):
        """Testa busca bem-sucedida de logs de processamento."""
        mock_logs = [
            {
                "id": "log1",
                "case_id": "CASE_123",
                "step": "document_upload",
                "status": "completed",
                "created_at": "2024-01-01T10:00:00Z"
            },
            {
                "id": "log2",
                "case_id": "CASE_123", 
                "step": "document_classification",
                "status": "completed",
                "created_at": "2024-01-01T10:05:00Z"
            }
        ]
        
        mock_response = Mock()
        mock_response.data = mock_logs
        mock_response.count = None
        database_service.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        
        result = await database_service.get_processing_logs("CASE_123")
        
        assert len(result) == 2
        assert result[0]["step"] == "document_upload"
        assert result[1]["step"] == "document_classification"

    @pytest.mark.asyncio
    async def test_update_document_metadata_success(self, database_service):
        """Testa atualização bem-sucedida de metadados de documento."""
        new_metadata = {
            "processed": True,
            "classification": "approved",
            "quality_score": 0.95
        }
        
        mock_response = Mock()
        mock_response.data = [{"id": "doc_id", "metadata": new_metadata}]
        mock_response.count = None
        database_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await database_service.update_document_metadata("doc_id", new_metadata)
        
        assert result["metadata"]["processed"] is True
        assert result["metadata"]["classification"] == "approved"

    @pytest.mark.asyncio
    async def test_get_cases_by_status_success(self, database_service):
        """Testa busca bem-sucedida de casos por status."""
        mock_cases = [
            {"id": "case1", "case_id": "CASE_123", "status": "pending"},
            {"id": "case2", "case_id": "CASE_124", "status": "pending"}
        ]
        
        mock_response = Mock()
        mock_response.data = mock_cases
        mock_response.count = None
        database_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await database_service.get_cases_by_status("pending")
        
        assert len(result) == 2
        assert all(case["status"] == "pending" for case in result)

    @pytest.mark.asyncio
    async def test_get_case_statistics_success(self, database_service):
        """Testa busca bem-sucedida de estatísticas de casos."""
        mock_stats = [
            {"status": "pending", "count": 5},
            {"status": "approved", "count": 10},
            {"status": "rejected", "count": 2}
        ]
        
        mock_response = Mock()
        mock_response.data = mock_stats
        mock_response.count = None
        database_service.supabase.rpc.return_value.execute.return_value = mock_response
        
        result = await database_service.get_case_statistics()
        
        assert len(result) == 3
        assert result[0]["status"] == "pending"
        assert result[0]["count"] == 5

    def test_format_case_data(self, database_service, sample_case_data):
        """Testa formatação de dados de caso."""
        formatted = database_service._format_case_data(sample_case_data)
        
        assert "created_at" in formatted
        assert "updated_at" in formatted
        assert formatted["case_id"] == sample_case_data["case_id"]
        assert isinstance(formatted["missing_documents"], str)  # JSON string
        assert isinstance(formatted["blocking_issues"], str)  # JSON string

    def test_format_document_data(self, database_service, sample_document_data):
        """Testa formatação de dados de documento."""
        formatted = database_service._format_document_data(sample_document_data)
        
        assert "created_at" in formatted
        assert "updated_at" in formatted
        assert formatted["filename"] == sample_document_data["filename"]
        assert isinstance(formatted["metadata"], str)  # JSON string

    def test_validate_case_data_valid(self, database_service, sample_case_data):
        """Testa validação de dados de caso válidos."""
        is_valid, errors = database_service._validate_case_data(sample_case_data)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_case_data_invalid(self, database_service):
        """Testa validação de dados de caso inválidos."""
        invalid_data = {
            "case_id": "",  # Vazio
            "company_name": None,  # Nulo
            # cnpj ausente
        }
        
        is_valid, errors = database_service._validate_case_data(invalid_data)
        
        assert is_valid is False
        assert len(errors) > 0
        assert "case_id é obrigatório" in errors
        assert "company_name é obrigatório" in errors
        assert "cnpj é obrigatório" in errors

    def test_validate_document_data_valid(self, database_service, sample_document_data):
        """Testa validação de dados de documento válidos."""
        is_valid, errors = database_service._validate_document_data(sample_document_data)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_document_data_invalid(self, database_service):
        """Testa validação de dados de documento inválidos."""
        invalid_data = {
            "case_id": "",
            "filename": None,
            "file_size": -1  # Tamanho inválido
        }
        
        is_valid, errors = database_service._validate_document_data(invalid_data)
        
        assert is_valid is False
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, database_service):
        """Testa tratamento de erro de conexão."""
        database_service.supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = ConnectionError("Connection failed")
        
        with pytest.raises(ConnectionError):
            await database_service.get_case_tracking("CASE_123")

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, database_service):
        """Testa rollback de transação em caso de erro."""
        # Simula erro durante operação
        database_service.supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Transaction failed")
        
        with pytest.raises(Exception, match="Transaction failed"):
            await database_service.create_case_tracking({"case_id": "CASE_123"})

    @pytest.mark.asyncio
    async def test_batch_insert_documents(self, database_service):
        """Testa inserção em lote de documentos."""
        documents = [
            {"case_id": "CASE_123", "filename": f"doc_{i}.pdf", "file_type": "application/pdf"}
            for i in range(5)
        ]
        
        mock_response = Mock()
        mock_response.data = [{"id": f"doc_{i}", **doc} for i, doc in enumerate(documents)]
        mock_response.count = None
        database_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response
        
        result = await database_service.batch_insert_documents(documents)
        
        assert len(result) == 5
        assert all("id" in doc for doc in result)

    @pytest.mark.asyncio
    async def test_search_cases_by_cnpj(self, database_service):
        """Testa busca de casos por CNPJ."""
        mock_cases = [
            {"id": "case1", "case_id": "CASE_123", "cnpj": "11.222.333/0001-81"},
            {"id": "case2", "case_id": "CASE_124", "cnpj": "11.222.333/0001-81"}
        ]
        
        mock_response = Mock()
        mock_response.data = mock_cases
        mock_response.count = None
        database_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await database_service.search_cases_by_cnpj("11.222.333/0001-81")
        
        assert len(result) == 2
        assert all(case["cnpj"] == "11.222.333/0001-81" for case in result)

    @pytest.mark.asyncio
    async def test_get_document_by_filename(self, database_service):
        """Testa busca de documento por nome de arquivo."""
        mock_document = {
            "id": "doc1",
            "filename": "cartao_cnpj.pdf",
            "case_id": "CASE_123"
        }
        
        mock_response = Mock()
        mock_response.data = [mock_document]
        mock_response.count = None
        database_service.supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
        
        result = await database_service.get_document_by_filename("CASE_123", "cartao_cnpj.pdf")
        
        assert result is not None
        assert result["filename"] == "cartao_cnpj.pdf"
        assert result["case_id"] == "CASE_123"
