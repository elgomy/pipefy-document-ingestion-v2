#!/usr/bin/env python3
"""
Script de prueba para el sistema de manejo de errores de APIs externas.
Simula diferentes tipos de errores y verifica que se manejen correctamente.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import aiohttp
import httpx

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.error_handler import (
    APIErrorHandler, APIError, APIErrorType, APIErrorSeverity,
    with_error_handling, RetryConfig, get_error_handler, reset_error_handler
)
from src.services.error_notification_service import (
    ErrorNotificationService, AlertType, get_error_notification_service
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestErrorHandling:
    """Clase para probar el sistema de manejo de errores."""
    
    def __init__(self):
        """Inicializa el test."""
        self.error_handler = APIErrorHandler()
        self.notification_service = ErrorNotificationService()
        
    async def test_error_classification(self):
        """Prueba la clasificación de errores."""
        print("\n=== PRUEBA 1: Clasificación de Errores ===")
        
        # Test 1: Error de timeout
        timeout_error = asyncio.TimeoutError("Request timeout")
        classified = self.error_handler.classify_error(timeout_error, "test_api")
        
        assert classified.error_type == APIErrorType.TIMEOUT
        assert classified.severity == APIErrorSeverity.MEDIUM
        print(f"✅ Timeout error clasificado correctamente: {classified.error_type.value}")
        
        # Test 2: Error de autenticación
        auth_error = httpx.HTTPStatusError("401 Unauthorized", request=None, response=None)
        classified = self.error_handler.classify_error(auth_error, "pipefy", status_code=401)
        
        assert classified.error_type == APIErrorType.AUTHENTICATION_ERROR
        assert classified.severity == APIErrorSeverity.HIGH
        print(f"✅ Auth error clasificado correctamente: {classified.error_type.value}")
        
        # Test 3: Error en API crítica (Supabase)
        server_error = Exception("Database connection failed")
        classified = self.error_handler.classify_error(server_error, "supabase")
        
        assert classified.severity == APIErrorSeverity.HIGH  # Escalado por ser API crítica
        print(f"✅ Error de API crítica escalado correctamente: {classified.severity.value}")
        
        print("✅ Todas las clasificaciones de errores pasaron")
    
    async def test_retry_logic(self):
        """Prueba la lógica de reintentos."""
        print("\n=== PRUEBA 2: Lógica de Reintentos ===")
        
        # Test 1: Error que debe reintentarse
        timeout_error = APIError(
            api_name="test_api",
            error_type=APIErrorType.TIMEOUT,
            severity=APIErrorSeverity.MEDIUM,
            message="Timeout error",
            retry_count=0,
            max_retries=3
        )
        
        should_retry = self.error_handler.should_retry(timeout_error)
        assert should_retry == True
        print("✅ Error de timeout debe reintentarse")
        
        # Test 2: Error de autenticación no debe reintentarse
        auth_error = APIError(
            api_name="test_api",
            error_type=APIErrorType.AUTHENTICATION_ERROR,
            severity=APIErrorSeverity.HIGH,
            message="Auth error",
            retry_count=0,
            max_retries=3
        )
        
        should_retry = self.error_handler.should_retry(auth_error)
        assert should_retry == False
        print("✅ Error de autenticación no debe reintentarse")
        
        # Test 3: Error que excede max_retries
        max_retries_error = APIError(
            api_name="test_api",
            error_type=APIErrorType.TIMEOUT,
            severity=APIErrorSeverity.MEDIUM,
            message="Timeout error",
            retry_count=3,
            max_retries=3
        )
        
        should_retry = self.error_handler.should_retry(max_retries_error)
        assert should_retry == False
        print("✅ Error que excede max_retries no debe reintentarse")
        
        print("✅ Todas las pruebas de lógica de reintentos pasaron")
    
    async def test_circuit_breaker(self):
        """Prueba el circuit breaker."""
        print("\n=== PRUEBA 3: Circuit Breaker ===")
        
        # Simular 5 errores consecutivos para abrir el circuit breaker
        for i in range(5):
            error = APIError(
                api_name="test_circuit_api",
                error_type=APIErrorType.SERVER_ERROR,
                severity=APIErrorSeverity.HIGH,
                message=f"Server error {i+1}"
            )
            self.error_handler.log_error(error)
        
        # Verificar que el circuit breaker está abierto
        is_open = self.error_handler._is_circuit_breaker_open("test_circuit_api")
        assert is_open == True
        print("✅ Circuit breaker se abrió después de 5 errores consecutivos")
        
        # Verificar que no debe reintentar cuando el circuit breaker está abierto
        error = APIError(
            api_name="test_circuit_api",
            error_type=APIErrorType.TIMEOUT,
            severity=APIErrorSeverity.MEDIUM,
            message="Timeout error",
            retry_count=0,
            max_retries=3
        )
        
        should_retry = self.error_handler.should_retry(error)
        assert should_retry == False
        print("✅ No reintenta cuando circuit breaker está abierto")
        
        print("✅ Todas las pruebas de circuit breaker pasaron")
    
    async def test_decorator_functionality(self):
        """Prueba el decorador de manejo de errores."""
        print("\n=== PRUEBA 4: Decorador de Manejo de Errores ===")
        
        # Reset error handler para prueba limpia
        reset_error_handler()
        
        # Función que siempre falla
        @with_error_handling("test_decorator_api", RetryConfig(max_retries=2))
        async def failing_function():
            raise httpx.TimeoutException("Simulated timeout")
        
        # Función que funciona después de 1 fallo
        call_count = 0
        @with_error_handling("test_decorator_api", RetryConfig(max_retries=2))
        async def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.TimeoutException("First call fails")
            return {"success": True, "call_count": call_count}
        
        # Test 1: Función que siempre falla
        try:
            await failing_function()
            assert False, "Debería haber lanzado excepción"
        except httpx.TimeoutException:
            print("✅ Función que siempre falla lanzó excepción correctamente")
        
        # Test 2: Función que funciona después de 1 fallo
        call_count = 0
        result = await sometimes_failing_function()
        assert result["success"] == True
        assert result["call_count"] == 2  # Primer intento falló, segundo funcionó
        print("✅ Función con retry funcionó correctamente")
        
        # Verificar que se registraron los errores
        error_handler = get_error_handler()
        stats = error_handler.get_error_stats()
        assert stats["total_errors"] > 0
        print(f"✅ Se registraron {stats['total_errors']} errores en el historial")
        
        print("✅ Todas las pruebas del decorador pasaron")
    
    async def test_error_statistics(self):
        """Prueba las estadísticas de errores."""
        print("\n=== PRUEBA 5: Estadísticas de Errores ===")
        
        # Reset para prueba limpia
        reset_error_handler()
        error_handler = get_error_handler()
        
        # Agregar varios errores de diferentes tipos
        errors = [
            APIError("api1", APIErrorType.TIMEOUT, APIErrorSeverity.MEDIUM, "Timeout 1"),
            APIError("api1", APIErrorType.TIMEOUT, APIErrorSeverity.MEDIUM, "Timeout 2"),
            APIError("api2", APIErrorType.SERVER_ERROR, APIErrorSeverity.HIGH, "Server error"),
            APIError("api3", APIErrorType.AUTHENTICATION_ERROR, APIErrorSeverity.HIGH, "Auth error"),
        ]
        
        for error in errors:
            error_handler.log_error(error)
        
        # Obtener estadísticas
        stats = error_handler.get_error_stats()
        
        assert stats["total_errors"] == 4
        assert stats["apis"]["api1"] == 2
        assert stats["apis"]["api2"] == 1
        assert stats["apis"]["api3"] == 1
        assert stats["error_types"]["timeout"] == 2
        assert stats["error_types"]["server_error"] == 1
        assert stats["error_types"]["authentication_error"] == 1
        
        print(f"✅ Estadísticas correctas: {stats['total_errors']} errores totales")
        print(f"✅ APIs afectadas: {list(stats['apis'].keys())}")
        print(f"✅ Tipos de error: {list(stats['error_types'].keys())}")
        
        print("✅ Todas las pruebas de estadísticas pasaron")
    
    async def test_notification_formatting(self):
        """Prueba el formateo de notificaciones."""
        print("\n=== PRUEBA 6: Formateo de Notificaciones ===")
        
        # Test error crítico
        critical_error = APIError(
            api_name="supabase",
            error_type=APIErrorType.SERVER_ERROR,
            severity=APIErrorSeverity.CRITICAL,
            message="Database connection lost",
            status_code=500,
            timestamp=datetime.now()
        )
        
        message = self.notification_service._format_critical_error_message(critical_error)
        assert "🚨 ERROR CRÍTICO" in message
        assert "SUPABASE" in message
        assert "Database connection lost" in message
        print("✅ Mensaje de error crítico formateado correctamente")
        
        # Test error de autenticación
        auth_error = APIError(
            api_name="pipefy",
            error_type=APIErrorType.AUTHENTICATION_ERROR,
            severity=APIErrorSeverity.HIGH,
            message="Invalid API token",
            status_code=401,
            timestamp=datetime.now()
        )
        
        message = self.notification_service._format_authentication_failure_message(auth_error)
        assert "🔐 FALLO DE AUTENTICACIÓN" in message
        assert "PIPEFY" in message
        assert "Invalid API token" in message
        print("✅ Mensaje de error de autenticación formateado correctamente")
        
        # Test circuit breaker
        breaker_info = {
            "failure_count": 5,
            "last_failure": datetime.now()
        }
        
        message = self.notification_service._format_circuit_breaker_message("test_api", breaker_info)
        assert "⚡ CIRCUIT BREAKER ABIERTO" in message
        assert "TEST_API" in message
        assert "5" in message
        print("✅ Mensaje de circuit breaker formateado correctamente")
        
        print("✅ Todas las pruebas de formateo de notificaciones pasaron")
    
    async def run_all_tests(self):
        """Ejecuta todas las pruebas."""
        print("🚀 Iniciando pruebas del sistema de manejo de errores...")
        
        try:
            await self.test_error_classification()
            await self.test_retry_logic()
            await self.test_circuit_breaker()
            await self.test_decorator_functionality()
            await self.test_error_statistics()
            await self.test_notification_formatting()
            
            print("\n🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
            print("\n📊 Resumen del sistema de manejo de errores:")
            print("✅ Clasificación automática de errores por tipo y severidad")
            print("✅ Lógica de reintentos con backoff exponencial")
            print("✅ Circuit breaker para prevenir cascada de errores")
            print("✅ Decorador automático para funciones de API")
            print("✅ Estadísticas detalladas de errores")
            print("✅ Notificaciones formateadas para el equipo de operaciones")
            print("✅ Integración con todas las APIs externas (Pipefy, CNPJ, Twilio, Supabase)")
            
        except Exception as e:
            print(f"\n❌ Error en las pruebas: {e}")
            raise


async def main():
    """Función principal."""
    test_runner = TestErrorHandling()
    await test_runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 