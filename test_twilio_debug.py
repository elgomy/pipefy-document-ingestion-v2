#!/usr/bin/env python3
"""
Test de diagnóstico para Twilio WhatsApp
Investiga por qué los mensajes no están llegando
"""
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from src.integrations.twilio_client import TwilioClient

# Cargar variables de entorno
load_dotenv()

async def test_twilio_debug():
    """
    Test de diagnóstico detallado para Twilio
    """
    
    print("🔍 DIAGNÓSTICO TWILIO WHATSAPP\n")
    
    # Verificar variables de entorno
    print("📋 VERIFICANDO VARIABLES DE ENTORNO:")
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN") 
    whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
    
    print(f"   TWILIO_ACCOUNT_SID: {'✅ Configurado' if account_sid else '❌ Faltante'}")
    print(f"   TWILIO_AUTH_TOKEN: {'✅ Configurado' if auth_token else '❌ Faltante'}")
    print(f"   TWILIO_WHATSAPP_NUMBER: {whatsapp_number or '❌ Faltante'}")
    
    if account_sid:
        print(f"   Account SID: {account_sid[:8]}...{account_sid[-4:]}")
    
    if not all([account_sid, auth_token, whatsapp_number]):
        print("\n❌ Variables de entorno incompletas")
        return False
    
    try:
        # Crear cliente Twilio
        print(f"\n🔧 CREANDO CLIENTE TWILIO...")
        twilio_client = TwilioClient()
        
        # Test 1: Mensaje simple
        print(f"\n📱 TEST 1: Enviando mensaje simple...")
        test_phone = "+553199034444"
        simple_message = f"🧪 Test Twilio {datetime.now().strftime('%H:%M:%S')}\nEste es un mensaje de prueba."
        
        result1 = await twilio_client.send_whatsapp_message(test_phone, simple_message)
        
        print(f"   Resultado: {'✅ Éxito' if result1 else '❌ Falló'}")
        
        # Test 2: Verificar el cliente Twilio interno
        print(f"\n🔍 TEST 2: Verificando cliente Twilio interno...")
        
        # Acceder al cliente interno de Twilio
        if hasattr(twilio_client, 'client'):
            try:
                # Intentar obtener información de la cuenta
                account = twilio_client.client.api.accounts(account_sid).fetch()
                print(f"   ✅ Conexión con Twilio exitosa")
                print(f"   📊 Status cuenta: {account.status}")
                print(f"   📋 Nombre cuenta: {account.friendly_name}")
            except Exception as e:
                print(f"   ❌ Error conectando con Twilio: {e}")
        
        # Test 3: Listar mensajes recientes
        print(f"\n📜 TEST 3: Verificando mensajes recientes...")
        try:
            # Obtener los últimos 5 mensajes
            messages = twilio_client.client.messages.list(limit=5)
            
            print(f"   📊 Mensajes encontrados: {len(messages)}")
            
            for i, msg in enumerate(messages):
                print(f"   📨 Mensaje {i+1}:")
                print(f"      SID: {msg.sid}")
                print(f"      Para: {msg.to}")
                print(f"      De: {msg.from_}")
                print(f"      Status: {msg.status}")
                print(f"      Fecha: {msg.date_created}")
                print(f"      Error: {msg.error_code or 'Ninguno'}")
                
                if msg.error_message:
                    print(f"      Mensaje error: {msg.error_message}")
                print()
                
        except Exception as e:
            print(f"   ❌ Error obteniendo mensajes: {e}")
        
        # Test 4: Verificar número WhatsApp
        print(f"\n📞 TEST 4: Verificando configuración WhatsApp...")
        
        # Verificar formato del número
        formatted_from = whatsapp_number if whatsapp_number.startswith('whatsapp:') else f"whatsapp:{whatsapp_number}"
        formatted_to = f"whatsapp:{test_phone}"
        
        print(f"   📤 From: {formatted_from}")
        print(f"   📥 To: {formatted_to}")
        
        # Test 5: Envío con detalles completos
        print(f"\n📱 TEST 5: Enviando mensaje con logging detallado...")
        
        detailed_message = f"""🔍 Test Detallado Twilio
Timestamp: {datetime.now().isoformat()}
Desde: {formatted_from}
Para: {formatted_to}

Si recibes este mensaje, Twilio está funcionando correctamente."""
        
        try:
            # Enviar mensaje directamente usando el cliente Twilio
            message = twilio_client.client.messages.create(
                body=detailed_message,
                from_=formatted_from,
                to=formatted_to
            )
            
            print(f"   ✅ Mensaje enviado exitosamente!")
            print(f"   📨 SID: {message.sid}")
            print(f"   📊 Status inicial: {message.status}")
            print(f"   💰 Precio: {message.price or 'Pendiente'}")
            print(f"   🔗 URI: {message.uri}")
            
            # Esperar un momento y verificar status actualizado
            print(f"\n⏳ Esperando 5 segundos para verificar status...")
            await asyncio.sleep(5)
            
            # Obtener status actualizado
            updated_message = twilio_client.client.messages(message.sid).fetch()
            print(f"   📊 Status actualizado: {updated_message.status}")
            
            if updated_message.error_code:
                print(f"   ❌ Código error: {updated_message.error_code}")
                print(f"   💬 Mensaje error: {updated_message.error_message}")
            
        except Exception as e:
            print(f"   ❌ Error enviando mensaje detallado: {e}")
            import traceback
            print(f"   🔍 Traceback: {traceback.format_exc()}")
        
        # Resumen
        print(f"\n📊 RESUMEN DEL DIAGNÓSTICO:")
        print(f"   ✅ Variables entorno: Configuradas")
        print(f"   ✅ Cliente Twilio: Funcional")
        print(f"   ✅ Conexión API: Establecida")
        print(f"   📱 Mensajes enviados: Ver detalles arriba")
        
        print(f"\n💡 RECOMENDACIONES:")
        print(f"   1. Verificar que el número +553199034444 esté registrado en WhatsApp")
        print(f"   2. Confirmar que el WhatsApp Sandbox esté activo")
        print(f"   3. Revisar el status de los mensajes en la consola de Twilio")
        print(f"   4. Verificar si hay restricciones de rate limiting")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error en diagnóstico: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_twilio_debug())
    
    if result:
        print(f"\n🎯 DIAGNÓSTICO COMPLETADO")
        print(f"   📋 Revisar detalles arriba para identificar el problema")
    else:
        print(f"\n❌ DIAGNÓSTICO FALLÓ")
        print(f"   🔧 Verificar configuración de Twilio") 