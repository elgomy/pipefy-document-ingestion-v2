#!/usr/bin/env python3
"""
Test local para envío de WhatsApp - Probar diferentes formatos de número
"""

import os
import logging
from datetime import datetime
from twilio.rest import Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_different_number_formats():
    """
    Prueba envío de WhatsApp con diferentes formatos de número
    """
    
    # Obtener credenciales
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")
    
    if not account_sid or not auth_token:
        logger.error("❌ Credenciales de Twilio no configuradas")
        return
    
    # Inicializar cliente Twilio
    client = Client(account_sid, auth_token)
    
    # Diferentes formatos del número para probar
    test_numbers = [
        "+5531999034444",  # Número completo con 9 adicional
        "+553199034444",   # Número sin el 9 adicional (como aparece en Twilio)
        "5531999034444",   # Sin el +
        "553199034444",    # Sin el + y sin el 9
    ]
    
    logger.info("🧪 PRUEBA LOCAL DE WHATSAPP - DIFERENTES FORMATOS")
    logger.info(f"   📞 Account SID: {account_sid[:8]}...")
    logger.info(f"   📱 WhatsApp Number: {whatsapp_number}")
    
    for i, test_number in enumerate(test_numbers, 1):
        logger.info(f"\n🔍 PRUEBA {i}/4: Probando número {test_number}")
        
        try:
            # Mensaje de prueba específico para cada formato
            message_body = f"""
🧪 PRUEBA LOCAL {i}/4
📱 Número probado: {test_number}
⏰ Hora: {datetime.now().strftime('%H:%M:%S')}
🎯 Objetivo: Identificar formato correcto

Si recibes este mensaje, el formato {test_number} es correcto!
            """.strip()
            
            # Formatear número para WhatsApp
            whatsapp_to = f"whatsapp:{test_number}" if not test_number.startswith("whatsapp:") else test_number
            whatsapp_from = f"whatsapp:{whatsapp_number}" if not whatsapp_number.startswith("whatsapp:") else whatsapp_number
            
            logger.info(f"   📤 Enviando desde: {whatsapp_from}")
            logger.info(f"   📥 Enviando hacia: {whatsapp_to}")
            
            message = client.messages.create(
                body=message_body,
                from_=whatsapp_from,
                to=whatsapp_to
            )
            
            logger.info(f"   ✅ Mensaje enviado!")
            logger.info(f"   📧 SID: {message.sid}")
            logger.info(f"   📊 Status inicial: {message.status}")
            
            # Esperar un momento y verificar status
            import time
            time.sleep(2)
            
            # Refrescar mensaje para obtener status actualizado
            updated_message = client.messages(message.sid).fetch()
            logger.info(f"   🔄 Status actualizado: {updated_message.status}")
            
            if updated_message.error_code:
                logger.error(f"   ❌ Error Code: {updated_message.error_code}")
                logger.error(f"   ❌ Error Message: {updated_message.error_message}")
            else:
                if updated_message.status in ['sent', 'delivered']:
                    logger.info(f"   🎉 ¡ÉXITO! El formato {test_number} funciona correctamente")
                elif updated_message.status == 'queued':
                    logger.info(f"   ⏳ En cola - puede funcionar")
                
        except Exception as e:
            logger.error(f"   ❌ Error al enviar a {test_number}: {e}")
        
        # Pausa entre pruebas
        if i < len(test_numbers):
            logger.info("   ⏸️  Esperando 3 segundos antes de la siguiente prueba...")
            time.sleep(3)
    
    logger.info("\n📋 RESUMEN:")
    logger.info("   Revisa tu WhatsApp para ver qué mensajes llegaron")
    logger.info("   El formato que funcione será el correcto para usar en producción")

def check_sandbox_participants():
    """
    Verificar qué números están registrados en el sandbox
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        logger.error("❌ Credenciales de Twilio no configuradas")
        return
    
    client = Client(account_sid, auth_token)
    
    try:
        # Intentar obtener mensajes recientes para ver números registrados
        messages = client.messages.list(limit=10)
        
        logger.info("📱 NÚMEROS DETECTADOS EN MENSAJES RECIENTES:")
        unique_numbers = set()
        
        for msg in messages:
            if 'whatsapp:' in msg.to:
                unique_numbers.add(msg.to)
            if 'whatsapp:' in msg.from_:
                unique_numbers.add(msg.from_)
        
        for number in unique_numbers:
            logger.info(f"   📞 {number}")
            
        if not unique_numbers:
            logger.info("   ℹ️  No se encontraron números en mensajes recientes")
            
    except Exception as e:
        logger.error(f"❌ Error al verificar participantes: {e}")

if __name__ == "__main__":
    print("🧪 PRUEBA LOCAL WHATSAPP - FORMATOS DE NÚMERO")
    print("=" * 60)
    
    # Verificar números en sandbox
    check_sandbox_participants()
    print()
    
    # Probar diferentes formatos
    test_different_number_formats()
    
    print()
    print("💡 PRÓXIMOS PASOS:")
    print("   1. Revisa tu WhatsApp para ver qué mensajes llegaron")
    print("   2. El formato que funcione será el que debemos usar en producción")
    print("   3. Actualizar el código con el formato correcto") 