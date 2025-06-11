"""
Tests unitarios para el servicio de generación de reportes.
"""
import pytest
from datetime import datetime, timedelta
from src.services.report_service import (
    ReportService,
    ReportMetadata,
    report_service
)
from src.services.classification_service import (
    ClassificationResult,
    DocumentAnalysis,
    ClassificationType,
    DocumentType
)

class TestReportService:
    """Tests para el servicio de generación de reportes."""
    
    @pytest.fixture
    def service(self):
        """Fixture que retorna una instancia del servicio."""
        return ReportService()
    
    @pytest.fixture
    def sample_metadata(self):
        """Fixture con metadados de exemplo."""
        return ReportMetadata(
            generated_at=datetime(2024, 6, 15, 14, 30, 0),
            case_id="CASE-12345",
            company_name="Empresa Teste Ltda",
            cnpj="12.345.678/0001-99",
            analyst="João Silva"
        )
    
    @pytest.fixture
    def approved_classification_result(self):
        """Fixture com resultado de classificação aprovado."""
        analyses = [
            DocumentAnalysis(DocumentType.CARTAO_CNPJ, True, True, [], 30),
            DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, True, True, [], 60),
            DocumentAnalysis(DocumentType.RG_CPF_SOCIOS, True, True, []),
            DocumentAnalysis(DocumentType.BALANCO_PATRIMONIAL, True, True, [])
        ]
        
        return ClassificationResult(
            classification=ClassificationType.APROVADO,
            confidence_score=0.95,
            summary="Documentação aprovada",
            document_analyses=analyses,
            blocking_issues=[],
            non_blocking_issues=[],
            auto_actions_possible=[]
        )
    
    @pytest.fixture
    def blocking_issues_result(self):
        """Fixture com resultado com pendências bloqueantes."""
        analyses = [
            DocumentAnalysis(DocumentType.CARTAO_CNPJ, True, True, [], 30),
            DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, False, False, ["Documento obrigatório ausente"], None),
            DocumentAnalysis(DocumentType.RG_CPF_SOCIOS, False, False, ["Documento obrigatório ausente"], None)
        ]
        
        return ClassificationResult(
            classification=ClassificationType.PENDENCIA_BLOQUEANTE,
            confidence_score=0.25,
            summary="Pendências bloqueantes identificadas",
            document_analyses=analyses,
            blocking_issues=[
                "Contrato Social ausente",
                "RG/CPF dos sócios ausente"
            ],
            non_blocking_issues=[],
            auto_actions_possible=[]
        )
    
    @pytest.fixture
    def non_blocking_issues_result(self):
        """Fixture com resultado com pendências não-bloqueantes."""
        analyses = [
            DocumentAnalysis(DocumentType.CARTAO_CNPJ, False, False, ["Documento ausente"], None, True),
            DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, True, True, [], 60),
            DocumentAnalysis(DocumentType.RG_CPF_SOCIOS, True, True, [])
        ]
        
        return ClassificationResult(
            classification=ClassificationType.PENDENCIA_NAO_BLOQUEANTE,
            confidence_score=0.75,
            summary="Pendências não-bloqueantes identificadas",
            document_analyses=analyses,
            blocking_issues=[],
            non_blocking_issues=["Cartão CNPJ ausente"],
            auto_actions_possible=["Gerar automaticamente: Cartão CNPJ"]
        )
    
    def test_service_initialization(self, service):
        """Test inicialização do serviço."""
        assert service is not None
        assert service.classification_service is not None
    
    def test_generate_detailed_report_approved(self, service, approved_classification_result, sample_metadata):
        """Test geração de relatório detalhado para caso aprovado."""
        report = service.generate_detailed_report(
            approved_classification_result,
            sample_metadata,
            include_technical_details=True
        )
        
        # Verificar estrutura básica
        assert "# ✅ Relatório de Triagem Documental" in report
        assert "## 📋 Resumo Executivo" in report
        assert "## 🎯 Detalhes da Classificação" in report
        assert "## 📄 Análise Detalhada dos Documentos" in report
        assert "## 🔍 Pendências e Recomendações" in report
        assert "## 🔧 Detalhes Técnicos" in report
        
        # Verificar metadados
        assert "Empresa Teste Ltda" in report
        assert "12.345.678/0001-99" in report
        assert "CASE-12345" in report
        assert "João Silva" in report
        
        # Verificar classificação
        assert "Aprovado" in report
        assert "95.0%" in report
        assert "APROVADA" in report
        
        # Verificar que não há seção de ações automáticas (caso aprovado)
        assert "## 🤖 Ações Automáticas Disponíveis" not in report
    
    def test_generate_detailed_report_blocking_issues(self, service, blocking_issues_result):
        """Test geração de relatório para caso com pendências bloqueantes."""
        report = service.generate_detailed_report(
            blocking_issues_result,
            include_technical_details=False
        )
        
        # Verificar classificação
        assert "🚫" in report
        assert "Pendencia_Bloqueante" in report
        assert "25.0%" in report
        
        # Verificar pendências bloqueantes
        assert "🚫 Pendências Bloqueantes" in report
        assert "Contrato Social ausente" in report
        assert "RG/CPF dos sócios ausente" in report
        
        # Verificar que não há detalhes técnicos
        assert "## 🔧 Detalhes Técnicos" not in report
    
    def test_generate_detailed_report_non_blocking_issues(self, service, non_blocking_issues_result):
        """Test geração de relatório para caso com pendências não-bloqueantes."""
        report = service.generate_detailed_report(non_blocking_issues_result)
        
        # Verificar classificação
        assert "⚠️" in report
        assert "Pendencia_NaoBloqueante" in report
        assert "75.0%" in report
        
        # Verificar pendências não-bloqueantes
        assert "⚠️ Pendências Não-Bloqueantes" in report
        assert "Cartão CNPJ ausente" in report
        
        # Verificar ações automáticas
        assert "## 🤖 Ações Automáticas Disponíveis" in report
        assert "Gerar automaticamente: Cartão CNPJ" in report
    
    def test_generate_summary_report_approved(self, service, approved_classification_result, sample_metadata):
        """Test geração de relatório resumido para caso aprovado."""
        summary = service.generate_summary_report(approved_classification_result, sample_metadata)
        
        # Verificar elementos essenciais
        assert "**Status:** ✅ Aprovado" in summary
        assert "**Confiança:** 95.0%" in summary
        assert "**Documentos:** 4/4 válidos" in summary
        assert "15/06/2024 às 14:30" in summary
        
        # Verificar que não há pendências (caso aprovado)
        assert "Pendências Bloqueantes" not in summary
        assert "Pendências Não-Bloqueantes" not in summary
    
    def test_generate_summary_report_with_issues(self, service, blocking_issues_result):
        """Test geração de relatório resumido com pendências."""
        summary = service.generate_summary_report(blocking_issues_result)
        
        # Verificar elementos essenciais
        assert "**Status:** 🚫 Pendencia_Bloqueante" in summary
        assert "**Confiança:** 25.0%" in summary
        assert "**🚫 Pendências Bloqueantes:** 2" in summary
    
    def test_generate_summary_report_with_auto_actions(self, service, non_blocking_issues_result):
        """Test geração de relatório resumido com ações automáticas."""
        summary = service.generate_summary_report(non_blocking_issues_result)
        
        # Verificar elementos essenciais
        assert "**Status:** ⚠️ Pendencia_NaoBloqueante" in summary
        assert "**⚠️ Pendências Não-Bloqueantes:** 1" in summary
        assert "**🤖 Ações Automáticas:** 1 disponíveis" in summary
    
    def test_get_status_emoji(self, service):
        """Test obtenção de emojis por status."""
        assert service._get_status_emoji(ClassificationType.APROVADO) == "✅"
        assert service._get_status_emoji(ClassificationType.PENDENCIA_BLOQUEANTE) == "🚫"
        assert service._get_status_emoji(ClassificationType.PENDENCIA_NAO_BLOQUEANTE) == "⚠️"
    
    def test_get_document_display_name(self, service):
        """Test obtenção de nomes de exibição dos documentos."""
        assert "Cartão CNPJ emitido dentro dos 90 dias" in service._get_document_display_name(DocumentType.CARTAO_CNPJ)
        assert "Último Contrato Social" in service._get_document_display_name(DocumentType.CONTRATO_SOCIAL)
        assert "RG e CPF dos sócios" in service._get_document_display_name(DocumentType.RG_CPF_SOCIOS)
    
    def test_global_service_instance(self):
        """Test instância global do serviço."""
        assert report_service is not None
        assert isinstance(report_service, ReportService)