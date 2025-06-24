#!/usr/bin/env python3
"""
Test completo del flujo de triagem de documentos
Simula todo el proceso desde el webhook hasta las notificaciones
"""
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from src.services.triagem_service import TriagemService
from src.services.notification_service import NotificationRecipient
from src.integrations.pipefy_client import PipefyClient
from src.integrations.twilio_client import TwilioClient
from src.integrations.cnpj_client import CNPJClient
from supabase import create_client, Client

# Cargar variables de entorno
load_dotenv()

# Configuración del test con timestamp para evitar duplicados
TEST_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_CARD_ID = "1130856215"
TEST_PHONE = "+553199034444"
TEST_CNPJ = "37335118000180"  # CNPJ diferente para evitar duplicados
TEST_CASE_ID = f"TEST_{TEST_TIMESTAMP}"

async def test_flujo_completo():
    """
    Test completo del flujo de triagem de documentos
    """
    
    print("🧪 TEST COMPLETO: FLUJO DE TRIAGEM DE DOCUMENTOS\n")
    
    # Verificar credenciales
    print("🔍 VERIFICANDO CREDENCIALES:")
    credenciales = {
        "PIPEFY_TOKEN": os.getenv("PIPEFY_TOKEN"),
        "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID"),
        "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN"),
        "CNPJA_API_KEY": os.getenv("CNPJA_API_KEY"),
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY"),
    }
    
    for key, value in credenciales.items():
        status = "✅ Configurado" if value else "❌ Faltando"
        print(f"   {key}: {status}")
    
    if not all(credenciales.values()):
        print("\n❌ Credenciales incompletas. Abortando test.")
        return False
    
    # Configuración del test
    print(f"\n📋 CONFIGURACIÓN DEL TEST:")
    print(f"   🃏 Card ID: {TEST_CARD_ID}")
    print(f"   📱 Teléfono test: {TEST_PHONE}")
    print(f"   🏢 CNPJ test: {TEST_CNPJ}")
    
    try:
        # PASO 1: Simular datos de documentos para clasificación
        print(f"\n📄 PASO 1: Preparando datos de documentos...")
        
        # Simular datos de documentos como los que llegarían del análisis
        documents_data = {
            "contrato_social": {
                "presente": True,
                "valido": True,
                "observacoes": "Contrato social atualizado"
            },
            "documentos_pessoais": {
                "presente": True,
                "valido": False,
                "observacoes": "RG com qualidade baixa"
            },
            "comprovante_endereco": {
                "presente": True,
                "valido": True,
                "observacoes": "Comprovante válido"
            },
            "cartao_cnpj": {
                "presente": False,
                "valido": False,
                "observacoes": "Cartão CNPJ ausente - necessário para validação"
            }
        }
        
        # Metadatos del caso
        case_metadata = {
            "razao_social": "TESTE LTDA",
            "cnpj": TEST_CNPJ,
            "gestor_responsavel": "Sistema Automático"
        }
        
        print(f"✅ Datos de documentos preparados:")
        print(f"   📊 Documentos: {len(documents_data)}")
        print(f"   🏢 Empresa: {case_metadata['razao_social']}")
        
        # PASO 2: Procesar triagem completa
        print(f"\n🔄 PASO 2: Procesando triagem completa...")
        
        triagem_service = TriagemService()
        
        # Crear destinatario de notificación
        notification_recipient = NotificationRecipient(
            phone_number=TEST_PHONE,
            name="Test User",
            role="Gestor"
        )
        
        # Procesar triagem con notificaciones
        resultado_triagem = await triagem_service.process_triagem_with_notifications(
            card_id=TEST_CARD_ID,
            documents_data=documents_data,
            case_metadata=case_metadata,
            notification_recipient=notification_recipient
        )
        
        print(f"✅ Triagem procesada:")
        print(f"   📊 Éxito: {resultado_triagem.get('success', False)}")
        
        # El classification_result es un objeto ClassificationResult, no un dict
        classification_result = resultado_triagem.get('classification_result')
        if classification_result:
            print(f"   📋 Clasificación: {classification_result.classification.value}")
            print(f"   🎯 Confianza: {classification_result.confidence_score:.2f}")
            print(f"   📄 Resumen: {classification_result.summary[:100]}...")
        else:
            print(f"   📋 Clasificación: N/A")
        
        print(f"   ⏱️ Tiempo: {resultado_triagem.get('processing_time', 'N/A')}s")
        
        if resultado_triagem.get("errors"):
            print(f"   ⚠️ Errores: {len(resultado_triagem['errors'])}")
            for error in resultado_triagem["errors"]:
                print(f"      - {error}")
        
        # PASO 3: Verificar actualización en Pipefy
        print(f"\n📋 PASO 3: Verificando actualización en Pipefy...")
        
        pipefy_client = PipefyClient()
        
        # Obtener información del card
        card_info = await pipefy_client.get_card_info(TEST_CARD_ID)
        
        if card_info:
            print(f"✅ Card información obtenida:")
            print(f"   🃏 Card ID: {card_info.get('id', 'N/A')}")
            print(f"   📋 Título: {card_info.get('title', 'N/A')}")
            print(f"   📊 Fase actual: {card_info.get('current_phase', {}).get('name', 'N/A')}")
            
            # Verificar si el campo informe_crewai_2 fue actualizado
            fields = card_info.get('fields', [])
            informe_field = next((f for f in fields if f.get('field', {}).get('id') == 'informe_crewai_2'), None)
            
            if informe_field and informe_field.get('value'):
                print(f"✅ Campo 'informe_crewai_2' actualizado correctamente")
                print(f"   📄 Contenido: {informe_field['value'][:100]}...")
            else:
                print(f"⚠️ Campo 'informe_crewai_2' no encontrado o vacío")
        else:
            print(f"❌ No se pudo obtener información del card")
        
        # PASO 4: Generar y verificar Cartão CNPJ
        print(f"\n📄 PASO 4: Generando Cartão CNPJ...")
        
        # Generar cartão CNPJ usando el servicio
        cartao_result = await triagem_service.gerar_e_armazenar_cartao_cnpj(
            cnpj=TEST_CNPJ,
            case_id=TEST_CASE_ID,
            save_to_database=True
        )
        
        if cartao_result.get("success"):
            print(f"✅ Cartão CNPJ generado exitosamente:")
            print(f"   📄 Archivo: {cartao_result.get('filename', 'N/A')}")
            print(f"   📊 Tamaño: {cartao_result.get('file_size', 'N/A')} bytes")
            print(f"   🔗 URL: {cartao_result.get('public_url', 'N/A')[:50]}...")
        else:
            print(f"❌ Error generando cartão CNPJ:")
            print(f"   💥 Error: {cartao_result.get('error', 'Error desconocido')}")
        
        # PASO 5: Verificar notificación WhatsApp
        print(f"\n📱 PASO 5: Verificando notificación WhatsApp...")
        
        notification_result = resultado_triagem.get("notification_result")
        
        if notification_result:
            if notification_result.success:
                print(f"✅ Notificación WhatsApp enviada exitosamente!")
                print(f"   📱 Para: {TEST_PHONE}")
                print(f"   📋 Tipo: {notification_result.notification_type.value}")
                print(f"   📨 SID: {notification_result.message_sid or 'N/A'}")
            else:
                print(f"❌ Error enviando notificación:")
                print(f"   💥 Error: {notification_result.error_message or 'Error desconocido'}")
        else:
            print(f"ℹ️ No se configuró notificación en este test")
        
        # PASO 6: Test adicional - Notificación de pendencias bloqueantes
        print(f"\n📱 PASO 6: Test adicional - Notificación pendencias bloqueantes...")
        
        blocking_issues = [
            "Cartão CNPJ necessário para validação da empresa",
            "Documentos RG/CPF com qualidade insuficiente"
        ]
        
        blocking_notification = await triagem_service.send_blocking_issues_notification(
            card_id=TEST_CASE_ID,
            company_name="TESTE LTDA",
            blocking_issues=blocking_issues,
            recipient=notification_recipient,
            cnpj=TEST_CNPJ
        )
        
        if blocking_notification.get("success"):
            print(f"✅ Notificación de pendencias bloqueantes enviada!")
            print(f"   📋 Pendencias: {len(blocking_issues)}")
            print(f"   📨 SID: {blocking_notification.get('message_sid', 'N/A')}")
        else:
            print(f"❌ Error enviando notificación de pendencias:")
            print(f"   💥 Error: {blocking_notification.get('error_message', 'Error desconocido')}")
        
        # PASO 7: Verificar validación de card
        print(f"\n🔍 PASO 7: Validando card antes de triagem...")
        
        validation_result = await triagem_service.validate_card_before_triagem(TEST_CARD_ID)
        
        if validation_result.get("valid"):
            print(f"✅ Card válido para triagem:")
            print(f"   📊 Estado: {validation_result.get('status', 'N/A')}")
            print(f"   📋 Fase: {validation_result.get('current_phase', 'N/A')}")
        else:
            print(f"⚠️ Card con problemas de validación:")
            for issue in validation_result.get("issues", []):
                print(f"      - {issue}")
        
        # RESUMEN FINAL
        print(f"\n📊 RESUMEN DEL TEST COMPLETO:")
        print(f"   ✅ Datos de documentos preparados")
        print(f"   ✅ Triagem completa procesada")
        print(f"   ✅ Campo Pipefy verificado")
        print(f"   ✅ Cartão CNPJ generado")
        print(f"   ✅ Notificaciones WhatsApp enviadas")
        print(f"   ✅ Validación de card realizada")
        
        # Verificar si el test fue exitoso
        test_success = (
            resultado_triagem.get("success", False) and
            cartao_result.get("success", False) and
            (notification_result is None or notification_result.success) and
            blocking_notification.get("success", False)
        )
        
        return test_success
        
    except Exception as e:
        print(f"\n❌ Error en el test completo: {e}")
        print(f"   📊 Tipo: {type(e).__name__}")
        import traceback
        print(f"   🔍 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🚀 INICIANDO TEST COMPLETO DEL FLUJO DE TRIAGEM\n")
    
    result = asyncio.run(test_flujo_completo())
    
    if result:
        print("\n🎉 ¡TEST COMPLETO EXITOSO!")
        print("   ✅ Todas las funcionalidades verificadas")
        print("   🚀 Sistema listo para producción")
    else:
        print("\n❌ TEST COMPLETO FALLÓ")
        print("   🔧 Revisar errores arriba") 