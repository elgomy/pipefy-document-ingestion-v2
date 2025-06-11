"""
Serviço para gerenciamento de dados de CNPJ.

Este módulo fornece funcionalidades de alto nível para:
- Consulta de dados de CNPJ com cache
- Geração e armazenamento de cartões CNPJ
- Validação de CNPJ para triagem
- Gerenciamento de cache e estatísticas
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from src.integrations.cnpj_client import cnpj_client, CNPJData, CNPJAPIError
from src.services.database_service import database_service

# Configurar logging
logger = logging.getLogger(__name__)


class CNPJServiceError(Exception):
    """Exceção personalizada para erros do serviço CNPJ."""
    pass


class CNPJService:
    """Serviço para gerenciamento de dados de CNPJ."""
    
    def __init__(self, cache_dir: Optional[Path] = None, cards_dir: Optional[Path] = None):
        """
        Inicializa o serviço CNPJ.
        
        Args:
            cache_dir: Diretório para cache de dados CNPJ
            cards_dir: Diretório para cartões CNPJ gerados
        """
        self.cache_dir = cache_dir or Path("data/cnpj_cache")
        self.cards_dir = cards_dir or Path("data/cnpj_cards")
        self.cache_max_age_hours = 24  # Cache válido por 24 horas
        self.cnpj_client = cnpj_client
        self.database_service = database_service
        
        # Criar diretórios se não existirem
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cards_dir.mkdir(parents=True, exist_ok=True)
    
    async def gerar_e_armazenar_cartao_cnpj(self, cnpj: str, case_id: Optional[str] = None, save_to_database: bool = True) -> Dict[str, Any]:
        """
        Gera e armazena cartão CNPJ, incluindo upload para Supabase Storage.
        
        Args:
            cnpj: CNPJ para gerar cartão
            case_id: ID do caso associado (opcional)
            save_to_database: Se deve salvar na base de dados
            
        Returns:
            Dados do cartão gerado
            
        Raises:
            CNPJServiceError: Se não conseguir gerar cartão
        """
        try:
            logger.info(f"Gerando cartão CNPJ para {cnpj}")
            
            # 1. Baixar PDF do certificado CNPJ da API CNPJá
            cnpj_clean = ''.join(filter(str.isdigit, cnpj))
            temp_pdf_path = self.cards_dir / f"temp_cartao_cnpj_{cnpj_clean}.pdf"
            
            pdf_result = await self.cnpj_client.download_cnpj_certificate_pdf(
                cnpj=cnpj,
                output_path=temp_pdf_path
            )
            
            if not pdf_result["success"]:
                raise CNPJServiceError(f"Falha ao baixar certificado CNPJ: {pdf_result.get('error', 'Erro desconhecido')}")
            
            # 2. Obter dados básicos do CNPJ
            cnpj_data = await self.cnpj_client.get_cnpj_data(cnpj)
            
            # 3. Preparar dados do cartão
            card_data = {
                "cnpj": cnpj_data.cnpj,
                "razao_social": cnpj_data.razao_social,
                "nome_fantasia": cnpj_data.nome_fantasia,
                "situacao_cadastral": cnpj_data.situacao_cadastral,
                "endereco_completo": cnpj_data.endereco_completo,
                "uf": cnpj_data.uf,
                "municipio": cnpj_data.municipio,
                "telefone": cnpj_data.telefone,
                "api_source": pdf_result["api_source"],
                "generated_at": datetime.now().isoformat(),
                "consulted_at": cnpj_data.consulted_at.isoformat(),
                "file_size_bytes": pdf_result["file_size_bytes"]
            }
            
            # 4. Salvar JSON local (cache)
            card_file = self.cards_dir / f"cartao_cnpj_{cnpj_clean}.json"
            with open(card_file, 'w', encoding='utf-8') as f:
                json.dump(card_data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Cartão CNPJ JSON salvo em: {card_file}")
            
            # 5. Se temos case_id e save_to_database, subir para Supabase
            if case_id and save_to_database and pdf_result.get("file_path"):
                try:
                    # Ler o PDF baixado
                    with open(pdf_result["file_path"], 'rb') as f:
                        pdf_content = f.read()
                    
                    # Nome do arquivo para Supabase
                    pdf_filename = f"cartao_cnpj_{cnpj_clean}.pdf"
                    
                    # Subir para Supabase Storage e registrar na tabela documents
                    supabase_result = await self.database_service.upload_and_register_document(
                        file_content=pdf_content,
                        file_name=pdf_filename,
                        case_id=case_id,
                        document_tag="cartao_cnpj",
                        content_type="application/pdf",
                        metadata={
                            "cnpj": cnpj_data.cnpj,
                            "razao_social": cnpj_data.razao_social,
                            "api_source": pdf_result["api_source"],
                            "generated_by": "cnpj_service",
                            "original_file_path": str(card_file)
                        }
                    )
                    
                    # Adicionar informações do Supabase ao resultado
                    card_data.update({
                        "supabase_document_id": supabase_result["document_id"],
                        "supabase_public_url": supabase_result["public_url"],
                        "supabase_storage_path": supabase_result["storage_path"],
                        "saved_to_database": True
                    })
                    
                    logger.info(f"Cartão CNPJ subido para Supabase: {supabase_result['public_url']}")
                    
                    # Limpar arquivo temporal
                    if temp_pdf_path.exists():
                        temp_pdf_path.unlink()
                        
                except Exception as e:
                    logger.error(f"Erro ao subir cartão CNPJ para Supabase: {e}")
                    card_data["saved_to_database"] = False
                    card_data["supabase_error"] = str(e)
            else:
                card_data["saved_to_database"] = False
                card_data["supabase_reason"] = "case_id não fornecido ou save_to_database=False"
            
            # Adicionar informações do arquivo local
            card_data["local_file_path"] = str(card_file)
            card_data["pdf_file_path"] = pdf_result.get("file_path")
            
            return card_data
            
        except CNPJAPIError as e:
            raise CNPJServiceError(f"Erro ao gerar cartão CNPJ para {cnpj}: {e.message}")
        except Exception as e:
            raise CNPJServiceError(f"Erro inesperado ao gerar cartão CNPJ para {cnpj}: {e}")
    
    async def validate_cnpj_for_triagem(self, cnpj: str) -> Dict[str, Any]:
        """
        Valida CNPJ para processo de triagem.
        
        Args:
            cnpj: CNPJ para validar
            
        Returns:
            Resultado da validação com dados básicos
        """
        try:
            cnpj_data = await self.cnpj_client.get_cnpj_data(cnpj)
            
            return {
                "valid": True,
                "cnpj": cnpj_data.cnpj,
                "razao_social": cnpj_data.razao_social,
                "nome_fantasia": cnpj_data.nome_fantasia,
                "situacao_cadastral": cnpj_data.situacao_cadastral,
                "uf": cnpj_data.uf,
                "municipio": cnpj_data.municipio,
                "api_source": cnpj_data.api_source,
                "consulted_at": cnpj_data.consulted_at.isoformat()
            }
            
        except CNPJAPIError as e:
            return {
                "valid": False,
                "cnpj": cnpj,
                "error": str(e)
            }
        except Exception as e:
            return {
                "valid": False,
                "cnpj": cnpj,
                "error": f"Erro inesperado: {e}"
            }


# Instância global do serviço
cnpj_service = CNPJService()