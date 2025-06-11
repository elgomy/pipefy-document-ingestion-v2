#!/usr/bin/env python3
"""
Script de prueba para la integración completa de CNPJ con Supabase.
Testa el flujo completo: validación -> descarga PDF -> upload a Supabase -> registro en tabla documents.
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.cnpj_service import cnpj_service, CNPJServiceError
from src.services.database_service import database_service
from src.integrations.cnpj_client import cnpj_client, CNPJAPIError


async def test_cnpj_supabase_integration():
    """Testa la integración completa de CNPJ con Supabase."""
    
    # CNPJ de prueba proporcionado por el usuario
    test_cnpj = "14616875000127"
    test_case_id = "TEST_CASE_001"
    
    print("=" * 80)
    print("🧪 TESTE DE INTEGRAÇÃO CNPJ + SUPABASE")
    print("=" * 80)
    print(f"📋 CNPJ de teste: {test_cnpj}")
    print(f"📋 Case ID: {test_case_id}")
    print()
    
    try:
        # 1. Teste de validação de CNPJ
        print("1️⃣ Testando validação de CNPJ...")
        validation_result = await cnpj_service.validate_cnpj_for_triagem(test_cnpj)
        
        if validation_result["valid"]:
            print(f"   ✅ CNPJ válido: {validation_result['cnpj']}")
            print(f"   📊 Razão Social: {validation_result['razao_social']}")
            print(f"   🏢 Situação: {validation_result['situacao_cadastral']}")
            print(f"   📍 UF: {validation_result['uf']}")
            print(f"   🔗 API Source: {validation_result['api_source']}")
        else:
            print(f"   ❌ CNPJ inválido: {validation_result.get('error', 'Erro desconhecido')}")
            return
        
        print()
        
        # 2. Teste de download do certificado PDF
        print("2️⃣ Testando download do certificado PDF...")
        try:
            pdf_result = await cnpj_client.download_cnpj_certificate_pdf(test_cnpj)
            
            if pdf_result["success"]:
                print(f"   ✅ PDF baixado com sucesso")
                print(f"   📄 Arquivo: {pdf_result.get('file_path', 'Mock data')}")
                print(f"   📊 Tamanho: {pdf_result['file_size_bytes']} bytes")
                print(f"   🔗 API Source: {pdf_result['api_source']}")
                print(f"   📅 Baixado em: {pdf_result['downloaded_at']}")
                
                if pdf_result.get("mock_data"):
                    print("   ⚠️  Usando dados mock (CNPJA_API_KEY não configurada)")
            else:
                print(f"   ❌ Falha no download: {pdf_result.get('error', 'Erro desconhecido')}")
                
        except CNPJAPIError as e:
            print(f"   ❌ Erro da API: {e.message}")
        except Exception as e:
            print(f"   ❌ Erro inesperado: {e}")
        
        print()
        
        # 3. Teste de geração e armazenamento completo
        print("3️⃣ Testando geração e armazenamento completo...")
        try:
            card_result = await cnpj_service.gerar_e_armazenar_cartao_cnpj(
                cnpj=test_cnpj,
                case_id=test_case_id,
                save_to_database=True
            )
            
            print(f"   ✅ Cartão gerado com sucesso")
            print(f"   📋 CNPJ: {card_result['cnpj']}")
            print(f"   🏢 Razão Social: {card_result['razao_social']}")
            print(f"   📄 Arquivo local: {card_result['local_file_path']}")
            print(f"   💾 Salvo na base: {card_result['saved_to_database']}")
            
            if card_result.get("saved_to_database"):
                print(f"   🆔 Document ID: {card_result['supabase_document_id']}")
                print(f"   🔗 URL pública: {card_result['supabase_public_url']}")
                print(f"   📁 Storage path: {card_result['supabase_storage_path']}")
            else:
                reason = card_result.get("supabase_reason", card_result.get("supabase_error", "Motivo desconhecido"))
                print(f"   ⚠️  Não salvo na base: {reason}")
                
        except CNPJServiceError as e:
            print(f"   ❌ Erro do serviço CNPJ: {e}")
        except Exception as e:
            print(f"   ❌ Erro inesperado: {e}")
        
        print()
        
        # 4. Teste de consulta de documentos do caso
        print("4️⃣ Testando consulta de documentos do caso...")
        try:
            case_documents = await database_service.get_case_documents(test_case_id)
            
            print(f"   📊 Documentos encontrados: {len(case_documents)}")
            
            for i, doc in enumerate(case_documents, 1):
                print(f"   📄 Documento {i}:")
                print(f"      🆔 ID: {doc['id']}")
                print(f"      📝 Nome: {doc['name']}")
                print(f"      🏷️  Tag: {doc['document_tag']}")
                print(f"      🔗 URL: {doc['file_url']}")
                print(f"      📅 Criado: {doc['created_at']}")
                
                if doc.get('metadata'):
                    metadata = doc['metadata']
                    if metadata.get('cnpj'):
                        print(f"      📋 CNPJ: {metadata['cnpj']}")
                    if metadata.get('razao_social'):
                        print(f"      🏢 Razão Social: {metadata['razao_social']}")
                
        except Exception as e:
            print(f"   ❌ Erro ao consultar documentos: {e}")
        
        print()
        
        # 5. Teste de health check do Supabase
        print("5️⃣ Testando conectividade com Supabase...")
        try:
            health_ok = await database_service.health_check()
            if health_ok:
                print("   ✅ Conexão com Supabase OK")
            else:
                print("   ❌ Falha na conexão com Supabase")
        except Exception as e:
            print(f"   ❌ Erro no health check: {e}")
        
        print()
        print("=" * 80)
        print("🎉 TESTE CONCLUÍDO")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Erro geral no teste: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Iniciando teste de integração CNPJ + Supabase...")
    asyncio.run(test_cnpj_supabase_integration()) 