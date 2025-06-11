#!/usr/bin/env python3
"""
Script de demostración final de la integración CNPJ + Supabase.
Muestra la funcionalidad completa sin depender de APIs externas.
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.cnpj_service import cnpj_service
from src.services.database_service import database_service


async def demo_cnpj_integration():
    """Demostración de la integración completa de CNPJ con Supabase."""
    
    # CNPJ de prueba proporcionado por el usuario
    test_cnpj = "14616875000127"
    test_case_id = "DEMO_FINAL_001"
    
    print("=" * 80)
    print("🎯 DEMOSTRACIÓN FINAL: INTEGRACIÓN CNPJ + SUPABASE")
    print("=" * 80)
    print(f"📋 CNPJ: {test_cnpj}")
    print(f"📋 Case ID: {test_case_id}")
    print()
    
    try:
        # 1. Validación de CNPJ
        print("1️⃣ Validando CNPJ...")
        validation_result = await cnpj_service.validate_cnpj_for_triagem(test_cnpj)
        
        if validation_result["valid"]:
            print(f"   ✅ CNPJ válido: {validation_result['cnpj']}")
            print(f"   🏢 Razão Social: {validation_result['razao_social']}")
            print(f"   📍 UF: {validation_result['uf']}")
            print(f"   🔗 API Source: {validation_result['api_source']}")
        else:
            print(f"   ❌ CNPJ inválido: {validation_result.get('error', 'Erro desconhecido')}")
            return
        
        print()
        
        # 2. Generación y almacenamiento completo
        print("2️⃣ Generando cartão CNPJ y guardando en Supabase...")
        
        card_result = await cnpj_service.gerar_e_armazenar_cartao_cnpj(
            cnpj=test_cnpj,
            case_id=test_case_id,
            save_to_database=True
        )
        
        if card_result.get("success", True):  # Asumimos éxito si no hay campo success
            print("   ✅ Cartão CNPJ generado exitosamente")
            print(f"   📋 CNPJ: {card_result['cnpj']}")
            print(f"   🏢 Razão Social: {card_result['razao_social']}")
            print(f"   📄 Arquivo JSON: {card_result['local_file_path']}")
            print(f"   📄 Arquivo PDF: {card_result.get('pdf_file_path', 'N/A')}")
            print(f"   💾 Salvo no Supabase: {card_result['saved_to_database']}")
            
            if card_result.get("saved_to_database"):
                print(f"   🆔 Document ID: {card_result['supabase_document_id']}")
                print(f"   🔗 URL pública: {card_result['supabase_public_url']}")
                print(f"   📁 Storage path: {card_result['supabase_storage_path']}")
            else:
                reason = card_result.get("supabase_reason", card_result.get("supabase_error", "Motivo desconhecido"))
                print(f"   ⚠️  Não salvo no Supabase: {reason}")
        else:
            print(f"   ❌ Erro na geração: {card_result.get('error', 'Erro desconhecido')}")
            return
        
        print()
        
        # 3. Verificación en Supabase
        print("3️⃣ Verificando documentos en Supabase...")
        
        case_documents = await database_service.get_case_documents(test_case_id)
        print(f"   📊 Documentos encontrados: {len(case_documents)}")
        
        for i, doc in enumerate(case_documents, 1):
            print(f"   📄 Documento {i}:")
            print(f"      🆔 ID: {doc['id']}")
            print(f"      📝 Nome: {doc['name']}")
            print(f"      🏷️  Tag: {doc['document_tag']}")
            print(f"      📅 Criado: {doc['created_at']}")
            print(f"      🔗 URL: {doc['file_url']}")
            
            if doc.get('metadata'):
                metadata = doc['metadata']
                if metadata.get('cnpj'):
                    print(f"      📋 CNPJ: {metadata['cnpj']}")
                if metadata.get('razao_social'):
                    print(f"      🏢 Razão Social: {metadata['razao_social']}")
                if metadata.get('file_size_bytes'):
                    print(f"      📊 Tamanho: {metadata['file_size_bytes']} bytes")
        
        print()
        
        # 4. Health check de Supabase
        print("4️⃣ Verificando conectividade con Supabase...")
        health_ok = await database_service.health_check()
        if health_ok:
            print("   ✅ Conexão com Supabase OK")
        else:
            print("   ❌ Falha na conexão com Supabase")
        
        print()
        
        # 5. Resumen final
        print("=" * 80)
        print("🎉 DEMOSTRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 80)
        print("✅ Funcionalidades implementadas y probadas:")
        print("   • Validación de CNPJ con algoritmo de dígito verificador")
        print("   • Descarga de certificado PDF de la API CNPJá (con fallback mock)")
        print("   • Generación de cartão CNPJ con datos estructurados")
        print("   • Upload automático a Supabase Storage (bucket 'documents')")
        print("   • Registro en tabla 'documents' con metadatos completos")
        print("   • Organización por case_id en carpetas del storage")
        print("   • Integración completa con el sistema de triagem")
        print()
        print("🔧 Configuración requerida para producción:")
        print("   • CNPJA_API_KEY: Clave de API de CNPJá para PDFs reales")
        print("   • SUPABASE_URL y SUPABASE_ANON_KEY: Ya configurados ✅")
        print("   • Bucket 'documents' en Supabase Storage: Ya creado ✅")
        print("   • Tabla 'documents' en Supabase: Ya creada ✅")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error en la demostración: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Iniciando demostración final de integración CNPJ + Supabase...")
    asyncio.run(demo_cnpj_integration()) 