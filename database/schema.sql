-- Schema para el Sistema de Triagem de Documentos
-- Adaptado para usar FAQ.pdf como knowledge base en lugar de checklist_config

-- Tabla para tracking de casos procesados
CREATE TABLE IF NOT EXISTS case_tracking (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL UNIQUE,
    company_name VARCHAR(500),
    cnpj VARCHAR(18),
    analyst_name VARCHAR(255),
    classification_result JSONB NOT NULL,
    pipefy_card_id VARCHAR(255),
    phase_moved_to VARCHAR(255),
    processing_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Tabla para logs detallados de procesamiento
CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL,
    log_level VARCHAR(20) NOT NULL DEFAULT 'INFO',
    component VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    error_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (case_id) REFERENCES case_tracking(case_id) ON DELETE CASCADE
);

-- Tabla para historial de notificaciones WhatsApp
CREATE TABLE IF NOT EXISTS notification_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    recipient_name VARCHAR(255) NOT NULL,
    recipient_phone VARCHAR(20) NOT NULL,
    message_content TEXT NOT NULL,
    twilio_message_sid VARCHAR(255),
    delivery_status VARCHAR(50) DEFAULT 'sent',
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    FOREIGN KEY (case_id) REFERENCES case_tracking(case_id) ON DELETE CASCADE
);

-- Tabla para configuraciones del sistema
CREATE TABLE IF NOT EXISTS system_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    config_key VARCHAR(255) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_case_tracking_case_id ON case_tracking(case_id);
CREATE INDEX IF NOT EXISTS idx_case_tracking_cnpj ON case_tracking(cnpj);
CREATE INDEX IF NOT EXISTS idx_case_tracking_status ON case_tracking(processing_status);
CREATE INDEX IF NOT EXISTS idx_case_tracking_created_at ON case_tracking(created_at);

CREATE INDEX IF NOT EXISTS idx_processing_logs_case_id ON processing_logs(case_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_level ON processing_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_processing_logs_component ON processing_logs(component);
CREATE INDEX IF NOT EXISTS idx_processing_logs_created_at ON processing_logs(created_at);

CREATE INDEX IF NOT EXISTS idx_notification_history_case_id ON notification_history(case_id);
CREATE INDEX IF NOT EXISTS idx_notification_history_type ON notification_history(notification_type);
CREATE INDEX IF NOT EXISTS idx_notification_history_status ON notification_history(delivery_status);
CREATE INDEX IF NOT EXISTS idx_notification_history_sent_at ON notification_history(sent_at);

CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key);
CREATE INDEX IF NOT EXISTS idx_system_config_active ON system_config(is_active);

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_case_tracking_updated_at 
    BEFORE UPDATE ON case_tracking 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at 
    BEFORE UPDATE ON system_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insertar configuraciones iniciales del sistema
INSERT INTO system_config (config_key, config_value, description) VALUES
('notification_recipients', 
 '[
   {
     "name": "Analista Principal",
     "phone_number": "+5511999999999",
     "role": "analyst",
     "is_active": true
   },
   {
     "name": "Supervisor",
     "phone_number": "+5511888888888", 
     "role": "supervisor",
     "is_active": true
   }
 ]', 
 'Lista de destinatarios para notificaciones WhatsApp'),

('pipefy_phases', 
 '{
   "aprovado": "338000018",
   "pendencias": "338000017", 
   "emitir_docs": "338000019"
 }', 
 'IDs das fases do Pipefy para movimentação de cards'),

('classification_rules',
 '{
   "blocking_threshold": 3,
   "auto_approve_threshold": 0,
   "notification_delay_minutes": 5
 }',
 'Regras para classificação automática de documentos'),

('system_settings',
 '{
   "max_retries": 3,
   "timeout_seconds": 30,
   "log_retention_days": 90
 }',
 'Configurações gerais do sistema')

ON CONFLICT (config_key) DO NOTHING;