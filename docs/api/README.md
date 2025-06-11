# 📚 Documentación de APIs - Pipefy Document Analysis Platform

Esta documentación describe todas las APIs, servicios y funciones disponibles en la plataforma de análisis de documentos de Pipefy.

## 📋 Índice

- [🔧 Servicios Principales](#-servicios-principales)
- [🔌 Integraciones Externas](#-integraciones-externas)
- [🛠️ Utilidades](#️-utilidades)
- [📊 Modelos de Datos](#-modelos-de-datos)
- [🚀 Guías de Uso](#-guías-de-uso)

## 🔧 Servicios Principales

### [TriagemService](./services/triagem_service.md)
Servicio principal que orquesta todo el flujo de análisis de documentos.

**Funciones principales:**
- `process_triagem_complete()` - Procesamiento completo de triagem
- `process_triagem_with_notifications()` - Triagem con notificaciones WhatsApp
- `gerar_e_armazenar_cartao_cnpj()` - Generación de cartões CNPJ

### [DocumentClassificationService](./services/classification_service.md)
Servicio de clasificación de documentos usando IA.

**Funciones principales:**
- `classify_case()` - Clasificación completa de un caso
- `analyze_document_quality()` - Análisis de calidad individual
- `verify_required_documents()` - Verificación de documentos obligatorios

### [DatabaseService](./services/database_service.md)
Servicio de gestión de base de datos con Supabase.

**Funciones principales:**
- `track_case()` - Seguimiento de casos
- `upload_document()` - Subida de documentos
- `get_case_documents()` - Consulta de documentos

### [NotificationService](./services/notification_service.md)
Servicio de notificaciones WhatsApp via Twilio.

**Funciones principales:**
- `send_classification_notification()` - Notificaciones de clasificación
- `send_blocking_issues_notification()` - Notificaciones de pendencias
- `send_approval_notification()` - Notificaciones de aprobación

### [ReportService](./services/report_service.md)
Servicio de generación de informes detallados.

**Funciones principales:**
- `generate_detailed_report()` - Informes detallados
- `generate_summary_report()` - Informes resumidos
- `generate_markdown_report()` - Informes en formato Markdown

### [CNPJService](./services/cnpj_service.md)
Servicio de validación y generación de cartões CNPJ.

**Funciones principales:**
- `validate_cnpj_for_triagem()` - Validación para triagem
- `generate_and_store_cartao()` - Generación y almacenamiento
- `get_cached_cnpj_data()` - Consulta de datos en caché

## 🔌 Integraciones Externas

### [PipefyClient](./integrations/pipefy_client.md)
Cliente GraphQL para la API de Pipefy.

**Funciones principales:**
- `move_card_to_phase()` - Movimiento entre fases
- `update_card_field()` - Actualización de campos
- `get_card_info()` - Consulta de información

### [TwilioClient](./integrations/twilio_client.md)
Cliente para envío de mensajes WhatsApp via Twilio.

**Funciones principales:**
- `send_whatsapp_message()` - Envío de mensajes
- `send_notification_template()` - Envío con templates
- `validate_phone_number()` - Validación de números

### [CNPJClient](./integrations/cnpj_client.md)
Cliente para consulta de datos CNPJ en APIs externas.

**Funciones principales:**
- `get_cnpj_data()` - Consulta de datos CNPJ
- `generate_cartao_pdf()` - Generación de PDFs
- `validate_cnpj()` - Validación de CNPJ

## 🛠️ Utilidades

### [ErrorHandler](./utils/error_handler.md)
Sistema de manejo de errores con circuit breaker y reintentos.

**Funciones principales:**
- `classify_error()` - Clasificación de errores
- `should_retry()` - Lógica de reintentos
- `@with_error_handling` - Decorador de manejo de errores

## 📊 Modelos de Datos

### [Tipos de Clasificación](./models/classification_types.md)
- `ClassificationType` - Tipos de clasificación (APROVADO, PENDENCIA_BLOQUEANTE, etc.)
- `DocumentType` - Tipos de documentos
- `DocumentRequirement` - Requisitos de documentos

### [Resultados de Análisis](./models/analysis_results.md)
- `ClassificationResult` - Resultado de clasificación
- `DocumentAnalysis` - Análisis de documento individual
- `QualityScore` - Puntuación de calidad

### [Notificaciones](./models/notifications.md)
- `NotificationRecipient` - Destinatario de notificación
- `NotificationContext` - Contexto de notificación
- `NotificationType` - Tipos de notificación

## 🚀 Guías de Uso

### [Guía de Inicio Rápido](./guides/quick_start.md)
Cómo empezar a usar la plataforma.

### [Flujo de Triagem](./guides/triagem_flow.md)
Descripción completa del flujo de análisis.

### [Configuración de APIs](./guides/api_configuration.md)
Configuración de claves y endpoints.

### [Manejo de Errores](./guides/error_handling.md)
Estrategias de manejo de errores y recuperación.

### [Ejemplos de Uso](./guides/examples.md)
Ejemplos prácticos de uso de las APIs.

## 🔐 Autenticación y Seguridad

Todas las APIs requieren configuración de variables de entorno:

```bash
# Pipefy
PIPEFY_API_TOKEN=your_token_here

# Twilio
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Supabase
SUPABASE_URL=your_url_here
SUPABASE_KEY=your_key_here

# OpenAI (para clasificación)
OPENAI_API_KEY=your_key_here
```

## 📈 Monitoreo y Métricas

El sistema incluye logging completo y métricas de rendimiento:

- **Logs estructurados** con niveles INFO, WARNING, ERROR
- **Métricas de tiempo** de procesamiento
- **Estadísticas de errores** por API
- **Circuit breaker** para protección de APIs externas

## 🤝 Contribución

Para contribuir a la documentación:

1. Sigue el formato establecido en cada sección
2. Incluye ejemplos de código cuando sea relevante
3. Documenta todos los parámetros y valores de retorno
4. Mantén la documentación actualizada con los cambios de código

---

**Última actualización:** $(date)
**Versión:** 1.0.0 