#!/usr/bin/env python3
"""
Script para probar la conexión y operaciones básicas con Supabase.
Adaptado para usar FAQ.pdf como knowledge base en lugar de checklist_config.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz al path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

from src.services.database_service import (
    database_service, 
    CaseTrackingRecord, 
    ProcessingLogRecord, 
    NotificationRecord
)
from src.config.settings import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_connection():
    """Prueba la conexión básica con Supabase."""
    print("🔗 Probando conexión con Supabase...")
    
    try:
        health_ok = await database_service.health_check()
        if health_ok:
            print("✅ Conexión exitosa con Supabase")
            return True
        else:
            print("❌ Fallo en health check")
            return False
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

async def test_system_config():
    """Prueba operaciones de configuración del sistema."""
    print("\n⚙️  Probando configuraciones del sistema...")
    
    try:
        # Obtener destinatarios de notificaciones
        recipients = await database_service.get_notification_recipients()
        print(f"✅ Destinatarios encontrados: {len(recipients)}")
        
        for recipient in recipients:
            print(f"   • {recipient.get('name', 'Sin nombre')} - {recipient.get('phone_number', 'Sin teléfono')}")
        
        # Obtener configuración de fases Pipefy
        pipefy_phases = await database_service.get_system_config("pipefy_phases")
        if pipefy_phases:
            print("✅ Configuración de fases Pipefy encontrada:")
            for phase, id in pipefy_phases.items():
                print(f"   • {phase}: {id}")
        else:
            print("⚠️  Configuración de fases Pipefy no encontrada")
        
        # Obtener reglas de clasificación
        classification_rules = await database_service.get_system_config("classification_rules")
        if classification_rules:
            print("✅ Reglas de clasificación encontradas:")
            for rule, value in classification_rules.items():
                print(f"   • {rule}: {value}")
        else:
            print("⚠️  Reglas de clasificación no encontradas")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando configuraciones: {e}")
        return False

async def test_case_tracking():
    """Prueba operaciones de tracking de casos."""
    print("\n📋 Probando tracking de casos...")
    
    try:
        # Crear un caso de prueba
        test_case_id = f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        case_record = CaseTrackingRecord(
            case_id=test_case_id,
            company_name="Empresa de Prueba S.A.",
            cnpj="12345678000195",
            analyst_name="Analista de Prueba",
            classification_result={
                "status": "pending",
                "blocking_issues": ["Documento faltante", "CNPJ inválido"],
                "score": 7.5
            },
            pipefy_card_id="12345",
            processing_status="pending"
        )
        
        # Crear el caso
        created_case = await database_service.create_case_tracking(case_record)
        print(f"✅ Caso creado: {created_case.get('case_id', 'ID no disponible')}")
        
        # Obtener el caso
        retrieved_case = await database_service.get_case_tracking(test_case_id)
        if retrieved_case:
            print(f"✅ Caso recuperado: {retrieved_case['company_name']}")
        else:
            print("❌ No se pudo recuperar el caso")
            return False
        
        # Actualizar el caso
        updates = {
            "processing_status": "completed",
            "phase_moved_to": "338000018",
            "processed_at": datetime.now().isoformat()
        }
        
        updated_case = await database_service.update_case_tracking(test_case_id, updates)
        print(f"✅ Caso actualizado: status = {updated_case.get('processing_status', 'N/A')}")
        
        # Listar casos por status
        pending_cases = await database_service.list_cases_by_status("pending", limit=5)
        print(f"✅ Casos pendientes encontrados: {len(pending_cases)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando tracking de casos: {e}")
        return False

async def test_processing_logs():
    """Prueba operaciones de logs de procesamiento."""
    print("\n📝 Probando logs de procesamiento...")
    
    try:
        test_case_id = f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Agregar varios logs
        logs_to_add = [
            ProcessingLogRecord(
                case_id=test_case_id,
                log_level="INFO",
                component="triagem_service",
                message="Iniciando procesamiento de caso",
                details={"step": "initialization"}
            ),
            ProcessingLogRecord(
                case_id=test_case_id,
                log_level="WARNING",
                component="document_classifier",
                message="Documento con calidad baja detectado",
                details={"quality_score": 0.6}
            ),
            ProcessingLogRecord(
                case_id=test_case_id,
                log_level="ERROR",
                component="pipefy_integration",
                message="Error al mover card en Pipefy",
                error_details={"error_code": "PIPEFY_001", "retry_count": 1}
            )
        ]
        
        for log_record in logs_to_add:
            created_log = await database_service.add_processing_log(log_record)
            print(f"✅ Log agregado: {log_record.log_level} - {log_record.message[:50]}...")
        
        # Obtener todos los logs del caso
        all_logs = await database_service.get_case_logs(test_case_id)
        print(f"✅ Total de logs recuperados: {len(all_logs)}")
        
        # Obtener solo logs de error
        error_logs = await database_service.get_case_logs(test_case_id, "ERROR")
        print(f"✅ Logs de error recuperados: {len(error_logs)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando logs de procesamiento: {e}")
        return False

async def test_notification_history():
    """Prueba operaciones de historial de notificaciones."""
    print("\n📱 Probando historial de notificaciones...")
    
    try:
        test_case_id = f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Crear notificaciones de prueba
        notifications = [
            NotificationRecord(
                case_id=test_case_id,
                notification_type="blocking_issues",
                recipient_name="Analista Principal",
                recipient_phone="+5511999999999",
                message_content="Pendencias bloqueantes detectadas en caso TEST",
                twilio_message_sid="SM123456789",
                delivery_status="sent"
            ),
            NotificationRecord(
                case_id=test_case_id,
                notification_type="approval",
                recipient_name="Supervisor",
                recipient_phone="+5511888888888",
                message_content="Caso aprovado para emissão de documentos",
                twilio_message_sid="SM987654321",
                delivery_status="delivered",
                delivered_at=datetime.now()
            )
        ]
        
        notification_ids = []
        for notif_record in notifications:
            created_notif = await database_service.add_notification_record(notif_record)
            notification_ids.append(created_notif.get('id'))
            print(f"✅ Notificación registrada: {notif_record.notification_type}")
        
        # Actualizar status de una notificación
        if notification_ids[0]:
            updated_notif = await database_service.update_notification_status(
                notification_ids[0],
                "delivered",
                datetime.now()
            )
            print(f"✅ Status de notificación actualizado: {updated_notif.get('delivery_status', 'N/A')}")
        
        # Obtener notificaciones del caso
        case_notifications = await database_service.get_case_notifications(test_case_id)
        print(f"✅ Notificaciones del caso recuperadas: {len(case_notifications)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando historial de notificaciones: {e}")
        return False

async def test_cleanup_operations():
    """Prueba operaciones de limpieza."""
    print("\n🧹 Probando operaciones de limpieza...")
    
    try:
        # Simular limpieza de logs antiguos (con 0 días para no eliminar nada real)
        deleted_count = await database_service.cleanup_old_logs(0)
        print(f"✅ Operación de limpieza ejecutada (simulación): {deleted_count} registros procesados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando operaciones de limpieza: {e}")
        return False

async def main():
    """Función principal del script de pruebas."""
    print("🧪 Iniciando pruebas de base de datos...")
    print("=" * 60)
    
    # Verificar configuración
    missing_vars = settings.validate_required_vars()
    if missing_vars:
        print(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        print("   Configura el archivo .env antes de continuar")
        return False
    
    print("✅ Variables de entorno verificadas")
    
    # Ejecutar pruebas
    tests = [
        ("Conexión", test_connection),
        ("Configuraciones del Sistema", test_system_config),
        ("Tracking de Casos", test_case_tracking),
        ("Logs de Procesamiento", test_processing_logs),
        ("Historial de Notificaciones", test_notification_history),
        ("Operaciones de Limpieza", test_cleanup_operations)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error en prueba '{test_name}': {e}")
            results.append((test_name, False))
    
    # Resumen de resultados
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status:10} | {test_name}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"Resultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La base de datos está funcionando correctamente.")
        print("✨ El sistema está listo para usar con FAQ.pdf como knowledge base")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa la configuración y conexión.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)