"""
Pruebas unitarias para el servicio de clasificación de documentos.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from src.services.classification_service import (
    DocumentClassificationService,
    ClassificationType,
    DocumentType,
    DocumentRequirement,
    DocumentAnalysis,
    ClassificationResult
)

class TestDocumentClassificationService:
    """Pruebas para DocumentClassificationService."""
    
    @pytest.fixture
    def classification_service(self):
        """Fixture del servicio de clasificación."""
        return DocumentClassificationService()
    
    def test_init(self, classification_service):
        """Prueba la inicialización del servicio."""
        assert classification_service is not None
        assert hasattr(classification_service, 'requirements')
        assert len(classification_service.requirements) > 0
        
        # Verificar que se inicializaron los requisitos básicos
        assert DocumentType.CARTAO_CNPJ in classification_service.requirements
        assert DocumentType.CONTRATO_SOCIAL in classification_service.requirements
    
    def test_classify_case_approved(self, classification_service):
        """Prueba clasificación de caso aprobado."""
        # Datos de documentos completos y válidos
        documents_data = {
            "cartao_cnpj": {
                "present": True,
                "valid": True,
                "date_issued": (datetime.now() - timedelta(days=30)).isoformat(),
                "issues": []
            },
            "contrato_social": {
                "present": True,
                "valid": True,
                "date_issued": (datetime.now() - timedelta(days=365)).isoformat(),
                "registration_number": "12345",
                "issues": []
            },
            "rg_cpf_socios": {
                "present": True,
                "valid": True,
                "legible": True,
                "issues": []
            },
            "comprovante_residencia": {
                "present": True,
                "valid": True,
                "date_issued": (datetime.now() - timedelta(days=60)).isoformat(),
                "issues": []
            }
        }
        
        result = classification_service.classify_case(documents_data)
        
        assert isinstance(result, ClassificationResult)
        assert result.classification == ClassificationType.APROVADO
        assert result.confidence_score > 0.8
        assert len(result.blocking_issues) == 0
    
    def test_classify_case_pending_blocking(self, classification_service):
        """Prueba clasificación de caso con pendencias bloqueantes."""
        documents_data = {
            "cartao_cnpj": {
                "present": False,
                "valid": False,
                "issues": ["Documento ausente"]
            },
            "contrato_social": {
                "present": True,
                "valid": False,
                "registration_number": None,
                "issues": ["Falta número de registro"]
            },
            "rg_cpf_socios": {
                "present": True,
                "valid": False,
                "legible": False,
                "issues": ["Documento ilegível"]
            }
        }
        
        result = classification_service.classify_case(documents_data)
        
        assert result.classification == ClassificationType.PENDENCIA_BLOQUEANTE
        assert len(result.blocking_issues) > 0
        assert result.confidence_score > 0.7
    
    def test_classify_case_pending_non_blocking(self, classification_service):
        """Prueba clasificación de caso con pendencias no bloqueantes."""
        documents_data = {
            "cartao_cnpj": {
                "present": False,  # Cartão CNPJ ausente (não bloqueante)
                "valid": False,
                "issues": ["Documento ausente - pode ser gerado automaticamente"]
            },
            "contrato_social": {
                "present": True,
                "valid": True,
                "date_issued": (datetime.now() - timedelta(days=1200)).isoformat(),  # > 3 anos
                "registration_number": "12345",
                "issues": ["Documento antigo - aceitar Certidão Simplificada"]
            },
            "rg_cpf_socios": {
                "present": True,
                "valid": True,
                "legible": True,
                "issues": []
            }
        }
        
        result = classification_service.classify_case(documents_data)
        
        assert result.classification == ClassificationType.PENDENCIA_NAO_BLOQUEANTE
        assert len(result.blocking_issues) == 0
        assert len(result.non_blocking_issues) > 0
    
    def test_classify_case_empty_documents(self, classification_service):
        """Prueba clasificación con lista vacía de documentos."""
        documents_data = {}
        
        result = classification_service.classify_case(documents_data)
        
        assert result.classification == ClassificationType.PENDENCIA_BLOQUEANTE
        assert len(result.blocking_issues) > 0
        assert "documentos obrigatórios ausentes" in result.summary.lower()
    
    def test_analyze_single_document_valid(self, classification_service):
        """Prueba análisis de documento individual válido."""
        doc_data = {
            "present": True,
            "valid": True,
            "date_issued": (datetime.now() - timedelta(days=30)).isoformat(),
            "issues": []
        }
        
        analysis = classification_service._analyze_single_document(
            DocumentType.CARTAO_CNPJ, {"cartao_cnpj": doc_data}
        )
        
        assert isinstance(analysis, DocumentAnalysis)
        assert analysis.document_type == DocumentType.CARTAO_CNPJ
        assert analysis.present is True
        assert analysis.valid is True
        assert len(analysis.issues) == 0
    
    def test_analyze_single_document_invalid(self, classification_service):
        """Prueba análisis de documento individual inválido."""
        doc_data = {
            "present": True,
            "valid": False,
            "legible": False,
            "issues": ["Documento ilegível", "Qualidade baixa"]
        }
        
        analysis = classification_service._analyze_single_document(
            DocumentType.RG_CPF_SOCIOS, {"rg_cpf_socios": doc_data}
        )
        
        assert analysis.document_type == DocumentType.RG_CPF_SOCIOS
        assert analysis.present is True
        assert analysis.valid is False
        assert len(analysis.issues) > 0
    
    def test_determine_classification_approved(self, classification_service):
        """Prueba determinación de clasificación aprobada."""
        analyses = [
            DocumentAnalysis(
                document_type=DocumentType.CARTAO_CNPJ,
                present=True,
                valid=True,
                issues=[]
            ),
            DocumentAnalysis(
                document_type=DocumentType.CONTRATO_SOCIAL,
                present=True,
                valid=True,
                issues=[]
            )
        ]
        
        classification = classification_service._determine_classification(analyses)
        assert classification == ClassificationType.APROVADO
    
    def test_determine_classification_blocking(self, classification_service):
        """Prueba determinación de clasificación bloqueante."""
        analyses = [
            DocumentAnalysis(
                document_type=DocumentType.RG_CPF_SOCIOS,
                present=True,
                valid=False,
                issues=["Documento ilegível"]
            ),
            DocumentAnalysis(
                document_type=DocumentType.CONTRATO_SOCIAL,
                present=True,
                valid=False,
                issues=["Falta número de registro"]
            )
        ]
        
        classification = classification_service._determine_classification(analyses)
        assert classification == ClassificationType.PENDENCIA_BLOQUEANTE
    
    def test_calculate_confidence_score_high(self, classification_service):
        """Prueba cálculo de score de confianza alto."""
        analyses = [
            DocumentAnalysis(
                document_type=DocumentType.CARTAO_CNPJ,
                present=True,
                valid=True,
                issues=[]
            )
        ]
        
        score = classification_service._calculate_confidence_score(
            analyses, ClassificationType.APROVADO
        )
        
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Score alto para documentos válidos
    
    def test_calculate_confidence_score_low(self, classification_service):
        """Prueba cálculo de score de confianza bajo."""
        analyses = [
            DocumentAnalysis(
                document_type=DocumentType.RG_CPF_SOCIOS,
                present=False,
                valid=False,
                issues=["Documento ausente", "Informações incompletas"]
            )
        ]
        
        score = classification_service._calculate_confidence_score(
            analyses, ClassificationType.PENDENCIA_BLOQUEANTE
        )
        
        assert 0.0 <= score <= 1.0
        assert score < 0.7  # Score baixo para documentos com problemas
    
    def test_categorize_issues(self, classification_service):
        """Prueba categorización de issues."""
        analyses = [
            DocumentAnalysis(
                document_type=DocumentType.CARTAO_CNPJ,
                present=False,
                valid=False,
                issues=["Documento ausente - pode ser gerado"],
                can_auto_generate=True
            ),
            DocumentAnalysis(
                document_type=DocumentType.RG_CPF_SOCIOS,
                present=True,
                valid=False,
                issues=["Documento ilegível"]
            )
        ]
        
        blocking, non_blocking, auto_actions = classification_service._categorize_issues(analyses)
        
        assert isinstance(blocking, list)
        assert isinstance(non_blocking, list)
        assert isinstance(auto_actions, list)
        assert len(blocking) > 0  # RG ilegível é bloqueante
        assert len(auto_actions) > 0  # Cartão CNPJ pode ser gerado
    
    def test_generate_summary(self, classification_service):
        """Prueba generación de resumen."""
        analyses = [
            DocumentAnalysis(
                document_type=DocumentType.CARTAO_CNPJ,
                present=True,
                valid=True,
                issues=[]
            )
        ]
        
        summary = classification_service._generate_summary(
            ClassificationType.APROVADO,
            analyses,
            blocking_issues=[],
            non_blocking_issues=[]
        )
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "aprovado" in summary.lower()
    
    def test_calculate_document_age(self, classification_service):
        """Prueba cálculo de edad de documento."""
        # Documento de 30 días
        date_30_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        age = classification_service._calculate_document_age(date_30_days_ago)
        
        assert age == 30
        
        # Documento de hoy
        today = datetime.now().isoformat()
        age_today = classification_service._calculate_document_age(today)
        
        assert age_today == 0
    
    def test_get_document_display_name(self, classification_service):
        """Prueba obtención de nombre de display de documento."""
        display_name = classification_service._get_document_display_name(
            DocumentType.CARTAO_CNPJ
        )
        
        assert isinstance(display_name, str)
        assert len(display_name) > 0
        assert "cnpj" in display_name.lower()
    
    def test_document_requirements_initialization(self, classification_service):
        """Prueba inicialización de requisitos de documentos."""
        requirements = classification_service.requirements
        
        # Verificar que se inicializaron los requisitos principales
        cartao_req = requirements[DocumentType.CARTAO_CNPJ]
        assert cartao_req.required is True
        assert cartao_req.can_auto_generate is True
        assert cartao_req.blocking_if_missing is False  # Não bloqueante
        
        contrato_req = requirements[DocumentType.CONTRATO_SOCIAL]
        assert contrato_req.required is True
        assert contrato_req.blocking_if_missing is True
        assert contrato_req.max_age_days == 1095  # 3 anos
    
    def test_validate_document_rules(self, classification_service):
        """Prueba validación de reglas de documento."""
        doc_data = {
            "present": True,
            "valid": True,
            "date_issued": (datetime.now() - timedelta(days=30)).isoformat(),
            "registration_number": "12345"
        }
        
        requirement = classification_service.requirements[DocumentType.CONTRATO_SOCIAL]
        
        is_valid, issues, age = classification_service._validate_document_rules(
            DocumentType.CONTRATO_SOCIAL, doc_data, requirement
        )
        
        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)
        assert isinstance(age, (int, type(None)))
        assert age == 30 