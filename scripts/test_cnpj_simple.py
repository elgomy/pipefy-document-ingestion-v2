#!/usr/bin/env python3
"""
Script de teste simples para validação de CNPJ.
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_cnpj_validation():
    """Teste simples de validação de CNPJ."""
    print("🔧 Teste Simples de Validação CNPJ")
    
    # Implementação básica de validação de CNPJ
    def validate_cnpj(cnpj):
        """Valida CNPJ usando algoritmo de dígito verificador."""
        # Remover caracteres não numéricos
        cnpj = ''.join(filter(str.isdigit, cnpj))
        
        # Verificar se tem 14 dígitos
        if len(cnpj) != 14:
            return False
        
        # Verificar se todos os dígitos são iguais
        if cnpj == cnpj[0] * 14:
            return False
        
        # Calcular primeiro dígito verificador
        sequence = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum_result = sum(int(cnpj[i]) * sequence[i] for i in range(12))
        remainder = sum_result % 11
        first_digit = 0 if remainder < 2 else 11 - remainder
        
        # Verificar primeiro dígito
        if int(cnpj[12]) != first_digit:
            return False
        
        # Calcular segundo dígito verificador
        sequence = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum_result = sum(int(cnpj[i]) * sequence[i] for i in range(13))
        remainder = sum_result % 11
        second_digit = 0 if remainder < 2 else 11 - remainder
        
        # Verificar segundo dígito
        return int(cnpj[13]) == second_digit
    
    def format_cnpj(cnpj):
        """Formata CNPJ com pontos, barra e hífen."""
        cnpj = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return cnpj
    
    # Casos de teste
    test_cases = [
        ("11.222.333/0001-81", "CNPJ formatado"),
        ("11222333000181", "CNPJ sem formatação"),
        ("00.000.000/0000-00", "CNPJ inválido"),
        ("123", "Formato inválido"),
        ("", "CNPJ vazio"),
        ("11111111111111", "CNPJ com dígitos iguais"),
        ("11.444.777/0001-61", "Outro CNPJ teste")
    ]
    
    print("\n" + "="*60)
    print(" RESULTADOS DOS TESTES")
    print("="*60)
    
    for cnpj, description in test_cases:
        try:
            is_valid = validate_cnpj(cnpj)
            status = "✅ Válido" if is_valid else "❌ Inválido"
            print(f"\n{description}: {cnpj}")
            print(f"Status: {status}")
            
            if is_valid:
                formatted = format_cnpj(cnpj)
                print(f"Formatado: {formatted}")
                
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    print("\n" + "="*60)
    print(" ✅ TESTE CONCLUÍDO")
    print("="*60)

if __name__ == "__main__":
    test_cnpj_validation() 