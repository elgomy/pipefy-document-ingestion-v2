#!/usr/bin/env python3
"""
Script de prueba directo para verificar la funcionalidad de triagem.
No depende del servidor FastAPI - prueba las funciones directamente.
"""

import os
import sys
import json
import asyncio
import httpx
from datetime import datetime

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

async def test_pipefy_connection():
    """Probar conexión directa con Pipefy"""
    print("🔗 Probando conexión directa con Pipefy...")
    
    token = os.getenv('PIPEFY_TOKEN')
    if not token:
        print("❌ No se encontró PIPEFY_TOKEN")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    query = """
    query {
        me {
            id
            name
            email
        }
    }
    """
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.pipefy.com/graphql",
                json={"query": query},
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'data' in result and 'me' in result['data']:
                    user_info = result['data']['me']
                    print(f"✅ Conexión exitosa con Pipefy")
                    print(f"   Usuario: {user_info['name']}")
                    print(f"   Email: {user_info['email']}")
                    return True
                else:
                    print(f"❌ Respuesta inesperada: {result}")
                    return False
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error al conectar: {str(e)}")
        return False

async def test_card_query(card_id="test_card_456789"):
    """Probar consulta de información de card específico"""
    print(f"\n📋 Probando consulta de card: {card_id}")
    
    token = os.getenv('PIPEFY_TOKEN')
    if not token:
        print("❌ No se encontró PIPEFY_TOKEN")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    query = """
    query GetCard($cardId: ID!) {
        card(id: $cardId) {
            id
            title
            current_phase {
                id
                name
            }
            fields {
                field {
                    id
                    label
                    type
                }
                name
                value
            }
        }
    }
    """
    
    variables = {"cardId": card_id}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.pipefy.com/graphql",
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'errors' in result:
                    print(f"❌ Errores GraphQL: {result['errors']}")
                    return False
                
                card_data = result.get('data', {}).get('card')
                if card_data:
                    print(f"✅ Card encontrado: {card_data['title']}")
                    current_phase = card_data.get('current_phase', {})
                    print(f"   Fase actual: {current_phase.get('name')} (ID: {current_phase.get('id')})")
                    print(f"   Campos disponibles: {len(card_data.get('fields', []))}")
                    return True
                else:
                    print(f"⚠️  Card {card_id} no encontrado o sin datos")
                    return False
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error en consulta: {str(e)}")
        return False

async def test_field_update_mutation(card_id="test_card_456789"):
    """Probar actualización de campo usando mutation"""
    print(f"\n📝 Probando actualización de campo para card: {card_id}")
    
    token = os.getenv('PIPEFY_TOKEN')
    if not token:
        print("❌ No se encontró PIPEFY_TOKEN")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Usar el field_id fijo descubierto
    field_id = "informe_crewai_2"
    test_content = f"🧪 Prueba directa de actualización - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Escapar contenido para GraphQL
    escaped_content = test_content.replace('"', '\\"').replace('\\n', '\\\\n').replace('\\r', '')
    
    mutation = f'''
    mutation {{
        updateCardField(input: {{card_id: {card_id}, field_id: "{field_id}", new_value: "{escaped_content}"}}) {{
            card {{
                id
                title
            }}
        }}
    }}
    '''
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.pipefy.com/graphql",
                json={"query": mutation},
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'errors' in result:
                    print(f"❌ Errores GraphQL: {result['errors']}")
                    return False
                
                update_result = result.get('data', {}).get('updateCardField')
                if update_result and update_result.get('card'):
                    card_info = update_result['card']
                    print(f"✅ Campo actualizado exitosamente")
                    print(f"   Card ID: {card_info.get('id')}")
                    print(f"   Card Title: {card_info.get('title')}")
                    print(f"   Field ID: {field_id}")
                    print(f"   Contenido: {test_content[:50]}...")
                    return True
                else:
                    print(f"❌ Respuesta inesperada: {result}")
                    return False
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error en actualización: {str(e)}")
        return False

async def test_card_movement(card_id="test_card_456789"):
    """Probar movimiento de card entre fases"""
    print(f"\n🔄 Probando movimiento de card: {card_id}")
    
    token = os.getenv('PIPEFY_TOKEN')
    if not token:
        print("❌ No se encontró PIPEFY_TOKEN")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Usar fase de pendencias como ejemplo
    destination_phase_id = os.getenv('PHASE_ID_PENDENCIAS', '338000017')
    
    mutation = f'''
    mutation {{
        moveCardToPhase(input: {{card_id: {card_id}, destination_phase_id: {destination_phase_id}}}) {{
            card {{
                id
                current_phase {{
                    id
                    name
                }}
            }}
        }}
    }}
    '''
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.pipefy.com/graphql",
                json={"query": mutation},
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'errors' in result:
                    print(f"❌ Errores GraphQL: {result['errors']}")
                    # Los errores de movimiento son normales si el card no existe
                    print(f"⚠️  Esto es normal si el card de prueba no existe")
                    return False
                
                move_result = result.get('data', {}).get('moveCardToPhase')
                if move_result and move_result.get('card'):
                    new_phase = move_result['card']['current_phase']
                    print(f"✅ Card movido exitosamente")
                    print(f"   Nueva fase: {new_phase['name']} (ID: {new_phase['id']})")
                    return True
                else:
                    print(f"❌ Respuesta inesperada: {result}")
                    return False
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error en movimiento: {str(e)}")
        return False

async def test_crewai_service():
    """Probar conexión con el servicio CrewAI"""
    print(f"\\n🤖 Probando conexión con servicio CrewAI...")
    
    crewai_url = os.getenv('CREWAI_SERVICE_URL')
    if not crewai_url:
        print("❌ No se encontró CREWAI_SERVICE_URL")
        return False
    
    health_url = f"{crewai_url}/health"
    print(f"   URL: {health_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(health_url)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Servicio CrewAI disponible")
                print(f"   Status: {result.get('status', 'unknown')}")
                print(f"   Service: {result.get('service', 'unknown')}")
                return True
            elif response.status_code == 502:
                print(f"🛌 Servicio CrewAI está dormido (502 Bad Gateway)")
                print(f"   Esto es normal en Render - el servicio se despierta con la primera solicitud")
                return False
            else:
                print(f"⚠️  Servicio responde con status: {response.status_code}")
                return False
                
    except httpx.TimeoutException:
        print(f"⏰ Timeout al conectar con CrewAI")
        print(f"   El servicio puede estar en cold start")
        return False
    except Exception as e:
        print(f"❌ Error al conectar: {str(e)}")
        return False

async def test_webhook_payload_processing():
    """Probar el procesamiento de payload de webhook simulado"""
    print(f"\\n📦 Probando procesamiento de payload de webhook...")
    
    # Payload simulado del webhook de Pipefy
    test_payload = {
        "data": {
            "card": {
                "id": "test_card_456789",
                "title": "Documento de Teste Real - CNPJ 12.345.678/0001-90",
                "current_phase": {
                    "id": "338000020",  # Fase de triagem
                    "name": "Triagem de Documentos"
                },
                "fields": [
                    {
                        "field": {
                            "id": "cnpj_field",
                            "label": "CNPJ"
                        },
                        "value": "12.345.678/0001-90"
                    }
                ],
                "attachments": [
                    {
                        "id": "attachment_test_1",
                        "name": "contrato_social.pdf",
                        "url": "https://example.com/contrato_social.pdf"
                    }
                ]
            }
        }
    }
    
    try:
        # Simular validaciones que haría el webhook
        card_data = test_payload.get('data', {}).get('card', {})
        card_id = card_data.get('id')
        current_phase = card_data.get('current_phase', {})
        current_phase_id = current_phase.get('id')
        attachments = card_data.get('attachments', [])
        
        print(f"✅ Payload válido:")
        print(f"   Card ID: {card_id}")
        print(f"   Fase actual: {current_phase.get('name')} (ID: {current_phase_id})")
        print(f"   Attachments: {len(attachments)}")
        
        # Verificar que es la fase de triagem
        if current_phase_id == "338000020":
            print(f"✅ Fase de triagem detectada correctamente")
            
            for i, attachment in enumerate(attachments, 1):
                print(f"   📎 Documento {i}: {attachment['name']}")
            
            return True
        else:
            print(f"⚠️  Fase diferente a triagem: {current_phase_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error al procesar payload: {str(e)}")
        return False

async def main():
    """Función principal de pruebas directas"""
    print("🧪 PRUEBAS DIRECTAS DE FUNCIONALIDAD TRIAGEM")
    print("=" * 50)
    
    print("📁 Variables de entorno configuradas:")
    print(f"   PIPEFY_TOKEN: {'✅' if os.getenv('PIPEFY_TOKEN') else '❌'}")
    print(f"   SUPABASE_URL: {'✅' if os.getenv('SUPABASE_URL') else '❌'}")
    print(f"   CREWAI_SERVICE_URL: {'✅' if os.getenv('CREWAI_SERVICE_URL') else '❌'}")
    
    # Ejecutar pruebas
    results = {}
    
    print("\\n" + "=" * 50)
    results['pipefy_connection'] = await test_pipefy_connection()
    
    print("\\n" + "=" * 50)
    results['webhook_payload'] = await test_webhook_payload_processing()
    
    print("\\n" + "=" * 50)
    results['crewai_service'] = await test_crewai_service()
    
    # Pruebas que requieren card real (pueden fallar si no existe)
    print("\\n" + "=" * 50)
    print("⚠️  Las siguientes pruebas pueden fallar si el card de prueba no existe:")
    
    results['card_query'] = await test_card_query()
    results['field_update'] = await test_field_update_mutation()
    results['card_movement'] = await test_card_movement()
    
    # Resumen final
    print("\\n" + "=" * 50)
    print("📊 RESUMEN DE PRUEBAS DIRECTAS:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\\n🎯 Resultado final: {passed}/{total} pruebas exitosas")
    
    if passed >= 3:  # Al menos las pruebas básicas deben pasar
        print("\\n🎉 ¡Funcionalidad básica verificada!")
        print("   El sistema está configurado correctamente.")
        print("   Las pruebas de card pueden fallar si no existe un card real para testing.")
    else:
        print("\\n⚠️  Problemas de configuración detectados.")
        print("   Revisar variables de entorno y conectividad.")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())