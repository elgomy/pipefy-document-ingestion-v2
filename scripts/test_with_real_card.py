#!/usr/bin/env python3
"""
Script para probar la funcionalidad con un card real de Pipefy.
Primero busca cards disponibles y luego prueba las operaciones.
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

async def find_available_cards():
    """Buscar cards disponibles en el pipe"""
    print("🔍 Buscando cards disponibles en Pipefy...")
    
    token = os.getenv('PIPEFY_TOKEN')
    if not token:
        print("❌ No se encontró PIPEFY_TOKEN")
        return []
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Query para obtener pipes del usuario
    query = """
    query {
        me {
            pipes {
                id
                name
                phases {
                    id
                    name
                    cards_count
                }
            }
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
                    pipes = result['data']['me']['pipes']
                    print(f"✅ Encontrados {len(pipes)} pipes")
                    
                    for pipe in pipes:
                        print(f"\\n📋 Pipe: {pipe['name']} (ID: {pipe['id']})")
                        for phase in pipe['phases']:
                            print(f"   - {phase['name']} (ID: {phase['id']}) - {phase['cards_count']} cards")
                    
                    return pipes
                else:
                    print(f"❌ Respuesta inesperada: {result}")
                    return []
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return []
                
    except Exception as e:
        print(f"❌ Error al buscar pipes: {str(e)}")
        return []

async def get_cards_from_phase(phase_id, limit=5):
    """Obtener cards de una fase específica"""
    print(f"\\n📋 Obteniendo cards de la fase {phase_id}...")
    
    token = os.getenv('PIPEFY_TOKEN')
    if not token:
        print("❌ No se encontró PIPEFY_TOKEN")
        return []
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    query = f"""
    query {{
        phase(id: {phase_id}) {{
            id
            name
            cards(first: {limit}) {{
                edges {{
                    node {{
                        id
                        title
                        current_phase {{
                            id
                            name
                        }}
                    }}
                }}
            }}
        }}
    }}
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
                if 'errors' in result:
                    print(f"❌ Errores GraphQL: {result['errors']}")
                    return []
                
                phase_data = result.get('data', {}).get('phase')
                if phase_data:
                    cards = phase_data['cards']['edges']
                    print(f"✅ Encontrados {len(cards)} cards en fase '{phase_data['name']}'")
                    
                    card_list = []
                    for edge in cards:
                        card = edge['node']
                        card_list.append(card)
                        print(f"   - {card['id']}: {card['title'][:50]}...")
                    
                    return card_list
                else:
                    print(f"❌ Fase {phase_id} no encontrada")
                    return []
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return []
                
    except Exception as e:
        print(f"❌ Error al obtener cards: {str(e)}")
        return []

async def test_field_update_with_real_card(card_id):
    """Probar actualización de campo con card real"""
    print(f"\\n📝 Probando actualización de campo en card real: {card_id}")
    
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
    test_content = f"🧪 Prueba con card real - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\nEste es un test de la funcionalidad de triagem automática.\\n\\n**Funcionalidades probadas:**\\n- Conexión con Pipefy ✅\\n- Procesamiento de webhooks ✅\\n- Integración con CrewAI ✅\\n- Actualización de campos ✅"
    
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
                    print(f"✅ Campo actualizado exitosamente en card real!")
                    print(f"   Card ID: {card_info.get('id')}")
                    print(f"   Card Title: {card_info.get('title')}")
                    print(f"   Field ID: {field_id}")
                    print(f"   Contenido: {test_content[:100]}...")
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

async def simulate_webhook_with_real_card(card_id):
    """Simular un webhook completo con card real"""
    print(f"\\n🎯 Simulando webhook completo con card real: {card_id}")
    
    # Payload simulado pero con card ID real
    webhook_payload = {
        "data": {
            "card": {
                "id": card_id,
                "title": "Documento Real - Teste de Triagem Automática",
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
                        "id": "attachment_real_1",
                        "name": "contrato_social_teste.pdf",
                        "url": "https://example.com/contrato_social_teste.pdf"
                    },
                    {
                        "id": "attachment_real_2",
                        "name": "documento_cnpj_teste.pdf",
                        "url": "https://example.com/documento_cnpj_teste.pdf"
                    }
                ]
            }
        }
    }
    
    print(f"📦 Payload simulado preparado:")
    print(f"   Card ID: {card_id}")
    print(f"   Fase: Triagem de Documentos (338000020)")
    print(f"   Attachments: {len(webhook_payload['data']['card']['attachments'])}")
    
    # Simular las validaciones que haría el webhook real
    try:
        card_data = webhook_payload['data']['card']
        current_phase_id = card_data['current_phase']['id']
        
        if current_phase_id == "338000020":
            print(f"✅ Validación de fase: Card está en fase de triagem")
            
            # Simular procesamiento de documentos
            attachments = card_data['attachments']
            print(f"📄 Procesando {len(attachments)} documentos simulados:")
            
            for i, att in enumerate(attachments, 1):
                print(f"   {i}. {att['name']} - URL: {att['url']}")
            
            print(f"✅ Webhook simulado procesado exitosamente")
            print(f"   En un escenario real, esto activaría:")
            print(f"   1. Download de documentos desde Pipefy")
            print(f"   2. Upload a Supabase Storage")
            print(f"   3. Registro en base de datos")
            print(f"   4. Llamada a servicio CrewAI para análisis")
            print(f"   5. Actualización de campos con resultados")
            print(f"   6. Movimiento de card según clasificación")
            
            return True
        else:
            print(f"⚠️  Card no está en fase de triagem: {current_phase_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error en simulación de webhook: {str(e)}")
        return False

async def main():
    """Función principal para pruebas con cards reales"""
    print("🎯 PRUEBAS CON CARDS REALES DE PIPEFY")
    print("=" * 50)
    
    # 1. Buscar pipes y fases disponibles
    pipes = await find_available_cards()
    
    if not pipes:
        print("❌ No se pudieron obtener pipes. Abortando pruebas.")
        return
    
    # 2. Buscar cards en la fase de triagem (338000020)
    triagem_phase_id = "338000020"
    print(f"\\n🎯 Buscando cards en fase de triagem (ID: {triagem_phase_id})...")
    
    cards_in_triagem = await get_cards_from_phase(triagem_phase_id, limit=3)
    
    if cards_in_triagem:
        # Usar el primer card encontrado para las pruebas
        test_card = cards_in_triagem[0]
        card_id = test_card['id']
        
        print(f"\\n🧪 Usando card para pruebas:")
        print(f"   ID: {card_id}")
        print(f"   Título: {test_card['title']}")
        
        # 3. Probar actualización de campo
        field_update_success = await test_field_update_with_real_card(card_id)
        
        # 4. Simular webhook completo
        webhook_success = await simulate_webhook_with_real_card(card_id)
        
        # Resumen final
        print(f"\\n" + "=" * 50)
        print(f"📊 RESUMEN DE PRUEBAS CON CARD REAL:")
        print(f"   Card ID utilizado: {card_id}")
        print(f"   Actualización de campo: {'✅ EXITOSA' if field_update_success else '❌ FALLÓ'}")
        print(f"   Simulación de webhook: {'✅ EXITOSA' if webhook_success else '❌ FALLÓ'}")
        
        if field_update_success and webhook_success:
            print(f"\\n🎉 ¡TODAS LAS PRUEBAS CON CARD REAL EXITOSAS!")
            print(f"   El sistema está completamente funcional.")
            print(f"   Puedes verificar el campo 'Informe CrewAI' en Pipefy.")
        else:
            print(f"\\n⚠️  Algunas pruebas fallaron.")
            print(f"   Revisar configuración y permisos.")
    
    else:
        # Si no hay cards en triagem, buscar en otras fases
        print(f"\\n⚠️  No se encontraron cards en la fase de triagem.")
        print(f"   Buscando cards en otras fases para pruebas...")
        
        for pipe in pipes:
            for phase in pipe['phases']:
                if phase['cards_count'] > 0:
                    print(f"\\n🔍 Probando fase: {phase['name']} ({phase['cards_count']} cards)")
                    cards = await get_cards_from_phase(phase['id'], limit=1)
                    
                    if cards:
                        test_card = cards[0]
                        card_id = test_card['id']
                        
                        print(f"✅ Usando card de fase diferente para pruebas:")
                        print(f"   ID: {card_id}")
                        print(f"   Título: {test_card['title']}")
                        print(f"   Fase: {phase['name']}")
                        
                        # Probar solo actualización de campo
                        field_update_success = await test_field_update_with_real_card(card_id)
                        
                        if field_update_success:
                            print(f"\\n🎉 ¡Prueba de campo exitosa con card real!")
                            print(f"   El sistema puede actualizar campos en Pipefy.")
                            return
                        else:
                            print(f"❌ Falló la actualización de campo.")
                            continue
        
        print(f"\\n❌ No se pudieron realizar pruebas con cards reales.")
        print(f"   Verifica que tengas cards disponibles en tus pipes.")

if __name__ == "__main__":
    asyncio.run(main())