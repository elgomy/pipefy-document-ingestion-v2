"""
Cliente Supabase para el servicio de ingestión.
"""
from supabase import create_client, Client

from src.config import settings

def get_supabase_client() -> Client:
    """
    Crea y retorna un cliente Supabase.
    
    Returns:
        Client: Cliente Supabase inicializado
        
    Raises:
        RuntimeError: Si las credenciales no están configuradas
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise RuntimeError("Credenciales de Supabase no configuradas")
    
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY
    ) 