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
from uuid import UUID

from src.integrations.cnpj_client import CNPJClient, CNPJData, CNPJAPIError
from src.services.database_service import database_service
from src.utils.error_handler import with_error_handling

# Configurar logging
logger = logging.getLogger(__name__)


class CNPJServiceError(Exception):
    """Exceção personalizada para erros do serviço CNPJ."""
    pass


class CNPJService:
    """Serviço para gerenciamento de dados de CNPJ."""
    
    def __init__(self, supabase_client, cnpj_client: Optional[CNPJClient] = None):
        """
        Inicializa o serviço CNPJ.
        
        Args:
            supabase_client: Cliente de Supabase
            cnpj_client: Cliente CNPJ (opcional)
        """
        self.client = supabase_client
        self.cnpj_client = cnpj_client or CNPJClient()
        self.storage_bucket = "cnpj_cards"
        self.cache_duration = timedelta(hours=24)
        
        # Configurar directorios
        self.base_dir = Path("data")
        self.cache_dir = self.base_dir / "cache"
        self.cards_dir = self.base_dir / "cards"
        
        # Crear directorios si no existen
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cards_dir.mkdir(parents=True, exist_ok=True)
    
    async def _get_cached_data(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos de CNPJ cacheados.
        
        Args:
            cnpj: CNPJ para buscar
            
        Returns:
            Datos cacheados o None si no existe o expiró
        """
        try:
            response = await self.client.table("cnpj_data_cache").select("*").eq("cnpj", cnpj).execute()
            
            if response.data:
                cache_data = response.data[0]
                cache_time = datetime.fromisoformat(cache_data["cached_at"])
                
                # Verificar si el caché expiró
                if datetime.now() - cache_time < self.cache_duration:
                    # Excluir campo cached_at antes de retornar
                    cache_data.pop("cached_at", None)
                    return cache_data
                
                # Si expiró, eliminar el caché
                await self.client.table("cnpj_data_cache").delete().eq("cnpj", cnpj).execute()
            
            return None
            
        except Exception as e:
            logger.warning(f"Error al obtener caché de CNPJ {cnpj}: {e}")
            return None
    
    async def _cache_data(self, cnpj_data: CNPJData) -> None:
        """
        Guarda datos de CNPJ en caché.
        
        Args:
            cnpj_data: Datos de CNPJ para cachear
        """
        try:
            # Convertir a diccionario y agregar timestamp
            cache_data = {
                "cnpj": cnpj_data.cnpj,
                "razao_social": cnpj_data.razao_social,
                "nome_fantasia": cnpj_data.nome_fantasia,
                "situacao_cadastral": cnpj_data.situacao_cadastral,
                "data_situacao_cadastral": cnpj_data.data_situacao_cadastral,
                "endereco_completo": cnpj_data.endereco_completo,
                "telefone": cnpj_data.telefone,
                "email": cnpj_data.email,
                "api_source": cnpj_data.api_source,
                "cached_at": datetime.now().isoformat()
            }
            
            # Guardar en caché
            await self.client.table("cnpj_data_cache").upsert(cache_data).execute()
            
            # Guardar también en archivo local
            cache_file = self.cache_dir / f"{cnpj_data.cnpj.replace('.', '').replace('/', '').replace('-', '')}.json"
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            
        except Exception as e:
            logger.warning(f"Error al cachear datos de CNPJ {cnpj_data.cnpj}: {e}")
    
    @with_error_handling("cnpj_service", context={"operation": "get_cnpj_data"})
    async def get_cnpj_data(self, cnpj: str, use_cache: bool = True) -> CNPJData:
        """
        Obtiene datos de CNPJ con soporte de caché.
        
        Args:
            cnpj: CNPJ para consultar
            use_cache: Si debe usar caché
            
        Returns:
            Datos del CNPJ
            
        Raises:
            CNPJAPIError: Si hay error al obtener los datos
        """
        # Verificar caché
        if use_cache:
            cached_data = await self._get_cached_data(cnpj)
            if cached_data:
                return CNPJData(**cached_data)
        
        # Obtener datos frescos
        cnpj_data = await self.cnpj_client.get_cnpj_data(cnpj)
        
        # Cachear datos
        if use_cache:
            await self._cache_data(cnpj_data)
        
        return cnpj_data
    
    @with_error_handling("cnpj_service", context={"operation": "generate_cnpj_card"})
    async def generate_cnpj_card(
        self,
        cnpj: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Genera cartón CNPJ y lo almacena en Supabase Storage.
        
        Args:
            cnpj: CNPJ para generar cartón
            force_refresh: Si debe forzar regeneración aunque exista
            
        Returns:
            Información del cartón generado
            
        Raises:
            CNPJAPIError: Si hay error al generar el cartón
        """
        # Verificar si ya existe
        if not force_refresh:
            try:
                existing_card = await self.get_cnpj_card(cnpj)
                if existing_card:
                    return existing_card
            except Exception:
                pass
        
        # Generar cartón
        card_file = self.cards_dir / f"{cnpj.replace('.', '').replace('/', '').replace('-', '')}.pdf"
            
        try:
            # Obtener datos del CNPJ
            cnpj_data = await self.get_cnpj_data(cnpj)
            
            # Descargar PDF y guardarlo
            pdf_info = await self.cnpj_client.download_cnpj_certificate_pdf(cnpj)
            
            # Guardar el contenido del PDF en el archivo
            with open(card_file, 'wb') as f:
                f.write(pdf_info["content"])
            
            # Subir a Supabase Storage
            with open(card_file, 'rb') as f:
                upload_result = await self.client.storage.from_(self.storage_bucket).upload(
                    path=f"cards/{card_file.name}",
                    file=f,
                    file_options={"content-type": "application/pdf"}
                )
            
            # Obtener URL pública
            public_url = self.client.storage.from_(self.storage_bucket).get_public_url(f"cards/{card_file.name}")
            
            # Registrar en base de datos
            card_data = {
                "cnpj": cnpj,
                "razao_social": cnpj_data.razao_social,
                "public_url": public_url,
                "file_size_bytes": pdf_info["file_size_bytes"],
                "generated_at": datetime.now().isoformat(),
                "api_source": cnpj_data.api_source
            }
            
            await self.client.table("cnpj_cards").upsert(card_data).execute()
            
            # Preparar respuesta
            response = {
                "success": True,
                "message": "Cartón CNPJ generado exitosamente",
                **card_data
            }
            
            return response
            
        except Exception as e:
            raise CNPJServiceError(f"Error al generar cartón CNPJ: {str(e)}")
        finally:
            # Limpiar archivo temporal
            if card_file.exists():
                card_file.unlink()
    
    @with_error_handling("cnpj_service", context={"operation": "get_cnpj_card"})
    async def get_cnpj_card(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de un cartón CNPJ existente.
        
        Args:
            cnpj: CNPJ para buscar
            
        Returns:
            Información del cartón o None si no existe
        """
        try:
            response = await self.client.table("cnpj_cards").select("*").eq("cnpj", cnpj).execute()
            
            if response.data:
                card_data = response.data[0]
                return {
                    "success": True,
                    "message": "Cartón CNPJ encontrado",
                    **card_data
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error al obtener cartón CNPJ {cnpj}: {e}")
            return None
    
    @with_error_handling("cnpj_service", context={"operation": "list_cnpj_cards"})
    async def list_cnpj_cards(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "generated_at",
        order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Lista los cartones CNPJ generados.
        
        Args:
            limit: Límite de registros
            offset: Desplazamiento para paginación
            order_by: Campo para ordenar
            order: Dirección del orden (asc/desc)
            
        Returns:
            Lista de cartones y metadata
        """
        try:
            # Obtener conteo total
            count_response = await self.client.table("cnpj_cards").select("count").execute()
            total = count_response.count
            
            # Obtener registros
            query = self.client.table("cnpj_cards").select("*")
            
            if order == "desc":
                query = query.order(order_by, desc=True)
            else:
                query = query.order(order_by)
                
            query = query.range(offset, offset + limit - 1)
            
            response = await query.execute()
            
            return {
                "success": True,
                "message": "Cartones CNPJ listados exitosamente",
                "data": response.data,
                "metadata": {
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
            }
            
        except Exception as e:
            raise CNPJServiceError(f"Error al listar cartones CNPJ: {str(e)}")
    
    @with_error_handling("cnpj_service", context={"operation": "gerar_e_armazenar_cartao_cnpj"})
    async def gerar_e_armazenar_cartao_cnpj(
        self,
        cnpj: str,
        case_id: str,
        save_to_database: bool = True
    ) -> Dict[str, Any]:
        """
        Gera e armazena cartão CNPJ no bucket 'documents' de Supabase Storage para um caso específico.
        Esta função é compatível com o formato esperado pelo triagem_service.
        
        Args:
            cnpj: CNPJ para gerar o cartão
            case_id: ID do caso associado
            save_to_database: Se deve salvar na base de dados (default: True)
            
        Returns:
            Resultado da geração do cartão com informações detalhadas
            
        Raises:
            CNPJServiceError: Se há erro ao gerar o cartão
        """
        try:
            logger.info(f"Gerando cartão CNPJ {cnpj} para caso {case_id}")
            
            # Limpar CNPJ
            cnpj_clean = cnpj.replace('.', '').replace('/', '').replace('-', '')
            
            # Verificar se CNPJ é válido
            if len(cnpj_clean) != 14 or not cnpj_clean.isdigit():
                raise CNPJServiceError(f"CNPJ inválido: {cnpj}")
            
            # Definir paths
            card_file = self.cards_dir / f"cartao_cnpj_{cnpj_clean}_{case_id}.pdf"
            storage_path = f"{case_id}/cartao_cnpj_gerado.pdf"
            
            try:
                # Obtener dados do CNPJ
                cnpj_data = await self.get_cnpj_data(cnpj)
                
                # Descargar PDF do cartão CNPJ
                pdf_info = await self.cnpj_client.download_cnpj_certificate_pdf(cnpj)
                
                # Guardar o conteúdo do PDF em arquivo temporário
                with open(card_file, 'wb') as f:
                    f.write(pdf_info["content"])
                
                # Subir para Supabase Storage no bucket 'documents'
                with open(card_file, 'rb') as f:
                    upload_result = await asyncio.to_thread(
                        self.client.storage.from_("documents").upload,
                        storage_path,
                        f,
                        {"content-type": "application/pdf"}
                    )
                
                # Obter URL pública
                public_url = await asyncio.to_thread(
                    self.client.storage.from_("documents").get_public_url,
                    storage_path
                )
                
                # Registrar na base de dados se solicitado
                supabase_document_id = None
                if save_to_database:
                    document_data = {
                        "name": f"Cartão CNPJ - {cnpj_data.razao_social}",
                        "case_id": case_id,
                        "document_tag": "cartao_cnpj",
                        "document_type": "cartao_cnpj",
                        "file_url": public_url,
                        "status": "uploaded",
                        "metadata": {
                            "cnpj": cnpj,
                            "razao_social": cnpj_data.razao_social,
                            "file_size_bytes": pdf_info.get("file_size_bytes", len(pdf_info["content"])),
                            "api_source": cnpj_data.api_source,
                            "generated_by": "cnpj_service",
                            "uploaded_at": datetime.now().isoformat()
                        }
                    }
                    
                    try:
                        db_result = await self.client.table("documents").insert(document_data).execute()
                        if db_result.data:
                            supabase_document_id = db_result.data[0].get("id")
                            logger.info(f"Documento registrado na tabela 'documents' com ID: {supabase_document_id}")
                    except Exception as db_error:
                        logger.warning(f"Erro ao registrar documento na tabela 'documents': {db_error}")
                            # Não falhar o processo se houver erro no registro da tabela
                
                # Preparar resposta no formato esperado
                result = {
                    "success": True,
                    "cnpj": cnpj,
                    "razao_social": cnpj_data.razao_social,
                    "file_path": storage_path,
                    "pdf_file_path": str(card_file),
                    "local_file_path": str(card_file),
                    "supabase_public_url": public_url,
                    "supabase_document_id": supabase_document_id,
                    "generated_at": datetime.now().isoformat(),
                    "api_source": cnpj_data.api_source,
                    "saved_to_database": save_to_database and supabase_document_id is not None,
                    "file_size_bytes": pdf_info.get("file_size_bytes", len(pdf_info["content"]))
                }
                
                logger.info(f"Cartão CNPJ gerado com sucesso para caso {case_id}: {storage_path}")
                return result
                
            except Exception as e:
                logger.error(f"Erro ao gerar cartão CNPJ para caso {case_id}: {str(e)}")
                raise CNPJServiceError(f"Erro ao gerar cartão CNPJ: {str(e)}")
            finally:
                # Limpar arquivo temporário
                if card_file.exists():
                    try:
                        card_file.unlink()
                    except Exception as e:
                        logger.warning(f"Erro ao remover arquivo temporário {card_file}: {e}")
                        
        except CNPJServiceError:
            # Re-raise CNPJServiceError as is
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao gerar cartão CNPJ para caso {case_id}: {str(e)}")
            raise CNPJServiceError(f"Erro inesperado: {str(e)}")
    
    def list_cached_cnpjs(self) -> List[Dict[str, Any]]:
        """
        Lista CNPJs em cache. Função de conveniência para estatísticas.
        
        Returns:
            Lista de dados de CNPJ em cache
        """
        try:
            # Listar arquivos de cache locais
            cache_files = list(self.cache_dir.glob("*.json"))
            cached_data = []
            
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        # Verificar se ainda é válido
                        cached_at = datetime.fromisoformat(data.get("cached_at", "1970-01-01"))
                        is_valid = datetime.now() - cached_at < self.cache_duration
                        data["is_valid"] = is_valid
                        cached_data.append(data)
                except Exception as e:
                    logger.warning(f"Erro ao ler arquivo de cache {cache_file}: {e}")
            
            # Ordenar por data de cache (mais recente primeiro)
            cached_data.sort(key=lambda x: x.get("cached_at", ""), reverse=True)
            return cached_data
            
        except Exception as e:
            logger.error(f"Erro ao listar CNPJs em cache: {e}")
            return []
    
    def list_generated_cards(self) -> List[Dict[str, Any]]:
        """
        Lista cartões gerados localmente. Função de conveniência para estatísticas.
        
        Returns:
            Lista de cartões gerados
        """
        try:
            # Esta função retorna uma lista simplificada
            # Os dados reais estão no Supabase Storage
            card_files = list(self.cards_dir.glob("cartao_cnpj_*.pdf"))
            cards_info = []
            
            for card_file in card_files[:10]:  # Limitar a 10 mais recentes
                try:
                    stat = card_file.stat()
                    cards_info.append({
                        "filename": card_file.name,
                        "generated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "file_size_bytes": stat.st_size
                    })
                except Exception as e:
                    logger.warning(f"Erro ao obter info do arquivo {card_file}: {e}")
            
            # Ordenar por data de modificação (mais recente primeiro)
            cards_info.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
            return cards_info
            
        except Exception as e:
            logger.error(f"Erro ao listar cartões gerados: {e}")
            return []
    
    async def validate_cnpj_for_triagem(self, cnpj: str) -> Dict[str, Any]:
        """
        Valida CNPJ para processo de triagem.
        
        Args:
            cnpj: CNPJ para validar
            
        Returns:
            Resultado da validação
        """
        try:
            # Limpar CNPJ
            cnpj_clean = cnpj.replace('.', '').replace('/', '').replace('-', '')
            
            # Validação básica de formato
            if len(cnpj_clean) != 14 or not cnpj_clean.isdigit():
                return {
                    "valid": False,
                    "error": f"Formato de CNPJ inválido: {cnpj}",
                    "cnpj": cnpj
                }
            
            # Tentar obter dados do CNPJ
            try:
                cnpj_data = await self.get_cnpj_data(cnpj)
                
                # Verificar situação cadastral
                situacao_ativa = cnpj_data.situacao_cadastral and cnpj_data.situacao_cadastral.upper() == "ATIVA"
                
                return {
                    "valid": True,
                    "cnpj": cnpj,
                    "razao_social": cnpj_data.razao_social,
                    "situacao_cadastral": cnpj_data.situacao_cadastral,
                    "situacao_ativa": situacao_ativa,
                    "api_source": cnpj_data.api_source,
                    "warning": None if situacao_ativa else "CNPJ com situação cadastral não ativa"
                }
                
            except CNPJAPIError as e:
                return {
                    "valid": False,
                    "error": f"Erro na API CNPJ: {str(e)}",
                    "cnpj": cnpj
                }
                
        except Exception as e:
            logger.error(f"Erro inesperado na validação de CNPJ {cnpj}: {str(e)}")
            return {
                "valid": False,
                "error": f"Erro inesperado: {str(e)}",
                "cnpj": cnpj
            }