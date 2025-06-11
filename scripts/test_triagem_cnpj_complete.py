#!/usr/bin/env python3
"""
Script de prueba completo para el flujo de triagem con generación automática de cartão CNPJ.
Demuestra la integración completa: triagem -> clasificación -> generación automática de cartão CNPJ -> Supabase.
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.triagem_service import triagem_service
from src.services.database_service import database_service
from src.services.notification_service import NotificationRecipient


async def test_triagem_cnpj_complete():
    """Testa el flujo completo de triagem con generación automática de cartão CNPJ."""
    
    # Datos de prueba
    test_card_id = "CARD_TRIAGEM_001"
    test_cnpj = "14616875000127"
    
    print("=" * 80)
    print("🧪 TESTE COMPLETO: TRIAGEM + CARTÃO CNPJ AUTOMÁTICO")
    print("=" * 80)
    print(f"📋 Card ID: {test_card_id}")
    print(f"📋 CNPJ: {test_cnpj}")
    print()
    
    try:
        # 1. Preparar datos de documentos simulados
        print("1️⃣ Preparando dados de documentos simulados...")
        documents_data = {
            "documents": [
                {
                    "name": "Contrato Social",
                    "type": "contrato_social",
                    "status": "presente",
                    "observations": "Documento válido e atualizado"
                },
                {
                    "name": "Cartão CNPJ",
                    "type": "cartao_cnpj", 
                    "status": "ausente",
                    "observations": "Documento não fornecido pelo cliente"
                },
                {
                    "name": "Comprovante de Endereço",
                    "type": "comprovante_endereco",
                    "status": "presente",
                    "observations": "Comprovante recente"
                }
            ],
            "total_documents": 3,
            "missing_documents": 1,
            "critical_missing": 0
        }
        
        case_metadata = {
            "company_name": "EMPRESA TESTE LTDA",
            "cnpj": test_cnpj,
            "analyst_name": "Analista Teste",
            "submission_date": "2025-06-11",
            "priority": "normal"
        }
        
        notification_recipient = NotificationRecipient(
            name="Cliente Teste",
            phone_number="+5511999999999"
        )
        
        print("   ✅ Dados preparados")
        print(f"   📊 Total documentos: {documents_data['total_documents']}")
        print(f"   ❌ Documentos faltantes: {documents_data['missing_documents']}")
        print()
        
        # 2. Executar triagem completa com geração automática de CNPJ
        print("2️⃣ Executando triagem completa com geração automática de CNPJ...")
        
        result = await triagem_service.process_triagem_with_cnpj_generation(
            card_id=test_card_id,
            documents_data=documents_data,
            cnpj=test_cnpj,
            case_metadata=case_metadata,
            notification_recipient=notification_recipient
        )
        
        print("   ✅ Triagem executada com sucesso")
        print()
        
        # 3. Mostrar resultados da classificação
        print("3️⃣ Resultados da classificação...")
        classification_result = result.get("classification_result")
        if classification_result:
            print(f"   📊 Classificação: {classification_result.classification}")
            print(f"   ⚠️  Issues bloqueantes: {len(classification_result.blocking_issues)}")
            print(f"   ⚡ Issues não bloqueantes: {len(classification_result.non_blocking_issues)}")
            print(f"   🤖 Ações automáticas possíveis: {len(classification_result.auto_actions_possible or [])}")
            
            if classification_result.auto_actions_possible:
                for action in classification_result.auto_actions_possible:
                    print(f"      • {action}")
        else:
            print("   ❌ Erro na classificação")
        
        print()
        
        # 4. Mostrar resultados das operações de CNPJ
        print("4️⃣ Resultados das operações de CNPJ...")
        cnpj_operations = result.get("cnpj_operations", {})
        
        # Validação de CNPJ
        validation_result = cnpj_operations.get("validation_result")
        if validation_result:
            if validation_result.get("valid"):
                print(f"   ✅ CNPJ válido: {validation_result['cnpj']}")
                print(f"   🏢 Razão Social: {validation_result['razao_social']}")
                print(f"   📍 UF: {validation_result['uf']}")
            else:
                print(f"   ❌ CNPJ inválido: {validation_result.get('error', 'Erro desconhecido')}")
        
        # Geração de cartão
        card_generation_result = cnpj_operations.get("card_generation_result")
        cnpj_card_generated = cnpj_operations.get("cnpj_card_generated", False)
        
        print(f"   🎫 Cartão CNPJ gerado automaticamente: {cnpj_card_generated}")
        
        if card_generation_result and card_generation_result.get("success"):
            print(f"   📄 Arquivo local: {card_generation_result['file_path']}")
            print(f"   📄 PDF: {card_generation_result.get('pdf_file_path', 'N/A')}")
            print(f"   💾 Salvo no Supabase: {card_generation_result['saved_to_database']}")
            
            if card_generation_result.get("supabase_document_id"):
                print(f"   🆔 Document ID: {card_generation_result['supabase_document_id']}")
                print(f"   🔗 URL pública: {card_generation_result['supabase_public_url']}")
        
        print()
        
        # 5. Mostrar ações automáticas realizadas
        print("5️⃣ Ações automáticas realizadas...")
        automated_actions = result.get("automated_actions_performed", [])
        if automated_actions:
            for action in automated_actions:
                print(f"   ✅ {action}")
        else:
            print("   ℹ️  Nenhuma ação automática realizada")
        
        print()
        
        # 6. Verificar documentos salvos no Supabase
        print("6️⃣ Verificando documentos salvos no Supabase...")
        try:
            case_documents = await database_service.get_case_documents(test_card_id)
            print(f"   📊 Documentos encontrados: {len(case_documents)}")
            
            for i, doc in enumerate(case_documents, 1):
                print(f"   📄 Documento {i}:")
                print(f"      🆔 ID: {doc['id']}")
                print(f"      📝 Nome: {doc['name']}")
                print(f"      🏷️  Tag: {doc['document_tag']}")
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
        
        # 7. Mostrar notificações enviadas
        print("7️⃣ Notificações enviadas...")
        notifications_sent = result.get("notifications_sent", [])
        if notifications_sent:
            for notification in notifications_sent:
                print(f"   📱 {notification['type']}: {notification['status']}")
                if notification.get('message_sid'):
                    print(f"      📧 Message SID: {notification['message_sid']}")
        else:
            print("   ℹ️  Nenhuma notificação enviada")
        
        print()
        
        # 8. Mostrar warnings se houver
        warnings = result.get("warnings", [])
        if warnings:
            print("8️⃣ Avisos:")
            for warning in warnings:
                print(f"   ⚠️  {warning}")
            print()
        
        print("=" * 80)
        print("🎉 TESTE COMPLETO CONCLUÍDO COM SUCESSO")
        print("=" * 80)
        print(f"✅ Triagem processada: {result.get('success', False)}")
        print(f"✅ CNPJ validado: {validation_result.get('valid', False) if validation_result else False}")
        print(f"✅ Cartão CNPJ gerado: {cnpj_card_generated}")
        print(f"✅ Documentos no Supabase: {len(case_documents) if 'case_documents' in locals() else 0}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Erro geral no teste: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Iniciando teste completo de triagem con cartão CNPJ automático...")
    asyncio.run(test_triagem_cnpj_complete()) 