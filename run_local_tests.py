#!/usr/bin/env python3
"""
Script maestro para ejecutar todas las pruebas locales antes del deploy
"""
import asyncio
import subprocess
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno al inicio
load_dotenv()

def print_header(title: str):
    """Imprime un header bonito para las secciones"""
    print("\n" + "="*60)
    print(f"🧪 {title}")
    print("="*60)

def print_separator():
    """Imprime un separador entre pruebas"""
    print("\n" + "-"*60)

async def run_test_script(script_name: str, description: str) -> bool:
    """Ejecuta un script de prueba y retorna True si fue exitoso"""
    
    print_header(f"EJECUTANDO: {description}")
    print(f"📄 Script: {script_name}")
    print(f"🕐 Hora: {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        # Ejecutar el script
        result = subprocess.run([
            sys.executable, script_name
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        print(f"\n📊 RESULTADO:")
        print(f"   ⚡ Exit Code: {result.returncode}")
        
        # Mostrar stdout
        if result.stdout:
            print(f"\n📄 STDOUT:")
            print(result.stdout)
        
        # Mostrar stderr si hay errores
        if result.stderr:
            print(f"\n🚨 STDERR:")
            print(result.stderr)
        
        success = result.returncode == 0
        
        if success:
            print(f"\n✅ {description}: SUCESSO!")
        else:
            print(f"\n❌ {description}: FALHOU!")
            
        return success
        
    except Exception as e:
        print(f"\n💥 ERRO ao executar {script_name}: {e}")
        return False

def check_environment():
    """Verifica se o ambiente está configurado corretamente"""
    
    print_header("VERIFICAÇÃO DO AMBIENTE")
    
    required_vars = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN", 
        "TWILIO_WHATSAPP_NUMBER",
        "PIPEFY_TOKEN",
        "CNPJA_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY"
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        status = "✅ Configurado" if value else "❌ Ausente"
        print(f"   {var}: {status}")
        
        if not value:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n🚨 VARIÁVEIS AUSENTES:")
        for var in missing_vars:
            print(f"   - {var}")
        print(f"\n💡 Configure essas variáveis no arquivo .env")
        return False
    else:
        print(f"\n✅ Todas as variáveis de ambiente estão configuradas!")
        return True

async def main():
    """Función principal que ejecuta todas las pruebas"""
    
    print("🚀 INICIANDO TESTES LOCAIS PRÉ-DEPLOY")
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Diretório: {os.getcwd()}")
    
    # Verificar ambiente
    if not check_environment():
        print("\n💥 AMBIENTE NÃO CONFIGURADO CORRETAMENTE!")
        print("Configure as variáveis de ambiente antes de continuar.")
        return False
    
    # Lista de pruebas a ejecutar
    tests = [
        {
            "script": "test_twilio_local.py",
            "description": "TESTE TWILIO WHATSAPP",
            "critical": True  # Prueba crítica
        },
        {
            "script": "test_pipefy_move_local.py", 
            "description": "TESTE MOVIMIENTO PIPEFY CARD",
            "critical": True  # Prueba crítica
        },
        {
            "script": "test_cnpj_cartao_local.py",
            "description": "TESTE CARTÃO CNPJ GENERATION",
            "critical": True  # Prueba crítica
        }
    ]
    
    results = []
    critical_failures = []
    
    # Ejecutar cada prueba
    for i, test in enumerate(tests, 1):
        print_separator()
        print(f"🔄 TESTE {i}/{len(tests)}")
        
        success = await run_test_script(test["script"], test["description"])
        results.append({
            "test": test["description"],
            "success": success,
            "critical": test["critical"]
        })
        
        if not success and test["critical"]:
            critical_failures.append(test["description"])
    
    # Mostrar resumen final
    print_header("RESUMEN FINAL DE TESTES")
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - successful_tests
    
    print(f"📊 ESTATÍSTICAS:")
    print(f"   🧪 Total de testes: {total_tests}")
    print(f"   ✅ Sucessos: {successful_tests}")
    print(f"   ❌ Falhas: {failed_tests}")
    print(f"   📈 Taxa de sucesso: {(successful_tests/total_tests)*100:.1f}%")
    
    print(f"\n📋 RESULTADOS DETALHADOS:")
    for result in results:
        status = "✅ SUCESSO" if result["success"] else "❌ FALHA"
        critical = "🚨 CRÍTICO" if result["critical"] else "ℹ️ OPCIONAL"
        print(f"   {status} {critical} - {result['test']}")
    
    # Verificar se está listo para deploy
    if critical_failures:
        print(f"\n🚨 TESTES CRÍTICOS FALHARAM:")
        for failure in critical_failures:
            print(f"   - {failure}")
        print(f"\n💥 NÃO RECOMENDADO FAZER DEPLOY!")
        print(f"   Corrija os problemas acima antes de fazer deploy.")
        return False
    else:
        print(f"\n🎉 TODOS OS TESTES CRÍTICOS PASSARAM!")
        print(f"✅ PRONTO PARA DEPLOY!")
        
        print(f"\n📋 PRÓXIMOS PASSOS:")
        print(f"   1. 🚀 Fazer commit das mudanças")
        print(f"   2. 📤 Push para GitHub")
        print(f"   3. 🔄 Redeploy no Render")
        print(f"   4. 🧪 Testar em produção")
        
        return True

if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print(f"\n🎊 TESTES LOCAIS: TODOS CRÍTICOS PASSARAM!")
        sys.exit(0)
    else:
        print(f"\n💥 TESTES LOCAIS: FALHAS CRÍTICAS DETECTADAS!")
        sys.exit(1) 