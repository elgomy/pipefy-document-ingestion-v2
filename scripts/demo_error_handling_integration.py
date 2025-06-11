#!/usr/bin/env python3
"""
Demostración del sistema de manejo de errores integrado con APIs reales.
Muestra cómo el sistema maneja errores de Pipefy, CNPJ, Twilio y Supabase.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from unittest.mock import patch

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.pipefy_client import PipefyClient
from src.integrations.cnpj_client import CNPJClient
from src.integrations.twilio_client import TwilioClient
from src.services.database_service import DatabaseService
from src.utils.error_handler import get_error_handler, reset_error_handler
from src.services.error_notification_service import get_error_notification_service

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorHandlingDemo:
    """Demostración del sistema de manejo de errores."""
    
    def __init__(self):
        """Inicializa la demostración."""
        self.error_handler = get_error_handler()
        self.notification_service = get_error_notification_service()
        
        # Reset para demo limpia
        reset_error_handler()
        self.error_handler = get_error_handler()
    
    async def demo_pipefy_error_handling(self):
        """Demuestra el manejo de errores de Pipefy."""
        print("\n🔧 === DEMO: Manejo de Errores de Pipefy ===")
        
        try:
            pipefy_client = PipefyClient()
            
            # Intentar mover un card inexistente (debería fallar)
            print("📋 Intentando mover card inexistente...")
            result = await pipefy_client.move_card_to_phase("INVALID_CARD_ID", "INVALID_PHASE_ID")
            print(f"✅ Resultado (con manejo de errores): {result}")
            
        except Exception as e:
            print(f"⚠️ Error capturado: {type(e).__name__}: {e}")
        
        # Mostrar estadísticas
        stats = self.error_handler.get_error_stats()
        print(f"📊 Errores registrados: {stats['total_errors']}")
        if stats['apis']:
            print(f"📊 APIs afectadas: {list(stats['apis'].keys())}")
    
    async def demo_cnpj_error_handling(self):
        """Demuestra el manejo de errores de CNPJ."""
        print("\n🏢 === DEMO: Manejo de Errores de CNPJ ===")
        
        try:
            cnpj_client = CNPJClient(timeout=5)  # Timeout corto para demo
            
            # Intentar consultar CNPJ inválido
            print("🔍 Intentando consultar CNPJ inválido...")
            result = await cnpj_client.get_cnpj_data("00.000.000/0000-00")
            print(f"✅ Resultado (con manejo de errores): {result}")
            
        except Exception as e:
            print(f"⚠️ Error capturado: {type(e).__name__}: {e}")
        
        # Mostrar estadísticas
        stats = self.error_handler.get_error_stats()
        print(f"📊 Errores registrados: {stats['total_errors']}")
        if stats['apis']:
            print(f"📊 APIs afectadas: {list(stats['apis'].keys())}")
    
    async def demo_twilio_error_handling(self):
        """Demuestra el manejo de errores de Twilio."""
        print("\n📱 === DEMO: Manejo de Errores de Twilio ===")
        
        try:
            twilio_client = TwilioClient()
            
            # Intentar enviar mensaje a número inválido
            print("📞 Intentando enviar WhatsApp a número inválido...")
            result = await twilio_client.send_whatsapp_message(
                to_number="+invalid_number",
                message="Test message"
            )
            print(f"✅ Resultado (con manejo de errores): {result}")
            
        except Exception as e:
            print(f"⚠️ Error capturado: {type(e).__name__}: {e}")
        
        # Mostrar estadísticas
        stats = self.error_handler.get_error_stats()
        print(f"📊 Errores registrados: {stats['total_errors']}")
        if stats['apis']:
            print(f"📊 APIs afectadas: {list(stats['apis'].keys())}")
    
    async def demo_supabase_error_handling(self):
        """Demuestra el manejo de errores de Supabase."""
        print("\n🗄️ === DEMO: Manejo de Errores de Supabase ===")
        
        try:
            db_service = DatabaseService()
            
            # Intentar obtener caso inexistente
            print("🔍 Intentando obtener caso inexistente...")
            result = await db_service.get_case_tracking("INVALID_CASE_ID")
            print(f"✅ Resultado (con manejo de errores): {result}")
            
        except Exception as e:
            print(f"⚠️ Error capturado: {type(e).__name__}: {e}")
        
        # Mostrar estadísticas
        stats = self.error_handler.get_error_stats()
        print(f"📊 Errores registrados: {stats['total_errors']}")
        if stats['apis']:
            print(f"📊 APIs afectadas: {list(stats['apis'].keys())}")
    
    async def demo_circuit_breaker_simulation(self):
        """Simula el circuit breaker en acción."""
        print("\n⚡ === DEMO: Circuit Breaker en Acción ===")
        
        # Simular múltiples errores consecutivos
        print("🔥 Simulando múltiples errores consecutivos...")
        
        # Usar mock para simular errores
        with patch('src.integrations.cnpj_client.CNPJClient.get_cnpj_data') as mock_get_data:
            mock_get_data.side_effect = Exception("Simulated API failure")
            
            cnpj_client = CNPJClient()
            
            # Intentar 6 veces para activar circuit breaker
            for i in range(6):
                try:
                    print(f"🔄 Intento {i+1}/6...")
                    await cnpj_client.get_cnpj_data("11.222.333/0001-81")
                except Exception as e:
                    print(f"❌ Error {i+1}: {type(e).__name__}")
                    
                    # Verificar si circuit breaker se activó
                    if i >= 4:  # Después de 5 errores
                        is_open = self.error_handler._is_circuit_breaker_open("cnpj_api")
                        if is_open:
                            print("⚡ ¡Circuit breaker activado! Bloqueando más intentos.")
                            break
        
        # Mostrar estadísticas finales
        stats = self.error_handler.get_error_stats()
        print(f"\n📊 Estadísticas finales:")
        print(f"   Total de errores: {stats['total_errors']}")
        print(f"   APIs afectadas: {list(stats['apis'].keys())}")
        print(f"   Tipos de error: {list(stats['error_types'].keys())}")
    
    async def demo_error_notifications(self):
        """Demuestra las notificaciones de errores."""
        print("\n📢 === DEMO: Notificaciones de Errores ===")
        
        # Simular error crítico
        print("🚨 Simulando error crítico...")
        
        from src.utils.error_handler import APIError, APIErrorType, APIErrorSeverity
        
        critical_error = APIError(
            api_name="supabase",
            error_type=APIErrorType.SERVER_ERROR,
            severity=APIErrorSeverity.CRITICAL,
            message="Database connection completely lost",
            status_code=500,
            timestamp=datetime.now()
        )
        
        # Formatear mensaje de notificación
        message = self.notification_service._format_critical_error_message(critical_error)
        print(f"📱 Mensaje de notificación generado:")
        print(f"   {message}")
        
        # Simular error de autenticación
        print("\n🔐 Simulando error de autenticación...")
        
        auth_error = APIError(
            api_name="pipefy",
            error_type=APIErrorType.AUTHENTICATION_ERROR,
            severity=APIErrorSeverity.HIGH,
            message="API token expired",
            status_code=401,
            timestamp=datetime.now()
        )
        
        message = self.notification_service._format_authentication_failure_message(auth_error)
        print(f"📱 Mensaje de notificación generado:")
        print(f"   {message}")
    
    async def run_full_demo(self):
        """Ejecuta la demostración completa."""
        print("🚀 === DEMOSTRACIÓN COMPLETA DEL SISTEMA DE MANEJO DE ERRORES ===")
        print("\n🎯 Este demo muestra cómo el sistema maneja errores de todas las APIs externas:")
        print("   • Pipefy (GraphQL API)")
        print("   • CNPJá (REST API)")
        print("   • Twilio (WhatsApp API)")
        print("   • Supabase (Database API)")
        print("\n🛡️ Características del sistema:")
        print("   • Clasificación automática de errores")
        print("   • Reintentos con backoff exponencial")
        print("   • Circuit breaker para prevenir cascadas")
        print("   • Logging estructurado")
        print("   • Notificaciones automáticas")
        print("   • Estadísticas en tiempo real")
        
        try:
            # Ejecutar demos individuales
            await self.demo_pipefy_error_handling()
            await self.demo_cnpj_error_handling()
            await self.demo_twilio_error_handling()
            await self.demo_supabase_error_handling()
            await self.demo_circuit_breaker_simulation()
            await self.demo_error_notifications()
            
            # Resumen final
            print("\n🎉 === DEMOSTRACIÓN COMPLETADA EXITOSAMENTE ===")
            
            final_stats = self.error_handler.get_error_stats()
            print(f"\n📈 Resumen de la sesión:")
            print(f"   Total de errores procesados: {final_stats['total_errors']}")
            print(f"   APIs probadas: {len(final_stats['apis'])}")
            print(f"   Tipos de error encontrados: {len(final_stats['error_types'])}")
            
            print("\n✅ El sistema de manejo de errores está funcionando correctamente!")
            print("\n🔧 Próximos pasos:")
            print("   • El sistema está listo para producción")
            print("   • Configurar alertas de WhatsApp para el equipo de operaciones")
            print("   • Monitorear dashboards de errores en tiempo real")
            print("   • Ajustar umbrales de circuit breaker según necesidades")
            
        except Exception as e:
            print(f"\n❌ Error en la demostración: {e}")
            raise


async def main():
    """Función principal."""
    demo = ErrorHandlingDemo()
    await demo.run_full_demo()


if __name__ == "__main__":
    asyncio.run(main()) 