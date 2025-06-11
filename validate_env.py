#!/usr/bin/env python3
"""
Script de validación de entorno para Pipefy Document Analysis Platform.

Este script verifica que todas las variables de entorno necesarias estén configuradas
y que las conexiones a las APIs externas funcionen correctamente.
"""

import os
import sys
import asyncio
import aiohttp
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class EnvironmentValidator:
    """Validador de configuración de entorno."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.success_count = 0
        self.total_checks = 0
    
    def check_required_env_vars(self) -> bool:
        """Verifica que todas las variables de entorno requeridas estén configuradas."""
        print("🔍 Verificando variables de entorno...")
        
        required_vars = {
            # Pipefy
            'PIPEFY_API_TOKEN': 'Token de API de Pipefy',
            
            # OpenAI
            'OPENAI_API_KEY': 'Clave de API de OpenAI',
            
            # Twilio
            'TWILIO_ACCOUNT_SID': 'SID de cuenta de Twilio',
            'TWILIO_AUTH_TOKEN': 'Token de autenticación de Twilio',
            'TWILIO_WHATSAPP_FROM': 'Número de WhatsApp de Twilio',
            
            # Supabase
            'SUPABASE_URL': 'URL de Supabase',
            'SUPABASE_KEY': 'Clave de API de Supabase'
        }
        
        optional_vars = {
            'API_TIMEOUT': 'Timeout para APIs (default: 30)',
            'AZURE_OPENAI_ENDPOINT': 'Endpoint de Azure OpenAI (opcional)',
            'AZURE_OPENAI_API_KEY': 'Clave de Azure OpenAI (opcional)',
            'OLLAMA_BASE_URL': 'URL base de Ollama (opcional)'
        }
        
        all_good = True
        
        # Verificar variables requeridas
        for var, description in required_vars.items():
            self.total_checks += 1
            value = os.getenv(var)
            
            if not value:
                self.errors.append(f"❌ {var} no está configurada ({description})")
                all_good = False
            elif len(value.strip()) == 0:
                self.errors.append(f"❌ {var} está vacía ({description})")
                all_good = False
            else:
                print(f"  ✅ {var}: {'*' * min(len(value), 20)}...")
                self.success_count += 1
        
        # Verificar variables opcionales
        for var, description in optional_vars.items():
            value = os.getenv(var)
            if value:
                print(f"  ℹ️  {var}: {'*' * min(len(value), 20)}... ({description})")
            else:
                self.warnings.append(f"⚠️  {var} no configurada ({description})")
        
        return all_good
    
    async def check_pipefy_connection(self) -> bool:
        """Verifica la conexión con Pipefy."""
        print("\n🔗 Verificando conexión con Pipefy...")
        self.total_checks += 1
        
        token = os.getenv('PIPEFY_API_TOKEN')
        if not token:
            self.errors.append("❌ No se puede verificar Pipefy: token no configurado")
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Query simple para verificar autenticación
            query = """
            query {
              me {
                id
                name
                email
              }
            }
            """
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.pipefy.com/graphql',
                    json={'query': query},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        if 'errors' not in data:
                            user_name = data.get('data', {}).get('me', {}).get('name', 'Usuario')
                            print(f"  ✅ Conexión exitosa con Pipefy (Usuario: {user_name})")
                            self.success_count += 1
                            return True
                        else:
                            self.errors.append(f"❌ Error GraphQL en Pipefy: {data['errors']}")
                            return False
                    else:
                        self.errors.append(f"❌ Error HTTP en Pipefy: {response.status}")
                        return False
                        
        except asyncio.TimeoutError:
            self.errors.append("❌ Timeout al conectar con Pipefy")
            return False
        except Exception as e:
            self.errors.append(f"❌ Error al conectar con Pipefy: {str(e)}")
            return False
    
    async def check_openai_connection(self) -> bool:
        """Verifica la conexión con OpenAI."""
        print("\n🤖 Verificando conexión con OpenAI...")
        self.total_checks += 1
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            self.errors.append("❌ No se puede verificar OpenAI: API key no configurada")
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Request simple para verificar autenticación
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://api.openai.com/v1/models',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        model_count = len(data.get('data', []))
                        print(f"  ✅ Conexión exitosa con OpenAI ({model_count} modelos disponibles)")
                        self.success_count += 1
                        return True
                    else:
                        self.errors.append(f"❌ Error HTTP en OpenAI: {response.status}")
                        return False
                        
        except asyncio.TimeoutError:
            self.errors.append("❌ Timeout al conectar con OpenAI")
            return False
        except Exception as e:
            self.errors.append(f"❌ Error al conectar con OpenAI: {str(e)}")
            return False
    
    async def check_twilio_connection(self) -> bool:
        """Verifica la conexión con Twilio."""
        print("\n📱 Verificando conexión con Twilio...")
        self.total_checks += 1
        
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        if not account_sid or not auth_token:
            self.errors.append("❌ No se puede verificar Twilio: credenciales no configuradas")
            return False
        
        try:
            import base64
            
            # Autenticación básica para Twilio
            credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json'
            }
            
            # Verificar cuenta
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        account_name = data.get('friendly_name', 'Cuenta Twilio')
                        print(f"  ✅ Conexión exitosa con Twilio (Cuenta: {account_name})")
                        self.success_count += 1
                        return True
                    else:
                        self.errors.append(f"❌ Error HTTP en Twilio: {response.status}")
                        return False
                        
        except asyncio.TimeoutError:
            self.errors.append("❌ Timeout al conectar con Twilio")
            return False
        except Exception as e:
            self.errors.append(f"❌ Error al conectar con Twilio: {str(e)}")
            return False
    
    async def check_supabase_connection(self) -> bool:
        """Verifica la conexión con Supabase."""
        print("\n🗄️  Verificando conexión con Supabase...")
        self.total_checks += 1
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            self.errors.append("❌ No se puede verificar Supabase: configuración no completa")
            return False
        
        try:
            headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json'
            }
            
            # Verificar conexión con una query simple
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{url}/rest/v1/',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        print(f"  ✅ Conexión exitosa con Supabase")
                        self.success_count += 1
                        return True
                    else:
                        self.errors.append(f"❌ Error HTTP en Supabase: {response.status}")
                        return False
                        
        except asyncio.TimeoutError:
            self.errors.append("❌ Timeout al conectar con Supabase")
            return False
        except Exception as e:
            self.errors.append(f"❌ Error al conectar con Supabase: {str(e)}")
            return False
    
    def check_python_dependencies(self) -> bool:
        """Verifica que las dependencias de Python estén instaladas."""
        print("\n📦 Verificando dependencias de Python...")
        
        required_packages = [
            'aiohttp',
            'openai',
            'twilio',
            'supabase',
            'python-dotenv',
            'asyncio'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"  ✅ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"  ❌ {package} no está instalado")
        
        if missing_packages:
            self.errors.append(f"❌ Paquetes faltantes: {', '.join(missing_packages)}")
            self.errors.append("   Ejecuta: pip install -r requirements.txt")
            return False
        
        return True
    
    def print_summary(self):
        """Imprime un resumen de la validación."""
        print("\n" + "="*60)
        print("📋 RESUMEN DE VALIDACIÓN")
        print("="*60)
        
        print(f"✅ Verificaciones exitosas: {self.success_count}/{self.total_checks}")
        
        if self.errors:
            print(f"\n❌ ERRORES ENCONTRADOS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print(f"\n⚠️  ADVERTENCIAS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if not self.errors:
            print(f"\n🎉 ¡Configuración válida! La plataforma está lista para usar.")
            print(f"\n📚 Próximos pasos:")
            print(f"  1. Ejecuta: python docs/api/guides/quick_start.py")
            print(f"  2. Lee la documentación: docs/api/README.md")
            print(f"  3. Explora los ejemplos: docs/api/guides/")
        else:
            print(f"\n🔧 Corrige los errores antes de continuar.")
            print(f"📖 Consulta la guía de configuración: docs/api/guides/quick_start.md")
        
        print("="*60)

async def main():
    """Función principal de validación."""
    print("🚀 VALIDADOR DE ENTORNO - Pipefy Document Analysis Platform")
    print("="*60)
    
    validator = EnvironmentValidator()
    
    # Verificar dependencias de Python
    deps_ok = validator.check_python_dependencies()
    
    # Verificar variables de entorno
    env_ok = validator.check_required_env_vars()
    
    if not deps_ok or not env_ok:
        validator.print_summary()
        return False
    
    # Verificar conexiones a APIs (solo si las variables están configuradas)
    await validator.check_pipefy_connection()
    await validator.check_openai_connection()
    await validator.check_twilio_connection()
    await validator.check_supabase_connection()
    
    # Imprimir resumen
    validator.print_summary()
    
    # Retornar True si no hay errores
    return len(validator.errors) == 0

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Validación interrumpida por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado durante la validación: {e}")
        sys.exit(1)