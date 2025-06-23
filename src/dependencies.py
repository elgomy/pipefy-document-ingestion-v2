"""
Dependencias para inyección en rutas FastAPI.
"""
from typing import Optional
from supabase import Client
from fastapi import Depends

from src.config import settings
from src.services.cnpj_service import CNPJService
from src.integrations.cnpj_client import CNPJClient
from src.integrations.supabase_client import get_supabase_client

# Variable global para el cliente Supabase
supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """
    Dependencia para obtener el cliente Supabase.
    
    Returns:
        Client: Cliente Supabase inicializado
        
    Raises:
        RuntimeError: Si el cliente no está inicializado
    """
    if not supabase_client:
        raise RuntimeError("Cliente Supabase no inicializado")
    return supabase_client

def get_cnpj_client() -> CNPJClient:
    """
    Dependencia para obtener el cliente CNPJ.
    
    Returns:
        CNPJClient: Cliente CNPJ inicializado
    """
    return CNPJClient()

def get_cnpj_service(
    supabase: Client = Depends(get_supabase_client),
    cnpj_client: CNPJClient = Depends(get_cnpj_client)
) -> CNPJService:
    """
    Dependencia para obtener el servicio CNPJ.
    
    Args:
        supabase: Cliente Supabase (inyectado)
        cnpj_client: Cliente CNPJ (inyectado)
        
    Returns:
        CNPJService: Servicio CNPJ inicializado
    """
    return CNPJService(
        supabase_client=supabase,
        cnpj_client=cnpj_client
    ) 