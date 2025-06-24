#!/usr/bin/env python3
"""
Test completo del flujo correcto de movimiento de card Pipefy
338000020 (Triagem Documentos AI) -> 338000017 (Pendências Documentais)
"""
import os
import asyncio
import httpx
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

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
        print(f"🔄 Movendo card {card_id} para fase {phase_id}...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(PIPEFY_API_URL, json=payload, headers=headers)
            print(f"📊 HTTP Status: {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                print(f"❌ Erro GraphQL: {data['errors']}")
                for error in data['errors']:
                    error_msg = error.get('message', 'Unknown error')
                    error_code = error.get('extensions', {}).get('code', 'Unknown code')
                    print(f"   - {error_code}: {error_msg}")
                return False
            
            move_result = data.get("data", {}).get("moveCardToPhase")
            if move_result and move_result.get("card"):
                new_phase = move_result["card"]["current_phase"]
                print(f"✅ Card movido exitosamente!")
                print(f"   📍 Nova fase: {new_phase['name']} (ID: {new_phase['id']})")
                return True
            else:
                print(f"❌ Resposta inesperada: {data}")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao mover card: {e}")
        return False

async def get_card_current_phase_info(card_id: str) -> dict:
    """
    Obtiene información de la fase actual del card.
    """
    PIPEFY_TOKEN = os.getenv("PIPEFY_TOKEN")
    PIPEFY_API_URL = "https://api.pipefy.com/graphql"
    
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
    except Exception as e:
        print(f"❌ Erro ao obter info do card: {e}")
    
    return None

async def test_correct_flow():
    """
    Testa o fluxo correto de movimiento de card:
    1. Verificar fase atual
    2. Mover para Triagem Documentos AI (338000020) se necessário
    3. Mover para Pendências Documentais (338000017)
    """
    
    card_id = "1130856215"
    triagem_phase_id = "338000020"    # Triagem Documentos AI
    pendencias_phase_id = "338000017" # Pendências Documentais
    
    print("🧪 TESTE FLUXO CORRETO MOVIMIENTO PIPEFY CARD")
    print(f"📋 Card ID: {card_id}")
    print(f"📍 Fase origem esperada: {triagem_phase_id} (Triagem Documentos AI)")
    print(f"📍 Fase destino: {pendencias_phase_id} (Pendências Documentais)")
    
    # PASO 1: Obtener información actual del card
    print(f"\n📍 PASO 1: Verificar fase atual do card")
    card_info = await get_card_current_phase_info(card_id)
    
    if not card_info:
        print("❌ Não foi possível obter informações do card")
        return False
    
    current_phase_id = card_info['current_phase']['id']
    current_phase_name = card_info['current_phase']['name']
    
    print(f"✅ Card encontrado:")
    print(f"   🎯 Título: {card_info['card_title']}")
    print(f"   📍 Fase atual: {current_phase_name} (ID: {current_phase_id})")
    
    # PASO 2: Mover para fase de triagem se necesario
    if current_phase_id != triagem_phase_id:
        print(f"\n🔄 PASO 2: Mover para fase de Triagem Documentos AI primeiro")
        print(f"   📍 {current_phase_name} -> Triagem Documentos AI")
        
        success = await move_pipefy_card_to_phase(card_id, triagem_phase_id)
        if not success:
            print("❌ Falha ao mover para fase de triagem")
            return False
        
        # Verificar se moveu corretamente
        updated_info = await get_card_current_phase_info(card_id)
        if updated_info and updated_info['current_phase']['id'] == triagem_phase_id:
            print("✅ Card movido para Triagem Documentos AI com sucesso!")
        else:
            print("❌ Card não foi movido para a fase esperada")
            return False
    else:
        print(f"✅ Card já está na fase de Triagem Documentos AI")
    
    # PASO 3: Mover para fase de pendencias
    print(f"\n🎯 PASO 3: Mover para Pendências Documentais")
    print(f"   📍 Triagem Documentos AI -> Pendências Documentais")
    
    success = await move_pipefy_card_to_phase(card_id, pendencias_phase_id)
    if not success:
        print("❌ Falha ao mover para Pendências Documentais")
        return False
    
    # PASO 4: Verificar movimiento final
    print(f"\n🔍 PASO 4: Verificar resultado final")
    final_info = await get_card_current_phase_info(card_id)
    
    if final_info:
        final_phase_id = final_info['current_phase']['id']
        final_phase_name = final_info['current_phase']['name']
        
        print(f"📊 Estado final:")
        print(f"   📍 Fase: {final_phase_name} (ID: {final_phase_id})")
        
        if final_phase_id == pendencias_phase_id:
            print(f"🎉 SUCESSO TOTAL: Card movido corretamente para Pendências Documentais!")
            return True
        else:
            print(f"⚠️ Card não está na fase final esperada")
            return False
    
    return False

if __name__ == "__main__":
    print("🧪 TESTE FLUXO CORRETO PIPEFY\n")
    result = asyncio.run(test_correct_flow())
    
    if result:
        print("\n🎉 TESTE FLUXO CORRETO: SUCESSO!")
    else:
        print("\n💥 TESTE FLUXO CORRETO: FALHOU!") 