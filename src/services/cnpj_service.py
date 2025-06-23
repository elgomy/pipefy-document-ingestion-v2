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