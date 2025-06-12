#!/usr/bin/env python3
"""
Script de utilidad para despertar los servicios en Render y verificar su estado.
Útil para evitar cold starts antes de procesar webhooks importantes.
"""

import asyncio
import httpx
import time
from datetime import datetime

# URLs de los servicios
INGESTION_SERVICE_URL = "https://pipefy-document-ingestion-modular.onrender.com"
CREWAI_SERVICE_URL = "https://pipefy-crewai-analysis-modular.onrender.com"

async def wake_service(service_name: str, service_url: str, timeout: int = 60) -> dict:
    """Despierta un servicio y mide el tiempo de respuesta."""
    print(f"🏥 Despertando {service_name}...")
    
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{service_url}/health")
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ {service_name} despertado exitosamente en {response_time:.2f}s")
                return {
                    "service": service_name,
                    "status": "success",
                    "response_time": response_time,
                    "health_data": health_data
                }
            else:
                print(f"⚠️ {service_name} respondió con status: {response.status_code}")
                return {
                    "service": service_name,
                    "status": "warning",
                    "response_time": response_time,
                    "status_code": response.status_code
                }
                
    except httpx.TimeoutException:
        print(f"⏰ Timeout al despertar {service_name}")
        return {
            "service": service_name,
            "status": "timeout",
            "timeout": timeout
        }
    except Exception as e:
        print(f"❌ Error al despertar {service_name}: {e}")
        return {
            "service": service_name,
            "status": "error",
            "error": str(e)
        }

async def wake_all_services():
    """Despierta todos los servicios en paralelo."""
    print("🚀 Iniciando proceso de despertar servicios...")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    print("-" * 60)
    
    # Despertar servicios en paralelo
    tasks = [
        wake_service("Servicio de Ingestión", INGESTION_SERVICE_URL),
        wake_service("Servicio CrewAI", CREWAI_SERVICE_URL)
    ]
    
    results = await asyncio.gather(*tasks)
    
    print("-" * 60)
    print("📊 Resumen de resultados:")
    
    all_healthy = True
    for result in results:
        service = result["service"]
        status = result["status"]
        
        if status == "success":
            response_time = result["response_time"]
            print(f"✅ {service}: OK ({response_time:.2f}s)")
        elif status == "warning":
            response_time = result["response_time"]
            status_code = result["status_code"]
            print(f"⚠️ {service}: Status {status_code} ({response_time:.2f}s)")
            all_healthy = False
        elif status == "timeout":
            timeout = result["timeout"]
            print(f"⏰ {service}: Timeout ({timeout}s)")
            all_healthy = False
        else:
            error = result["error"]
            print(f"❌ {service}: Error - {error}")
            all_healthy = False
    
    print("-" * 60)
    if all_healthy:
        print("🎉 Todos los servicios están funcionando correctamente!")
    else:
        print("⚠️ Algunos servicios tienen problemas. Revisa los logs arriba.")
    
    return results

async def test_crewai_integration():
    """Prueba la integración entre servicios."""
    print("\n🧪 Probando integración entre servicios...")
    
    try:
        # Probar endpoint de despertar CrewAI desde el servicio de ingestión
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{INGESTION_SERVICE_URL}/utils/wake-crewai")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Integración OK: {result}")
                return True
            else:
                print(f"❌ Error en integración: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error probando integración: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Script de Utilidad - Despertar Servicios Render")
    print("=" * 60)
    
    # Despertar servicios
    results = asyncio.run(wake_all_services())
    
    # Esperar un poco para que los servicios se estabilicen
    print("\n⏳ Esperando 5 segundos para estabilización...")
    time.sleep(5)
    
    # Probar integración si ambos servicios están OK
    success_count = sum(1 for r in results if r["status"] == "success")
    if success_count == 2:
        asyncio.run(test_crewai_integration())
    else:
        print("\n⚠️ Saltando prueba de integración debido a problemas en servicios.")
    
    print("\n🏁 Proceso completado.") 