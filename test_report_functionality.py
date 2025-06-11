#!/usr/bin/env python3

"""
Script de prueba manual para la funcionalidad de generación de reportes.
Permite probar diferentes tipos de reportes con casos de ejemplo.
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.report_service import (
    report_service,
    ReportMetadata
)
from src.services.classification_service import (
    ClassificationResult,
    DocumentAnalysis,
    ClassificationType,
    DocumentType
)

def create_sample_metadata() -> ReportMetadata:
    """Cria metadados de exemplo para os relatórios."""
    return ReportMetadata(
        generated_at=datetime.now(),
        case_id="CASE-2024-001",
        company_name="Empresa Exemplo S.A.",
        cnpj="12.345.678/0001-99",
        analyst="Maria Silva"
    )

def create_approved_case() -> ClassificationResult:
    """Cria um caso aprovado para teste."""
    analyses = [
        DocumentAnalysis(DocumentType.CARTAO_CNPJ, True, True, [], 15),
        DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, True, True, [], 45),
        DocumentAnalysis(DocumentType.RG_CPF_SOCIOS, True, True, []),
        DocumentAnalysis(DocumentType.COMPROVANTE_RESIDENCIA, True, True, [], 25),
        DocumentAnalysis(DocumentType.BALANCO_PATRIMONIAL, True, True, [], 180),
        DocumentAnalysis(DocumentType.DEMONSTRACOES_FINANCEIRAS, True, True, [], 90)
    ]
    
    return ClassificationResult(
        classification=ClassificationType.APROVADO,
        confidence_score=0.95,
        summary="Documentação completa e aprovada",
        document_analyses=analyses,
        blocking_issues=[],
        non_blocking_issues=[],
        auto_actions_possible=[]
    )

def create_blocking_issues_case() -> ClassificationResult:
    """Cria um caso com pendências bloqueantes para teste."""
    analyses = [
        DocumentAnalysis(DocumentType.CARTAO_CNPJ, True, True, [], 15),
        DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, False, False, ["Documento obrigatório ausente"], None),
        DocumentAnalysis(DocumentType.RG_CPF_SOCIOS, False, False, ["Documento obrigatório ausente"], None),
        DocumentAnalysis(DocumentType.BALANCO_PATRIMONIAL, True, False, ["Documento vencido há mais de 365 dias"], 400),
        DocumentAnalysis(DocumentType.DEMONSTRACOES_FINANCEIRAS, False, False, ["Nenhum documento financeiro válido"], None)
    ]
    
    return ClassificationResult(
        classification=ClassificationType.PENDENCIA_BLOQUEANTE,
        confidence_score=0.15,
        summary="Múltiplas pendências bloqueantes identificadas",
        document_analyses=analyses,
        blocking_issues=[
            "Contrato Social obrigatório ausente",
            "RG/CPF dos sócios obrigatório ausente",
            "Balanço Patrimonial vencido (400 dias)",
            "Nenhum documento financeiro válido presente"
        ],
        non_blocking_issues=[],
        auto_actions_possible=[]
    )

def create_non_blocking_issues_case() -> ClassificationResult:
    """Cria um caso com pendências não-bloqueantes para teste."""
    analyses = [
        DocumentAnalysis(DocumentType.CARTAO_CNPJ, False, False, ["Documento ausente mas auto-gerável"], None, True),
        DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, True, True, [], 45),
        DocumentAnalysis(DocumentType.RG_CPF_SOCIOS, True, True, []),
        DocumentAnalysis(DocumentType.COMPROVANTE_RESIDENCIA, True, False, ["Documento vencido mas não-bloqueante"], 95),
        DocumentAnalysis(DocumentType.BALANCO_PATRIMONIAL, True, True, [], 180),
        DocumentAnalysis(DocumentType.PROCURACAO, False, False, ["Documento opcional ausente"], None)
    ]
    
    return ClassificationResult(
        classification=ClassificationType.PENDENCIA_NAO_BLOQUEANTE,
        confidence_score=0.75,
        summary="Pendências menores que podem ser resolvidas automaticamente",
        document_analyses=analyses,
        blocking_issues=[],
        non_blocking_issues=[
            "Cartão CNPJ ausente",
            "Comprovante de residência vencido (95 dias)",
            "Procuração opcional ausente"
        ],
        auto_actions_possible=[
            "Gerar automaticamente: Cartão CNPJ via CNPJá API",
            "Solicitar novo comprovante de residência via WhatsApp"
        ]
    )

def test_detailed_reports():
    """Testa a geração de relatórios detalhados."""
    print("=" * 80)
    print("🧪 TESTE DE RELATÓRIOS DETALHADOS")
    print("=" * 80)
    
    metadata = create_sample_metadata()
    
    # Teste 1: Caso Aprovado
    print("\n📋 TESTE 1: Caso Aprovado")
    print("-" * 40)
    approved_case = create_approved_case()
    detailed_report = report_service.generate_detailed_report(
        approved_case, 
        metadata, 
        include_technical_details=True
    )
    
    print("✅ Relatório detalhado gerado com sucesso!")
    print(f"📊 Tamanho: {len(detailed_report)} caracteres")
    print(f"📄 Linhas: {detailed_report.count(chr(10))} linhas")
    
    # Salvar relatório
    with open("report_approved_detailed.md", "w", encoding="utf-8") as f:
        f.write(detailed_report)
    print("💾 Salvo como: report_approved_detailed.md")
    
    # Teste 2: Caso com Pendências Bloqueantes
    print("\n📋 TESTE 2: Caso com Pendências Bloqueantes")
    print("-" * 40)
    blocking_case = create_blocking_issues_case()
    detailed_report = report_service.generate_detailed_report(
        blocking_case, 
        metadata, 
        include_technical_details=False
    )
    
    print("🚫 Relatório de pendências bloqueantes gerado!")
    print(f"📊 Tamanho: {len(detailed_report)} caracteres")
    print(f"📄 Linhas: {detailed_report.count(chr(10))} linhas")
    
    # Salvar relatório
    with open("report_blocking_detailed.md", "w", encoding="utf-8") as f:
        f.write(detailed_report)
    print("💾 Salvo como: report_blocking_detailed.md")
    
    # Teste 3: Caso com Pendências Não-Bloqueantes
    print("\n📋 TESTE 3: Caso com Pendências Não-Bloqueantes")
    print("-" * 40)
    non_blocking_case = create_non_blocking_issues_case()
    detailed_report = report_service.generate_detailed_report(
        non_blocking_case, 
        metadata, 
        include_technical_details=True
    )
    
    print("⚠️ Relatório de pendências não-bloqueantes gerado!")
    print(f"📊 Tamanho: {len(detailed_report)} caracteres")
    print(f"📄 Linhas: {detailed_report.count(chr(10))} linhas")
    
    # Salvar relatório
    with open("report_non_blocking_detailed.md", "w", encoding="utf-8") as f:
        f.write(detailed_report)
    print("💾 Salvo como: report_non_blocking_detailed.md")

def test_summary_reports():
    """Testa a geração de relatórios resumidos."""
    print("\n" + "=" * 80)
    print("📝 TESTE DE RELATÓRIOS RESUMIDOS")
    print("=" * 80)
    
    metadata = create_sample_metadata()
    
    # Teste 1: Resumo Aprovado
    print("\n📋 TESTE 1: Resumo Aprovado")
    print("-" * 40)
    approved_case = create_approved_case()
    summary_report = report_service.generate_summary_report(approved_case, metadata)
    
    print("✅ Resumo aprovado gerado!")
    print("📄 Conteúdo:")
    print(summary_report)
    print()
    
    # Teste 2: Resumo com Pendências Bloqueantes
    print("\n📋 TESTE 2: Resumo com Pendências Bloqueantes")
    print("-" * 40)
    blocking_case = create_blocking_issues_case()
    summary_report = report_service.generate_summary_report(blocking_case, metadata)
    
    print("🚫 Resumo bloqueante gerado!")
    print("📄 Conteúdo:")
    print(summary_report)
    print()
    
    # Teste 3: Resumo com Pendências Não-Bloqueantes
    print("\n📋 TESTE 3: Resumo com Pendências Não-Bloqueantes")
    print("-" * 40)
    non_blocking_case = create_non_blocking_issues_case()
    summary_report = report_service.generate_summary_report(non_blocking_case, metadata)
    
    print("⚠️ Resumo não-bloqueante gerado!")
    print("📄 Conteúdo:")
    print(summary_report)
    print()

def main():
    """Função principal do teste."""
    print("🚀 INICIANDO TESTES DE FUNCIONALIDADE DE RELATÓRIOS")
    print("=" * 80)
    print("📅 Data/Hora:", datetime.now().strftime("%d/%m/%Y às %H:%M:%S"))
    print("🔧 Versão: Sistema de Triagem Documental v2.0")
    print("📋 Fonte: FAQ.md (Versão 2.0 - com Automação IA)")
    
    try:
        # Executar todos os testes
        test_detailed_reports()
        test_summary_reports()
        
        print("\n" + "=" * 80)
        print("✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
        print("=" * 80)
        print("📁 Arquivos gerados:")
        print("   - report_approved_detailed.md")
        print("   - report_blocking_detailed.md")
        print("   - report_non_blocking_detailed.md")
        print("\n💡 Dica: Abra os arquivos .md para visualizar os relatórios formatados")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE OS TESTES: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())