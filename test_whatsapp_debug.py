#!/usr/bin/env python3
"""
Script de debug para WhatsApp - Diagnóstico de problemas de entrega
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

def test_whatsapp_delivery():
    """
    Testa la entrega de WhatsApp y diagnostica problemas
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
    
    # Número de prueba actualizado
    test_number = "+5531999034444"
    
    logger.info("🔍 DIAGNÓSTICO WHATSAPP")
    logger.info(f"   📞 Account SID: {account_sid[:8]}...")
    logger.info(f"   📱 WhatsApp Number: {whatsapp_number}")
    logger.info(f"   📱 Destinatário: {test_number}")
    
    try:
        # Enviar mensaje de prueba
        message_body = f"""
🔍 TESTE DE ENTREGA WHATSAPP
⏰ Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
📱 Sistema: Pipefy Document Ingestion
🎯 Objetivo: Verificar entrega de mensagens

Se você recebeu esta mensagem, o sistema está funcionando corretamente!
        """.strip()
        
        logger.info(f"📤 Enviando mensaje de prueba...")
        
        message = client.messages.create(
            body=message_body,
            from_=f"whatsapp:{whatsapp_number}",
            to=f"whatsapp:{test_number}"
        )
        
        logger.info(f"✅ Mensaje enviado exitosamente!")
        logger.info(f"   📧 SID: {message.sid}")
        logger.info(f"   📊 Status: {message.status}")
        logger.info(f"   💰 Price: {message.price}")
        logger.info(f"   🌍 Direction: {message.direction}")
        
        # Verificar detalles del mensaje después de un momento
        import time
        time.sleep(3)
        
        # Refrescar mensaje para obtener status actualizado
        updated_message = client.messages(message.sid).fetch()
        logger.info(f"🔄 Status actualizado: {updated_message.status}")
        
        if updated_message.error_code:
            logger.error(f"❌ Error Code: {updated_message.error_code}")
            logger.error(f"❌ Error Message: {updated_message.error_message}")
        
        # Verificar si hay problemas conocidos
        if updated_message.status in ['failed', 'undelivered']:
            logger.error("❌ MENSAJE NO ENTREGADO")
            logger.error("   Posibles causas:")
            logger.error("   1. Número no registrado en WhatsApp Business")
            logger.error("   2. Número no verificado en Twilio Sandbox")
            logger.error("   3. Mensaje bloqueado por políticas de WhatsApp")
            logger.error("   4. Número inválido o fuera de servicio")
        elif updated_message.status == 'sent':
            logger.info("✅ MENSAJE ENVIADO - Esperando entrega")
        elif updated_message.status == 'delivered':
            logger.info("✅ MENSAJE ENTREGADO EXITOSAMENTE")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error al enviar WhatsApp: {e}")
        return False

def check_twilio_account_info():
    """
    Verifica información de la cuenta de Twilio
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        logger.error("❌ Credenciales de Twilio no configuradas")
        return
    
    client = Client(account_sid, auth_token)
    
    try:
        # Obtener información de la cuenta
        account = client.api.accounts(account_sid).fetch()
        logger.info(f"📊 INFORMACIÓN DE LA CUENTA TWILIO")
        logger.info(f"   🏷️  Account Name: {account.friendly_name}")
        logger.info(f"   📊 Status: {account.status}")
        logger.info(f"   💰 Type: {account.type}")
        
        # Verificar números de WhatsApp disponibles
        incoming_numbers = client.incoming_phone_numbers.list()
        whatsapp_numbers = [num for num in incoming_numbers if 'whatsapp' in str(num.capabilities).lower()]
        
        if whatsapp_numbers:
            logger.info(f"📱 NÚMEROS WHATSAPP DISPONIBLES:")
            for num in whatsapp_numbers:
                logger.info(f"   📞 {num.phone_number} - {num.friendly_name}")
        else:
            logger.warning("⚠️  No se encontraron números de WhatsApp configurados")
            logger.info("   💡 Usando número sandbox: +14155238886")
            
    except Exception as e:
        logger.error(f"❌ Error al obtener información de cuenta: {e}")

if __name__ == "__main__":
    print("🔍 DIAGNÓSTICO WHATSAPP - PIPEFY DOCUMENT INGESTION")
    print("=" * 60)
    
    # Verificar información de cuenta
    check_twilio_account_info()
    print()
    
    # Probar entrega de mensaje
    test_whatsapp_delivery()
    
    print()
    print("💡 RECOMENDACIONES:")
    print("   1. Verificar que el número +5531999034444 esté registrado en WhatsApp")
    print("   2. Si usas Twilio Sandbox, agregar el número a la lista de verificados")
    print("   3. Verificar que el número no esté bloqueado")
    print("   4. Comprobar políticas de WhatsApp Business") 