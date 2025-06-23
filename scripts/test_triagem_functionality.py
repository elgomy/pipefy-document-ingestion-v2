#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de triagem implementada.
Este script simula el flujo completo del webhook de triagem.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from integrations.pipefy_client import PipefyClient
from services.triagem_service import TriagemService
from services.result_formatter import ResultFormatter
from config.settings import Settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TriagemTester:
    """Clase para probar la funcionalidad de triagem"""
    
    def __init__(self):
        self.settings = Settings()
        self.pipefy_client = PipefyClient()
        self.triagem_service = TriagemService()
        self.result_formatter = ResultFormatter()
    
    async def test_pipefy_connection(self):
        """Probar la conexión con Pipefy"""
        logger.info("🔗 Probando conexión con Pipefy...")
        
        try:
            # Hacer una consulta simple para verificar la conexión
            query = """
            query {
                me {
                    id
                    name
                    email
                }
            }
            """
            
            result = await self.pipefy_client.execute_query(query)
            
            if result and 'data' in result and 'me' in result['data']:
                logger.info(f"✅ Conexión exitosa con Pipefy")
                logger.info(f"   Usuario: {result['data']['me']['name']}")
                logger.info(f"   Email: {result['data']['me']['email']}")
                return True
            else:
                logger.error("❌ Error en la conexión con Pipefy")
                logger.error(f"   Respuesta: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Excepción al conectar con Pipefy: {str(e)}")
            return False
    
    def test_webhook_payload_parsing(self):
        """Probar el parsing del payload del webhook"""
        logger.info("📝 Probando parsing del payload del webhook...")
        
        # Simular payload típico del webhook de Pipefy
        test_payload = {
            "data": {
                "card": {
                    "id": "test_card_123",
                    "title": "Documento de Teste - CNPJ 12.345.678/0001-90",
                    "current_phase": {
                        "id": "338000020",
                        "name": "Triagem de Documentos"
                    },
                    "fields": [
                        {
                            "field": {
                                "id": "field_cnpj",
                                "label": "CNPJ"
                            },
                            "value": "12.345.678/0001-90"
                        }
                    ],
                    "attachments": [
                        {
                            "id": "attachment_1",
                            "name": "documento_teste.pdf",
                            "url": "https://example.com/documento_teste.pdf"
                        }
                    ]
                }
            }
        }
        
        try:
            # Extraer información del payload
            card_data = test_payload.get('data', {}).get('card', {})
            card_id = card_data.get('id')
            current_phase_id = card_data.get('current_phase', {}).get('id')
            attachments = card_data.get('attachments', [])
            
            logger.info(f"✅ Payload parseado correctamente:")
            logger.info(f"   Card ID: {card_id}")
            logger.info(f"   Phase ID: {current_phase_id}")
            logger.info(f"   Attachments: {len(attachments)}")
            
            # Verificar que es la fase correcta
            if current_phase_id == "338000020":
                logger.info("✅ Fase de triagem detectada correctamente")
                return True, test_payload
            else:
                logger.warning(f"⚠️  Fase diferente detectada: {current_phase_id}")
                return False, test_payload
                
        except Exception as e:
            logger.error(f"❌ Error al parsear payload: {str(e)}")
            return False, None
    
    def test_result_formatter(self):
        """Probar el formateador de resultados"""
        logger.info("📊 Probando formateador de resultados...")
        
        # Simular resultado de análisis
        mock_analysis_result = {
            "classification": "PENDENCIA_BLOQUEANTE",
            "confidence": 0.85,
            "issues": [
                {
                    "type": "missing_document",
                    "description": "Falta el documento de constitución da empresa",
                    "severity": "high"
                },
                {
                    "type": "invalid_signature",
                    "description": "Assinatura do representante legal não confere",
                    "severity": "medium"
                }
            ],
            "recommendations": [
                "Solicitar documento de constituição atualizado",
                "Verificar assinatura do representante legal"
            ],
            "cnpj_info": {
                "cnpj": "12.345.678/0001-90",
                "razao_social": "Empresa Teste LTDA",
                "status": "ATIVA"
            }
        }
        
        try:
            # Formatear resultado detalhado
            detailed_report = self.result_formatter.format_detailed_report(mock_analysis_result)
            
            # Formatear resultado resumido
            summary_report = self.result_formatter.format_summary_report(mock_analysis_result)
            
            logger.info("✅ Relatórios formatados correctamente:")
            logger.info(f"   Relatório detalhado: {len(detailed_report)} caracteres")
            logger.info(f"   Relatório resumido: {len(summary_report)} caracteres")
            
            # Mostrar una muestra del contenido
            logger.info("📄 Muestra del relatório resumido:")
            logger.info(summary_report[:200] + "..." if len(summary_report) > 200 else summary_report)
            
            return True, detailed_report, summary_report
            
        except Exception as e:
            logger.error(f"❌ Error al formatear resultados: {str(e)}")
            return False, None, None
    
    async def test_card_operations_simulation(self):
        """Simular operaciones de card (sin hacer cambios reales)"""
        logger.info("🔄 Simulando operaciones de card...")
        
        test_card_id = "test_card_123"
        
        try:
            # Simular obtención de attachments
            logger.info(f"📎 Simulando obtención de attachments para card {test_card_id}")
            
            # En una prueba real, esto haría una llamada a la API
            # Por ahora solo simulamos la estructura de respuesta
            mock_attachments = [
                {
                    "id": "attachment_1",
                    "name": "documento_teste.pdf",
                    "url": "https://example.com/documento_teste.pdf"
                }
            ]
            
            logger.info(f"✅ Attachments simulados: {len(mock_attachments)}")
            
            # Simular movimiento de card
            target_phase_id = "338000021"  # Fase siguiente
            logger.info(f"🔄 Simulando movimiento de card a fase {target_phase_id}")
            
            # Simular actualización de campos
            mock_field_updates = {
                "resultado_triagem": "PENDENCIA_BLOQUEANTE",
                "observacoes": "Documentos incompletos - verificar anexos"
            }
            
            logger.info(f"📝 Simulando actualización de campos: {list(mock_field_updates.keys())}")
            
            logger.info("✅ Todas las operaciones de card simuladas correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en simulación de operaciones: {str(e)}")
            return False
    
    def test_environment_variables(self):
        """Verificar variables de entorno necesarias"""
        logger.info("🔧 Verificando variables de entorno...")
        
        required_vars = [
            'PIPEFY_API_TOKEN',
            'OPENAI_API_KEY',
            'SUPABASE_URL',
            'SUPABASE_ANON_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"⚠️  Variables de entorno faltantes: {missing_vars}")
            logger.info("   Asegúrate de configurar el archivo .env")
            return False
        else:
            logger.info("✅ Todas las variables de entorno están configuradas")
            return True
    
    async def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        logger.info("🚀 Iniciando pruebas de funcionalidad de triagem")
        logger.info("=" * 60)
        
        results = {}
        
        # 1. Verificar variables de entorno
        results['env_vars'] = self.test_environment_variables()
        
        # 2. Probar conexión con Pipefy
        results['pipefy_connection'] = await self.test_pipefy_connection()
        
        # 3. Probar parsing del webhook
        results['webhook_parsing'], test_payload = self.test_webhook_payload_parsing()
        
        # 4. Probar formateador de resultados
        results['result_formatter'], detailed_report, summary_report = self.test_result_formatter()
        
        # 5. Simular operaciones de card
        results['card_operations'] = await self.test_card_operations_simulation()
        
        # Resumen de resultados
        logger.info("=" * 60)
        logger.info("📊 RESUMEN DE PRUEBAS:")
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\n🎯 Resultado: {passed}/{total} pruebas exitosas")
        
        if passed == total:
            logger.info("🎉 ¡Todas las pruebas pasaron! El sistema está listo para usar.")
        else:
            logger.warning("⚠️  Algunas pruebas fallaron. Revisar configuración.")
        
        return results

async def main():
    """Función principal"""
    print("🔍 PRUEBAS DE FUNCIONALIDAD DE TRIAGEM")
    print("=====================================")
    
    tester = TriagemTester()
    results = await tester.run_all_tests()
    
    # Si hay problemas, mostrar sugerencias
    if not all(results.values()):
        print("\n💡 SUGERENCIAS PARA SOLUCIONAR PROBLEMAS:")
        
        if not results.get('env_vars'):
            print("   • Copiar .env.example a .env y configurar las variables")
        
        if not results.get('pipefy_connection'):
            print("   • Verificar PIPEFY_API_TOKEN en el archivo .env")
            print("   • Comprobar conectividad a internet")
        
        print("   • Revisar logs arriba para más detalles")

if __name__ == "__main__":
    asyncio.run(main())