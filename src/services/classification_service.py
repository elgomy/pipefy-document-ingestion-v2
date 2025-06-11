"""
Servicio de Clasificación de Documentos para Triagem.
Implementa la lógica de negocio para clasificar casos según el FAQ v2.0 con IA.

Este servicio utiliza el FAQ.md como fuente única de conocimiento, que contiene:
- Reglas específicas de clasificación (Bloqueante vs No-Bloqueante)
- Lógica de IA detallada para cada tipo de documento
- Acciones automáticas del sistema claramente definidas
- Casos de uso específicos con ejemplos prácticos

Fuente de Conocimiento: FAQ.md (Versión 2.0 - con Automação IA)

NOTA IMPORTANTE: 
Se decidió usar SOLO el FAQ.md como fuente de conocimiento para evitar confusión
del agente de IA. El FAQ contiene información más específica y actualizada que
el checklist básico, incluyendo las reglas exactas de clasificación de pendencias
y las acciones automáticas del sistema. Esto garantiza decisiones más precisas
y consistentes del agente CrewAI.

Para el agente CrewAI, se debe configurar:
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
pdf_source = PDFKnowledgeSource(file_paths=["knowledge/FAQ.pdf"])
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class ClassificationType(Enum):
    """Tipos de clasificación posibles según el FAQ v2.0."""
    APROVADO = "Aprovado"
    PENDENCIA_BLOQUEANTE = "Pendencia_Bloqueante"
    PENDENCIA_NAO_BLOQUEANTE = "Pendencia_NaoBloqueante"

class DocumentType(Enum):
    """Tipos de documentos según FAQ v2.0 - Tabela 1: Checklist Simplificado."""
    CARTAO_CNPJ = "cartao_cnpj"
    CONTRATO_SOCIAL = "contrato_social"
    PROCURACAO = "procuracao"
    RG_CPF_SOCIOS = "rg_cpf_socios"
    COMPROVANTE_RESIDENCIA = "comprovante_residencia"
    BALANCO_PATRIMONIAL = "balanco_patrimonial"
    DEMONSTRACOES_FINANCEIRAS = "demonstracoes_financeiras"
    RELACAO_FATURAMENTO = "relacao_faturamento"
    DECLARACAO_RELACIONAMENTO_CREDITO = "declaracao_relacionamento_credito"
    RELATORIO_VISITA = "relatorio_visita"
    ATA_COMITE_CREDITO = "ata_comite_credito"

@dataclass
class DocumentRequirement:
    """
    Requisitos de documento baseados no FAQ v2.0.
    
    Attributes:
        document_type: Tipo do documento
        required: Se é obrigatório
        max_age_days: Idade máxima em dias (None se não aplicável)
        can_auto_generate: Se pode ser gerado automaticamente
        blocking_if_missing: Se ausência é bloqueante
        blocking_if_invalid: Se invalidez é bloqueante
        validation_rules: Regras específicas de validação
    """
    document_type: DocumentType
    required: bool
    max_age_days: Optional[int] = None
    can_auto_generate: bool = False
    blocking_if_missing: bool = True
    blocking_if_invalid: bool = True
    validation_rules: List[str] = None

    def __post_init__(self):
        if self.validation_rules is None:
            self.validation_rules = []

@dataclass
class DocumentAnalysis:
    """Resultado da análise de um documento específico."""
    document_type: DocumentType
    present: bool
    valid: bool
    issues: List[str]
    age_days: Optional[int] = None
    can_auto_generate: bool = False

@dataclass
class ClassificationResult:
    """Resultado completo da classificação de um caso."""
    classification: ClassificationType
    confidence_score: float
    summary: str
    document_analyses: List[DocumentAnalysis]
    blocking_issues: List[str]
    non_blocking_issues: List[str]
    auto_actions_possible: List[str]

class DocumentClassificationService:
    """
    Serviço de classificação de documentos baseado no FAQ v2.0.
    
    Implementa as regras específicas definidas na Tabela 1 do FAQ:
    - Cartão CNPJ: Não Bloqueante (auto-gerável via API)
    - Contrato Social: Não Bloqueante se > 3 anos (Certidão Simplificada)
    - Falta de Nº Registro: Bloqueante
    - Documentos Sócios: Bloqueante se inválidos
    - Documentos Financeiros: Bloqueante se faltarem assinaturas
    - Relatório Visita: Bloqueante se ausente/incompleto
    """
    
    def __init__(self):
        self.requirements = self._initialize_requirements()
    
    def _initialize_requirements(self) -> Dict[DocumentType, DocumentRequirement]:
        """
        Inicializa os requisitos baseados no FAQ v2.0 - Tabela 1.
        
        Returns:
            Dicionário com requisitos por tipo de documento
        """
        return {
            # Item 1: Cartão CNPJ - Não Bloqueante, auto-gerável
            DocumentType.CARTAO_CNPJ: DocumentRequirement(
                document_type=DocumentType.CARTAO_CNPJ,
                required=True,
                max_age_days=90,
                can_auto_generate=True,
                blocking_if_missing=False,  # FAQ: "Não Bloqueante"
                blocking_if_invalid=False,
                validation_rules=["Emitido há no máximo 90 dias"]
            ),
            
            # Item 2: Contrato Social - Não Bloqueante se > 3 anos
            DocumentType.CONTRATO_SOCIAL: DocumentRequirement(
                document_type=DocumentType.CONTRATO_SOCIAL,
                required=True,
                max_age_days=1095,  # 3 anos
                can_auto_generate=False,
                blocking_if_missing=True,  # FAQ: Ausência é bloqueante
                blocking_if_invalid=True,  # FAQ: Falta de nº registro é bloqueante
                validation_rules=[
                    "Último consolidado com nº de registro",
                    "Emitido há no máx. 3 anos ou Certidão Simplificada"
                ]
            ),
            
            # Item 3: Procuração - Bloqueante se validação falhar
            DocumentType.PROCURACAO: DocumentRequirement(
                document_type=DocumentType.PROCURACAO,
                required=False,  # Opcional
                can_auto_generate=False,
                blocking_if_missing=False,
                blocking_if_invalid=True,  # FAQ: "Bloqueante se validação falhar"
                validation_rules=["Reconhecimento de firma ou assinatura digital", "Vigente"]
            ),
            
            # Item 6: RG/CPF Sócios - Bloqueante se ilegível/inválido
            DocumentType.RG_CPF_SOCIOS: DocumentRequirement(
                document_type=DocumentType.RG_CPF_SOCIOS,
                required=True,
                can_auto_generate=False,
                blocking_if_missing=True,
                blocking_if_invalid=True,  # FAQ: "Bloqueante se ilegível ou inválido"
                validation_rules=["RG/CPF ou CNH legíveis e vigentes"]
            ),
            
            # Item 7: Comprovante Residência - Bloqueante
            DocumentType.COMPROVANTE_RESIDENCIA: DocumentRequirement(
                document_type=DocumentType.COMPROVANTE_RESIDENCIA,
                required=True,
                max_age_days=90,
                can_auto_generate=False,
                blocking_if_missing=True,
                blocking_if_invalid=True,  # FAQ: "Bloqueante"
                validation_rules=[
                    "Conta de consumo (máx. 90 dias)",
                    "Titularidade correta ou Certidão de Casamento"
                ]
            ),
            
            # Item 8: Documentos Financeiros - Bloqueante se faltar assinatura
            DocumentType.BALANCO_PATRIMONIAL: DocumentRequirement(
                document_type=DocumentType.BALANCO_PATRIMONIAL,
                required=False,  # Alternativo
                can_auto_generate=False,
                blocking_if_missing=False,  # Pelo menos um dos financeiros
                blocking_if_invalid=True,  # FAQ: "Bloqueante se faltar assinatura"
                validation_rules=["Datado, assinado (contador/representante)"]
            ),
            
            DocumentType.DEMONSTRACOES_FINANCEIRAS: DocumentRequirement(
                document_type=DocumentType.DEMONSTRACOES_FINANCEIRAS,
                required=False,  # Alternativo
                can_auto_generate=False,
                blocking_if_missing=False,
                blocking_if_invalid=True,
                validation_rules=["Datado, assinado (contador/representante)"]
            ),
            
            DocumentType.RELACAO_FATURAMENTO: DocumentRequirement(
                document_type=DocumentType.RELACAO_FATURAMENTO,
                required=False,  # Alternativo
                can_auto_generate=False,
                blocking_if_missing=False,
                blocking_if_invalid=True,
                validation_rules=["Datado, assinado (contador/representante)"]
            ),
            
            # Item 9: Relatório Visita - Bloqueante se ausente/incompleto
            DocumentType.DECLARACAO_RELACIONAMENTO_CREDITO: DocumentRequirement(
                document_type=DocumentType.DECLARACAO_RELACIONAMENTO_CREDITO,
                required=True,
                can_auto_generate=False,
                blocking_if_missing=True,
                blocking_if_invalid=True,
                validation_rules=["Declaração de relacionamento de crédito"]
            ),
            
            DocumentType.RELATORIO_VISITA: DocumentRequirement(
                document_type=DocumentType.RELATORIO_VISITA,
                required=True,
                can_auto_generate=False,
                blocking_if_missing=True,  # FAQ: "Bloqueante se ausente ou incompleto"
                blocking_if_invalid=True,
                validation_rules=["Datado e assinado pelo gestor"]
            ),
            
            # Ata Comitê Crédito
            DocumentType.ATA_COMITE_CREDITO: DocumentRequirement(
                document_type=DocumentType.ATA_COMITE_CREDITO,
                required=True,
                can_auto_generate=False,
                blocking_if_missing=True,
                blocking_if_invalid=True,
                validation_rules=[
                    "Razão social obrigatória",
                    "CNPJ obrigatório",
                    "Limite aprovado obrigatório",
                    "Data aprovação obrigatória"
                ]
            )
        }
    
    def classify_case(self, documents_data: Dict[str, Any]) -> ClassificationResult:
        """
        Classifica um caso baseado nos dados dos documentos usando regras do FAQ v2.0.
        
        Args:
            documents_data: Dados dos documentos do caso
            
        Returns:
            Resultado da classificação
        """
        logger.info("Iniciando classificação de caso baseada no FAQ v2.0")
        
        # Analisar cada documento
        document_analyses = []
        for doc_type in DocumentType:
            analysis = self._analyze_single_document(doc_type, documents_data)
            document_analyses.append(analysis)
        
        # Classificar baseado nas análises
        classification = self._determine_classification(document_analyses)
        
        # Calcular score de confiança
        confidence_score = self._calculate_confidence_score(document_analyses, classification)
        
        # Gerar listas de pendências
        blocking_issues, non_blocking_issues, auto_actions = self._categorize_issues(document_analyses)
        
        # Gerar resumo
        summary = self._generate_summary(classification, document_analyses, blocking_issues, non_blocking_issues)
        
        result = ClassificationResult(
            classification=classification,
            confidence_score=confidence_score,
            summary=summary,
            document_analyses=document_analyses,
            blocking_issues=blocking_issues,
            non_blocking_issues=non_blocking_issues,
            auto_actions_possible=auto_actions
        )
        
        logger.info(f"Classificação concluída: {classification.value} (confiança: {confidence_score:.2%})")
        return result
    
    def _analyze_single_document(self, doc_type: DocumentType, documents_data: Dict[str, Any]) -> DocumentAnalysis:
        """
        Analisa um documento específico baseado nas regras do FAQ v2.0.
        
        Args:
            doc_type: Tipo do documento
            documents_data: Dados dos documentos
            
        Returns:
            Análise do documento
        """
        requirement = self.requirements[doc_type]
        doc_key = doc_type.value
        doc_data = documents_data.get(doc_key, {})
        
        present = doc_data.get('present', False)
        issues = []
        valid = True
        age_days = None
        
        if not present:
            if requirement.required:
                if requirement.can_auto_generate:
                    issues.append(f"Documento obrigatório ausente: {self._get_document_display_name(doc_type)}")
                    valid = False  # Inválido mas não bloqueante
                else:
                    issues.append(f"Documento obrigatório ausente: {self._get_document_display_name(doc_type)}")
                    valid = False
            # Se não é obrigatório e está ausente, não há problema
        else:
            # Documento presente, validar regras específicas
            valid, document_issues, age_days = self._validate_document_rules(doc_type, doc_data, requirement)
            issues.extend(document_issues)
        
        # Verificar se pode ser auto-gerado
        can_auto_generate = requirement.can_auto_generate and not present
        
        return DocumentAnalysis(
            document_type=doc_type,
            present=present,
            valid=valid,
            issues=issues,
            age_days=age_days,
            can_auto_generate=can_auto_generate
        )
    
    def _validate_document_rules(self, doc_type: DocumentType, doc_data: Dict[str, Any], requirement: DocumentRequirement) -> Tuple[bool, List[str], Optional[int]]:
        """
        Valida regras específicas de um documento baseadas no FAQ v2.0.
        
        Args:
            doc_type: Tipo do documento
            doc_data: Dados do documento
            requirement: Requisitos do documento
            
        Returns:
            Tupla (válido, lista_de_issues, idade_em_dias)
        """
        issues = []
        valid = True
        age_days = None
        
        # Validar idade do documento
        if requirement.max_age_days and doc_data.get('date'):
            age_days = self._calculate_document_age(doc_data['date'])
            if age_days > requirement.max_age_days:
                issues.append(f"Documento vencido: {age_days} dias (máximo: {requirement.max_age_days})")
                valid = False
        
        # Validações específicas por tipo de documento (baseadas no FAQ)
        if doc_type == DocumentType.CONTRATO_SOCIAL:
            if not doc_data.get('has_registration_number', True):
                issues.append("Documento obrigatório ausente: Último Contrato Social/Estatuto consolidado")
                valid = False
        
        elif doc_type == DocumentType.COMPROVANTE_RESIDENCIA:
            if not doc_data.get('is_utility_bill', True):
                issues.append("Deve ser emitido por Concessionária com dados de consumo")
                valid = False
        
        elif doc_type == DocumentType.ATA_COMITE_CREDITO:
            required_fields = ['razao_social', 'cnpj', 'limite_aprovado', 'data_aprovacao']
            missing_fields = [field for field in required_fields if not doc_data.get(field)]
            if missing_fields:
                issues.append(f"Campos obrigatórios ausentes: {', '.join(missing_fields)}")
                valid = False
        
        return valid, issues, age_days
    
    def _determine_classification(self, document_analyses: List[DocumentAnalysis]) -> ClassificationType:
        """
        Determina a classificação final baseada nas regras do FAQ v2.0.
        
        Args:
            document_analyses: Lista de análises de documentos
            
        Returns:
            Classificação final
        """
        has_blocking_issues = False
        has_non_blocking_issues = False
        
        # Verificar documentos financeiros (pelo menos um deve estar presente)
        financial_docs = [
            DocumentType.BALANCO_PATRIMONIAL,
            DocumentType.DEMONSTRACOES_FINANCEIRAS,
            DocumentType.RELACAO_FATURAMENTO
        ]
        
        financial_present = any(
            analysis.present for analysis in document_analyses
            if analysis.document_type in financial_docs
        )
        
        if not financial_present:
            # Adicionar issues para documentos financeiros ausentes
            for analysis in document_analyses:
                if analysis.document_type in financial_docs:
                    analysis.issues.append("Pelo menos um documento financeiro é obrigatório")
                    analysis.valid = False
        
        # Analisar cada documento
        for analysis in document_analyses:
            requirement = self.requirements[analysis.document_type]
            
            if not analysis.valid:
                if not analysis.present:
                    # Documento ausente
                    if requirement.required:
                        if requirement.can_auto_generate:
                            has_non_blocking_issues = True
                        else:
                            has_blocking_issues = True
                elif requirement.blocking_if_invalid:
                    # Documento presente mas inválido e invalidez é bloqueante
                    has_blocking_issues = True
                else:
                    # Documento presente mas inválido e invalidez não é bloqueante
                    has_non_blocking_issues = True
        
        # Determinar classificação final baseada no FAQ v2.0
        if has_blocking_issues:
            return ClassificationType.PENDENCIA_BLOQUEANTE
        elif has_non_blocking_issues:
            return ClassificationType.PENDENCIA_NAO_BLOQUEANTE
        else:
            return ClassificationType.APROVADO
    
    def _calculate_confidence_score(self, document_analyses: List[DocumentAnalysis], classification: ClassificationType) -> float:
        """
        Calcula o score de confiança da classificação.
        
        Args:
            document_analyses: Lista de análises
            classification: Classificação determinada
            
        Returns:
            Score de confiança (0.0 a 1.0)
        """
        total_docs = len(document_analyses)
        valid_docs = sum(1 for analysis in document_analyses if analysis.valid)
        
        base_score = valid_docs / total_docs if total_docs > 0 else 0.0
        
        # Ajustar baseado na classificação
        if classification == ClassificationType.APROVADO:
            return 1.0 if base_score == 1.0 else max(0.9, base_score)
        elif classification == ClassificationType.PENDENCIA_NAO_BLOQUEANTE:
            return max(0.5, base_score * 0.8)
        else:  # PENDENCIA_BLOQUEANTE
            return min(0.5, base_score * 0.6)
    
    def _categorize_issues(self, document_analyses: List[DocumentAnalysis]) -> Tuple[List[str], List[str], List[str]]:
        """
        Categoriza as pendências em bloqueantes, não-bloqueantes e auto-ações.
        
        Args:
            document_analyses: Lista de análises
            
        Returns:
            Tupla (bloqueantes, não_bloqueantes, auto_ações)
        """
        blocking_issues = []
        non_blocking_issues = []
        auto_actions = []
        
        for analysis in document_analyses:
            requirement = self.requirements[analysis.document_type]
            
            for issue in analysis.issues:
                if not analysis.present and requirement.required:
                    if requirement.can_auto_generate:
                        non_blocking_issues.append(issue)
                        auto_actions.append(f"Gerar automaticamente: {self._get_document_display_name(analysis.document_type)}")
                    else:
                        blocking_issues.append(issue)
                elif analysis.present and not analysis.valid:
                    if requirement.blocking_if_invalid:
                        blocking_issues.append(issue)
                    else:
                        non_blocking_issues.append(issue)
                        # Se o documento pode ser auto-gerado e está inválido, adicionar auto-ação
                        if requirement.can_auto_generate:
                            auto_actions.append(f"Gerar automaticamente: {self._get_document_display_name(analysis.document_type)}")
                else:
                    non_blocking_issues.append(issue)
        
        return blocking_issues, non_blocking_issues, auto_actions
    
    def _generate_summary(self, classification: ClassificationType, document_analyses: List[DocumentAnalysis], 
                         blocking_issues: List[str], non_blocking_issues: List[str]) -> str:
        """
        Gera um resumo da análise baseado no FAQ v2.0.
        
        Args:
            classification: Classificação determinada
            document_analyses: Lista de análises
            blocking_issues: Lista de pendências bloqueantes
            non_blocking_issues: Lista de pendências não-bloqueantes
            
        Returns:
            Resumo em texto
        """
        total_docs = len(document_analyses)
        valid_docs = sum(1 for analysis in document_analyses if analysis.valid)
        compliance_rate = (valid_docs / total_docs * 100) if total_docs > 0 else 0
        
        summary_lines = [
            f"**Classificação: {classification.value}**",
            "",
            "**Resumo da Análise:**",
            f"- Documentos analisados: {total_docs}",
            f"- Documentos válidos: {valid_docs}",
            f"- Taxa de conformidade: {compliance_rate:.1f}%",
            ""
        ]
        
        if classification == ClassificationType.APROVADO:
            summary_lines.extend([
                "**✅ Resultado: Documentação APROVADA**",
                "Todos os requisitos obrigatórios foram atendidos."
            ])
        elif classification == ClassificationType.PENDENCIA_BLOQUEANTE:
            summary_lines.extend([
                f"**⚠️ Pendências Bloqueantes ({len(blocking_issues)}):**"
            ])
            for issue in blocking_issues[:5]:  # Mostrar apenas os primeiros 5
                summary_lines.append(f"- {issue}")
            if len(blocking_issues) > 5:
                summary_lines.append(f"- ... e mais {len(blocking_issues) - 5} pendências")
            
            if non_blocking_issues:
                summary_lines.extend([
                    "",
                    f"**📋 Pendências Não-Bloqueantes ({len(non_blocking_issues)}):**"
                ])
                for issue in non_blocking_issues[:3]:
                    summary_lines.append(f"- {issue}")
                if len(non_blocking_issues) > 3:
                    summary_lines.append(f"- ... e mais {len(non_blocking_issues) - 3} pendências")
        
        elif classification == ClassificationType.PENDENCIA_NAO_BLOQUEANTE:
            summary_lines.extend([
                f"**📋 Pendências Não-Bloqueantes ({len(non_blocking_issues)}):**"
            ])
            for issue in non_blocking_issues:
                summary_lines.append(f"- {issue}")
            
            summary_lines.extend([
                "",
                "**🤖 Ações Automáticas Possíveis:**",
                "- Sistema tentará resolver pendências internamente"
            ])
        
        return "\n".join(summary_lines)
    
    def _calculate_document_age(self, date_str: str) -> int:
        """
        Calcula a idade de um documento em dias.
        
        Args:
            date_str: Data em string (vários formatos suportados)
            
        Returns:
            Idade em dias (999 se não conseguir parsear)
        """
        if not date_str:
            return 999
        
        try:
            # Tentar vários formatos de data
            date_formats = [
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%m/%d/%Y',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S'
            ]
            
            document_date = None
            for fmt in date_formats:
                try:
                    document_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if document_date is None:
                logger.warning(f"Não foi possível parsear a data: {date_str}")
                return 999
            
            age = (datetime.now() - document_date).days
            return max(0, age)
            
        except Exception as e:
            logger.error(f"Erro ao calcular idade do documento: {e}")
            return 999
    
    def _get_document_display_name(self, doc_type: DocumentType) -> str:
        """
        Retorna o nome de exibição do documento baseado no FAQ v2.0.
        
        Args:
            doc_type: Tipo do documento
            
        Returns:
            Nome de exibição
        """
        display_names = {
            DocumentType.CARTAO_CNPJ: "Cartão CNPJ emitido dentro dos 90 dias",
            DocumentType.CONTRATO_SOCIAL: "Último Contrato Social/Estatuto consolidado",
            DocumentType.PROCURACAO: "Procuração com reconhecimento de firma",
            DocumentType.RG_CPF_SOCIOS: "RG e CPF dos sócios (≥10%) e signatários",
            DocumentType.COMPROVANTE_RESIDENCIA: "Comprovante de residência (conta de concessionária)",
            DocumentType.BALANCO_PATRIMONIAL: "Balanço Patrimonial assinado",
            DocumentType.DEMONSTRACOES_FINANCEIRAS: "Demonstrações Financeiras assinadas",
            DocumentType.RELACAO_FATURAMENTO: "Relação de Faturamento assinada",
            DocumentType.DECLARACAO_RELACIONAMENTO_CREDITO: "Declaração de relacionamento de crédito",
            DocumentType.RELATORIO_VISITA: "Relatório de Visita ao Cedente",
            DocumentType.ATA_COMITE_CREDITO: "Ata do Comitê de Crédito completa"
        }
        
        return display_names.get(doc_type, doc_type.value.replace('_', ' ').title())

# Instância global do serviço
classification_service = DocumentClassificationService() 