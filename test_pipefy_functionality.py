#!/usr/bin/env python3
"""
Script de prueba para la funcionalidad de Pipefy.
Permite probar el movimiento de cards y actualización de campos.
"""
import asyncio
import sys
from src.services.pipefy_service import pipefy_service
from src.integrations.pipefy_client import PipefyAPIError

async def test_card_operations():
    """Prueba las operaciones básicas con cards de Pipefy."""
    
    # Solicitar ID del card para prueba
    card_id = input("Ingresa el ID del card de Pipefy para probar: ").strip()
    
    if not card_id:
        print("❌ ID de card requerido")
        return
    
    print(f"\n🔍 Probando operaciones con card {card_id}...")
    print("=" * 60)
    
    try:
        # 1. Verificar que el card existe
        print("1. Verificando existencia del card...")
        exists = await pipefy_service.validate_card_exists(card_id)
        if not exists:
            print(f"❌ Card {card_id} no encontrado")
            return
        print(f"✅ Card {card_id} existe")
        
        # 2. Obtener información actual del card
        print("\n2. Obteniendo información del card...")
        card_info = await pipefy_service.get_card_status(card_id)
        print(f"   - Título: {card_info.get('title', 'N/A')}")
        print(f"   - Fase actual: {card_info.get('current_phase', {}).get('name', 'N/A')}")
        print(f"   - ID de fase: {card_info.get('current_phase', {}).get('id', 'N/A')}")
        
        # 3. Probar actualización de informe
        print("\n3. Actualizando campo de informe...")
        test_informe = f"""# 🤖 Informe de Prueba - Triagem CrewAI v2.0

## Resultado de la Prueba
- **Fecha**: {asyncio.get_event_loop().time()}
- **Card ID**: {card_id}
- **Estado**: Prueba de funcionalidad

## Validaciones Realizadas
✅ Conexión con API Pipefy  
✅ Autenticación exitosa  
✅ Actualización de campo funcional  

## Próximos Pasos
- Integrar con servicio CrewAI v2.0
- Implementar clasificación automática
- Configurar notificaciones WhatsApp

---
*Generado automáticamente por el sistema de pruebas*"""
        
        update_result = await pipefy_service.update_card_informe(card_id, test_informe)
        if update_result["success"]:
            print("✅ Campo de informe actualizado exitosamente")
        else:
            print("❌ Error actualizando campo de informe")
        
        # 4. Preguntar si probar movimiento de card
        print(f"\n4. ¿Probar movimiento de card?")
        print("   Clasificaciones disponibles:")
        print("   - Aprovado (fase 338000018)")
        print("   - Pendencia_Bloqueante (fase 338000017)")
        print("   - Pendencia_NaoBloqueante (fase 338000019)")
        
        test_move = input("\n¿Probar movimiento? (s/N): ").strip().lower()
        
        if test_move == 's':
            classification = input("Ingresa clasificación (Aprovado/Pendencia_Bloqueante/Pendencia_NaoBloqueante): ").strip()
            
            if classification in ["Aprovado", "Pendencia_Bloqueante", "Pendencia_NaoBloqueante"]:
                print(f"\n   Moviendo card a clasificación '{classification}'...")
                
                # Procesar resultado completo de triagem
                triagem_result = await pipefy_service.process_triagem_result(
                    card_id,
                    classification,
                    test_informe + f"\n\n## Clasificación Final: {classification}"
                )
                
                if triagem_result["success"]:
                    print("✅ Triagem procesada exitosamente")
                    for operation in triagem_result["operations"]:
                        if operation["type"] == "move_card":
                            print(f"   - Card movido a: {operation['new_phase_name']} (ID: {operation['new_phase_id']})")
                        elif operation["type"] == "update_field":
                            print(f"   - Campo actualizado: {operation['field_id']}")
                else:
                    print("❌ Error procesando triagem:")
                    for error in triagem_result["errors"]:
                        print(f"   - {error}")
            else:
                print("❌ Clasificación inválida")
        
        print(f"\n🎉 Pruebas completadas para card {card_id}")
        
    except PipefyAPIError as e:
        print(f"❌ Error de API Pipefy: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

async def test_configuration():
    """Prueba la configuración del sistema."""
    print("🔧 Verificando configuración...")
    print("=" * 40)
    
    from src.config import settings
    
    # Verificar variables críticas
    config_items = [
        ("PIPEFY_TOKEN", settings.PIPEFY_TOKEN, "Token de Pipefy"),
        ("PHASE_ID_APROVADO", settings.PHASE_ID_APROVADO, "ID Fase Aprovado"),
        ("PHASE_ID_PENDENCIAS", settings.PHASE_ID_PENDENCIAS, "ID Fase Pendências"),
        ("PHASE_ID_EMITIR_DOCS", settings.PHASE_ID_EMITIR_DOCS, "ID Fase Emitir Docs"),
        ("FIELD_ID_INFORME", settings.FIELD_ID_INFORME, "ID Campo Informe"),
    ]
    
    all_configured = True
    for var_name, var_value, description in config_items:
        status = "✅" if var_value else "❌"
        print(f"{status} {description}: {'Configurado' if var_value else 'FALTANTE'}")
        if not var_value:
            all_configured = False
    
    if all_configured:
        print("\n🎯 Configuración completa - Sistema listo para pruebas")
        return True
    else:
        print("\n⚠️  Configuración incompleta - Revisa el archivo .env")
        return False

async def main():
    """Función principal del script de pruebas."""
    print("🤖 Script de Prueba - Funcionalidad Pipefy v2.0")
    print("=" * 50)
    
    # Verificar configuración
    config_ok = await test_configuration()
    
    if not config_ok:
        print("\n💡 Para configurar:")
        print("   1. Copia .env.example como .env")
        print("   2. Completa las variables requeridas")
        print("   3. Ejecuta: python validate_env.py")
        sys.exit(1)
    
    # Probar operaciones con cards
    print("\n" + "=" * 50)
    await test_card_operations()

if __name__ == "__main__":
    asyncio.run(main())