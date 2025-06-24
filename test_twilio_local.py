#!/usr/bin/env python3
"""
Teste local das configurações do Twilio WhatsApp
"""
import asyncio
import os
from dotenv import load_dotenv
from src.integrations.twilio_client import TwilioClient

# Cargar variables de entorno
load_dotenv()

async def test_twilio_config():
    """Teste completo da configuração Twilio"""
    print("🧪 TESTE LOCAL TWILIO WHATSAPP\n")
    
    # Verificar credenciais
    print("🔍 VERIFICANDO CREDENCIALES TWILIO:")
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
    
    print(f"   📞 Account SID: {'✅ Configurado' if account_sid else '❌ Faltando'}")
    print(f"   🔑 Auth Token: {'✅ Configurado' if auth_token else '❌ Faltando'}")
    print(f"   📱 WhatsApp Number: {'✅ Configurado' if whatsapp_number else '❌ Faltando'}")
    
    # Verificar se está usando o número correto
    if whatsapp_number and whatsapp_number != "whatsapp:+14155238886":
        print(f"⚠️  ATENÇÃO: Número WhatsApp atual: {whatsapp_number}")
        print("   💡 Para sandbox, deve ser: whatsapp:+14155238886")
        print("   📝 Atualize seu arquivo .env:")
        print("      TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886")
    
    if not all([account_sid, auth_token, whatsapp_number]):
        print("❌ Credenciais incompletas! Configure o arquivo .env")
        return
    
    # Validar formato das credenciais
    if not account_sid.startswith("AC") or len(account_sid) != 34:
        print("❌ TWILIO_ACCOUNT_SID deve começar com 'AC' e ter 34 caracteres")
        return
    if len(auth_token) != 32:
        print("❌ TWILIO_AUTH_TOKEN deve ter 32 caracteres")
        return
    
    print("✅ Formato das credenciais correto!")
    print(f"   📞 Account SID: {account_sid[:10]}...{account_sid[-4:]}")
    print(f"   🔑 Auth Token: {auth_token[:8]}...{auth_token[-4:]}")
    print(f"   📱 WhatsApp Number: {whatsapp_number}")
    
    # Teste conexão
    try:
        print("\n🔄 Testando conexão com Twilio...")
        twilio_client = TwilioClient()
        account = twilio_client.client.api.account.fetch()
        print("✅ Conexão estabelecida com sucesso!")
        print(f"   📊 Account Status: {account.status}")
        print(f"   📊 Account Type: {getattr(account, 'type', 'N/A')}")
        
        # Aviso sobre conta Trial
        account_type = getattr(account, 'type', '')
        if account_type == "Trial":
            print("⚠️  CONTA TRIAL: Só pode enviar para números verificados")
            print("   💡 Para produção, faça upgrade para conta PAID")
        
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return
    
    # Teste envio WhatsApp
    # SUBSTITUA +5531999999999 pelo SEU número WhatsApp que já ativou o sandbox
    test_number = "+553199034444"  # ✅ NÚMERO TESTADO COM CURL
    print(f"\n⚠️  ATENÇÃO: Para teste completo, configure um número real que já ativou o sandbox")
    print(f"   📱 Para ativar sandbox, envie 'join <código>' para +14155238886")
    print(f"📱 Enviando mensagem de teste para {test_number}...")
    
    try:
        success = await twilio_client.send_whatsapp_message(
            to=test_number,
            message="🤖 Teste do sistema Pipefy-Twilio\n\nSe você recebeu esta mensagem, a configuração está funcionando!"
        )
        
        if success:
            print("✅ TESTE TWILIO: SUCESSO!")
            print(f"   📱 Mensagem enviada para {test_number}")
        else:
            print("❌ TESTE TWILIO: FALHOU!")
            
    except Exception as e:
        print(f"❌ Erro ao testar Twilio: {e}")
        print(f"   📊 Tipo: {type(e).__name__}")
        
        # Mensagens de ajuda específicas
        error_str = str(e)
        if "63007" in error_str:
            print("\n💡 SOLUÇÃO ERRO 63007:")
            print("   1. Use número sandbox: whatsapp:+14155238886")
            print("   2. Ou configure WhatsApp Business API")
        elif "21211" in error_str:
            print("\n💡 SOLUÇÃO: Use número no formato internacional (+5531999999999)")
        elif "authenticate" in error_str.lower():
            print("\n💡 SOLUÇÃO: Verifique TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN")
        
        print("\n💥 TESTE TWILIO: FALHOU!")

if __name__ == "__main__":
    asyncio.run(test_twilio_config()) 