#!/usr/bin/env python3
"""
Script de prueba completo para demostrar la integración automática
de métricas con el sistema de manejo de errores.
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

# Importar módulos necesarios
from utils.error_handler import with_error_handling, RetryConfig, get_metrics_service
from services.metrics_service import ServiceType

# Funciones de prueba decoradas con error handling

@with_error_handling("pipefy", RetryConfig(max_retries=2, base_delay=0.1))
async def test_pipefy_success():
    """Simula una llamada exitosa a Pipefy."""
    await asyncio.sleep(0.1)  # Simular latencia
    return {"status": "success", "card_id": "12345"}

@with_error_handling("pipefy", RetryConfig(max_retries=2, base_delay=0.1))
async def test_pipefy_failure():
    """Simula una falla en Pipefy."""
    await asyncio.sleep(0.05)
    raise Exception("Pipefy API rate limit exceeded")

@with_error_handling("crewai", RetryConfig(max_retries=1, base_delay=0.2))
async def test_crewai_timeout():
    """Simula un timeout en CrewAI."""
    await asyncio.sleep(0.05)
    raise asyncio.TimeoutError("CrewAI service timeout")

@with_error_handling("twilio")  # Usar configuración por defecto
async def test_twilio_success():
    """Simula una llamada exitosa a Twilio."""
    await asyncio.sleep(0.15)
    return {"message_sid": "SM123456", "status": "sent"}

@with_error_handling("cnpj", RetryConfig(max_retries=1, base_delay=0.1))
def test_cnpj_sync_success():
    """Simula una llamada síncrona exitosa a CNPJ."""
    time.sleep(0.12)
    return {"cnpj": "12345678000199", "company": "Test Company Ltd"}

@with_error_handling("supabase", RetryConfig(max_retries=1, base_delay=0.1))
async def test_supabase_failure():
    """Simula una falla en Supabase."""
    await asyncio.sleep(0.08)
    raise ConnectionError("Database connection lost")

async def run_comprehensive_test():
    """Ejecuta una prueba completa del sistema integrado."""
    logger.info("🚀 Iniciando prueba completa de integración...")
    
    # Limpiar métricas antes de empezar
    metrics_service = get_metrics_service()
    if metrics_service:
        metrics_service.clear_metrics()
        metrics_service.clear_alerts()
        logger.info("🧹 Métricas y alertas limpiadas")
    
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
        logger.error(f"❌ Error inesperado en operaciones exitosas: {e}")
    
    # Test 2: Operaciones con fallos
    logger.info("\n📊 Test 2: Operaciones con fallos (esperados)")
    
    # Pipefy failure (con retry)
    try:
        await test_pipefy_failure()
    except Exception as e:
        logger.info(f"🔥 Pipefy failure (esperado): {e}")
    
    # CrewAI timeout (con retry)
    try:
        await test_crewai_timeout()
    except Exception as e:
        logger.info(f"⏱️ CrewAI timeout (esperado): {e}")
    
    # Supabase connection error (con retry)
    try:
        await test_supabase_failure()
    except Exception as e:
        logger.info(f"💥 Supabase failure (esperado): {e}")
    
    # Test 3: Carga de trabajo mixta
    logger.info("\n📊 Test 3: Carga de trabajo mixta")
    
    # Ejecutar múltiples operaciones en paralelo
    tasks = []
    
    # Agregar operaciones exitosas
    for i in range(3):
        tasks.append(test_pipefy_success())
        tasks.append(test_twilio_success())
    
    # Agregar algunas operaciones que fallan
    tasks.append(test_pipefy_failure())
    tasks.append(test_crewai_timeout())
    
    # Ejecutar todas en paralelo
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = sum(1 for r in results if not isinstance(r, Exception))
    failures = len(results) - successes
    
    logger.info(f"📈 Operaciones paralelas: {successes} éxitos, {failures} fallos")
    
    # Test 4: Operaciones síncronas adicionales
    logger.info("\n📊 Test 4: Operaciones síncronas adicionales")
    for i in range(3):
        try:
            result = test_cnpj_sync_success()
            logger.info(f"✅ CNPJ sync #{i+1}: {result['company']}")
        except Exception as e:
            logger.error(f"❌ CNPJ sync #{i+1} error: {e}")
    
    # Mostrar métricas finales integradas
    await show_final_metrics()

async def show_final_metrics():
    """Muestra las métricas finales capturadas automáticamente."""
    logger.info("\n📈 MÉTRICAS FINALES (Capturadas Automáticamente):")
    
    metrics_service = get_metrics_service()
    if not metrics_service:
        logger.warning("⚠️ Servicio de métricas no disponible")
        return
    
    all_metrics = metrics_service.get_all_metrics()
    
    # Mostrar métricas por servicio
    for service_name, service_metrics in all_metrics["services"].items():
        if service_metrics['total_requests'] > 0:  # Solo mostrar servicios con actividad
            logger.info(f"\n🔧 {service_name.upper()}:")
            logger.info(f"  📊 Total requests: {service_metrics['total_requests']}")
            logger.info(f"  ✅ Successful: {service_metrics['successful_requests']}")
            logger.info(f"  ❌ Failed: {service_metrics['failed_requests']}")
            logger.info(f"  ⏱️ Timeouts: {service_metrics['timeout_requests']}")
            logger.info(f"  📈 Success rate: {service_metrics['success_rate']:.1f}%")
            logger.info(f"  ⚡ Avg response time: {service_metrics['avg_response_time_seconds']:.3f}s")
            logger.info(f"  🔄 Consecutive failures: {service_metrics['consecutive_failures']}")
            logger.info(f"  🚨 Circuit breaker open: {service_metrics['circuit_breaker_open']}")
            
            if service_metrics['last_success']:
                logger.info(f"  ✅ Last success: {service_metrics['last_success']}")
            if service_metrics['last_failure']:
                logger.info(f"  ❌ Last failure: {service_metrics['last_failure']}")
    
    # Mostrar alertas generadas automáticamente
    alerts = metrics_service.get_recent_alerts(hours=1)
    if alerts:
        logger.info(f"\n🚨 ALERTAS AUTOMÁTICAS GENERADAS ({len(alerts)}):")
        for alert in alerts:
            logger.info(f"  [{alert['level'].upper()}] {alert['service']}: {alert['message']}")
            if alert['context']:
                logger.info(f"    Context: {alert['context']}")
    else:
        logger.info("\n✅ No se generaron alertas automáticas")
    
    # Mostrar resumen general
    summary = all_metrics["summary"]
    logger.info(f"\n📋 RESUMEN GENERAL DEL SISTEMA:")
    logger.info(f"  📊 Total requests: {summary['total_requests']}")
    logger.info(f"  ✅ Total successful: {summary['total_successful']}")
    logger.info(f"  ❌ Total failed: {summary['total_failed']}")
    logger.info(f"  📈 Overall success rate: {summary['overall_success_rate']:.1f}%")
    logger.info(f"  🔥 Services with failures: {summary['services_with_failures']}")
    logger.info(f"  🚨 Services with circuit open: {summary['services_with_circuit_open']}")
    logger.info(f"  🏢 Total services monitored: {summary['total_services']}")
    
    # Exportar métricas a archivo
    export_file = "metrics_export.json"
    metrics_service.export_metrics(export_file)
    logger.info(f"\n💾 Métricas exportadas a: {export_file}")

def main():
    """Función principal."""
    try:
        asyncio.run(run_comprehensive_test())
        logger.info("\n🎉 Prueba completa de integración finalizada exitosamente!")
        logger.info("\n✨ El sistema ahora captura métricas automáticamente en todas las llamadas a APIs externas")
        logger.info("🔍 Revisa el archivo metrics_export.json para ver todas las métricas capturadas")
    except Exception as e:
        logger.error(f"💥 Error durante la prueba completa: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 