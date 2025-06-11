#!/usr/bin/env python3
"""
Script de prueba manual para la funcionalidad de clasificación de documentos.
Permite probar diferentes escenarios de clasificación sin necesidad de datos reales.

NOTA: Este servicio usa el FAQ.md como fuente única de conocimiento para evitar
confusión del agente de IA. Las reglas implementadas aquí reflejan exactamente
las especificaciones del FAQ v2.0 - Tabela 1: Checklist Simplificado.
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.classification_service import (
    classification_service,
    ClassificationType,
    DocumentType
)

def create_test_case_aprovado() -> Dict[str, Any]:
    """Crea un caso de teste com documentação completa e válida."""
    today = datetime.now()
    recent_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    
    return {
        'cartao_cnpj': {
            'present': True,
            'date': recent_date
        },
        'contrato_social': {
            'present': True,
            'date': recent_date,
            'has_registration_number': True
        },
        'rg_cpf_socios': {
            'present': True
        },
        'comprovante_residencia': {
            'present': True,
            'date': recent_date,
            'is_utility_bill': True
        },
        'balanco_patrimonial': {
            'present': True,
            'date': recent_date
        },
        'declaracao_relacionamento_credito': {
            'present': True,
            'date': recent_date
        },
        'relatorio_visita': {
            'present': True
        },
        'ata_comite_credito': {
            'present': True,
            'date': recent_date,
            'razao_social': 'Empresa Teste Ltda',
            'cnpj': '12345678000199',
            'limite_aprovado': '5000000',
            'data_aprovacao': recent_date
        }
    }

def create_test_case_pendencia_bloqueante() -> Dict[str, Any]:
    """Cria um caso com pendências bloqueantes."""
    return {
        'cartao_cnpj': {
            'present': True,
            'date': '2023-01-01'  # Muito antigo (>90 dias)
        },
        'contrato_social': {
            'present': False  # Documento obrigatório ausente
        },
        'rg_cpf_socios': {
            'present': False  # Documento obrigatório ausente
        },
        'comprovante_residencia': {
            'present': True,
            'date': '2024-01-01',
            'is_utility_bill': False  # Não é conta de concessionária
        },
        'declaracao_relacionamento_credito': {
            'present': False  # Documento obrigatório ausente
        },
        'relatorio_visita': {
            'present': False  # Documento obrigatório ausente
        },
        'ata_comite_credito': {
            'present': True,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'razao_social': 'Empresa Teste Ltda'
            # Faltam campos obrigatórios: cnpj, limite_aprovado, data_aprovacao
        }
    }

def create_test_case_pendencia_nao_bloqueante() -> Dict[str, Any]:
    """Cria um caso com pendências não-bloqueantes (auto-geráveis)."""
    today = datetime.now()
    recent_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    
    return {
        'cartao_cnpj': {
            'present': False  # Ausente mas pode ser gerado automaticamente
        },
        'contrato_social': {
            'present': True,
            'date': recent_date,
            'has_registration_number': True
        },
        'rg_cpf_socios': {
            'present': True
        },
        'comprovante_residencia': {
            'present': True,
            'date': recent_date,
            'is_utility_bill': True
        },
        'balanco_patrimonial': {
            'present': True,
            'date': recent_date
        },
        'declaracao_relacionamento_credito': {
            'present': True,
            'date': recent_date
        },
        'relatorio_visita': {
            'present': True
        },
        'ata_comite_credito': {
            'present': True,
            'date': recent_date,
            'razao_social': 'Empresa Teste Ltda',
            'cnpj': '12345678000199',
            'limite_aprovado': '5000000',
            'data_aprovacao': recent_date
        }
    }

def create_test_case_documentos_financeiros_alternativos() -> Dict[str, Any]:
    """Testa a lógica de documentos financeiros alternativos."""
    today = datetime.now()
    recent_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    
    return {
        'cartao_cnpj': {
            'present': True,
            'date': recent_date
        },
        'contrato_social': {
            'present': True,
            'date': recent_date,
            'has_registration_number': True
        },
        'rg_cpf_socios': {
            'present': True
        },
        'comprovante_residencia': {
            'present': True,
            'date': recent_date,
            'is_utility_bill': True
        },
        # Apenas um dos documentos financeiros presente
        'relacao_faturamento': {
            'present': True,
            'date': recent_date
        },
        # Os outros documentos financeiros ausentes (mas não devem gerar erro)
        'balanco_patrimonial': {
            'present': False
        },
        'demonstracoes_financeiras': {
            'present': False
        },
        'declaracao_relacionamento_credito': {
            'present': True,
            'date': recent_date
        },
        'relatorio_visita': {
            'present': True
        },
        'ata_comite_credito': {
            'present': True,
            'date': recent_date,
            'razao_social': 'Empresa Teste Ltda',
            'cnpj': '12345678000199',
            'limite_aprovado': '5000000',
            'data_aprovacao': recent_date
        }
    }

def print_classification_result(case_name: str, result):
    """Imprime o resultado da classificação de forma formatada."""
    print(f"\n{'='*60}")
    print(f"CASO DE TESTE: {case_name}")
    print(f"{'='*60}")
    
    print(f"\n🎯 CLASSIFICAÇÃO: {result.classification.value}")
    print(f"📊 CONFIANÇA: {result.confidence_score:.2%}")
    
    if result.blocking_issues:
        print(f"\n⚠️  PENDÊNCIAS BLOQUEANTES ({len(result.blocking_issues)}):")
        for issue in result.blocking_issues:
            print(f"   • {issue}")
    
    if result.non_blocking_issues:
        print(f"\n📋 PENDÊNCIAS NÃO-BLOQUEANTES ({len(result.non_blocking_issues)}):")
        for issue in result.non_blocking_issues:
            print(f"   • {issue}")
    
    if result.auto_actions_possible:
        print(f"\n🤖 AÇÕES AUTOMÁTICAS POSSÍVEIS ({len(result.auto_actions_possible)}):")
        for action in result.auto_actions_possible:
            print(f"   • {action}")
    
    print(f"\n📄 RESUMO COMPLETO:")
    print("-" * 40)
    print(result.summary)
    
    print(f"\n📈 ANÁLISE DETALHADA DOS DOCUMENTOS:")
    print("-" * 40)
    for analysis in result.document_analyses:
        status = "✅" if analysis.valid else "❌"
        presence = "Presente" if analysis.present else "Ausente"
        auto_gen = " (Auto-gerável)" if analysis.can_auto_generate else ""
        
        print(f"{status} {analysis.document_type.value}: {presence}{auto_gen}")
        
        if analysis.issues:
            for issue in analysis.issues:
                print(f"     ⚠️  {issue}")
        
        if analysis.age_days is not None:
            print(f"     📅 Idade: {analysis.age_days} dias")

def test_document_age_calculation():
    """Testa o cálculo de idade de documentos."""
    print(f"\n{'='*60}")
    print("TESTE: CÁLCULO DE IDADE DE DOCUMENTOS")
    print(f"{'='*60}")
    
    test_dates = [
        ('2024-01-15', 'Data ISO válida'),
        ('15/01/2024', 'Data DD/MM/YYYY'),
        ('01/15/2024', 'Data MM/DD/YYYY'),
        ('invalid-date', 'Data inválida'),
        ('2023-12-01T10:30:00Z', 'Data ISO com timezone')
    ]
    
    for date_str, description in test_dates:
        age = classification_service._calculate_document_age(date_str)
        print(f"📅 {description}: '{date_str}' → {age} dias")

def main():
    """Função principal que executa todos os testes."""
    print("🚀 INICIANDO TESTES DE CLASSIFICAÇÃO DE DOCUMENTOS")
    print("=" * 60)
    
    # Teste 1: Caso Aprovado
    case_aprovado = create_test_case_aprovado()
    result_aprovado = classification_service.classify_case(case_aprovado)
    print_classification_result("DOCUMENTAÇÃO COMPLETA E VÁLIDA", result_aprovado)
    
    # Teste 2: Pendência Bloqueante
    case_bloqueante = create_test_case_pendencia_bloqueante()
    result_bloqueante = classification_service.classify_case(case_bloqueante)
    print_classification_result("PENDÊNCIAS BLOQUEANTES", result_bloqueante)
    
    # Teste 3: Pendência Não-Bloqueante
    case_nao_bloqueante = create_test_case_pendencia_nao_bloqueante()
    result_nao_bloqueante = classification_service.classify_case(case_nao_bloqueante)
    print_classification_result("PENDÊNCIAS NÃO-BLOQUEANTES", result_nao_bloqueante)
    
    # Teste 4: Documentos Financeiros Alternativos
    case_alternativos = create_test_case_documentos_financeiros_alternativos()
    result_alternativos = classification_service.classify_case(case_alternativos)
    print_classification_result("DOCUMENTOS FINANCEIROS ALTERNATIVOS", result_alternativos)
    
    # Teste 5: Cálculo de Idade
    test_document_age_calculation()
    
    print(f"\n{'='*60}")
    print("✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
    print(f"{'='*60}")
    
    # Resumo dos resultados
    print(f"\n📊 RESUMO DOS RESULTADOS:")
    print(f"   • Caso Aprovado: {result_aprovado.classification.value} ({result_aprovado.confidence_score:.1%})")
    print(f"   • Pendência Bloqueante: {result_bloqueante.classification.value} ({result_bloqueante.confidence_score:.1%})")
    print(f"   • Pendência Não-Bloqueante: {result_nao_bloqueante.classification.value} ({result_nao_bloqueante.confidence_score:.1%})")
    print(f"   • Documentos Alternativos: {result_alternativos.classification.value} ({result_alternativos.confidence_score:.1%})")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERRO DURANTE A EXECUÇÃO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 