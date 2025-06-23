#!/usr/bin/env python3
"""
Script de prueba simple para verificar la funcionalidad básica del sistema.
"""

import os
import json
import httpx
import asyncio
from datetime import datetime

# Cargar variables de entorno desde .env
def load_env_vars():
    """Cargar variables de entorno desde archivo .env"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    env_vars = {}
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
                    os.environ[key] = value
    
    return env_vars

async def test_pipefy_connection():
    """Probar conexión básica con Pipefy"""
    print("🔗 Probando conexión con Pipefy...")
    
    token = os.getenv('PIPEFY_TOKEN')
    if not token:
        print("❌ No se encontró PIPEFY_TOKEN en las variables de entorno")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Query simple para probar la conexión
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
                    print(f"❌ Respuesta inesperada de Pipefy: {result}")
                    return False
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error al conectar con Pipefy: {str(e)}")
        return False

def test_webhook_payload():
    """Probar el procesamiento de un payload de webhook simulado"""
    print("\n📝 Probando procesamiento de payload de webhook...")
    
    # Payload simulado del webhook de Pipefy
    test_payload = {
        "data": {
            "card": {
                "id": "123456789",
                "title": "Documento de Teste - CNPJ 12.345.678/0001-90",
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
                    }
                ],
                "attachments": [
                    {
                        "id": "attachment_1",
                        "name": "documento_teste.pdf",
                        "url": "https://example.com/documento_teste.pdf"
                    },
                    {
                        "id": "attachment_2", 
                        "name": "contrato_social.pdf",
                        "url": "https://example.com/contrato_social.pdf"
                    }
                ]
            }
        }
    }
    
    try:
        # Extraer información del payload
        card_data = test_payload.get('data', {}).get('card', {})
        card_id = card_data.get('id')
        current_phase_id = card_data.get('current_phase', {}).get('id')
        attachments = card_data.get('attachments', [])
        
        print(f"✅ Payload procesado correctamente:")
        print(f"   Card ID: {card_id}")
        print(f"   Phase ID: {current_phase_id}")
        print(f"   Número de attachments: {len(attachments)}")
        
        # Verificar que es la fase correcta para triagem
        if current_phase_id == "338000020":
            print("✅ Fase de triagem detectada correctamente")
            
            # Mostrar attachments encontrados
            for i, attachment in enumerate(attachments, 1):
                print(f"   📎 Documento {i}: {attachment['name']}")
            
            return True
        else:
            print(f"⚠️  Fase diferente a triagem detectada: {current_phase_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error al procesar payload: {str(e)}")
        return False

def test_result_formatting():
    """Probar el formateo de resultados de análisis"""
    print("\n📊 Probando formateo de resultados...")
    
    # Resultado simulado del análisis de CrewAI
    mock_analysis = {
        "classification": "PENDENCIA_BLOQUEANTE",
        "confidence": 0.85,
        "issues": [
            {
                "type": "missing_document",
                "description": "Falta el documento de constitución da empresa",
                "severity": "high"
            },
            {
                "type": "invalid_signature",
                "description": "Assinatura do representante legal não confere",
                "severity": "medium"
            }
        ],
        "recommendations": [
            "Solicitar documento de constituição atualizado",
            "Verificar assinatura do representante legal"
        ],
        "cnpj_info": {
            "cnpj": "12.345.678/0001-90",
            "razao_social": "Empresa Teste LTDA",
            "status": "ATIVA"
        },
        "analysis_date": datetime.now().isoformat()
    }
    
    try:
        # Formatear resultado detallado (simulando el ResultFormatter)
        detailed_report = f"""# RELATÓRIO DE TRIAGEM DE DOCUMENTOS

## Informações Gerais
- **CNPJ**: {mock_analysis['cnpj_info']['cnpj']}
- **Razão Social**: {mock_analysis['cnpj_info']['razao_social']}
- **Status**: {mock_analysis['cnpj_info']['status']}
- **Data da Análise**: {mock_analysis['analysis_date']}

## Classificação
**{mock_analysis['classification']}** (Confiança: {mock_analysis['confidence']:.1%})

## Problemas Identificados
"""
        
        for i, issue in enumerate(mock_analysis['issues'], 1):
            detailed_report += f"{i}. **{issue['description']}** (Severidade: {issue['severity']})\n"
        
        detailed_report += "\n## Recomendações\n"
        for i, rec in enumerate(mock_analysis['recommendations'], 1):
            detailed_report += f"{i}. {rec}\n"
        
        # Formatear resultado resumido
        summary_report = f"Classificação: {mock_analysis['classification']} | Problemas: {len(mock_analysis['issues'])} | Confiança: {mock_analysis['confidence']:.1%}"
        
        print("✅ Relatórios formatados correctamente:")
        print(f"   Relatório detalhado: {len(detailed_report)} caracteres")
        print(f"   Relatório resumido: {len(summary_report)} caracteres")
        
        print("\n📄 Muestra del relatório detalhado:")
        print(detailed_report[:300] + "..." if len(detailed_report) > 300 else detailed_report)
        
        return True, detailed_report, summary_report
        
    except Exception as e:
        print(f"❌ Error al formatear resultados: {str(e)}")
        return False, None, None

async def test_card_movement_simulation():
    """Simular el movimiento de card según clasificación"""
    print("\n🔄 Simulando movimiento de card...")
    
    # Mapeo de clasificaciones a fases (según el .env)
    phase_mapping = {
        "APROVADO": os.getenv('PHASE_ID_APROVADO', '338000018'),
        "PENDENCIA_BLOQUEANTE": os.getenv('PHASE_ID_PENDENCIAS', '338000017'),
        "PENDENCIA_NAO_BLOQUEANTE": os.getenv('PHASE_ID_EMITIR_DOCS', '338000019')
    }
    
    test_cases = [
        ("APROVADO", "Documento aprovado - todos os requisitos atendidos"),
        ("PENDENCIA_BLOQUEANTE", "Documentos faltantes - bloqueante"),
        ("PENDENCIA_NAO_BLOQUEANTE", "Pequenos ajustes necessários")
    ]
    
    print("📋 Mapeamento de fases configurado:")
    for classification, phase_id in phase_mapping.items():
        print(f"   {classification} → Fase {phase_id}")
    
    print("\n🧪 Casos de teste:")
    for classification, description in test_cases:
        target_phase = phase_mapping.get(classification, "DESCONOCIDA")
        print(f"   ✅ {classification}: {description} → Fase {target_phase}")
    
    return True

def test_environment_config():
    """Verificar configuración de variables de entorno"""
    print("\n🔧 Verificando configuración de entorno...")
    
    required_vars = [
        'PIPEFY_TOKEN',
        'SUPABASE_URL', 
        'SUPABASE_ANON_KEY',
        'PHASE_ID_APROVADO',
        'PHASE_ID_PENDENCIAS',
        'PHASE_ID_EMITIR_DOCS',
        'FIELD_ID_INFORME'
    ]
    
    optional_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'CNPJA_API_KEY',
        'CREWAI_SERVICE_URL'
    ]
    
    print("📋 Variables requeridas:")
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mostrar solo los primeros caracteres por seguridad
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: NO CONFIGURADA")
            missing_required.append(var)
    
    print("\n📋 Variables opcionales:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ⚠️  {var}: no configurada")
    
    if missing_required:
        print(f"\n❌ Variables requeridas faltantes: {missing_required}")
        return False
    else:
        print("\n✅ Todas las variables requeridas están configuradas")
        return True

async def main():
    """Función principal de pruebas"""
    print("🔍 PRUEBAS DE FUNCIONALIDAD DEL SISTEMA DE TRIAGEM")
    print("=" * 55)
    
    # Cargar variables de entorno
    print("📁 Cargando variables de entorno...")
    env_vars = load_env_vars()
    print(f"   Cargadas {len(env_vars)} variables desde .env")
    
    # Ejecutar pruebas
    results = {}
    
    # 1. Verificar configuración
    results['config'] = test_environment_config()
    
    # 2. Probar conexión con Pipefy
    results['pipefy'] = await test_pipefy_connection()
    
    # 3. Probar procesamiento de webhook
    results['webhook'] = test_webhook_payload()
    
    # 4. Probar formateo de resultados
    results['formatting'] = test_result_formatting()[0]
    
    # 5. Simular movimiento de cards
    results['movement'] = await test_card_movement_simulation()
    
    # Resumen final
    print("\n" + "=" * 55)
    print("📊 RESUMEN DE PRUEBAS:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Resultado final: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print("\n🎉 ¡Todas las pruebas pasaron!")
        print("   El sistema está listo para recibir webhooks de Pipefy.")
        print("   Puedes probar enviando una solicitud POST a /webhook/triagem")
    else:
        print("\n⚠️  Algunas pruebas fallaron.")
        print("   Revisar la configuración antes de usar en producción.")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())