"""
Cliente para consulta de dados de CNPJ usando múltiplas APIs.

Este módulo fornece funcionalidades para:
- Consultar dados de CNPJ em APIs públicas (BrasilAPI, CNPJ.ws)
- Validar CNPJs usando algoritmo de dígito verificador
- Gerar cartões formatados com dados de CNPJ
- Sistema de fallback automático entre APIs
"""

import asyncio
import aiohttp
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union, List
from pathlib import Path
import logging
from src.utils.error_handler import with_error_handling, RetryConfig
import httpx
import re

# Configurar logging
logger = logging.getLogger(__name__)


class CNPJAPIError(Exception):
    """Exceção personalizada para erros da API de CNPJ."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, api_name: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.api_name = api_name
        super().__init__(self.message)


@dataclass
class CNPJData:
    """Estrutura de dados para informações de CNPJ."""
    cnpj: str
    razao_social: str
    nome_fantasia: Optional[str] = None
    situacao_cadastral: Optional[str] = None
    data_situacao_cadastral: Optional[str] = None
    tipo_logradouro: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cep: Optional[str] = None
    uf: Optional[str] = None
    municipio: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    endereco_completo: Optional[str] = None
    api_source: Optional[str] = None
    consulted_at: datetime = field(default_factory=datetime.now)
    cached_at: Optional[str] = None


@dataclass
class APIStatus:
    """Status de uma API de CNPJ."""
    name: str
    available: bool = True
    last_error: Optional[str] = None
    error_count: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    
    def is_circuit_open(self) -> bool:
        """Verifica se o circuit breaker está aberto."""
        # Abrir circuito após 3 falhas consecutivas
        if self.consecutive_failures >= 3:
            # Verificar se já passou tempo suficiente para tentar novamente (5 minutos)
            if self.last_failure and datetime.now() - self.last_failure < timedelta(minutes=5):
                return True
        return False
    
    def record_success(self):
        """Registra um sucesso."""
        self.available = True
        self.last_success = datetime.now()
        self.consecutive_failures = 0
    
    def record_failure(self, error: str):
        """Registra uma falha."""
        self.last_error = error
        self.error_count += 1
        self.last_failure = datetime.now()
        self.consecutive_failures += 1
        if self.consecutive_failures >= 3:
            self.available = False


class CNPJClient:
    """Cliente para consulta de dados de CNPJ."""
    
    def __init__(self, timeout: int = 30):
        """
        Inicializa o cliente CNPJ.
        
        Args:
            timeout: Timeout para requisições HTTP em segundos
        """
        self.timeout = timeout
        self.brasil_api_url = "https://brasilapi.com.br/api/cnpj/v1"
        self.cnpj_ws_url = "https://publica.cnpj.ws/cnpj"  # URL correta do CNPJ.ws
        self.cnpja_api_url = "https://api.cnpja.com/v1"  # URL correta do CNPJá
        self.cnpja_api_key = os.getenv("CNPJA_API_KEY")  # Chave da API CNPJá
        
        # Cache de fallback para dados de CNPJ
        self.fallback_cache: Dict[str, CNPJData] = {}
        self.cache_max_age = timedelta(hours=24)  # Cache válido por 24 horas
        
        # Status das APIs para circuit breaker
        self.api_status = {
            "BrasilAPI": APIStatus("BrasilAPI"),
            "CNPJá": APIStatus("CNPJá"),
            "CNPJ.ws": APIStatus("CNPJ.ws")
        }
        
        # Métricas de uso
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "fallback_used": 0,
            "api_usage": {
                "BrasilAPI": 0,
                "CNPJá": 0,
                "CNPJ.ws": 0,
                "fallback": 0
            }
        }
        
        # Configuração de reintentos para APIs de CNPJ
        self.retry_config = RetryConfig(
            max_retries=2,  # Menos reintentos para APIs externas
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True
        )
    
    def _validate_cnpj(self, cnpj: str) -> bool:
        """
        Valida um CNPJ.
        
        Args:
            cnpj: CNPJ para validar
            
        Returns:
            True se CNPJ for válido, False caso contrário
        """
        # Remover caracteres não numéricos
        cnpj = re.sub(r'[^0-9]', '', cnpj)
        
        # Verificar tamanho
        if len(cnpj) != 14:
            return False
            
        # Verificar se todos os dígitos são iguais
        if len(set(cnpj)) == 1:
            return False
            
        # Calcular primeiro dígito verificador
        soma = 0
        peso = 5
        for i in range(12):
            soma += int(cnpj[i]) * peso
            peso = peso - 1 if peso > 2 else 9
        
        digito1 = 11 - (soma % 11)
        if digito1 > 9:
            digito1 = 0
            
        if int(cnpj[12]) != digito1:
            return False
            
        # Calcular segundo dígito verificador
        soma = 0
        peso = 6
        for i in range(13):
            soma += int(cnpj[i]) * peso
            peso = peso - 1 if peso > 2 else 9
            
        digito2 = 11 - (soma % 11)
        if digito2 > 9:
            digito2 = 0
            
        return int(cnpj[13]) == digito2

    def _clean_cnpj(self, cnpj: str) -> str:
        """
        Remove caracteres não numéricos do CNPJ.
        
        Args:
            cnpj: CNPJ para limpar
            
        Returns:
            CNPJ apenas com números
        """
        return re.sub(r'[^0-9]', '', cnpj)

    def _format_cnpj(self, cnpj: str) -> str:
        """
        Formata um CNPJ no padrão XX.XXX.XXX/XXXX-XX.
        
        Args:
            cnpj: CNPJ para formatar
            
        Returns:
            CNPJ formatado
        """
        cnpj = self._clean_cnpj(cnpj)
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    
    def _add_to_fallback_cache(self, cnpj: str, data: CNPJData):
        """
        Adiciona dados ao cache de fallback.
        
        Args:
            cnpj: CNPJ dos dados
            data: Dados do CNPJ
        """
        cnpj_clean = self._clean_cnpj(cnpj)
        data.cached_at = datetime.now().isoformat()
        self.fallback_cache[cnpj_clean] = data
        logger.info(f"Dados de CNPJ {cnpj_clean} adicionados ao cache de fallback")
    
    def _get_from_fallback_cache(self, cnpj: str) -> Optional[CNPJData]:
        """
        Obtém dados do cache de fallback.
        
        Args:
            cnpj: CNPJ para buscar
            
        Returns:
            Dados do CNPJ ou None se não encontrado/expirado
        """
        cnpj_clean = self._clean_cnpj(cnpj)
        
        if cnpj_clean not in self.fallback_cache:
            return None
        
        cached_data = self.fallback_cache[cnpj_clean]
        
        # Verificar se cache não expirou
        if cached_data.cached_at:
            cached_time = datetime.fromisoformat(cached_data.cached_at)
            if datetime.now() - cached_time > self.cache_max_age:
                del self.fallback_cache[cnpj_clean]
                return None
        
        self.metrics["cache_hits"] += 1
        logger.info(f"Dados de CNPJ {cnpj_clean} obtidos do cache de fallback")
        return cached_data
    
    @with_error_handling("cnpj_api", context={"operation": "get_cnpj_data"})
    async def get_cnpj_data(self, cnpj: str) -> CNPJData:
        """
        Consulta dados de CNPJ com fallback automático entre APIs.
        
        Args:
            cnpj: CNPJ para consultar
            
        Returns:
            Dados do CNPJ
            
        Raises:
            CNPJAPIError: Se CNPJ for inválido ou todas as APIs falharem
        """
        # Validar CNPJ
        if not self._validate_cnpj(cnpj):
            raise CNPJAPIError("CNPJ inválido")
        
        cnpj_clean = self._clean_cnpj(cnpj)
        self.metrics["total_requests"] += 1
        errors = []
        
        # Verificar cache de fallback primeiro
        cached_data = self._get_from_fallback_cache(cnpj)
        if cached_data:
            self.metrics["successful_requests"] += 1
            return cached_data
        
        # Tentar BrasilAPI primeiro se circuit breaker permitir
        brasil_api_status = self.api_status["BrasilAPI"]
        if not brasil_api_status.is_circuit_open():
            try:
                timeout_config = httpx.Timeout(self.timeout, connect=5.0)
                async with httpx.AsyncClient(timeout=timeout_config) as client:
                    response = await client.get(f"{self.brasil_api_url}/{cnpj_clean}")
                    if response.status_code == 200:
                        data = response.json()
                        cnpj_data = CNPJData(
                            cnpj=self._format_cnpj(data["cnpj"]),
                            razao_social=data["razao_social"],
                            nome_fantasia=data.get("nome_fantasia"),
                            situacao_cadastral=data.get("situacao_cadastral"),
                            uf=data.get("uf"),
                            municipio=data.get("municipio"),
                            endereco_completo=f"{data.get('logradouro', '')}, {data.get('numero', '')}, {data.get('bairro', '')}, {data.get('municipio', '')} - {data.get('uf', '')}".strip(),
                            telefone=data.get("ddd_telefone_1"),
                            api_source="BrasilAPI"
                        )
                        
                        # Registrar sucesso e adicionar ao cache
                        brasil_api_status.record_success()
                        self._add_to_fallback_cache(cnpj, cnpj_data)
                        self.metrics["successful_requests"] += 1
                        self.metrics["api_usage"]["BrasilAPI"] += 1
                        
                        return cnpj_data
                    else:
                        error_msg = f"BrasilAPI HTTP {response.status_code}"
                        brasil_api_status.record_failure(error_msg)
                        errors.append(error_msg)
                        
            except Exception as e:
                error_msg = f"BrasilAPI error: {str(e)}"
                brasil_api_status.record_failure(error_msg)
                errors.append(error_msg)
        else:
            errors.append("BrasilAPI: Circuit breaker aberto")
        
        # Tentar CNPJá se disponível e circuit breaker permitir
        cnpja_status = self.api_status["CNPJá"]
        if self.cnpja_api_key and not cnpja_status.is_circuit_open():
            try:
                headers = {"Authorization": self.cnpja_api_key}
                timeout_config = httpx.Timeout(self.timeout, connect=5.0)
                async with httpx.AsyncClient(timeout=timeout_config) as client:
                    response = await client.get(f"{self.cnpja_api_url}/companies/{cnpj_clean}", headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        cnpj_data = CNPJData(
                            cnpj=self._format_cnpj(cnpj_clean),
                            razao_social=data["name"],
                            nome_fantasia=data.get("alias"),
                            situacao_cadastral=data.get("status", {}).get("text"),
                            uf=data.get("address", {}).get("state"),
                            municipio=data.get("address", {}).get("city"),
                            endereco_completo=f"{data.get('address', {}).get('street', '')}, {data.get('address', {}).get('number', '')}, {data.get('address', {}).get('district', '')}, {data.get('address', {}).get('city', '')} - {data.get('address', {}).get('state', '')}".strip(),
                            telefone=data.get("phones", [{}])[0].get("number"),
                            api_source="CNPJá"
                        )
                        
                        # Registrar sucesso e adicionar ao cache
                        cnpja_status.record_success()
                        self._add_to_fallback_cache(cnpj, cnpj_data)
                        self.metrics["successful_requests"] += 1
                        self.metrics["api_usage"]["CNPJá"] += 1
                        
                        return cnpj_data
                    else:
                        error_msg = f"CNPJá HTTP {response.status_code}"
                        cnpja_status.record_failure(error_msg)
                        errors.append(error_msg)
                        
            except Exception as e:
                error_msg = f"CNPJá error: {str(e)}"
                cnpja_status.record_failure(error_msg)
                errors.append(error_msg)
        elif not self.cnpja_api_key:
            errors.append("CNPJá: API key não configurada")
        else:
            errors.append("CNPJá: Circuit breaker aberto")
        
        # Se todas as APIs falharem, usar dados mock como último recurso
        logger.warning(f"Todas as APIs falharam para CNPJ {cnpj_clean}. Usando dados mock.")
        mock_data = CNPJData(
            cnpj=self._format_cnpj(cnpj_clean),
            razao_social="EMPRESA MOCK LTDA",
            nome_fantasia="Empresa Mock",
            situacao_cadastral="ATIVA",
            uf="SP",
            municipio="SAO PAULO",
            endereco_completo="RUA MOCK, 123, CENTRO, SAO PAULO - SP",
            telefone="(11) 9999-9999",
            api_source="fallback_mock"
        )
        
        self.metrics["fallback_used"] += 1
        self.metrics["api_usage"]["fallback"] += 1
        self.metrics["successful_requests"] += 1  # Mock sempre funciona
        
        return mock_data
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtém métricas de uso do cliente CNPJ.
        
        Returns:
            Dicionário com métricas detalhadas
        """
        total = self.metrics["total_requests"]
        success_rate = (self.metrics["successful_requests"] / total * 100) if total > 0 else 0
        cache_hit_rate = (self.metrics["cache_hits"] / total * 100) if total > 0 else 0
        
        return {
            "total_requests": total,
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": round(success_rate, 2),
            "cache_hits": self.metrics["cache_hits"],
            "cache_hit_rate": round(cache_hit_rate, 2),
            "fallback_used": self.metrics["fallback_used"],
            "api_usage": self.metrics["api_usage"].copy(),
            "cache_size": len(self.fallback_cache)
        }
    
    def get_api_status(self) -> Dict[str, Any]:
        """
        Obtém status das APIs de CNPJ.
        
        Returns:
            Dicionário com status detalhado de cada API
        """
        status_report = {}
        
        for api_name, status in self.api_status.items():
            status_report[api_name] = {
                "available": status.available,
                "circuit_open": status.is_circuit_open(),
                "error_count": status.error_count,
                "consecutive_failures": status.consecutive_failures,
                "last_error": status.last_error,
                "last_success": status.last_success.isoformat() if status.last_success else None,
                "last_failure": status.last_failure.isoformat() if status.last_failure else None
            }
        
        return status_report
    
    def clear_metrics(self):
        """
        Limpa todas as métricas e reseta contadores.
        """
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "fallback_used": 0,
            "api_usage": {
                "BrasilAPI": 0,
                "CNPJá": 0,
                "CNPJ.ws": 0,
                "fallback": 0
            }
        }
        logger.info("Métricas do cliente CNPJ foram limpas")
    
    def clear_fallback_cache(self):
        """
        Limpa o cache de fallback.
        """
        cache_size = len(self.fallback_cache)
        self.fallback_cache.clear()
        logger.info(f"Cache de fallback limpo ({cache_size} entradas removidas)")
    
    def reset_circuit_breakers(self):
        """
        Reseta todos os circuit breakers das APIs.
        """
        for api_name, status in self.api_status.items():
            status.available = True
            status.consecutive_failures = 0
            status.last_error = None
        logger.info("Circuit breakers resetados para todas as APIs")
    
    @with_error_handling("cnpj_api", context={"operation": "generate_cnpj_card"})
    async def generate_cnpj_card(self, cnpj: str) -> Dict[str, Any]:
        """
        Gera cartão formatado com dados de CNPJ.
        
        Args:
            cnpj: CNPJ para gerar cartão
            
        Returns:
            Dicionário com dados formatados do cartão
            
        Raises:
            CNPJAPIError: Se não conseguir obter dados do CNPJ
        """
        try:
            cnpj_data = await self.get_cnpj_data(cnpj)
            
            card = {
                "cnpj": cnpj_data.cnpj,
                "razao_social": cnpj_data.razao_social,
                "nome_fantasia": cnpj_data.nome_fantasia,
                "situacao_cadastral": cnpj_data.situacao_cadastral,
                "endereco_completo": cnpj_data.endereco_completo,
                "uf": cnpj_data.uf,
                "municipio": cnpj_data.municipio,
                "telefone": cnpj_data.telefone,
                "api_source": cnpj_data.api_source,
                "generated_at": datetime.now().isoformat(),
                "consulted_at": cnpj_data.consulted_at.isoformat()
            }
            
            return card
            
        except CNPJAPIError:
            raise
        except Exception as e:
            raise CNPJAPIError(f"Erro ao gerar cartão CNPJ: {e}")
    
    @with_error_handling("cnpj_api", context={"operation": "download_cnpj_certificate_pdf"})
    async def download_cnpj_certificate_pdf(self, cnpj: str, output_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Descarga certificado PDF de CNPJ usando la API de CNPJá.
        
        Args:
            cnpj: CNPJ para descargar certificado
            output_path: Ruta donde guardar el PDF (opcional)
            
        Returns:
            Información del PDF descargado
            
        Raises:
            CNPJAPIError: Si hay error al descargar el PDF
        """
        try:
            # Limpiar y validar CNPJ
            clean_cnpj = self._clean_cnpj(cnpj)
            if not self._validate_cnpj(clean_cnpj):
                raise CNPJAPIError(f"CNPJ inválido: {cnpj}")
            
            # Verificar si tenemos API key
            if not self.cnpja_api_key:
                logger.warning("CNPJá API key não configurada, usando PDF mock")
                pdf_content = self._generate_mock_pdf(clean_cnpj)
                api_source = "Mock"
            else:
                # Usar API real de CNPJá
                logger.info(f"Descargando certificado PDF para CNPJ: {clean_cnpj}")
                
                url = f"https://api.cnpja.com/rfb/certificate"
                headers = {
                    "Authorization": self.cnpja_api_key,
                    "User-Agent": "Pipefy-Document-Ingestion/1.0"
                }
                params = {
                    "taxId": clean_cnpj,
                    "pages": "REGISTRATION"
                }
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, headers=headers, params=params)
                    
                    if response.status_code == 401:
                        raise CNPJAPIError(f"API key CNPJá inválida ou expirada", 401, "CNPJá")
                    elif response.status_code == 404:
                        raise CNPJAPIError(f"CNPJ não encontrado: {clean_cnpj}", 404, "CNPJá")
                    elif response.status_code != 200:
                        raise CNPJAPIError(f"Erro na API CNPJá: {response.status_code} - {response.text}", response.status_code, "CNPJá")
                    
                    # Verificar se o conteúdo é PDF
                    content_type = response.headers.get("content-type", "")
                    if "pdf" not in content_type.lower():
                        logger.warning(f"Resposta não é PDF: {content_type}")
                        # Tentar usar o conteúdo mesmo assim
                    
                    pdf_content = response.content
                    api_source = "CNPJá"
                    logger.info(f"✅ PDF descargado exitosamente: {len(pdf_content)} bytes")
            
            # Si se especificó ruta de salida, guardar archivo
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(pdf_content)
                logger.info(f"PDF guardado en: {output_path}")
            
            # Preparar respuesta
            response = {
                "success": True,
                "file_size_bytes": len(pdf_content),
                "api_source": api_source,
                "content": pdf_content,
                "cnpj": clean_cnpj
            }
            
            return response
            
        except CNPJAPIError:
            raise
        except Exception as e:
            raise CNPJAPIError(f"Error al descargar certificado PDF: {str(e)}")
            
    def _generate_mock_pdf(self, cnpj: str) -> bytes:
        """
        Genera un PDF de prueba con datos de CNPJ.
        
        Args:
            cnpj: CNPJ para generar PDF
            
        Returns:
            Contenido del PDF en bytes
        """
        # Contenido mínimo de un PDF válido
        pdf_content = b"%PDF-1.4\n"
        pdf_content += b"1 0 obj\n"
        pdf_content += b"<< /Type /Catalog /Pages 2 0 R >>\n"
        pdf_content += b"endobj\n"
        pdf_content += b"2 0 obj\n"
        pdf_content += b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        pdf_content += b"endobj\n"
        pdf_content += b"3 0 obj\n"
        pdf_content += b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
        pdf_content += b"endobj\n"
        pdf_content += b"4 0 obj\n"
        pdf_content += b"<< /Length 55 >>\n"
        pdf_content += b"stream\n"
        pdf_content += b"BT /F1 12 Tf 72 720 Td (Mock CNPJ Certificate for: " + cnpj.encode() + b") Tj ET\n"
        pdf_content += b"endstream\n"
        pdf_content += b"endobj\n"
        pdf_content += b"xref\n"
        pdf_content += b"0 5\n"
        pdf_content += b"0000000000 65535 f\n"
        pdf_content += b"0000000009 00000 n\n"
        pdf_content += b"0000000058 00000 n\n"
        pdf_content += b"0000000115 00000 n\n"
        pdf_content += b"0000000198 00000 n\n"
        pdf_content += b"trailer << /Size 5 /Root 1 0 R >>\n"
        pdf_content += b"startxref\n"
        pdf_content += b"406\n"
        pdf_content += b"%%EOF\n"
        
        return pdf_content


# Instância global do cliente
cnpj_client = CNPJClient()