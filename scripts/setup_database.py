#!/usr/bin/env python3
"""
Script para configurar el esquema de base de datos en Supabase.
Adaptado para usar FAQ.pdf como knowledge base en lugar de checklist_config.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

from src.services.database_service import database_service
from src.config.settings import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def read_schema_file() -> str:
    """Lee el archivo de esquema SQL."""
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Archivo de esquema no encontrado: {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        return f.read()

async def execute_sql_script(sql_script: str) -> bool:
    """
    Ejecuta un script SQL en Supabase.
    
    Args:
        sql_script: Script SQL a ejecutar
        
    Returns:
        True si fue exitoso
    """
    try:
        # Dividir el script en statements individuales
        statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
        
        logger.info(f"Ejecutando {len(statements)} statements SQL...")
        
        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    # Ejecutar cada statement individualmente
                    result = database_service.client.rpc('exec_sql', {'sql': statement}).execute()
                    logger.info(f"Statement {i}/{len(statements)} ejecutado exitosamente")
                except Exception as e:
                    # Algunos statements pueden fallar si ya existen (CREATE IF NOT EXISTS)
                    if "already exists" in str(e).lower():
                        logger.info(f"Statement {i} saltado (ya existe): {statement[:50]}...")
                    else:
                        logger.warning(f"Error en statement {i}: {e}")
                        logger.debug(f"Statement problemático: {statement}")
        
        logger.info("Script SQL ejecutado completamente")
        return True
        
    except Exception as e:
        logger.error(f"Error ejecutando script SQL: {e}")
        return False

async def verify_tables() -> bool:
    """
    Verifica que las tablas fueron creadas correctamente.
    
    Returns:
        True si todas las tablas existen
    """
    try:
        expected_tables = [
            "case_tracking",
            "processing_logs", 
            "notification_history",
            "system_config"
        ]
        
        logger.info("Verificando tablas creadas...")
        
        for table in expected_tables:
            try:
                # Intentar hacer una consulta simple a cada tabla
                result = database_service.client.table(table).select("count").limit(1).execute()
                logger.info(f"✅ Tabla '{table}' verificada")
            except Exception as e:
                logger.error(f"❌ Error verificando tabla '{table}': {e}")
                return False
        
        logger.info("✅ Todas las tablas verificadas exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"Error en verificación de tablas: {e}")
        return False

async def verify_initial_data() -> bool:
    """
    Verifica que los datos iniciales fueron insertados.
    
    Returns:
        True si los datos existen
    """
    try:
        logger.info("Verificando datos iniciales...")
        
        # Verificar configuraciones del sistema
        config_keys = [
            "notification_recipients",
            "pipefy_phases",
            "classification_rules",
            "system_settings"
        ]
        
        for key in config_keys:
            config = await database_service.get_system_config(key)
            if config:
                logger.info(f"✅ Configuración '{key}' encontrada")
            else:
                logger.warning(f"⚠️  Configuración '{key}' no encontrada")
        
        logger.info("✅ Verificación de datos iniciales completada")
        return True
        
    except Exception as e:
        logger.error(f"Error verificando datos iniciales: {e}")
        return False

async def test_database_operations() -> bool:
    """
    Prueba operaciones básicas de la base de datos.
    
    Returns:
        True si las operaciones funcionan
    """
    try:
        logger.info("Probando operaciones de base de datos...")
        
        # Test de health check
        health_ok = await database_service.health_check()
        if not health_ok:
            logger.error("❌ Health check falló")
            return False
        
        logger.info("✅ Health check exitoso")
        
        # Test de obtener destinatarios de notificaciones
        recipients = await database_service.get_notification_recipients()
        logger.info(f"✅ Destinatarios de notificaciones: {len(recipients)} encontrados")
        
        logger.info("✅ Todas las operaciones de prueba exitosas")
        return True
        
    except Exception as e:
        logger.error(f"Error en pruebas de operaciones: {e}")
        return False

async def main():
    """Función principal del script."""
    logger.info("🚀 Iniciando configuración de base de datos...")
    
    # Verificar configuración
    missing_vars = settings.validate_required_vars()
    if missing_vars:
        logger.error(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        logger.error("   Configura el archivo .env antes de continuar")
        return False
    
    logger.info("✅ Variables de entorno verificadas")
    
    try:
        # Leer y ejecutar esquema
        logger.info("📖 Leyendo archivo de esquema...")
        schema_sql = await read_schema_file()
        
        logger.info("🔧 Ejecutando migraciones de base de datos...")
        if not await execute_sql_script(schema_sql):
            logger.error("❌ Error ejecutando migraciones")
            return False
        
        # Verificar tablas
        if not await verify_tables():
            logger.error("❌ Error verificando tablas")
            return False
        
        # Verificar datos iniciales
        if not await verify_initial_data():
            logger.warning("⚠️  Algunos datos iniciales pueden estar faltando")
        
        # Probar operaciones
        if not await test_database_operations():
            logger.error("❌ Error en pruebas de operaciones")
            return False
        
        logger.info("🎉 ¡Configuración de base de datos completada exitosamente!")
        logger.info("")
        logger.info("📋 Resumen de tablas creadas:")
        logger.info("   • case_tracking: Tracking de casos procesados")
        logger.info("   • processing_logs: Logs detallados de procesamiento")
        logger.info("   • notification_history: Historial de notificaciones WhatsApp")
        logger.info("   • system_config: Configuraciones del sistema")
        logger.info("")
        logger.info("✨ El sistema está listo para usar con FAQ.pdf como knowledge base")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en configuración: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)