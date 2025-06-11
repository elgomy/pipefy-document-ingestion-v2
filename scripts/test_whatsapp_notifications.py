#!/usr/bin/env python3
"""
Script de prueba manual para el sistema de notificaciones WhatsApp.
Permite probar el envío de notificaciones sin necesidad de un caso real.
"""
import asyncio
import sys
import os
from datetime import datetime

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.notification_service import (
    notification_service,
    NotificationRecipient,
    NotificationContext,
    NotificationType
)
from services.classification_service import (
    ClassificationResult,
    ClassificationType,
    DocumentAnalysis,
    DocumentType
)

def print_header(title: str):
    """Imprime un header formateado."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_result(result):
    """Imprime el resultado de una notificación."""
    if result.success:
        print(f"✅ Notificación enviada exitosamente!")
        print(f"   📱 Message SID: {result.message_sid}")
        print(f"   📞 Destinatario: {result.recipient.name} ({result.recipient.phone_number})")
        print(f"   🕐 Enviado en: {result.sent_at}")
    else:
        print(f"❌ Falló el envío de notificación")
        print(f"   🚫 Error: {result.error_message}")

async def test_phone_validation():
    """Test validación de números de teléfono."""
    print_header("TEST: Validación de Números de Teléfono")
    
    test_numbers = [
        "+5511999999999",  # Válido
        "5511999999999",   # Válido (sin +)
        "11999999999",     # Válido (código de área)
        "(11) 99999-9999", # Válido (com formatação)
        "123",             # Inválido (muito curto)
        "1234567890123456", # Inválido (muito longo)
    ]
    
    for number in test_numbers:
        print(f"\n📞 Testando: {number}")
        
        # Criar recipient de teste
        recipient = NotificationRecipient(
            name="Teste",
            phone_number=number,
            role="gestor_comercial"
        )
        
        # Validar
        result = notification_service.validate_recipient(recipient)
        
        if result["valid"]:
            print(f"   ✅ Válido: {result['formatted_phone']}")
        else:
            print(f"   ❌ Inválido: {result['error']}")

async def test_blocking_issues_notification():
    """Test notificação de pendências bloqueantes."""
    print_header("TEST: Notificação de Pendências Bloqueantes")
    
    # Criar destinatário de teste
    recipient = NotificationRecipient(
        name="João Silva",
        phone_number="+5511999999999",  # Número de teste
        role="gestor_comercial",
        is_active=True
    )
    
    # Criar contexto
    context = NotificationContext(
        case_id="CASE-TEST-001",
        company_name="Empresa Teste Ltda",
        cnpj="12.345.678/0001-99",
        analyst_name="Sistema de Teste"
    )
    
    # Criar resultado de classificação com pendências bloqueantes
    classification_result = ClassificationResult(
        ClassificationType.PENDENCIA_BLOQUEANTE,
        0.85,
        "Documentos com pendências bloqueantes detectadas",
        [
            DocumentAnalysis(DocumentType.CARTAO_CNPJ, False, False, ["Ausente"], None),
            DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, True, False, ["Vencido há 120 dias"], 120)
        ],
        [
            "Cartão CNPJ não foi enviado",
            "Contrato social está vencido há mais de 90 dias",
            "Necessário envio de nova documentação"
        ],
        [],
        []
    )
    
    print("📋 Enviando notificação de pendências bloqueantes...")
    print(f"   👤 Para: {recipient.name} ({recipient.phone_number})")
    print(f"   🏢 Empresa: {context.company_name}")
    print(f"   📄 Caso: {context.case_id}")
    
    try:
        result = await notification_service.send_classification_notification(
            classification_result,
            context,
            recipient
        )
        print_result(result)
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

async def test_approval_notification():
    """Test notificação de aprovação."""
    print_header("TEST: Notificação de Aprovação")
    
    # Criar destinatário de teste
    recipient = NotificationRecipient(
        name="Maria Santos",
        phone_number="+5511888888888",  # Número de teste
        role="gestor_comercial",
        is_active=True
    )
    
    # Criar contexto
    context = NotificationContext(
        case_id="CASE-TEST-002",
        company_name="Empresa Aprovada S.A.",
        cnpj="98.765.432/0001-11",
        analyst_name="Sistema de Teste"
    )
    
    # Criar resultado de classificação aprovado
    classification_result = ClassificationResult(
        ClassificationType.APROVADO,
        0.95,
        "Documentação aprovada para prosseguimento",
        [
            DocumentAnalysis(DocumentType.CARTAO_CNPJ, True, True, [], 30),
            DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, True, True, [], 45),
            DocumentAnalysis(DocumentType.RG_CPF_SOCIOS, True, True, [], 60)
        ],
        [],
        [],
        []
    )
    
    print("📋 Enviando notificação de aprovação...")
    print(f"   👤 Para: {recipient.name} ({recipient.phone_number})")
    print(f"   🏢 Empresa: {context.company_name}")
    print(f"   📄 Caso: {context.case_id}")
    
    try:
        result = await notification_service.send_classification_notification(
            classification_result,
            context,
            recipient
        )
        print_result(result)
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

async def test_non_blocking_issues_notification():
    """Test notificação de pendências não bloqueantes."""
    print_header("TEST: Notificação de Pendências Não Bloqueantes")
    
    # Criar destinatário de teste
    recipient = NotificationRecipient(
        name="Carlos Oliveira",
        phone_number="+5511777777777",  # Número de teste
        role="gestor_comercial",
        is_active=True
    )
    
    # Criar contexto
    context = NotificationContext(
        case_id="CASE-TEST-003",
        company_name="Empresa Com Observações Ltda",
        cnpj="11.222.333/0001-44",
        analyst_name="Sistema de Teste"
    )
    
    # Criar resultado com pendências não bloqueantes
    classification_result = ClassificationResult(
        ClassificationType.PENDENCIA_NAO_BLOQUEANTE,
        0.75,
        "Documentação aprovada com observações",
        [
            DocumentAnalysis(DocumentType.CARTAO_CNPJ, False, False, ["Ausente"], None, True),
            DocumentAnalysis(DocumentType.CONTRATO_SOCIAL, True, True, [], 45),
            DocumentAnalysis(DocumentType.RG_CPF_SOCIOS, True, True, [], 60)
        ],
        [],
        [
            "Cartão CNPJ pode ser gerado automaticamente",
            "Recomenda-se atualização do contrato social"
        ],
        [
            "Gerar Cartão CNPJ automaticamente",
            "Notificar sobre atualização recomendada"
        ]
    )
    
    print("📋 Enviando notificação de pendências não bloqueantes...")
    print(f"   👤 Para: {recipient.name} ({recipient.phone_number})")
    print(f"   🏢 Empresa: {context.company_name}")
    print(f"   📄 Caso: {context.case_id}")
    
    try:
        result = await notification_service.send_classification_notification(
            classification_result,
            context,
            recipient
        )
        print_result(result)
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

async def test_custom_notification():
    """Test notificação personalizada."""
    print_header("TEST: Notificação Personalizada")
    
    # Criar destinatário de teste
    recipient = NotificationRecipient(
        name="Ana Costa",
        phone_number="+5511666666666",  # Número de teste
        role="gestor_comercial",
        is_active=True
    )
    
    # Mensagem personalizada
    custom_message = """🔧 *TESTE DO SISTEMA DE NOTIFICAÇÕES*

📋 *Caso:* CASE-TEST-CUSTOM
🏢 *Empresa:* Sistema de Teste

✅ Esta é uma mensagem de teste do sistema de notificações WhatsApp.

🎯 *Funcionalidades testadas:*
• Envio de mensagens personalizadas
• Formatação de texto
• Emojis e caracteres especiais

📱 Se você recebeu esta mensagem, o sistema está funcionando corretamente!

_Mensagem automática do Sistema de Triagem v2.0_"""
    
    print("📋 Enviando notificação personalizada...")
    print(f"   👤 Para: {recipient.name} ({recipient.phone_number})")
    
    try:
        result = await notification_service.send_custom_notification(
            recipient,
            custom_message,
            NotificationType.SYSTEM_ERROR
        )
        print_result(result)
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

async def test_message_status():
    """Test consulta de status de mensagem."""
    print_header("TEST: Consulta de Status de Mensagem")
    
    # SID de teste (normalmente seria retornado de un envío anterior)
    test_message_sid = "SM123456789abcdef"
    
    print(f"📋 Consultando status da mensagem: {test_message_sid}")
    
    try:
        status = await notification_service.get_notification_status(test_message_sid)
        
        if status.get("success"):
            print("✅ Status obtido com sucesso:")
            print(f"   📱 SID: {status.get('message_sid')}")
            print(f"   📊 Status: {status.get('status')}")
            print(f"   📅 Criado: {status.get('date_created')}")
            print(f"   📤 Enviado: {status.get('date_sent')}")
            print(f"   💰 Preço: {status.get('price')} {status.get('price_unit')}")
        else:
            print(f"❌ Erro ao obter status: {status.get('error')}")
            
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

def print_menu():
    """Imprime o menu de opções."""
    print("\n" + "="*60)
    print(" SISTEMA DE TESTE - NOTIFICAÇÕES WHATSAPP")
    print("="*60)
    print("1. Testar validação de números de telefone")
    print("2. Testar notificação de pendências bloqueantes")
    print("3. Testar notificação de aprovação")
    print("4. Testar notificação de pendências não bloqueantes")
    print("5. Testar notificação personalizada")
    print("6. Testar consulta de status de mensagem")
    print("7. Executar todos os testes")
    print("0. Sair")
    print("="*60)

async def run_all_tests():
    """Executa todos os testes."""
    print_header("EXECUTANDO TODOS OS TESTES")
    
    tests = [
        ("Validação de Telefones", test_phone_validation),
        ("Pendências Bloqueantes", test_blocking_issues_notification),
        ("Aprovação", test_approval_notification),
        ("Pendências Não Bloqueantes", test_non_blocking_issues_notification),
        ("Notificação Personalizada", test_custom_notification),
        ("Status de Mensagem", test_message_status),
    ]
    
    for test_name, test_func in tests:
        print(f"\n🧪 Executando: {test_name}")
        try:
            await test_func()
            print(f"✅ {test_name} - Concluído")
        except Exception as e:
            print(f"❌ {test_name} - Erro: {e}")
        
        # Pausa entre testes
        await asyncio.sleep(1)
    
    print_header("TODOS OS TESTES CONCLUÍDOS")

async def main():
    """Função principal do script."""
    print_header("INICIALIZANDO SISTEMA DE TESTE")
    
    # Verificar configuração
    try:
        from config.settings import settings
        
        print("🔧 Verificando configuração...")
        
        if not settings.TWILIO_ACCOUNT_SID:
            print("⚠️  TWILIO_ACCOUNT_SID não configurado")
        if not settings.TWILIO_AUTH_TOKEN:
            print("⚠️  TWILIO_AUTH_TOKEN não configurado")
        if not settings.TWILIO_WHATSAPP_NUMBER:
            print("⚠️  TWILIO_WHATSAPP_NUMBER não configurado")
        
        print("✅ Configuração carregada")
        
    except Exception as e:
        print(f"❌ Erro na configuração: {e}")
        print("⚠️  Alguns testes podem falhar")
    
    # Menu interativo
    while True:
        print_menu()
        
        try:
            choice = input("\nEscolha uma opção: ").strip()
            
            if choice == "0":
                print("\n👋 Encerrando sistema de teste...")
                break
            elif choice == "1":
                await test_phone_validation()
            elif choice == "2":
                await test_blocking_issues_notification()
            elif choice == "3":
                await test_approval_notification()
            elif choice == "4":
                await test_non_blocking_issues_notification()
            elif choice == "5":
                await test_custom_notification()
            elif choice == "6":
                await test_message_status()
            elif choice == "7":
                await run_all_tests()
            else:
                print("❌ Opção inválida. Tente novamente.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Encerrando sistema de teste...")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando sistema de teste de notificações WhatsApp...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Sistema encerrado pelo usuário.")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1) 