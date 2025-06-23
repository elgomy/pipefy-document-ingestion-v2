#!/usr/bin/env python3
"""
Script para probar el webhook de triagem en tiempo real.
Envía una solicitud POST al servidor local para simular el webhook de Pipefy.
"""

import json
import httpx
import asyncio
from datetime import datetime

async def test_webhook_endpoint():
    """Probar el endpoint del webhook con datos simulados"""
    
    print("🚀 PRUEBA REAL DEL WEBHOOK DE TRIAGEM")
    print("=" * 45)
    
    # URL del servidor local
    webhook_url = "http://localhost:8000/webhook/triagem"
    
    # Payload simulado del webhook de Pipefy
    test_payload = {
        "data": {
            "card": {
                "id": "test_card_456789",
                "title": "Documento de Teste Real - CNPJ 12.345.678/0001-90",
                "current_phase": {
                    "id": "338000020",
                    "name": "Triagem de Documentos"
                },
                "fields": [
                    {
                        "field": {
                            "id": "cnpj_field",
                            "label": "CNPJ"
                        },
                        "value": "12.345.678/0001-90"
                    },
                    {
                        "field": {
                            "id": "empresa_field",
                            "label": "Nome da Empresa"
                        },
                        "value": "Empresa Teste LTDA"
                    }
                ],
                "attachments": [
                    {
                        "id": "attachment_test_1",
                        "name": "contrato_social.pdf",
                        "url": "https://example.com/contrato_social.pdf"
                    },
                    {
                        "id": "attachment_test_2",
                        "name": "documento_cnpj.pdf", 
                        "url": "https://example.com/documento_cnpj.pdf"
                    }
                ]
            }
        }
    }
    
    print(f"📡 Enviando payload al webhook: {webhook_url}")
    print(f"📄 Card ID: {test_payload['data']['card']['id']}")
    print(f"📎 Attachments: {len(test_payload['data']['card']['attachments'])}")
    
    try:
        # Enviar solicitud POST al webhook
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                json=test_payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\n📊 RESPUESTA DEL SERVIDOR:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Webhook procesado exitosamente!")
                print(f"   Respuesta: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                # Verificar que el procesamiento fue exitoso
                if result.get("success"):
                    print(f"\n🎉 ¡Procesamiento completado exitosamente!")
                    if "card_moved" in result:
                        print(f"   Card movido: {result.get('card_moved', False)}")
                    if "fields_updated" in result:
                        print(f"   Campos actualizados: {result.get('fields_updated', False)}")
                else:
                    print(f"\n⚠️  Procesamiento completado con advertencias")
                    if "error" in result:
                        print(f"   Error: {result['error']}")
                        
            else:
                print(f"❌ Error en el webhook:")
                print(f"   Status: {response.status_code}")
                print(f"   Texto: {response.text}")
                
    except httpx.ConnectError:
        print("❌ No se pudo conectar al servidor.")
        print("   Asegúrate de que el servidor esté ejecutándose en localhost:8000")
        print("   Ejecuta: python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload")
        
    except httpx.TimeoutException:
        print("❌ Timeout al conectar con el servidor.")
        print("   El procesamiento puede estar tomando más tiempo del esperado.")
        
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

async def test_health_endpoint():
    """Verificar que el servidor esté funcionando"""
    print("🏥 Verificando estado del servidor...")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Servidor funcionando correctamente")
                print(f"   Status: {result.get('status', 'unknown')}")
                print(f"   Timestamp: {result.get('timestamp', 'unknown')}")
                return True
            else:
                print(f"⚠️  Servidor responde pero con error: {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print("❌ Servidor no está ejecutándose o no es accesible")
        return False
    except Exception as e:
        print(f"❌ Error al verificar servidor: {str(e)}")
        return False

async def test_endpoints_list():
    """Verificar endpoints disponibles"""
    print("\n📋 Verificando endpoints disponibles...")
    
    endpoints_to_test = [
        ("GET", "/", "Página principal"),
        ("GET", "/health", "Health check"),
        ("GET", "/docs", "Documentación API"),
        ("POST", "/webhook/triagem", "Webhook de triagem")
    ]
    
    for method, endpoint, description in endpoints_to_test:
        url = f"http://localhost:8000{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                if method == "GET":
                    response = await client.get(url)
                elif method == "POST":
                    # Para POST, solo verificamos que el endpoint existe
                    response = await client.post(url, json={})
                
                status_icon = "✅" if response.status_code < 500 else "❌"
                print(f"   {status_icon} {method} {endpoint}: {response.status_code} - {description}")
                
        except Exception as e:
            print(f"   ❌ {method} {endpoint}: Error - {description}")

async def main():
    """Función principal"""
    print("🔧 PRUEBA COMPLETA DEL SISTEMA DE TRIAGEM")
    print("=" * 50)
    
    # 1. Verificar que el servidor esté funcionando
    server_ok = await test_health_endpoint()
    
    if not server_ok:
        print("\n💡 INSTRUCCIONES PARA INICIAR EL SERVIDOR:")
        print("   1. Abrir una nueva terminal")
        print("   2. Navegar al directorio del proyecto")
        print("   3. Ejecutar: python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload")
        print("   4. Esperar a que aparezca 'Application startup complete'")
        print("   5. Ejecutar este script nuevamente")
        return
    
    # 2. Verificar endpoints disponibles
    await test_endpoints_list()
    
    # 3. Probar el webhook de triagem
    print("\n" + "=" * 50)
    await test_webhook_endpoint()
    
    print("\n" + "=" * 50)
    print("🎯 PRUEBA COMPLETADA")
    print("   Para ver los logs del servidor, revisa la terminal donde está ejecutándose.")
    print("   Para detener el servidor, presiona Ctrl+C en esa terminal.")

if __name__ == "__main__":
    asyncio.run(main())