#!/usr/bin/env python3
"""
Script de prueba simple para verificar la integración de métricas.
"""

import asyncio
import time
import logging
import sys
import os
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

# Importar directamente las métricas
from services.metrics_service import MetricsService, ServiceType

# Crear instancia global de métricas
metrics_service = MetricsService()

# Función simple para probar métricas
def test_metrics():
    """Prueba básica del sistema de métricas."""
    logger.info("🚀 Iniciando prueba simple de métricas...")
    
    # Limpiar métricas
    metrics_service.clear_metrics()
    
    # Simular algunas operaciones
    logger.info("📊 Registrando operaciones de prueba...")
    
    # Éxitos
    metrics_service.record_request(ServiceType.PIPEFY, True, 0.1, False)
    metrics_service.record_request(ServiceType.TWILIO, True, 0.2, False)
    metrics_service.record_request(ServiceType.CNPJ, True, 0.15, False)
    
    # Fallos
    metrics_service.record_request(ServiceType.PIPEFY, False, 0.5, False, "API Error")
    metrics_service.record_request(ServiceType.CREWAI, False, 30.0, True, "Timeout")
    metrics_service.record_request(ServiceType.SUPABASE, False, 0.1, False, "Connection Error")
    
    # Más éxitos para generar estadísticas
    for i in range(5):
        metrics_service.record_request(ServiceType.PIPEFY, True, 0.1 + i * 0.02, False)
    
    # Mostrar métricas
    logger.info("\n📈 MÉTRICAS REGISTRADAS:")
    all_metrics = metrics_service.get_all_metrics()
    
    for service_name, service_metrics in all_metrics["services"].items():
        logger.info(f"\n🔧 {service_name.upper()}:")
        logger.info(f"  📊 Total requests: {service_metrics['total_requests']}")
        logger.info(f"  ✅ Successful: {service_metrics['successful_requests']}")
        logger.info(f"  ❌ Failed: {service_metrics['failed_requests']}")
        logger.info(f"  ⏱️ Timeouts: {service_metrics['timeout_requests']}")
        logger.info(f"  📈 Success rate: {service_metrics['success_rate']:.1f}%")
        logger.info(f"  ⚡ Avg response time: {service_metrics['avg_response_time_seconds']:.3f}s")
        logger.info(f"  🔄 Consecutive failures: {service_metrics['consecutive_failures']}")
        logger.info(f"  🚨 Circuit breaker open: {service_metrics['circuit_breaker_open']}")
    
    # Mostrar alertas
    alerts = metrics_service.get_recent_alerts(hours=1)
    if alerts:
        logger.info(f"\n🚨 ALERTAS GENERADAS ({len(alerts)}):")
        for alert in alerts:
            logger.info(f"  [{alert['level'].upper()}] {alert['service']}: {alert['message']}")
    else:
        logger.info("\n✅ No se generaron alertas")
    
    # Mostrar resumen
    summary = all_metrics["summary"]
    logger.info(f"\n📋 RESUMEN GENERAL:")
    logger.info(f"  📊 Total requests: {summary['total_requests']}")
    logger.info(f"  ✅ Total successful: {summary['total_successful']}")
    logger.info(f"  ❌ Total failed: {summary['total_failed']}")
    logger.info(f"  📈 Overall success rate: {summary['overall_success_rate']:.1f}%")
    logger.info(f"  🔥 Services with failures: {summary['services_with_failures']}")
    logger.info(f"  🚨 Services with circuit open: {summary['services_with_circuit_open']}")
    
    logger.info("\n🎉 Prueba de métricas completada!")

if __name__ == "__main__":
    try:
        test_metrics()
    except Exception as e:
        logger.error(f"💥 Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 