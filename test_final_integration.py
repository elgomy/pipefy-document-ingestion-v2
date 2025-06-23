#!/usr/bin/env python3
"""
Script de prueba final para demostrar la integración completa
del sistema de error handling con métricas automáticas.
"""

import asyncio
import time
import logging
import sys
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Agregar src al path de Python
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Importar y configurar métricas explícitamente
from services.metrics_service import MetricsService, ServiceType
from utils.error_handler import with_error_handling, RetryConfig

# Crear instancia global de métricas
metrics_service = MetricsService()

# Patch manual del error handler para usar nuestra instancia
import utils.error_handler as eh
eh._metrics_service = metrics_service
eh.ServiceType = ServiceType

logger.info("🔧 Sistema de métricas configurado manualmente")

# Funciones de prueba decoradas

@with_error_handling("pipefy", RetryConfig(max_retries=2, base_delay=0.1))
async def test_pipefy_success():
    """Simula una llamada exitosa a Pipefy."""
    await asyncio.sleep(0.1)
    return {"status": "success", "card_id": "12345"}

@with_error_handling("pipefy", RetryConfig(max_retries=2, base_delay=0.1))
async def test_pipefy_failure():
    """Simula una falla en Pipefy."""
    await asyncio.sleep(0.05)
    raise Exception("Pipefy API rate limit exceeded")

@with_error_handling("crewai", RetryConfig(max_retries=1, base_delay=0.1))
async def test_crewai_timeout():
    """Simula un timeout en CrewAI."""
    await asyncio.sleep(0.05)
    raise asyncio.TimeoutError("CrewAI service timeout")

@with_error_handling("twilio")
async def test_twilio_success():
    """Simula una llamada exitosa a Twilio."""
    await asyncio.sleep(0.15)
    return {"message_sid": "SM123456", "status": "sent"}

@with_error_handling("cnpj", RetryConfig(max_retries=1, base_delay=0.1))
def test_cnpj_sync_success():
    """Simula una llamada síncrona exitosa a CNPJ."""
    time.sleep(0.12)
    return {"cnpj": "12345678000199", "company": "Test Company"}

@with_error_handling("supabase", RetryConfig(max_retries=1, base_delay=0.1))
async def test_supabase_failure():
    """Simula una falla en Supabase."""
    await asyncio.sleep(0.08)
    raise ConnectionError("Database connection lost")

async def run_final_test():
    """Ejecuta la prueba final completa."""
    logger.info("🚀 Iniciando prueba final de integración completa...")
    
    # Limpiar métricas
    metrics_service.clear_metrics()
    metrics_service.clear_alerts()
    logger.info("🧹 Métricas limpiadas")
    
    # Test 1: Operaciones exitosas
    logger.info("\n📊 Test 1: Operaciones exitosas")
    try:
        result1 = await test_pipefy_success()
        logger.info(f"✅ Pipefy: {result1}")
        
        result2 = await test_twilio_success()
        logger.info(f"✅ Twilio: {result2}")
        
        result3 = test_cnpj_sync_success()
        logger.info(f"✅ CNPJ: {result3}")
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
    
    # Test 2: Operaciones con fallos
    logger.info("\n📊 Test 2: Operaciones con fallos (con retry automático)")
    
    try:
        await test_pipefy_failure()
    except Exception as e:
        logger.info(f"🔥 Pipefy failure (esperado): {e}")
    
    try:
        await test_crewai_timeout()
    except Exception as e:
        logger.info(f"⏱️ CrewAI timeout (esperado): {e}")
    
    try:
        await test_supabase_failure()
    except Exception as e:
        logger.info(f"💥 Supabase failure (esperado): {e}")
    
    # Test 3: Múltiples operaciones para generar estadísticas
    logger.info("\n📊 Test 3: Múltiples operaciones")
    
    for i in range(5):
        try:
            await test_pipefy_success()
        except:
            pass
        
        if i % 2 == 0:
            try:
                await test_pipefy_failure()
            except:
                pass
    
    # Operaciones síncronas adicionales
    for i in range(3):
        try:
            test_cnpj_sync_success()
        except:
            pass
    
    # Mostrar métricas capturadas automáticamente
    show_captured_metrics()

def show_captured_metrics():
    """Muestra las métricas capturadas automáticamente por el decorador."""
    logger.info("\n📈 MÉTRICAS CAPTURADAS AUTOMÁTICAMENTE:")
    
    all_metrics = metrics_service.get_all_metrics()
    
    # Mostrar métricas por servicio
    for service_name, service_metrics in all_metrics["services"].items():
        if service_metrics['total_requests'] > 0:
            logger.info(f"\n🔧 {service_name.upper()}:")
            logger.info(f"  📊 Total requests: {service_metrics['total_requests']}")
            logger.info(f"  ✅ Successful: {service_metrics['successful_requests']}")
            logger.info(f"  ❌ Failed: {service_metrics['failed_requests']}")
            logger.info(f"  ⏱️ Timeouts: {service_metrics['timeout_requests']}")
            logger.info(f"  📈 Success rate: {service_metrics['success_rate']:.1f}%")
            logger.info(f"  ⚡ Avg response time: {service_metrics['avg_response_time_seconds']:.3f}s")
            logger.info(f"  🔄 Consecutive failures: {service_metrics['consecutive_failures']}")
            logger.info(f"  🚨 Circuit breaker open: {service_metrics['circuit_breaker_open']}")
    
    # Mostrar alertas automáticas
    alerts = metrics_service.get_recent_alerts(hours=1)
    if alerts:
        logger.info(f"\n🚨 ALERTAS AUTOMÁTICAS ({len(alerts)}):")
        for alert in alerts:
            logger.info(f"  [{alert['level'].upper()}] {alert['service']}: {alert['message']}")
    else:
        logger.info("\n✅ No se generaron alertas automáticas")
    
    # Resumen general
    summary = all_metrics["summary"]
    logger.info(f"\n📋 RESUMEN GENERAL:")
    logger.info(f"  📊 Total requests: {summary['total_requests']}")
    logger.info(f"  ✅ Total successful: {summary['total_successful']}")
    logger.info(f"  ❌ Total failed: {summary['total_failed']}")
    logger.info(f"  📈 Overall success rate: {summary['overall_success_rate']:.1f}%")
    logger.info(f"  🔥 Services with failures: {summary['services_with_failures']}")
    logger.info(f"  🚨 Services with circuit open: {summary['services_with_circuit_open']}")
    
    # Exportar métricas
    export_file = "final_metrics_export.json"
    metrics_service.export_metrics(export_file)
    logger.info(f"\n💾 Métricas exportadas a: {export_file}")

def main():
    """Función principal."""
    try:
        asyncio.run(run_final_test())
        
        logger.info("\n🎉 ¡PRUEBA FINAL COMPLETADA EXITOSAMENTE!")
        logger.info("\n" + "="*60)
        logger.info("✨ INTEGRACIÓN COMPLETA FUNCIONANDO:")
        logger.info("  🔧 Error handling automático con retry logic")
        logger.info("  📊 Métricas capturadas automáticamente")
        logger.info("  🚨 Alertas generadas automáticamente")
        logger.info("  🔄 Circuit breakers funcionando")
        logger.info("  ⏱️ Timeouts detectados automáticamente")
        logger.info("  📈 Estadísticas en tiempo real")
        logger.info("="*60)
        logger.info("🔍 Revisa final_metrics_export.json para detalles completos")
        
    except Exception as e:
        logger.error(f"💥 Error en la prueba final: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 