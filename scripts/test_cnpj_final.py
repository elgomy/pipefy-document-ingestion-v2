#!/usr/bin/env python3
"""
Script de teste final para integração CNPJ.
"""

import asyncio
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.cnpj_client import CNPJClient, CNPJAPIError
from src.services.cnpj_service import CNPJService, CNPJServiceError


async def test_cnpj_integration():
    """Teste completo da integração CNPJ."""
    print("🔧 Teste Final da Integração CNPJ")
    print("=" * 50)
    
    # Teste 1: Validação de CNPJ
    print("\n1. Teste de Validação de CNPJ:")
    client = CNPJClient()
    
    cnpjs_teste = [
        "11.222.333/0001-81",  # Válido
        "00.000.000/0000-00",  # Inválido
        "123",                 # Formato inválido
    ]
    
    for cnpj in cnpjs_teste:
        is_valid = client._validate_cnpj(cnpj)
        status = "✅ Válido" if is_valid else "❌ Inválido"
        print(f"   {cnpj}: {status}")
    
    # Teste 2: Consulta de dados (mock)
    print("\n2. Teste de Consulta de Dados:")
    try:
        cnpj_data = await client.get_cnpj_data("11.222.333/0001-81")
        print(f"   ✅ CNPJ: {cnpj_data.cnpj}")
        print(f"   ✅ Razão Social: {cnpj_data.razao_social}")
        print(f"   ✅ Situação: {cnpj_data.situacao_cadastral}")
        print(f"   ✅ API Source: {cnpj_data.api_source}")
    except CNPJAPIError as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 3: Geração de cartão
    print("\n3. Teste de Geração de Cartão:")
    try:
        card = await client.generate_cnpj_card("11.222.333/0001-81")
        print(f"   ✅ Cartão gerado para: {card['cnpj']}")
        print(f"   ✅ Razão Social: {card['razao_social']}")
        print(f"   ✅ Gerado em: {card['generated_at']}")
    except CNPJAPIError as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 4: Serviço CNPJ
    print("\n4. Teste do Serviço CNPJ:")
    service = CNPJService()
    
    try:
        # Validação para triagem
        validation = await service.validate_cnpj_for_triagem("11.222.333/0001-81")
        print(f"   ✅ Validação: {validation['valid']}")
        print(f"   ✅ CNPJ: {validation['cnpj']}")
        print(f"   ✅ Razão Social: {validation['razao_social']}")
        
        # Geração e armazenamento de cartão
        card_result = await service.gerar_e_armazenar_cartao_cnpj("11.222.333/0001-81")
        print(f"   ✅ Cartão armazenado: {card_result['cnpj']}")
        print(f"   ✅ Arquivo: {card_result.get('file_path', 'N/A')}")
        
    except CNPJServiceError as e:
        print(f"   ❌ Erro no serviço: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Teste Final Concluído!")


if __name__ == "__main__":
    asyncio.run(test_cnpj_integration())