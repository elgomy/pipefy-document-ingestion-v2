import pytest
from unittest.mock import patch, MagicMock
from src.services.triagem_service import TriagemService, measure_time_log
from src.services.classification_service import ClassificationType
import logging
import asyncio

class DummyLogger:
    def __init__(self):
        self.messages = []
    def info(self, msg):
        self.messages.append(msg)
    def error(self, msg):
        self.messages.append(msg)

def make_datetime_mock(seconds):
    mock_now = MagicMock()
    mock_now.__sub__.return_value.total_seconds.return_value = seconds
    return mock_now

@pytest.mark.asyncio
async def test_processing_time_success():
    service = TriagemService()
    dummy_logger = DummyLogger()
    # Mock de ClassificationResult mínimo válido
    mock_classification_result = MagicMock()
    mock_classification_result.classification = ClassificationType.APROVADO
    mock_classification_result.auto_actions_possible = []
    with patch('src.services.triagem_service.logger', dummy_logger):
        with patch('src.services.triagem_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = make_datetime_mock(2.0)
            with patch.object(service.classification_service, 'classify_case', return_value=mock_classification_result):
                with patch.object(service.report_service, 'generate_detailed_report', return_value='detallado'):
                    with patch.object(service.report_service, 'generate_summary_report', return_value='resumen'):
                        with patch.object(service.pipefy_service, 'process_triagem_result', return_value={'operations': [], 'success': True}):
                            result = await service.process_triagem_complete('dummy_card_id', {'doc': 'data'})
                            assert 'processing_time' in result
                            assert result['processing_time'] == 2.0
                            assert result['success'] is True
                            assert any('finalizado en 2.00s' in m for m in dummy_logger.messages)

@pytest.mark.asyncio
async def test_processing_time_error():
    service = TriagemService()
    dummy_logger = DummyLogger()
    with patch('src.services.triagem_service.logger', dummy_logger):
        with patch('src.services.triagem_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = make_datetime_mock(1.0)
            with patch.object(service.classification_service, 'classify_case', side_effect=Exception('error')):
                with patch.object(service.report_service, 'generate_detailed_report', return_value='detallado'):
                    with patch.object(service.report_service, 'generate_summary_report', return_value='resumen'):
                        with patch.object(service.pipefy_service, 'process_triagem_result', return_value={'operations': [], 'success': True}):
                            result = await service.process_triagem_complete('dummy_card_id', {'doc': 'data'})
                            assert 'processing_time' in result
                            assert result['processing_time'] == 1.0
                            assert result['success'] is False
                            assert any('finalizado en 1.00s' in m for m in dummy_logger.messages)
