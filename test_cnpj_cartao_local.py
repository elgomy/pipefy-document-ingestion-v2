#!/usr/bin/env python3
"""
Script de prueba local para generación de Cartão CNPJ via API CNPJá
"""
import os
import asyncio
import httpx
import tempfile
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

async def test_cnpj_cartao_generation():
    """Prueba la generación de Cartão CNPJ via API CNPJá"""
    
    # Credenciales y configuración
    CNPJA_API_KEY = os.getenv("CNPJA_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    
    print("🔍 VERIFICANDO CREDENCIALES:")
    print(f"   🔑 CNPJá API Key: {'✅ Configurado' if CNPJA_API_KEY else '❌ Não configurado'}")
    print(f"   🗄️ Supabase URL: {'✅ Configurado' if SUPABASE_URL else '❌ Não configurado'}")
    print(f"   🔑 Supabase Key: {'✅ Configurado' if SUPABASE_KEY else '❌ Não configurado'}")
    
    if not all([CNPJA_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        print("❌ Credenciais incompletas!")
        return False
    
    # CNPJ de teste (empresa real para teste)
    test_cnpj = "11222333000181"  # CNPJ de teste
    test_case_id = "TEST_LOCAL_001"
    
    print(f"\n🏭 TESTANDO GERAÇÃO DE CARTÃO CNPJ:")
    print(f"   📋 CNPJ: {test_cnpj}")
    print(f"   📁 Case ID: {test_case_id}")
    
    try:
        # PASO 1: Chamar API CNPJá para gerar PDF
        print(f"\n📄 PASO 1: Chamando API CNPJá...")
        
        headers = {
            "Authorization": f"Bearer {CNPJA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        cnpja_url = f"https://api.cnpja.com/companies/{test_cnpj}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(cnpja_url, headers=headers)
            print(f"📊 HTTP Status CNPJá: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Erro na API CNPJá: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                return False
            
            company_data = response.json()
            print(f"✅ Dados da empresa obtidos:")
            print(f"   🏢 Razão Social: {company_data.get('name', 'N/A')}")
            print(f"   📋 CNPJ: {company_data.get('tax_id', 'N/A')}")
            print(f"   📊 Status: {company_data.get('status', 'N/A')}")
            
            # PASO 2: Gerar PDF do cartão
            print(f"\n📄 PASO 2: Gerando PDF do cartão...")
            
            # Usar endpoint específico para PDF se disponível
            pdf_url = f"https://api.cnpja.com/companies/{test_cnpj}/card"
            
            pdf_response = await client.get(pdf_url, headers=headers)
            print(f"📊 HTTP Status PDF: {pdf_response.status_code}")
            
            if pdf_response.status_code == 200:
                # Verificar se é realmente um PDF
                content_type = pdf_response.headers.get('content-type', '')
                if 'pdf' in content_type.lower():
                    print(f"✅ PDF recebido com sucesso!")
                    print(f"   📊 Content-Type: {content_type}")
                    print(f"   📏 Tamanho: {len(pdf_response.content)} bytes")
                    
                    # PASO 3: Salvar temporariamente para teste
                    print(f"\n💾 PASO 3: Salvando PDF temporariamente...")
                    
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                        temp_file.write(pdf_response.content)
                        temp_path = temp_file.name
                    
                    print(f"✅ PDF salvo temporariamente: {temp_path}")
                    
                    # PASO 4: Testar upload para Supabase (simulado)
                    print(f"\n☁️ PASO 4: Testando conexão com Supabase...")
                    
                    try:
                        from supabase import create_client, Client
                        
                        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                        
                        # Testar conexão básica
                        test_query = supabase_client.table('documents').select('id').limit(1).execute()
                        print(f"✅ Conexão Supabase estabelecida!")
                        print(f"   📊 Tabela 'documents' acessível")
                        
                        # Simular upload (não vamos fazer upload real no teste)
                        bucket_name = "documents"
                        file_path = f"{test_case_id}/cartao_cnpj_gerado.pdf"
                        
                        print(f"✅ Upload simulado:")
                        print(f"   🪣 Bucket: {bucket_name}")
                        print(f"   📁 Caminho: {file_path}")
                        print(f"   📏 Tamanho: {len(pdf_response.content)} bytes")
                        
                        # Limpar arquivo temporário
                        os.unlink(temp_path)
                        print(f"🗑️ Arquivo temporário removido")
                        
                        return True
                        
                    except ImportError:
                        print("❌ Biblioteca Supabase não instalada. Execute: pip install supabase")
                        return False
                    except Exception as e:
                        print(f"❌ Erro ao testar Supabase: {e}")
                        return False
                else:
                    print(f"❌ Resposta não é um PDF: {content_type}")
                    print(f"   📄 Conteúdo: {pdf_response.text[:200]}...")
                    return False
            else:
                print(f"❌ Erro ao obter PDF: {pdf_response.status_code}")
                print(f"   📄 Response: {pdf_response.text}")
                
                # Tentar endpoint alternativo
                print(f"\n🔄 Tentando endpoint alternativo...")
                alt_url = f"https://api.cnpja.com/companies/{test_cnpj}/document"
                
                alt_response = await client.get(alt_url, headers=headers)
                print(f"📊 HTTP Status Alternativo: {alt_response.status_code}")
                
                if alt_response.status_code == 200:
                    print(f"✅ Endpoint alternativo funcionou!")
                    return True
                else:
                    print(f"❌ Endpoint alternativo também falhou")
                    return False
                    
    except Exception as e:
        print(f"❌ Erro geral no teste: {e}")
        print(f"   📊 Tipo: {type(e).__name__}")
        return False

async def test_cnpj_validation():
    """Testa validação e limpeza de CNPJ"""
    
    print("\n🧪 TESTANDO VALIDAÇÃO DE CNPJ:")
    
    test_cnpjs = [
        "11.222.333/0001-81",  # Formato com pontuação
        "11222333000181",      # Formato limpo
        "11 222 333 0001 81",  # Com espaços
        "CNPJ: 11.222.333/0001-81",  # Com prefixo
        "invalid",             # Inválido
        "123",                 # Muito curto
        "12345678901234567890" # Muito longo
    ]
    
    import re
    
    for test_cnpj in test_cnpjs:
        print(f"\n   🔍 Testando: '{test_cnpj}'")
        
        # Limpar CNPJ
        cnpj_clean = re.sub(r'[^\d]', '', test_cnpj)
        
        # Validar tamanho
        is_valid = len(cnpj_clean) == 14 and cnpj_clean.isdigit()
        
        print(f"      📝 Limpo: '{cnpj_clean}'")
        print(f"      📏 Tamanho: {len(cnpj_clean)}")
        print(f"      ✅ Válido: {'Sim' if is_valid else 'Não'}")

if __name__ == "__main__":
    print("🧪 TESTE LOCAL CARTÃO CNPJ\n")
    
    # Teste 1: Validação de CNPJ
    asyncio.run(test_cnpj_validation())
    
    # Teste 2: Geração de cartão
    result = asyncio.run(test_cnpj_cartao_generation())
    
    if result:
        print("\n🎉 TESTE CARTÃO CNPJ: SUCESSO!")
    else:
        print("\n💥 TESTE CARTÃO CNPJ: FALHOU!") 