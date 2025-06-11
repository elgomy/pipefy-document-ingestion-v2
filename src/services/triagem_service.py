"""
Servicio de Triagem que integra la clasificación de documentos con las operaciones de Pipefy.
Orquesta el flujo completo de análisis y procesamiento de casos.
"""
import logging
from typing import Dict, Any, Optional
from src.services.classification_service import classification_service, ClassificationType
from src.services.pipefy_service import pipefy_service
from src.services.report_service import report_service, ReportMetadata
from src.services.notification_service import (
    notification_service, 
    NotificationRecipient, 
    NotificationContext,
    NotificationType
)
from src.services.cnpj_service import cnpj_service, CNPJServiceError
from src.integrations.pipefy_client import PipefyAPIError
from datetime import datetime

logger = logging.getLogger(__name__)

class TriagemService:
    """Servicio principal de triagem que orquesta todo el flujo."""
    
    def __init__(self):
        self.classification_service = classification_service
        self.pipefy_service = pipefy_service
        self.report_service = report_service
        self.notification_service = notification_service
        self.cnpj_service = cnpj_service
    
    async def process_triagem_complete(
        self, 
        card_id: str, 
        documents_data: Dict[str, Any],
        case_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Procesa la triagem completa de un caso: clasificación + acciones en Pipefy.
        
        Args:
            card_id: ID del card de Pipefy
            documents_data: Datos de documentos del caso
            case_metadata: Metadatos adicionales del caso (opcional)
            
        Returns:
            Resultado completo del procesamiento
        """
        result = {
            "card_id": card_id,
            "success": False,
            "classification_result": None,
            "pipefy_operations": [],
            "errors": [],
            "warnings": [],
            "processing_time": None
        }
        
        start_time = logger.info(f"Iniciando triagem completa para card {card_id}")
        
        try:
            # 1. Clasificar documentos
            logger.info(f"Classificando documentos para card {card_id}")
            classification_result = self.classification_service.classify_case(documents_data)
            result["classification_result"] = classification_result
            
            # 2. Generar informes usando el servicio de reportes
            metadata = ReportMetadata(
                generated_at=datetime.now(),
                case_id=card_id,
                company_name=case_metadata.get("razao_social") if case_metadata else None,
                cnpj=case_metadata.get("cnpj") if case_metadata else None,
                analyst=case_metadata.get("gestor_responsavel", "Sistema Automático") if case_metadata else "Sistema Automático"
            )
            
            # Relatório detalhado para arquivamento
            detailed_report = self.report_service.generate_detailed_report(
                classification_result, 
                metadata, 
                include_technical_details=True
            )
            
            # Relatório resumido para campo Pipefy
            summary_report = self.report_service.generate_summary_report(
                classification_result, 
                metadata
            )
            
            # 3. Procesar resultado en Pipefy
            logger.info(f"Processando resultado no Pipefy para card {card_id}")
            pipefy_result = await self.pipefy_service.process_triagem_result(
                card_id,
                classification_result.classification.value,
                detailed_report,
                summary_report
            )
            
            result["pipefy_operations"] = pipefy_result.get("operations", [])
            
            # 4. Verificar se houve erros no Pipefy
            if not pipefy_result.get("success", False):
                result["errors"].extend(pipefy_result.get("errors", []))
                result["warnings"].append("Falha nas operações do Pipefy")
            else:
                result["success"] = True
                logger.info(f"Triagem concluída com sucesso para card {card_id}")
            
            # 5. Adicionar recomendações baseadas na classificação
            recommendations = self._generate_recommendations(classification_result)
            result["recommendations"] = recommendations
            
        except PipefyAPIError as e:
            error_msg = f"Erro da API Pipefy durante triagem do card {card_id}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            
        except Exception as e:
            error_msg = f"Erro inesperado durante triagem do card {card_id}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        finally:
            # Calcular tempo de processamento
            # result["processing_time"] = time.time() - start_time
            logger.info(f"Triagem finalizada para card {card_id}. Sucesso: {result['success']}")
        
        return result
    
    async def process_triagem_with_notifications(
        self, 
        card_id: str, 
        documents_data: Dict[str, Any],
        case_metadata: Optional[Dict[str, Any]] = None,
        notification_recipient: Optional[NotificationRecipient] = None
    ) -> Dict[str, Any]:
        """
        Procesa la triagem completa incluyendo envío de notificaciones WhatsApp.
        
        Args:
            card_id: ID del card de Pipefy
            documents_data: Datos de documentos del caso
            case_metadata: Metadatos adicionales del caso (opcional)
            notification_recipient: Destinatario para notificaciones (opcional)
            
        Returns:
            Resultado completo del procesamiento incluyendo notificaciones
        """
        # Procesar triagem normal
        result = await self.process_triagem_complete(card_id, documents_data, case_metadata)
        
        # Agregar información de notificaciones
        result["notification_result"] = None
        result["notification_sent"] = False
        
        # Enviar notificación si hay destinatario y clasificación exitosa
        if notification_recipient and result.get("classification_result"):
            try:
                logger.info(f"Enviando notificación para card {card_id}")
                
                # Crear contexto de notificación
                context = NotificationContext(
                    case_id=card_id,
                    company_name=case_metadata.get("razao_social", "Empresa") if case_metadata else "Empresa",
                    cnpj=case_metadata.get("cnpj") if case_metadata else None,
                    analyst_name=case_metadata.get("gestor_responsavel") if case_metadata else None,
                    classification_result=result["classification_result"]
                )
                
                # Enviar notificación basada en clasificación
                notification_result = await self.notification_service.send_classification_notification(
                    result["classification_result"],
                    context,
                    notification_recipient
                )
                
                result["notification_result"] = notification_result
                result["notification_sent"] = notification_result.success
                
                if notification_result.success:
                    logger.info(f"Notificación enviada exitosamente para card {card_id}")
                else:
                    logger.error(f"Falló envío de notificación para card {card_id}: {notification_result.error_message}")
                    result["warnings"].append(f"Falha no envio de notificação: {notification_result.error_message}")
                
            except Exception as e:
                error_msg = f"Erro inesperado enviando notificação para card {card_id}: {str(e)}"
                logger.error(error_msg)
                result["warnings"].append(error_msg)
        
        return result
    
    async def send_blocking_issues_notification(
        self,
        card_id: str,
        company_name: str,
        blocking_issues: list,
        recipient: NotificationRecipient,
        cnpj: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía notificación específica para pendencias bloqueantes.
        
        Args:
            card_id: ID del caso
            company_name: Nome da empresa
            blocking_issues: Lista de pendencias bloqueantes
            recipient: Destinatario de la notificación
            cnpj: CNPJ da empresa (opcional)
            
        Returns:
            Resultado del envío de notificación
        """
        try:
            # Crear contexto
            context = NotificationContext(
                case_id=card_id,
                company_name=company_name,
                cnpj=cnpj
            )
            
            # Crear resultado de clasificación temporal para notificación
            from src.services.classification_service import ClassificationResult
            temp_result = ClassificationResult(
                ClassificationType.PENDENCIA_BLOQUEANTE,
                0.9,  # Confianza alta para notificación manual
                "Pendências bloqueantes detectadas",
                [],  # document_analyses
                blocking_issues,  # blocking_issues
                [],  # non_blocking_issues
                []   # auto_generate_actions
            )
            
            # Enviar notificación
            notification_result = await self.notification_service._send_blocking_issues_notification(
                temp_result,
                context,
                recipient
            )
            
            return {
                "success": notification_result.success,
                "message_sid": notification_result.message_sid,
                "error_message": notification_result.error_message,
                "sent_at": notification_result.sent_at
            }
            
        except Exception as e:
            error_msg = f"Erro enviando notificação de pendências bloqueantes: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error_message": error_msg
            }
    
    async def send_approval_notification(
        self,
        card_id: str,
        company_name: str,
        recipient: NotificationRecipient,
        cnpj: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía notificación de aprobación de documentos.
        
        Args:
            card_id: ID del caso
            company_name: Nome da empresa
            recipient: Destinatario de la notificación
            cnpj: CNPJ da empresa (opcional)
            
        Returns:
            Resultado del envío de notificación
        """
        try:
            # Crear contexto
            context = NotificationContext(
                case_id=card_id,
                company_name=company_name,
                cnpj=cnpj
            )
            
            # Enviar notificación
            notification_result = await self.notification_service._send_approval_notification(
                context,
                recipient
            )
            
            return {
                "success": notification_result.success,
                "message_sid": notification_result.message_sid,
                "error_message": notification_result.error_message,
                "sent_at": notification_result.sent_at
            }
            
        except Exception as e:
            error_msg = f"Erro enviando notificação de aprovação: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error_message": error_msg
            }
    
    def _generate_markdown_report(
        self, 
        classification_result, 
        case_metadata: Dict[str, Any]
    ) -> str:
        """
        Gera um relatório detalhado em Markdown baseado na classificação.
        
        Args:
            classification_result: Resultado da classificação
            case_metadata: Metadados do caso
            
        Returns:
            Relatório em formato Markdown
        """
        from datetime import datetime
        
        # Header do relatório
        report_lines = [
            "# 📋 Relatório de Triagem Documental",
            "",
            f"**Data/Hora:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
            f"**Classificação:** {classification_result.classification.value}",
            f"**Confiança:** {classification_result.confidence_score:.1%}",
            ""
        ]
        
        # Informações do caso (se disponíveis)
        if case_metadata:
            report_lines.extend([
                "## 📊 Informações do Caso",
                ""
            ])
            
            if case_metadata.get('razao_social'):
                report_lines.append(f"**Razão Social:** {case_metadata['razao_social']}")
            if case_metadata.get('cnpj'):
                report_lines.append(f"**CNPJ:** {case_metadata['cnpj']}")
            if case_metadata.get('gestor_responsavel'):
                report_lines.append(f"**Gestor Responsável:** {case_metadata['gestor_responsavel']}")
            
            report_lines.append("")
        
        # Resumo da análise
        report_lines.extend([
            "## 🎯 Resumo da Análise",
            "",
            classification_result.summary,
            ""
        ])
        
        # Detalhamento por documento
        report_lines.extend([
            "## 📄 Análise Detalhada por Documento",
            ""
        ])
        
        for analysis in classification_result.document_analyses:
            status_icon = "✅" if analysis.valid else "❌"
            presence_text = "Presente" if analysis.present else "Ausente"
            
            report_lines.append(f"### {status_icon} {analysis.document_type.value.replace('_', ' ').title()}")
            report_lines.append(f"**Status:** {presence_text}")
            
            if analysis.age_days is not None:
                report_lines.append(f"**Idade:** {analysis.age_days} dias")
            
            if analysis.can_auto_generate:
                report_lines.append("**🤖 Pode ser gerado automaticamente**")
            
            if analysis.issues:
                report_lines.append("**Pendências:**")
                for issue in analysis.issues:
                    report_lines.append(f"- {issue}")
            
            report_lines.append("")
        
        # Próximos passos baseados na classificação
        next_steps = self._get_next_steps_text(classification_result.classification)
        if next_steps:
            report_lines.extend([
                "## 🚀 Próximos Passos",
                "",
                next_steps,
                ""
            ])
        
        # Footer
        report_lines.extend([
            "---",
            "*Relatório gerado automaticamente pelo Agente de Triagem Documental v2.0*"
        ])
        
        return "\n".join(report_lines)
    
    def _get_next_steps_text(self, classification: ClassificationType) -> str:
        """Retorna o texto de próximos passos baseado na classificação."""
        
        if classification == ClassificationType.APROVADO:
            return """
✅ **Documentação Aprovada**

O caso foi aprovado e pode prosseguir para as próximas etapas do processo de cadastro.

**Ações realizadas:**
- Card movido para a fase "Aprovado"
- Documentação validada conforme checklist

**Próximas etapas:**
- Aguardar processamento pela equipe de cadastro
- Acompanhar evolução do processo no Pipefy
"""
        
        elif classification == ClassificationType.PENDENCIA_BLOQUEANTE:
            return """
⚠️ **Pendências Bloqueantes Identificadas**

O caso possui pendências que impedem o prosseguimento do processo.

**Ações realizadas:**
- Card movido para a fase "Pendências Documentais"
- Gestor comercial notificado via WhatsApp

**Ações necessárias:**
- Contatar o cliente para regularização das pendências
- Solicitar envio dos documentos em conformidade
- Reenviar o caso após correções
"""
        
        elif classification == ClassificationType.PENDENCIA_NAO_BLOQUEANTE:
            return """
📋 **Pendências Não-Bloqueantes Identificadas**

O caso possui pendências que podem ser resolvidas internamente.

**Ações realizadas:**
- Card movido para a fase "Emitir Documentos"
- Tentativa de geração automática de documentos

**Ações necessárias:**
- Equipe de cadastro deve gerar/atualizar documentos pendentes
- Verificar se ações automáticas foram bem-sucedidas
- Finalizar documentação e aprovar o caso
"""
        
        return ""
    
    def _generate_recommendations(self, classification_result) -> Dict[str, Any]:
        """
        Gera recomendações baseadas no resultado da classificação.
        
        Args:
            classification_result: Resultado da classificação
            
        Returns:
            Dicionário com recomendações
        """
        recommendations = {
            "priority": "normal",
            "estimated_resolution_time": "1-2 dias úteis",
            "required_actions": [],
            "automated_actions": [],
            "manual_actions": []
        }
        
        classification = classification_result.classification
        
        if classification == ClassificationType.APROVADO:
            recommendations.update({
                "priority": "low",
                "estimated_resolution_time": "Imediato",
                "required_actions": ["Prosseguir com o processo de cadastro"]
            })
            
        elif classification == ClassificationType.PENDENCIA_BLOQUEANTE:
            recommendations.update({
                "priority": "high",
                "estimated_resolution_time": "3-5 dias úteis",
                "required_actions": [
                    "Contatar cliente urgentemente",
                    "Solicitar documentos em conformidade",
                    "Acompanhar regularização"
                ],
                "manual_actions": [
                    "Enviar lista detalhada de pendências ao cliente",
                    "Agendar reunião para esclarecimentos se necessário",
                    "Definir prazo para regularização"
                ]
            })
            
        elif classification == ClassificationType.PENDENCIA_NAO_BLOQUEANTE:
            recommendations.update({
                "priority": "medium",
                "estimated_resolution_time": "1-2 dias úteis",
                "required_actions": [
                    "Gerar documentos pendentes",
                    "Verificar ações automáticas",
                    "Finalizar documentação"
                ]
            })
            
            # Adicionar ações automáticas específicas
            for auto_action in classification_result.auto_actions_possible:
                if "Cartão CNPJ" in auto_action:
                    recommendations["automated_actions"].append("Gerar Cartão CNPJ via API CNPJá")
                else:
                    recommendations["automated_actions"].append(auto_action)
        
        return recommendations
    
    async def validate_card_before_triagem(self, card_id: str) -> Dict[str, Any]:
        """
        Valida se um card existe e está na fase correta para triagem.
        
        Args:
            card_id: ID do card a validar
            
        Returns:
            Resultado da validação
        """
        validation_result = {
            "valid": False,
            "card_exists": False,
            "current_phase": None,
            "can_process": False,
            "issues": []
        }
        
        try:
            # Verificar se o card existe
            card_exists = await self.pipefy_service.validate_card_exists(card_id)
            validation_result["card_exists"] = card_exists
            
            if not card_exists:
                validation_result["issues"].append(f"Card {card_id} não encontrado no Pipefy")
                return validation_result
            
            # Obter informações do card
            card_info = await self.pipefy_service.get_card_status(card_id)
            current_phase = card_info.get("current_phase", {})
            validation_result["current_phase"] = current_phase
            
            # Verificar se está na fase correta para triagem
            # Assumindo que a triagem deve ser feita em uma fase específica
            triagem_phases = ["triagem_documentos_ai", "nova_solicitacao", "pendente_analise"]
            current_phase_name = current_phase.get("name", "").lower()
            
            if any(phase in current_phase_name for phase in triagem_phases):
                validation_result["can_process"] = True
                validation_result["valid"] = True
            else:
                validation_result["issues"].append(
                    f"Card está na fase '{current_phase.get('name')}' que não permite triagem automática"
                )
            
        except Exception as e:
            error_msg = f"Erro ao validar card {card_id}: {str(e)}"
            logger.error(error_msg)
            validation_result["issues"].append(error_msg)
        
        return validation_result
    
    def get_classification_statistics(self, results: list) -> Dict[str, Any]:
        """
        Calcula estatísticas de classificação para um conjunto de resultados.
        
        Args:
            results: Lista de resultados de triagem
            
        Returns:
            Estatísticas calculadas
        """
        if not results:
            return {"total": 0, "error": "Nenhum resultado fornecido"}
        
        total = len(results)
        classifications = {}
        confidence_scores = []
        processing_times = []
        
        for result in results:
            if result.get("classification_result"):
                classification = result["classification_result"].classification.value
                classifications[classification] = classifications.get(classification, 0) + 1
                confidence_scores.append(result["classification_result"].confidence_score)
            
            if result.get("processing_time"):
                processing_times.append(result["processing_time"])
        
        stats = {
            "total_cases": total,
            "classifications": classifications,
            "classification_percentages": {
                k: (v / total) * 100 for k, v in classifications.items()
            }
        }
        
        if confidence_scores:
            stats["average_confidence"] = sum(confidence_scores) / len(confidence_scores)
            stats["min_confidence"] = min(confidence_scores)
            stats["max_confidence"] = max(confidence_scores)
        
        if processing_times:
            stats["average_processing_time"] = sum(processing_times) / len(processing_times)
            stats["min_processing_time"] = min(processing_times)
            stats["max_processing_time"] = max(processing_times)
        
        return stats

    async def gerar_e_armazenar_cartao_cnpj(
        self,
        cnpj: str,
        case_id: str,
        save_to_database: bool = True
    ) -> Dict[str, Any]:
        """
        Gera e armazena cartão CNPJ para um caso específico.
        
        Args:
            cnpj: CNPJ para gerar o cartão
            case_id: ID do caso associado
            save_to_database: Se deve salvar na base de dados
            
        Returns:
            Resultado da geração do cartão
        """
        try:
            logger.info(f"Gerando cartão CNPJ {cnpj} para caso {case_id}")
            
            # Gerar cartão usando o serviço de CNPJ
            result = await self.cnpj_service.gerar_e_armazenar_cartao_cnpj(
                cnpj=cnpj,
                case_id=case_id,
                save_to_database=save_to_database
            )
            
            logger.info(f"Cartão CNPJ gerado com sucesso para caso {case_id}")
            return {
                "success": True,
                "cnpj": result["cnpj"],
                "razao_social": result["razao_social"],
                "file_path": result.get("local_file_path", result.get("file_path")),
                "pdf_file_path": result.get("pdf_file_path"),
                "supabase_document_id": result.get("supabase_document_id"),
                "supabase_public_url": result.get("supabase_public_url"),
                "generated_at": result["generated_at"],
                "api_source": result["api_source"],
                "saved_to_database": result.get("saved_to_database", False)
            }
            
        except CNPJServiceError as e:
            error_msg = f"Erro do serviço CNPJ para caso {case_id}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "cnpj": cnpj,
                "case_id": case_id
            }
        except Exception as e:
            error_msg = f"Erro inesperado gerando cartão CNPJ para caso {case_id}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "cnpj": cnpj,
                "case_id": case_id
            }
    
    async def validate_cnpj_for_case(self, cnpj: str, case_id: str) -> Dict[str, Any]:
        """
        Valida CNPJ para um caso específico.
        
        Args:
            cnpj: CNPJ para validação
            case_id: ID do caso associado
            
        Returns:
            Resultado da validação
        """
        try:
            logger.info(f"Validando CNPJ {cnpj} para caso {case_id}")
            
            # Validar usando o serviço de CNPJ
            validation_result = await self.cnpj_service.validate_cnpj_for_triagem(cnpj)
            
            # Adicionar informações do caso
            validation_result["case_id"] = case_id
            
            if validation_result["valid"]:
                logger.info(f"CNPJ {cnpj} válido para caso {case_id}")
            else:
                logger.warning(f"CNPJ {cnpj} inválido para caso {case_id}: {validation_result.get('error', 'Erro desconhecido')}")
            
            return validation_result
            
        except Exception as e:
            error_msg = f"Erro inesperado validando CNPJ {cnpj} para caso {case_id}: {str(e)}"
            logger.error(error_msg)
            return {
                "valid": False,
                "error": error_msg,
                "cnpj": cnpj,
                "case_id": case_id
            }
    
    async def process_triagem_with_cnpj_generation(
        self,
        card_id: str,
        documents_data: Dict[str, Any],
        cnpj: str,
        case_metadata: Optional[Dict[str, Any]] = None,
        notification_recipient: Optional[NotificationRecipient] = None
    ) -> Dict[str, Any]:
        """
        Procesa triagem completa incluyendo generación automática de cartão CNPJ.
        
        Args:
            card_id: ID del card de Pipefy
            documents_data: Datos de documentos del caso
            cnpj: CNPJ para generar cartão
            case_metadata: Metadatos adicionales del caso
            notification_recipient: Destinatario para notificaciones
            
        Returns:
            Resultado completo del procesamiento incluyendo cartão CNPJ
        """
        # Procesar triagem con notificaciones
        result = await self.process_triagem_with_notifications(
            card_id, documents_data, case_metadata, notification_recipient
        )
        
        # Agregar información de CNPJ
        result["cnpj_operations"] = {
            "validation_result": None,
            "card_generation_result": None,
            "cnpj_card_generated": False
        }
        
        # Validar CNPJ
        try:
            logger.info(f"Validando CNPJ {cnpj} para card {card_id}")
            validation_result = await self.validate_cnpj_for_case(cnpj, card_id)
            result["cnpj_operations"]["validation_result"] = validation_result
            
            # Si CNPJ es válido y hay pendencias no bloqueantes, generar cartão
            classification_result = result.get("classification_result")
            if (validation_result.get("valid") and 
                classification_result and 
                classification_result.classification == ClassificationType.PENDENCIA_NAO_BLOQUEANTE):
                
                # Verificar si "Cartão CNPJ" está en las acciones automáticas posibles
                auto_actions = classification_result.auto_actions_possible or []
                if any("Cartão CNPJ" in action for action in auto_actions):
                    logger.info(f"Generando cartão CNPJ automáticamente para card {card_id}")
                    
                    card_result = await self.gerar_e_armazenar_cartao_cnpj(
                        cnpj=cnpj,
                        case_id=card_id,
                        save_to_database=True
                    )
                    
                    result["cnpj_operations"]["card_generation_result"] = card_result
                    result["cnpj_operations"]["cnpj_card_generated"] = card_result.get("success", False)
                    
                    if card_result.get("success"):
                        logger.info(f"Cartão CNPJ gerado automaticamente para card {card_id}")
                        # Agregar a las operaciones automáticas realizadas
                        if "automated_actions_performed" not in result:
                            result["automated_actions_performed"] = []
                        result["automated_actions_performed"].append(f"Cartão CNPJ gerado: {card_result['file_path']}")
                    else:
                        logger.error(f"Falha na geração automática de cartão CNPJ para card {card_id}")
                        result["warnings"].append(f"Falha na geração automática de cartão CNPJ: {card_result.get('error', 'Erro desconhecido')}")
            
        except Exception as e:
            error_msg = f"Erro nas operações de CNPJ para card {card_id}: {str(e)}"
            logger.error(error_msg)
            result["warnings"].append(error_msg)
        
        return result
    
    def get_cnpj_cache_statistics(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do cache de CNPJs.
        
        Returns:
            Estatísticas do cache
        """
        try:
            cached_cnpjs = self.cnpj_service.list_cached_cnpjs()
            generated_cards = self.cnpj_service.list_generated_cards()
            
            return {
                "cached_cnpjs_count": len(cached_cnpjs),
                "generated_cards_count": len(generated_cards),
                "valid_cache_count": len([c for c in cached_cnpjs if c["is_valid"]]),
                "expired_cache_count": len([c for c in cached_cnpjs if not c["is_valid"]]),
                "api_sources": list(set([c["api_source"] for c in cached_cnpjs if c["api_source"]])),
                "recent_cached": cached_cnpjs[:5],  # 5 mais recentes
                "recent_generated": generated_cards[:5]  # 5 mais recentes
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de cache CNPJ: {e}")
            return {
                "error": str(e),
                "cached_cnpjs_count": 0,
                "generated_cards_count": 0
            }


# Instância global do serviço
triagem_service = TriagemService() 