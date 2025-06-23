#!/usr/bin/env python3
"""
Script de prueba para verificar la integración automática de métricas
con el sistema de manejo de errores.
"""

import asyncio
import time
import logging
import sys
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Importar desde el directorio src correcto
import sys
sys.path.append(str(Path(__file__).parent / "src"))

from utils.error_handler import with_error_handling, RetryConfig, get_metrics_service

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Funciones de prueba que simulan APIs externas

@with_error_handling("pipefy", RetryConfig(max_retries=2, base_delay=0.1))
async def test_pipefy_success():
    """Simula una llamada exitosa a Pipefy."""
    await asyncio.sleep(0.1)  # Simular latencia
    return {"status": "success", "data": "pipefy_data"}

@with_error_handling("pipefy", RetryConfig(max_retries=2, base_delay=0.1))
async def test_pipefy_failure():
    """Simula una falla en Pipefy."""
    await asyncio.sleep(0.05)
    raise Exception("Pipefy API error")

@with_error_handling("crewai", RetryConfig(max_retries=1, base_delay=0.1))
async def test_crewai_timeout():
    """Simula un timeout en CrewAI."""
    await asyncio.sleep(0.05)
    raise asyncio.TimeoutError("CrewAI timeout")

@with_error_handling("twilio", RetryConfig(max_retries=1, base_delay=0.1))
async def test_twilio_success():
    """Simula una llamada exitosa a Twilio."""
    await asyncio.sleep(0.2)
    return {"message_sid": "SM123456", "status": "sent"}

@with_error_handling("cnpj")  # Usar configuración por defecto
def test_cnpj_sync_success():
    """Simula una llamada síncrona exitosa a CNPJ."""
    time.sleep(0.15)
    return {"cnpj": "12345678000199", "company": "Test Company"}

@with_error_handling("supabase", RetryConfig(max_retries=1, base_delay=0.1))
async def test_supabase_failure():
    """Simula una falla en Supabase."""
    await asyncio.sleep(0.1)
    raise Exception("Database connection error")

async def run_tests():
    """Ejecuta las pruebas y muestra las métricas."""
    logger.info("🚀 Iniciando pruebas de integración de métricas...")
    
    # Limpiar métricas antes de empezar
    if get_metrics_service():
        get_metrics_service().clear_metrics()
    
    # Test 1: Llamadas exitosas
    logger.info("\n📊 Test 1: Llamadas exitosas")
    try:
        result1 = await test_pipefy_success()
        logger.info(f"✅ Pipefy success: {result1}")
        
        result2 = await test_twilio_success()
        logger.info(f"✅ Twilio success: {result2}")
        
        result3 = test_cnpj_sync_success()
        logger.info(f"✅ CNPJ success: {result3}")
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
    
    # Test 2: Llamadas con fallos
    logger.info("\n📊 Test 2: Llamadas con fallos")
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
    
    # Test 3: Múltiples llamadas para generar estadísticas
    logger.info("\n📊 Test 3: Múltiples llamadas")
    for i in range(5):
        try:
            await test_pipefy_success()
        except:
            pass
        
        if i % 2 == 0:  # Algunas fallan
            try:
                await test_pipefy_failure()
            except:
                pass
    
    # Mostrar métricas finales
    logger.info("\n📈 MÉTRICAS FINALES:")
    metrics_service_instance = get_metrics_service()
    
    if metrics_service_instance:
        all_metrics = metrics_service_instance.get_all_metrics()
        
        for service_name, service_metrics in all_metrics["services"].items():
            logger.info(f"\n🔧 {service_name.upper()}:")
            logger.info(f"  📊 Total requests: {service_metrics['total_requests']}")
            logger.info(f"  ✅ Successful: {service_metrics['successful_requests']}")
            logger.info(f"  ❌ Failed: {service_metrics['failed_requests']}")
            logger.info(f"  ⏱️ Timeouts: {service_metrics['timeout_requests']}")
            logger.info(f"  📈 Success rate: {service_metrics['success_rate']:.1f}%")
            logger.info(f"  ⚡ Avg response time: {service_metrics['avg_response_time']:.3f}s")
            logger.info(f"  🔄 Consecutive failures: {service_metrics['consecutive_failures']}")
            logger.info(f"  🚨 Circuit breaker open: {service_metrics['circuit_breaker_open']}")
        
        # Mostrar alertas
        alerts = metrics_service_instance.get_recent_alerts(hours=1)
        if alerts:
            logger.info(f"\n🚨 ALERTAS RECIENTES ({len(alerts)}):")
            for alert in alerts[-5:]:  # Mostrar últimos 5
                logger.info(f"  [{alert['level'].upper()}] {alert['service']}: {alert['message']}")
        else:
            logger.info("\n✅ No hay alertas recientes")
        
        # Mostrar resumen general
        summary = all_metrics["summary"]
        logger.info(f"\n📋 RESUMEN GENERAL:")
        logger.info(f"  📊 Total requests: {summary['total_requests']}")
        logger.info(f"  ✅ Total successful: {summary['total_successful']}")
        logger.info(f"  ❌ Total failed: {summary['total_failed']}")
        logger.info(f"  📈 Overall success rate: {summary['overall_success_rate']:.1f}%")
        logger.info(f"  🔥 Services with issues: {summary['services_with_issues']}")
    else:
        logger.warning("⚠️ Servicio de métricas no disponible")

def main():
    """Función principal."""
    try:
        asyncio.run(run_tests())
        logger.info("\n🎉 Pruebas completadas exitosamente!")
    except Exception as e:
        logger.error(f"💥 Error durante las pruebas: {e}")
        raise

if __name__ == "__main__":
    main() 