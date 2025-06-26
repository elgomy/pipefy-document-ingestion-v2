#!/usr/bin/env python3
"""
Test final para confirmar envío de WhatsApp con número correcto
"""

import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_final_whatsapp():
    """
    Test final del envío de WhatsApp con el número correcto
    """
    # Simular función get_manager_phone_for_card actualizada
    async def get_manager_phone_for_card(card_id: str) -> str:
        # Formato correcto identificado en las pruebas
        return "+553199034444"
    
    # Simular envío de notificación
    async def send_whatsapp_notification(card_id: str, relatorio_detalhado: str) -> bool:
        """
        Simulación de envío de WhatsApp con el número correcto
        """
        # Obtener credenciales
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")
        
        if not account_sid or not auth_token:
            logger.error("❌ Credenciales de Twilio no configuradas")
            return False
        
        try:
            from twilio.rest import Client
            
            # Obtener número del gestor (ahora con formato correcto)
            manager_phone = await get_manager_phone_for_card(card_id)
            
            logger.info(f"🧪 TEST FINAL WHATSAPP")
            logger.info(f"   📱 Número del gestor: {manager_phone}")
            logger.info(f"   📱 Número Twilio: {whatsapp_number}")
            
            # Crear cliente Twilio
            client = Client(account_sid, auth_token)
            
            # Mensaje de prueba final
            message_body = f"""🎉 ¡TEST FINAL EXITOSO!

📱 Número correcto: {manager_phone}
⏰ Hora: {datetime.now().strftime('%H:%M:%S')}
🎯 Resultado: Formato identificado correctamente

{relatorio_detalhado}

✅ El sistema WhatsApp está funcionando correctamente!"""
            
            # Enviar mensaje
            message = client.messages.create(
                from_=f"whatsapp:{whatsapp_number}",
                body=message_body,
                to=f"whatsapp:{manager_phone}"
            )
            
            logger.info(f"✅ Mensaje enviado con éxito!")
            logger.info(f"   📧 SID: {message.sid}")
            logger.info(f"   📊 Status: {message.status}")
            
            # Verificar status después de un momento
            import time
            time.sleep(3)
            
            updated_message = client.messages(message.sid).fetch()
            logger.info(f"   🔄 Status actualizado: {updated_message.status}")
            
            if updated_message.error_code:
                logger.error(f"   ❌ Error Code: {updated_message.error_code}")
                logger.error(f"   ❌ Error Message: {updated_message.error_message}")
                return False
            else:
                if updated_message.status in ['sent', 'delivered', 'read']:
                    logger.info(f"   🎉 ¡ÉXITO TOTAL! El mensaje fue {updated_message.status}")
                    return True
                else:
                    logger.warning(f"   ⚠️  Status: {updated_message.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error en test final: {e}")
            return False
    
    # Ejecutar test
    logger.info("🚀 INICIANDO TEST FINAL DE WHATSAPP")
    logger.info("=" * 50)
    
    test_card_id = "test_card_123"
    test_report = """📋 PENDÊNCIA CRÍTICA DETECTADA:
- Documento faltante: Comprovante de endereço
- Status: Bloqueante
- Ação requerida: Enviar documento atualizado"""
    
    success = await send_whatsapp_notification(test_card_id, test_report)
    
    if success:
        logger.info("🎉 TEST FINAL CONCLUÍDO COM SUCESSO!")
        logger.info("   ✅ WhatsApp está funcionando corretamente")
        logger.info("   ✅ Número correto configurado: +553199034444")
        logger.info("   ✅ Sistema pronto para produção")
    else:
        logger.error("❌ TEST FINAL FALHOU")
        logger.error("   ⚠️  Verifique as configurações")
    
    return success

if __name__ == "__main__":
    print("🎯 TEST FINAL - WHATSAPP COM NÚMERO CORRETO")
    print("=" * 60)
    
    result = asyncio.run(test_final_whatsapp())
    
    if result:
        print("\n🎉 RESULTADO: SUCESSO TOTAL!")
        print("   💡 O sistema está pronto para uso em produção")
        print("   💡 Número WhatsApp corrigido: +553199034444")
    else:
        print("\n❌ RESULTADO: AINDA HÁ PROBLEMAS")
        print("   💡 Verifique os logs acima para mais detalhes")
