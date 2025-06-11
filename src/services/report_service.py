"""
Servicio de Generación de Reportes Detallados para Triagem.
Genera reportes en formato Markdown con análisis completo de documentos.

Fuente de Conocimiento: FAQ.md (Versión 2.0 - con Automação IA)
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from src.services.classification_service import (
    ClassificationResult,
    DocumentAnalysis,
    ClassificationType,
    DocumentType,
    classification_service
)

logger = logging.getLogger(__name__)

@dataclass
class ReportMetadata:
    """Metadados do relatório."""
    generated_at: datetime
    case_id: Optional[str] = None
    company_name: Optional[str] = None
    cnpj: Optional[str] = None
    analyst: Optional[str] = None

class ReportService:
    """Serviço para geração de relatórios detalhados de triagem."""
    
    def __init__(self):
        self.classification_service = classification_service
    
    def generate_detailed_report(
        self,
        classification_result: ClassificationResult,
        metadata: Optional[ReportMetadata] = None,
        include_technical_details: bool = True
    ) -> str:
        """
        Gera um relatório detalhado em formato Markdown.
        
        Args:
            classification_result: Resultado da classificação
            metadata: Metadados do caso
            include_technical_details: Se deve incluir detalhes técnicos
            
        Returns:
            Relatório em formato Markdown
        """
        if metadata is None:
            metadata = ReportMetadata(generated_at=datetime.now())
        
        report_sections = []
        
        # Header
        report_sections.append(self._generate_header(classification_result, metadata))
        
        # Executive Summary
        report_sections.append(self._generate_executive_summary(classification_result))
        
        # Classification Details
        report_sections.append(self._generate_classification_details(classification_result))
        
        # Document Analysis
        report_sections.append(self._generate_document_analysis(classification_result))
        
        # Issues and Recommendations
        report_sections.append(self._generate_issues_and_recommendations(classification_result))
        
        # Auto Actions
        if classification_result.auto_actions_possible:
            report_sections.append(self._generate_auto_actions_section(classification_result))
        
        # Technical Details (optional)
        if include_technical_details:
            report_sections.append(self._generate_technical_details(classification_result))
        
        # Footer
        report_sections.append(self._generate_footer(metadata))
        
        return "\n\n".join(report_sections)
    
    def generate_summary_report(
        self,
        classification_result: ClassificationResult,
        metadata: Optional[ReportMetadata] = None
    ) -> str:
        """
        Gera um relatório resumido para uso em campos de Pipefy.
        
        Args:
            classification_result: Resultado da classificação
            metadata: Metadados do caso
            
        Returns:
            Relatório resumido em formato Markdown
        """
        if metadata is None:
            metadata = ReportMetadata(generated_at=datetime.now())
        
        sections = []
        
        # Status
        sections.append(f"**Status:** {self._get_status_emoji(classification_result.classification)} {classification_result.classification.value}")
        sections.append(f"**Confiança:** {classification_result.confidence_score:.1%}")
        
        # Quick Stats
        total_docs = len(classification_result.document_analyses)
        valid_docs = sum(1 for doc in classification_result.document_analyses if doc.valid)
        sections.append(f"**Documentos:** {valid_docs}/{total_docs} válidos")
        
        # Issues Summary
        if classification_result.blocking_issues:
            sections.append(f"**🚫 Pendências Bloqueantes:** {len(classification_result.blocking_issues)}")
        
        if classification_result.non_blocking_issues:
            sections.append(f"**⚠️ Pendências Não-Bloqueantes:** {len(classification_result.non_blocking_issues)}")
        
        if classification_result.auto_actions_possible:
            sections.append(f"**🤖 Ações Automáticas:** {len(classification_result.auto_actions_possible)} disponíveis")
        
        # Timestamp
        sections.append(f"**Gerado em:** {metadata.generated_at.strftime('%d/%m/%Y às %H:%M')}")
        
        return "\n".join(sections)
    
    def _generate_header(self, result: ClassificationResult, metadata: ReportMetadata) -> str:
        """Gera o cabeçalho do relatório."""
        status_emoji = self._get_status_emoji(result.classification)
        
        header = f"# {status_emoji} Relatório de Triagem Documental\n"
        
        if metadata.company_name:
            header += f"**Empresa:** {metadata.company_name}\n"
        
        if metadata.cnpj:
            header += f"**CNPJ:** {metadata.cnpj}\n"
        
        if metadata.case_id:
            header += f"**Caso ID:** {metadata.case_id}\n"
        
        header += f"**Data/Hora:** {metadata.generated_at.strftime('%d/%m/%Y às %H:%M:%S')}\n"
        
        if metadata.analyst:
            header += f"**Analista:** {metadata.analyst}\n"
        
        return header
    
    def _generate_executive_summary(self, result: ClassificationResult) -> str:
        """Gera o resumo executivo."""
        status_emoji = self._get_status_emoji(result.classification)
        
        summary = "## 📋 Resumo Executivo\n\n"
        summary += f"**Classificação Final:** {status_emoji} **{result.classification.value}**\n"
        summary += f"**Nível de Confiança:** {result.confidence_score:.1%}\n\n"
        
        total_docs = len(result.document_analyses)
        valid_docs = sum(1 for doc in result.document_analyses if doc.valid)
        present_docs = sum(1 for doc in result.document_analyses if doc.present)
        
        summary += f"**Estatísticas dos Documentos:**\n"
        summary += f"- Total analisados: {total_docs}\n"
        summary += f"- Presentes: {present_docs}\n"
        summary += f"- Válidos: {valid_docs}\n"
        summary += f"- Taxa de conformidade: {(valid_docs/total_docs)*100:.1f}%\n\n"
        
        # Status-specific message
        if result.classification == ClassificationType.APROVADO:
            summary += "✅ **Resultado:** Documentação **APROVADA** para prosseguimento.\n"
            summary += "Todos os requisitos obrigatórios foram atendidos satisfatoriamente."
        elif result.classification == ClassificationType.PENDENCIA_BLOQUEANTE:
            summary += "🚫 **Resultado:** Documentação com **PENDÊNCIAS BLOQUEANTES**.\n"
            summary += f"Identificadas {len(result.blocking_issues)} pendências que impedem o prosseguimento."
        else:
            summary += "⚠️ **Resultado:** Documentação com **PENDÊNCIAS NÃO-BLOQUEANTES**.\n"
            summary += f"Identificadas {len(result.non_blocking_issues)} pendências menores que podem ser resolvidas automaticamente."
        
        return summary
    
    def _generate_classification_details(self, result: ClassificationResult) -> str:
        """Gera os detalhes da classificação."""
        section = "## 🎯 Detalhes da Classificação\n\n"
        
        # Classification explanation
        if result.classification == ClassificationType.APROVADO:
            section += "**Critérios Atendidos:**\n"
            section += "- ✅ Todos os documentos obrigatórios presentes\n"
            section += "- ✅ Documentos dentro do prazo de validade\n"
            section += "- ✅ Informações completas e consistentes\n"
            section += "- ✅ Pelo menos um documento financeiro válido\n"
        elif result.classification == ClassificationType.PENDENCIA_BLOQUEANTE:
            section += "**Critérios Não Atendidos (Bloqueantes):**\n"
            for issue in result.blocking_issues[:5]:  # Limit to first 5
                section += f"- 🚫 {issue}\n"
            if len(result.blocking_issues) > 5:
                section += f"- ... e mais {len(result.blocking_issues) - 5} pendências\n"
        else:
            section += "**Pendências Identificadas (Não-Bloqueantes):**\n"
            for issue in result.non_blocking_issues[:5]:  # Limit to first 5
                section += f"- ⚠️ {issue}\n"
            if len(result.non_blocking_issues) > 5:
                section += f"- ... e mais {len(result.non_blocking_issues) - 5} pendências\n"
        
        # Confidence explanation
        section += f"\n**Nível de Confiança: {result.confidence_score:.1%}**\n"
        if result.confidence_score >= 0.9:
            section += "🟢 **Alto:** Classificação muito confiável baseada em análise completa.\n"
        elif result.confidence_score >= 0.7:
            section += "🟡 **Médio:** Classificação confiável com algumas incertezas menores.\n"
        else:
            section += "🔴 **Baixo:** Classificação com incertezas significativas, requer revisão manual.\n"
        
        return section
    
    def _generate_document_analysis(self, result: ClassificationResult) -> str:
        """Gera a análise detalhada dos documentos."""
        section = "## 📄 Análise Detalhada dos Documentos\n\n"
        
        # Group documents by status
        valid_docs = [doc for doc in result.document_analyses if doc.valid]
        invalid_docs = [doc for doc in result.document_analyses if not doc.valid and doc.present]
        missing_docs = [doc for doc in result.document_analyses if not doc.present]
        
        if valid_docs:
            section += "### ✅ Documentos Válidos\n\n"
            for doc in valid_docs:
                section += f"**{self._get_document_display_name(doc.document_type)}**\n"
                if doc.age_days is not None:
                    section += f"- 📅 Idade: {doc.age_days} dias\n"
                if doc.present:
                    section += "- ✅ Status: Presente e válido\n"
                else:
                    section += "- ✅ Status: Não obrigatório (ausente mas válido)\n"
                section += "\n"
        
        if invalid_docs:
            section += "### ❌ Documentos com Problemas\n\n"
            for doc in invalid_docs:
                section += f"**{self._get_document_display_name(doc.document_type)}**\n"
                if doc.age_days is not None:
                    section += f"- 📅 Idade: {doc.age_days} dias\n"
                section += "- ❌ Status: Presente mas inválido\n"
                for issue in doc.issues:
                    section += f"- ⚠️ {issue}\n"
                section += "\n"
        
        if missing_docs:
            section += "### 📋 Documentos Ausentes\n\n"
            for doc in missing_docs:
                section += f"**{self._get_document_display_name(doc.document_type)}**\n"
                section += "- 📋 Status: Ausente\n"
                if doc.can_auto_generate:
                    section += "- 🤖 Pode ser gerado automaticamente\n"
                for issue in doc.issues:
                    section += f"- ⚠️ {issue}\n"
                section += "\n"
        
        return section
    
    def _generate_issues_and_recommendations(self, result: ClassificationResult) -> str:
        """Gera a seção de pendências e recomendações."""
        section = "## 🔍 Pendências e Recomendações\n\n"
        
        if result.blocking_issues:
            section += "### 🚫 Pendências Bloqueantes\n\n"
            section += "**Estas pendências impedem o prosseguimento e devem ser resolvidas imediatamente:**\n\n"
            for i, issue in enumerate(result.blocking_issues, 1):
                section += f"{i}. {issue}\n"
            section += "\n**Ação Requerida:** Solicitar documentos/correções ao cliente.\n\n"
        
        if result.non_blocking_issues:
            section += "### ⚠️ Pendências Não-Bloqueantes\n\n"
            section += "**Estas pendências podem ser resolvidas posteriormente ou automaticamente:**\n\n"
            for i, issue in enumerate(result.non_blocking_issues, 1):
                section += f"{i}. {issue}\n"
            section += "\n**Ação Recomendada:** Resolver quando possível ou aguardar resolução automática.\n\n"
        
        if not result.blocking_issues and not result.non_blocking_issues:
            section += "### ✅ Nenhuma Pendência Identificada\n\n"
            section += "Todos os requisitos foram atendidos satisfatoriamente.\n\n"
        
        return section
    
    def _generate_auto_actions_section(self, result: ClassificationResult) -> str:
        """Gera a seção de ações automáticas."""
        section = "## 🤖 Ações Automáticas Disponíveis\n\n"
        
        section += "**O sistema pode executar as seguintes ações automaticamente:**\n\n"
        for i, action in enumerate(result.auto_actions_possible, 1):
            section += f"{i}. {action}\n"
        
        section += "\n**Status:** Ações serão executadas automaticamente pelo sistema.\n"
        section += "**Tempo Estimado:** 2-5 minutos por ação.\n\n"
        
        return section
    
    def _generate_technical_details(self, result: ClassificationResult) -> str:
        """Gera os detalhes técnicos."""
        section = "## 🔧 Detalhes Técnicos\n\n"
        
        section += "### Configuração de Documentos\n\n"
        section += "| Documento | Obrigatório | Prazo Máximo | Auto-Gerável |\n"
        section += "|-----------|-------------|--------------|---------------|\n"
        
        for doc_analysis in result.document_analyses:
            req = self.classification_service.requirements[doc_analysis.document_type]
            doc_name = self._get_document_display_name(doc_analysis.document_type)
            required = "✅" if req.required else "❌"
            max_age = f"{req.max_age_days} dias" if req.max_age_days else "N/A"
            auto_gen = "✅" if req.can_auto_generate else "❌"
            section += f"| {doc_name} | {required} | {max_age} | {auto_gen} |\n"
        
        section += "\n### Algoritmo de Classificação\n\n"
        section += "**Critérios de Aprovação:**\n"
        section += "- Todos os documentos obrigatórios presentes e válidos\n"
        section += "- Pelo menos um documento financeiro válido\n"
        section += "- Nenhuma pendência bloqueante identificada\n\n"
        
        section += "**Critérios de Pendência Bloqueante:**\n"
        section += "- Documentos obrigatórios ausentes (não auto-geráveis)\n"
        section += "- Documentos inválidos com blocking_if_invalid=True\n"
        section += "- Nenhum documento financeiro válido\n\n"
        
        section += "**Critérios de Pendência Não-Bloqueante:**\n"
        section += "- Documentos auto-geráveis ausentes ou inválidos\n"
        section += "- Documentos vencidos mas não-bloqueantes\n"
        section += "- Problemas menores de formatação\n\n"
        
        return section
    
    def _generate_footer(self, metadata: ReportMetadata) -> str:
        """Gera o rodapé do relatório."""
        footer = "---\n\n"
        footer += "**Relatório gerado automaticamente pelo Sistema de Triagem Documental v2.0**\n"
        footer += f"**Timestamp:** {metadata.generated_at.isoformat()}\n"
        footer += "**Fonte de Conhecimento:** FAQ.md (Versão 2.0 - com Automação IA)\n"
        footer += "**Algoritmo:** Classificação baseada em regras de negócio FIDC\n"
        
        return footer
    
    def _get_status_emoji(self, classification: ClassificationType) -> str:
        """Retorna o emoji apropriado para o status."""
        emoji_map = {
            ClassificationType.APROVADO: "✅",
            ClassificationType.PENDENCIA_BLOQUEANTE: "🚫",
            ClassificationType.PENDENCIA_NAO_BLOQUEANTE: "⚠️"
        }
        return emoji_map.get(classification, "❓")
    
    def _get_document_display_name(self, doc_type: DocumentType) -> str:
        """Retorna o nome de exibição do documento."""
        display_names = {
            DocumentType.CARTAO_CNPJ: "Cartão CNPJ emitido dentro dos 90 dias",
            DocumentType.CONTRATO_SOCIAL: "Último Contrato Social/Estatuto consolidado",
            DocumentType.PROCURACAO: "Procuração (se aplicável)",
            DocumentType.RG_CPF_SOCIOS: "RG e CPF dos sócios (≥10%) e signatários",
            DocumentType.COMPROVANTE_RESIDENCIA: "Comprovante de residência dos sócios",
            DocumentType.BALANCO_PATRIMONIAL: "Balanço Patrimonial",
            DocumentType.DEMONSTRACOES_FINANCEIRAS: "Demonstrações Financeiras",
            DocumentType.RELACAO_FATURAMENTO: "Relação de Faturamento",
            DocumentType.DECLARACAO_RELACIONAMENTO_CREDITO: "Declaração de relacionamento de crédito",
            DocumentType.RELATORIO_VISITA: "Relatório de Visita ao Cedente",
            DocumentType.ATA_COMITE_CREDITO: "Ata de Comitê de Crédito"
        }
        return display_names.get(doc_type, doc_type.value)

# Instância global do serviço
report_service = ReportService() 