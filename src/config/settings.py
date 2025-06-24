"""
Configuración y carga de variables de entorno para el servicio de ingestión.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Settings:
    """Configuración centralizada del servicio de ingestión."""
    
    # Pipefy Configuration
    PIPEFY_TOKEN: str = os.getenv("PIPEFY_TOKEN", "")
    PHASE_ID_APROVADO: str = os.getenv("PHASE_ID_APROVADO", "338000018")
    PHASE_ID_PENDENCIAS: str = os.getenv("PHASE_ID_PENDENCIAS", "338000017")
    PHASE_ID_EMITIR_DOCS: str = os.getenv("PHASE_ID_EMITIR_DOCS", "338000019")
    FIELD_ID_INFORME: str = os.getenv("FIELD_ID_INFORME", "informe_crewai_2")
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    # Para WhatsApp Business API usa: whatsapp:+1XXXXXXXXXX
    # Para Sandbox usa: whatsapp:+14155238886 (probado exitosamente con curl)
    TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
    
    # CNPJá Configuration - API Key testada exitosamente
    CNPJA_API_KEY: str = os.getenv("CNPJA_API_KEY", "")
    
    # CrewAI Service Communication
    CREWAI_SERVICE_URL: str = os.getenv("CREWAI_SERVICE_URL", "https://pipefy-crewai-analysis-modular.onrender.com")
    CREWAI_SERVICE_TOKEN: str = os.getenv("CREWAI_SERVICE_TOKEN", "")
    
    # Application Configuration
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))
    
    @classmethod
    def validate_required_vars(cls) -> list[str]:
        """
        Valida que las variables de entorno requeridas estén configuradas.
        
        Returns:
            Lista de variables faltantes (vacía si todas están configuradas)
        """
        required_vars = {
            "PIPEFY_TOKEN": cls.PIPEFY_TOKEN,
            "SUPABASE_URL": cls.SUPABASE_URL,
            "SUPABASE_ANON_KEY": cls.SUPABASE_ANON_KEY,
            "CREWAI_SERVICE_URL": cls.CREWAI_SERVICE_URL,
            "CREWAI_SERVICE_TOKEN": cls.CREWAI_SERVICE_TOKEN,
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        return missing_vars
    
    @classmethod
    def get_pipefy_headers(cls) -> dict:
        """Retorna los headers para las llamadas a la API de Pipefy."""
        return {
            "Authorization": f"Bearer {cls.PIPEFY_TOKEN}",
            "Content-Type": "application/json"
        }
    
    @classmethod
    def get_crewai_headers(cls) -> dict:
        """Retorna los headers para las llamadas al servicio CrewAI."""
        return {
            "Authorization": f"Bearer {cls.CREWAI_SERVICE_TOKEN}",
            "Content-Type": "application/json"
        }

# Instancia global de configuración
settings = Settings()

# Validar variables requeridas al importar
missing_vars = settings.validate_required_vars()
if missing_vars:
    print(f"⚠️  ADVERTENCIA: Variables de entorno faltantes: {', '.join(missing_vars)}")
    print("   Asegúrate de configurar el archivo .env antes de ejecutar el servicio.")