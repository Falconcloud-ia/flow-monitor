"""
Tests unitarios para Intelligence Core.
"""

import pytest
from datetime import datetime

from intelligence_core.models import SensorData, RiskLevel, PredictionAlert, EnrichedData
from intelligence_core.rules_engine import RulesEngine
from intelligence_core.predictive_model import PredictiveModel
from intelligence_core.intelligence_service import IntelligenceService


class TestModels:
    """Tests para los modelos de datos."""
    
    def test_sensor_data_from_dict(self):
        """Verifica conversión de diccionario a SensorData."""
        data = {
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T01:00:00",
            "value": 35.5,
            "unit": "Celsius",
            "location": "Planta-A/Horno-1",
            "_meta": {"status": "NORMAL"}
        }
        
        sensor = SensorData.from_dict(data)
        
        assert sensor.sensor_id == "SENSOR_TEMP_01"
        assert sensor.value == 35.5
        assert sensor.unit == "Celsius"
        assert sensor.meta["status"] == "NORMAL"
    
    def test_sensor_data_to_dict(self):
        """Verifica serialización de SensorData."""
        sensor = SensorData(
            sensor_id="TEST_01",
            timestamp="2025-12-18T00:00:00",
            value=50.0,
            unit="Celsius",
            location="Test"
        )
        
        result = sensor.to_dict()
        
        assert result["sensor_id"] == "TEST_01"
        assert result["value"] == 50.0
    
    def test_risk_level_properties(self):
        """Verifica propiedades de RiskLevel."""
        assert RiskLevel.CRITICAL.priority > RiskLevel.HIGH.priority
        assert RiskLevel.HIGH.priority > RiskLevel.MEDIUM.priority
        assert RiskLevel.LOW.emoji == "🟢"
        assert RiskLevel.CRITICAL.emoji == "🔴"
    
    def test_enriched_data_to_dict(self):
        """Verifica serialización de EnrichedData."""
        sensor = SensorData.from_dict({
            "sensor_id": "TEST",
            "timestamp": "2025-12-18T00:00:00",
            "value": 85.0,
            "unit": "C",
            "location": "Test"
        })
        alert = PredictionAlert(failure_probability=0.75, alert_message="Test alert")
        enriched = EnrichedData(
            data_original=sensor,
            risk_level=RiskLevel.HIGH,
            prediction_alert=alert
        )
        
        result = enriched.to_dict()
        
        assert result["risk_level"] == "HIGH"
        assert result["prediction_alert"]["failure_probability"] == 0.75
        assert "data_original" in result


class TestRulesEngine:
    """Tests para el motor de reglas."""
    
    @pytest.fixture
    def engine(self):
        """Fixture que retorna un RulesEngine configurado."""
        engine = RulesEngine()
        engine.set_threshold("temperature", max_temp=60, warning_temp=80, critical_temp=90)
        return engine
    
    def test_evaluate_low_risk(self, engine):
        """Valores normales deben retornar LOW risk."""
        data = SensorData.from_dict({
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T00:00:00",
            "value": 35.0,
            "unit": "Celsius",
            "location": "Test"
        })
        
        risk = engine.evaluate(data)
        
        assert risk == RiskLevel.LOW
    
    def test_evaluate_medium_risk(self, engine):
        """Valores sobre normal_max deben retornar MEDIUM risk."""
        data = SensorData.from_dict({
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T00:00:00",
            "value": 65.0,
            "unit": "Celsius",
            "location": "Test"
        })
        
        risk = engine.evaluate(data)
        
        assert risk == RiskLevel.MEDIUM
    
    def test_evaluate_high_risk(self, engine):
        """Valores sobre warning deben retornar HIGH risk."""
        data = SensorData.from_dict({
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T00:00:00",
            "value": 82.0,
            "unit": "Celsius",
            "location": "Test"
        })
        
        risk = engine.evaluate(data)
        
        assert risk == RiskLevel.HIGH
    
    def test_evaluate_critical_risk(self, engine):
        """Valores sobre critical deben retornar CRITICAL risk."""
        data = SensorData.from_dict({
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T00:00:00",
            "value": 95.0,
            "unit": "Celsius",
            "location": "Test"
        })
        
        risk = engine.evaluate(data)
        
        assert risk == RiskLevel.CRITICAL
    
    def test_custom_threshold(self):
        """Verifica que umbrales personalizados funcionen."""
        engine = RulesEngine()
        engine.set_threshold("temperature", max_temp=50, warning_temp=70, critical_temp=80)
        
        data = SensorData.from_dict({
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T00:00:00",
            "value": 75.0,
            "unit": "Celsius",
            "location": "Test"
        })
        
        risk = engine.evaluate(data)
        
        assert risk == RiskLevel.HIGH  # Entre warning (70) y critical (80)


class TestPredictiveModel:
    """Tests para el modelo predictivo."""
    
    @pytest.fixture
    def model(self):
        """Fixture que retorna un PredictiveModel."""
        return PredictiveModel()
    
    def test_prediction_returns_alert(self, model):
        """Verifica que predict retorne un PredictionAlert."""
        data = SensorData.from_dict({
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T00:00:00",
            "value": 85.0,
            "unit": "Celsius",
            "location": "Test"
        })
        
        result = model.predict(data, RiskLevel.HIGH)
        
        assert isinstance(result, PredictionAlert)
        assert 0.0 <= result.failure_probability <= 1.0
        assert 0.0 <= result.confidence <= 1.0
    
    def test_high_value_high_probability(self, model):
        """Valores altos deben generar mayor probabilidad de fallo."""
        low_data = SensorData.from_dict({
            "sensor_id": "TEST", "timestamp": "2025-12-18T00:00:00",
            "value": 30.0, "unit": "C", "location": "Test"
        })
        high_data = SensorData.from_dict({
            "sensor_id": "TEST", "timestamp": "2025-12-18T00:00:00",
            "value": 92.0, "unit": "C", "location": "Test"
        })
        
        low_result = model.predict(low_data, RiskLevel.LOW)
        high_result = model.predict(high_data, RiskLevel.CRITICAL)
        
        # Probabilidad alta debe ser mayor (con margen por ruido)
        assert high_result.failure_probability > low_result.failure_probability
    
    def test_critical_value_generates_alert(self, model):
        """Valores críticos deben generar alerta."""
        data = SensorData.from_dict({
            "sensor_id": "TEST", "timestamp": "2025-12-18T00:00:00",
            "value": 95.0, "unit": "C", "location": "Test"
        })
        
        result = model.predict(data, RiskLevel.CRITICAL, threshold_critical=90)
        
        # Alta probabilidad de tener alerta en valores críticos
        assert result.failure_probability >= 0.5


class TestIntelligenceService:
    """Tests para el servicio principal."""
    
    @pytest.fixture
    def service(self):
        """Fixture que retorna un IntelligenceService configurado."""
        svc = IntelligenceService()
        svc.configure_threshold("temperature", max_temp=60, warning_temp=80, critical_temp=90)
        return svc
    
    def test_process_returns_enriched_data(self, service):
        """Verifica que process retorne EnrichedData."""
        data = {
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T00:00:00",
            "value": 35.0,
            "unit": "Celsius",
            "location": "Planta-A"
        }
        
        result = service.process(data)
        
        assert isinstance(result, EnrichedData)
        assert result.data_original.sensor_id == "SENSOR_TEMP_01"
        assert isinstance(result.risk_level, RiskLevel)
        assert isinstance(result.prediction_alert, PredictionAlert)
    
    def test_enriched_output_structure(self, service):
        """Verifica estructura de salida JSON."""
        data = {
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T00:00:00",
            "value": 85.0,
            "unit": "Celsius",
            "location": "Planta-A"
        }
        
        result = service.process(data)
        output = result.to_dict()
        
        # Verificar estructura requerida
        assert "data_original" in output
        assert "risk_level" in output
        assert "prediction_alert" in output
        
        # Verificar contenido
        assert output["data_original"]["sensor_id"] == "SENSOR_TEMP_01"
        assert output["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert "failure_probability" in output["prediction_alert"]
    
    def test_batch_processing(self, service):
        """Verifica procesamiento por lotes."""
        data_list = [
            {"sensor_id": "TEST", "timestamp": "2025-12-18T00:00:00", "value": 30.0, "unit": "C", "location": "A"},
            {"sensor_id": "TEST", "timestamp": "2025-12-18T00:00:02", "value": 50.0, "unit": "C", "location": "A"},
            {"sensor_id": "TEST", "timestamp": "2025-12-18T00:00:04", "value": 85.0, "unit": "C", "location": "A"},
        ]
        
        results = service.process_batch(data_list)
        
        assert len(results) == 3
        assert all(isinstance(r, EnrichedData) for r in results)
    
    def test_stats_tracking(self, service):
        """Verifica que las estadísticas se actualicen."""
        data = {"sensor_id": "TEST", "timestamp": "2025-12-18T00:00:00", "value": 50.0, "unit": "C", "location": "A"}
        
        service.process(data)
        service.process(data)
        stats = service.get_stats()
        
        assert stats["processed_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
