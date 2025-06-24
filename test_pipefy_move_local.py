#!/usr/bin/env python3
"""
Script de prueba local para movimiento de cards en Pipefy
"""
import os
import asyncio
import httpx
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

async def get_card_current_phase_info(card_id: str) -> dict:
    """
    Obtiene información de la fase actual del card para diagnóstico.
    """
    PIPEFY_TOKEN = os.getenv("PIPEFY_TOKEN")
    PIPEFY_API_URL = "https://api.pipefy.com/graphql"
    
    if not PIPEFY_TOKEN:
        print("❌ Token Pipefy não configurado")
        return None
    
    query = """
    query GetCardCurrentPhase($cardId: ID!) {
        card(id: $cardId) {
            id
            title
            current_phase {
                id
                name
            }
            pipe {
                id
                name
                phases {
                    id
                    name
                }
            }
        }
    }
    """
    
    variables = {"cardId": card_id}
    headers = {
        "Authorization": f"Bearer {PIPEFY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(PIPEFY_API_URL, json={"query": query, "variables": variables}, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "errors" not in data and data.get("data", {}).get("card"):
                    card_data = data["data"]["card"]
                    phase_info = card_data.get("current_phase", {})
                    pipe_info = card_data.get("pipe", {})
                    
                    return {
                        "card_id": card_data.get("id"),
                        "card_title": card_data.get("title"),
                        "current_phase": {
                            "id": phase_info.get("id"),
                            "name": phase_info.get("name")
                        },
                        "pipe": {
                            "id": pipe_info.get("id"),
                            "name": pipe_info.get("name"),
                            "phases": pipe_info.get("phases", [])
                        }
                    }
                else:
                    print(f"❌ Erro GraphQL ao obter fase atual: {data.get('errors', 'Unknown error')}")
            else:
                print(f"❌ HTTP {response.status_code} ao obter fase atual do card")
                
    except Exception as e:
        print(f"❌ Exceção ao obter fase atual: {str(e)}")
    
    return None

async def move_pipefy_card_to_phase(card_id: str, phase_id: str) -> bool:
    """
    Mueve un card de Pipefy a una nueva fase usando GraphQL.
    """
    PIPEFY_TOKEN = os.getenv("PIPEFY_TOKEN")
    PIPEFY_API_URL = "https://api.pipefy.com/graphql"
    
    if not PIPEFY_TOKEN:
        print("❌ Token Pipefy não configurado")
        return False
    
    # GraphQL mutation según documentación oficial de Pipefy
    mutation = f"""
    mutation {{
        moveCardToPhase(input: {{
            card_id: {card_id}
            destination_phase_id: {phase_id}
        }}) {{
            card {{
                id
                current_phase {{
                    id
                    name
                }}
            }}
        }}
    }}
    """
    
    headers = {
        "Authorization": f"Bearer {PIPEFY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {"query": mutation}
    
    try:
        print(f"🔄 Executando movimiento de card...")
        print(f"🔍 Payload GraphQL: {json.dumps(payload, indent=2)}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(PIPEFY_API_URL, json=payload, headers=headers)
            print(f"📊 HTTP Status: {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            print(f"📄 Response Data: {json.dumps(data, indent=2)}")
            
            if "errors" in data:
                print(f"❌ Erro GraphQL ao mover card {card_id}: {data['errors']}")
                for error in data['errors']:
                    error_msg = error.get('message', 'Unknown error')
                    error_code = error.get('extensions', {}).get('code', 'Unknown code')
                    print(f"   - {error_code}: {error_msg}")
                    
                    # Mensaje específico para errores de restricción de fase
                    if "Cannot move" in error_msg or "PHASE_TRANSITION_ERROR" in error_code:
                        print(f"🚨 FASE RESTRICTION ERROR: La fase destino {phase_id} no permite el movimiento desde la fase actual")
                        print(f"💡 SOLUCIÓN: Verificar 'Move card settings' en la UI de Pipefy para esta fase")
                        
                return False
            
            move_result = data.get("data", {}).get("moveCardToPhase")
            if move_result and move_result.get("card"):
                new_phase = move_result["card"]["current_phase"]
                print(f"✅ Card {card_id} movido exitosamente!")
                print(f"   📍 Nueva fase: {new_phase['name']} (ID: {new_phase['id']})")
                return True
            else:
                print(f"❌ Resposta inesperada ao mover card {card_id}: {data}")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao mover card {card_id} para fase {phase_id}: {e}")
        print(f"📍 Erro completo: {type(e).__name__}: {str(e)}")
        return False

async def test_pipefy_move():
    """Prueba el movimiento de card en Pipefy"""
    
    card_id = "1130856215"
    target_phase_id = "338000017"
    
    print("🔍 VERIFICANDO TOKEN PIPEFY:")
    PIPEFY_TOKEN = os.getenv("PIPEFY_TOKEN")
    print(f"   🔑 Pipefy Token: {'✅ Configurado' if PIPEFY_TOKEN else '❌ Não configurado'}")
    
    if not PIPEFY_TOKEN:
        print("❌ Token Pipefy não configurado!")
        return False
    
    print(f"   🔑 Token: {PIPEFY_TOKEN[:10]}...{PIPEFY_TOKEN[-10:] if len(PIPEFY_TOKEN) > 20 else PIPEFY_TOKEN}")
    
    # PASO 1: Obtener información actual del card
    print(f"\n📍 PASO 1: Obtener información del card {card_id}")
    card_info = await get_card_current_phase_info(card_id)
    
    if not card_info:
        print("❌ Não foi possível obter informações do card")
        return False
    
    print(f"✅ Informações do card obtidas:")
    print(f"   🎯 Card: {card_info['card_id']} - '{card_info['card_title']}'")
    print(f"   📍 Fase ATUAL: {card_info['current_phase']['name']} (ID: {card_info['current_phase']['id']})")
    print(f"   📍 Fase DESTINO: {target_phase_id}")
    print(f"   🏢 Pipe: {card_info['pipe']['name']} (ID: {card_info['pipe']['id']})")
    
    # Mostrar todas las fases disponibles
    print(f"\n📋 FASES DISPONIBLES NO PIPE:")
    for phase in card_info['pipe']['phases']:
        is_current = "🔸 ATUAL" if phase['id'] == card_info['current_phase']['id'] else ""
        is_target = "🎯 DESTINO" if phase['id'] == target_phase_id else ""
        print(f"   📍 {phase['name']} (ID: {phase['id']}) {is_current} {is_target}")
    
    # Verificar si ya está en la fase destino
    if card_info['current_phase']['id'] == target_phase_id:
        print(f"✅ Card ya está en la fase destino {target_phase_id}")
        return True
    
    # PASO 2: Intentar mover el card
    print(f"\n🔄 PASO 2: Mover card para fase {target_phase_id}")
    move_success = await move_pipefy_card_to_phase(card_id, target_phase_id)
    
    if move_success:
        print(f"✅ MOVIMIENTO EXITOSO!")
        
        # PASO 3: Verificar el movimiento
        print(f"\n🔍 PASO 3: Verificar movimiento")
        new_card_info = await get_card_current_phase_info(card_id)
        if new_card_info:
            print(f"✅ Verificação:")
            print(f"   📍 Fase ANTERIOR: {card_info['current_phase']['name']} (ID: {card_info['current_phase']['id']})")
            print(f"   📍 Fase ACTUAL: {new_card_info['current_phase']['name']} (ID: {new_card_info['current_phase']['id']})")
            
            if new_card_info['current_phase']['id'] == target_phase_id:
                print(f"🎉 SUCESSO TOTAL: Card movido corretamente!")
                return True
            else:
                print(f"⚠️ Card não está na fase esperada")
                return False
    else:
        print(f"❌ FALHA NO MOVIMIENTO")
        return False

if __name__ == "__main__":
    print("🧪 TESTE LOCAL MOVIMIENTO PIPEFY CARD\n")
    result = asyncio.run(test_pipefy_move())
    
    if result:
        print("\n🎉 TESTE PIPEFY: SUCESSO!")
    else:
        print("\n💥 TESTE PIPEFY: FALHOU!") 