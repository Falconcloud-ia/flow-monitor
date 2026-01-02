"""
Servicio principal de Intelligence Core.
Orquesta el procesamiento de datos de sensores.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from .models import SensorData, RiskLevel, PredictionAlert, EnrichedData
from .rules_engine import RulesEngine
from .predictive_model import PredictiveModel
from .config import IntelligenceConfig, config as default_config


class IntelligenceService:
    """
    🧠 Intelligence Service - Orquestador principal de Capa 2.
    
    Coordina el flujo de procesamiento:
    1. Recibe datos normalizados de Capa 1
    2. Evalúa reglas de negocio (RulesEngine)
    3. Genera predicciones (PredictiveModel)
    4. Retorna datos enriquecidos para Capa 3
    
    Ejemplo:
        service = IntelligenceService()
        service.configure_threshold("temperature", max_temp=80)
        
        enriched = service.process(sensor_data_dict)
        print(enriched.to_dict())
    """
    
    def __init__(self, config: Optional[IntelligenceConfig] = None):
        self.config = config or default_config
        self.rules_engine = RulesEngine(self.config)
        self.predictive_model = PredictiveModel(self.config)
        
        # Estadísticas
        self._processed_count = 0
        self._alerts_generated = 0
        self._risk_counts: Dict[str, int] = {level.value: 0 for level in RiskLevel}
        self._start_time = datetime.now()
    
    def configure_threshold(
        self,
        sensor_type: str,
        max_temp: Optional[float] = None,
        warning_temp: Optional[float] = None,
        critical_temp: Optional[float] = None,
        **kwargs
    ) -> None:
        """
        Configura umbrales personalizados para un tipo de sensor.
        
        Args:
            sensor_type: Tipo de sensor (ej: "temperature")
            max_temp: Umbral máximo normal
            warning_temp: Umbral de advertencia
            critical_temp: Umbral crítico
        """
        self.rules_engine.set_threshold(
            sensor_type,
            max_temp=max_temp,
            warning_temp=warning_temp,
            critical_temp=critical_temp,
            **kwargs
        )
    
    def process(self, data: Dict[str, Any]) -> EnrichedData:
        """
        Procesa datos de sensor y retorna datos enriquecidos.
        
        Args:
            data: Diccionario con datos del sensor (formato Capa 1)
            
        Returns:
            EnrichedData con análisis de riesgo y predicciones
        """
        # Convertir a modelo tipado
        sensor_data = SensorData.from_dict(data)
        
        # Evaluar reglas
        risk_level = self.rules_engine.evaluate(sensor_data)
        
        # Obtener umbrales para el modelo predictivo
        threshold_info = self.rules_engine.get_threshold_status(sensor_data)
        threshold_critical = threshold_info["thresholds"]["critical"]
        threshold_warning = threshold_info["thresholds"]["warning"]
        
        # Generar predicción
        prediction = self.predictive_model.predict(
            sensor_data,
            risk_level,
            threshold_critical=threshold_critical,
            threshold_warning=threshold_warning
        )
        
        # Actualizar estadísticas
        self._processed_count += 1
        self._risk_counts[risk_level.value] += 1
        if prediction.has_alert:
            self._alerts_generated += 1
        
        # Construir y retornar resultado enriquecido
        return EnrichedData(
            data_original=sensor_data,
            risk_level=risk_level,
            prediction_alert=prediction
        )
    
    def process_batch(self, data_list: List[Dict[str, Any]]) -> List[EnrichedData]:
        """
        Procesa múltiples lecturas de sensor.
        
        Args:
            data_list: Lista de diccionarios con datos de sensores
            
        Returns:
            Lista de EnrichedData
        """
        return [self.process(data) for data in data_list]
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del servicio."""
        runtime = datetime.now() - self._start_time
        
        return {
            "processed_count": self._processed_count,
            "alerts_generated": self._alerts_generated,
            "alert_rate": self._alerts_generated / self._processed_count if self._processed_count > 0 else 0,
            "risk_distribution": self._risk_counts.copy(),
            "runtime_seconds": runtime.total_seconds(),
            "model_stats": self.predictive_model.get_stats()
        }
    
    def reset_stats(self) -> None:
        """Reinicia estadísticas y modelo."""
        self._processed_count = 0
        self._alerts_generated = 0
        self._risk_counts = {level.value: 0 for level in RiskLevel}
        self._start_time = datetime.now()
        self.predictive_model.reset_history()


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO / CLI
# ═══════════════════════════════════════════════════════════════════════════════

def demo():
    """Ejecuta una demostración del Intelligence Service."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     🧠 Intelligence Core Demo 🧠                              ║
║                        Layer 2 - Flow-Monitor                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Crear servicio con umbral personalizado
    service = IntelligenceService()
    service.configure_threshold("temperature", max_temp=60, warning_temp=80, critical_temp=90)
    
    # Datos de prueba simulando lecturas de DataPulse
    test_readings = [
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:00", "value": 35.0, "unit": "Celsius", "location": "Planta-A/Horno-1"},
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:02", "value": 45.0, "unit": "Celsius", "location": "Planta-A/Horno-1"},
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:04", "value": 65.0, "unit": "Celsius", "location": "Planta-A/Horno-1"},
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:06", "value": 82.0, "unit": "Celsius", "location": "Planta-A/Horno-1"},
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:08", "value": 95.0, "unit": "Celsius", "location": "Planta-A/Horno-1"},
    ]
    
    print("📊 Procesando lecturas de sensor...\n")
    print("─" * 80)
    
    for reading in test_readings:
        result = service.process(reading)
        print(result)
        
        if result.prediction_alert.has_alert:
            print(f"   └─ 📢 {result.prediction_alert.alert_message}")
            print(f"   └─ 💡 {result.prediction_alert.recommended_action}")
        
        print()
    
    print("─" * 80)
    print("\n📈 ESTADÍSTICAS:")
    stats = service.get_stats()
    print(f"   ├─ Lecturas procesadas: {stats['processed_count']}")
    print(f"   ├─ Alertas generadas: {stats['alerts_generated']}")
    print(f"   ├─ Tasa de alertas: {stats['alert_rate']:.1%}")
    print(f"   └─ Distribución de riesgo: {stats['risk_distribution']}")
    
    print("\n✅ Demo completada.")
    
    # Retornar último resultado como ejemplo
    return result.to_dict()


if __name__ == "__main__":
    import json
    result = demo()
    print("\n📦 Ejemplo de salida JSON:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
