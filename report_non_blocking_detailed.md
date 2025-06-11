# ⚠️ Relatório de Triagem Documental
**Empresa:** Empresa Exemplo S.A.
**CNPJ:** 12.345.678/0001-99
**Caso ID:** CASE-2024-001
**Data/Hora:** 10/06/2025 às 16:58:06
**Analista:** Maria Silva


## 📋 Resumo Executivo

**Classificação Final:** ⚠️ **Pendencia_NaoBloqueante**
**Nível de Confiança:** 75.0%

**Estatísticas dos Documentos:**
- Total analisados: 6
- Presentes: 4
- Válidos: 3
- Taxa de conformidade: 50.0%

⚠️ **Resultado:** Documentação com **PENDÊNCIAS NÃO-BLOQUEANTES**.
Identificadas 3 pendências menores que podem ser resolvidas automaticamente.

## 🎯 Detalhes da Classificação

**Pendências Identificadas (Não-Bloqueantes):**
- ⚠️ Cartão CNPJ ausente
- ⚠️ Comprovante de residência vencido (95 dias)
- ⚠️ Procuração opcional ausente

**Nível de Confiança: 75.0%**
🟡 **Médio:** Classificação confiável com algumas incertezas menores.


## 📄 Análise Detalhada dos Documentos

### ✅ Documentos Válidos

**Último Contrato Social/Estatuto consolidado**
- 📅 Idade: 45 dias
- ✅ Status: Presente e válido

**RG e CPF dos sócios (≥10%) e signatários**
- ✅ Status: Presente e válido

**Balanço Patrimonial**
- 📅 Idade: 180 dias
- ✅ Status: Presente e válido

### ❌ Documentos com Problemas

**Comprovante de residência dos sócios**
- 📅 Idade: 95 dias
- ❌ Status: Presente mas inválido
- ⚠️ Documento vencido mas não-bloqueante

### 📋 Documentos Ausentes

**Cartão CNPJ emitido dentro dos 90 dias**
- 📋 Status: Ausente
- 🤖 Pode ser gerado automaticamente
- ⚠️ Documento ausente mas auto-gerável

**Procuração (se aplicável)**
- 📋 Status: Ausente
- ⚠️ Documento opcional ausente



## 🔍 Pendências e Recomendações

### ⚠️ Pendências Não-Bloqueantes

**Estas pendências podem ser resolvidas posteriormente ou automaticamente:**

1. Cartão CNPJ ausente
2. Comprovante de residência vencido (95 dias)
3. Procuração opcional ausente

**Ação Recomendada:** Resolver quando possível ou aguardar resolução automática.



## 🤖 Ações Automáticas Disponíveis

**O sistema pode executar as seguintes ações automaticamente:**

1. Gerar automaticamente: Cartão CNPJ via CNPJá API
2. Solicitar novo comprovante de residência via WhatsApp

**Status:** Ações serão executadas automaticamente pelo sistema.
**Tempo Estimado:** 2-5 minutos por ação.



## 🔧 Detalhes Técnicos

### Configuração de Documentos

| Documento | Obrigatório | Prazo Máximo | Auto-Gerável |
|-----------|-------------|--------------|---------------|
| Cartão CNPJ emitido dentro dos 90 dias | ✅ | 90 dias | ✅ |
| Último Contrato Social/Estatuto consolidado | ✅ | 1095 dias | ❌ |
| RG e CPF dos sócios (≥10%) e signatários | ✅ | N/A | ❌ |
| Comprovante de residência dos sócios | ✅ | 90 dias | ❌ |
| Balanço Patrimonial | ❌ | N/A | ❌ |
| Procuração (se aplicável) | ❌ | N/A | ❌ |

### Algoritmo de Classificação

**Critérios de Aprovação:**
- Todos os documentos obrigatórios presentes e válidos
- Pelo menos um documento financeiro válido
- Nenhuma pendência bloqueante identificada

**Critérios de Pendência Bloqueante:**
- Documentos obrigatórios ausentes (não auto-geráveis)
- Documentos inválidos com blocking_if_invalid=True
- Nenhum documento financeiro válido

**Critérios de Pendência Não-Bloqueante:**
- Documentos auto-geráveis ausentes ou inválidos
- Documentos vencidos mas não-bloqueantes
- Problemas menores de formatação



---

**Relatório gerado automaticamente pelo Sistema de Triagem Documental v2.0**
**Timestamp:** 2025-06-10T16:58:06.341676
**Fonte de Conhecimento:** FAQ.md (Versão 2.0 - com Automação IA)
**Algoritmo:** Classificação baseada em regras de negócio FIDC
