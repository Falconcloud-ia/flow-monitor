"""
Modelos de datos para Intelligence Core.
Define las estructuras de entrada, salida y estados intermedios.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class RiskLevel(Enum):
    """Niveles de riesgo evaluados por el motor de reglas."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    
    @property
    def emoji(self) -> str:
        """Retorna emoji representativo del nivel."""
        emojis = {
            "LOW": "🟢",
            "MEDIUM": "🟡", 
            "HIGH": "🟠",
            "CRITICAL": "🔴"
        }
        return emojis.get(self.value, "⚪")
    
    @property
    def priority(self) -> int:
        """Retorna prioridad numérica (mayor = más urgente)."""
        priorities = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        return priorities.get(self.value, 0)


@dataclass
class SensorData:
    """
    Datos normalizados de un sensor (entrada desde Capa 1).
    Compatible con el formato generado por DataPulse Agent.
    """
    sensor_id: str
    timestamp: str
    value: float
    unit: str
    location: str
    meta: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SensorData":
        """Crea una instancia desde un diccionario (payload de Capa 1)."""
        return cls(
            sensor_id=data.get("sensor_id", "UNKNOWN"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            value=float(data.get("value", 0.0)),
            unit=data.get("unit", ""),
            location=data.get("location", ""),
            meta=data.get("_meta")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        result = {
            "sensor_id": self.sensor_id,
            "timestamp": self.timestamp,
            "value": self.value,
            "unit": self.unit,
            "location": self.location
        }
        if self.meta:
            result["_meta"] = self.meta
        return result


@dataclass
class PredictionAlert:
    """
    Resultado del modelo predictivo.
    Contiene probabilidad de fallo y recomendaciones.
    """
    failure_probability: float
    alert_message: Optional[str] = None
    recommended_action: Optional[str] = None
    predicted_time_to_failure: Optional[str] = None
    confidence: float = 0.0
    
    @property
    def has_alert(self) -> bool:
        """Indica si hay una alerta activa."""
        return self.alert_message is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "failure_probability": round(self.failure_probability, 3),
            "alert_message": self.alert_message,
            "recommended_action": self.recommended_action,
            "predicted_time_to_failure": self.predicted_time_to_failure,
            "confidence": round(self.confidence, 3)
        }


@dataclass
class EnrichedData:
    """
    Datos enriquecidos de salida de Intelligence Core.
    Combina datos originales con análisis de riesgo y predicciones.
    """
    data_original: SensorData
    risk_level: RiskLevel
    prediction_alert: PredictionAlert
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización JSON."""
        return {
            "data_original": self.data_original.to_dict(),
            "risk_level": self.risk_level.value,
            "prediction_alert": self.prediction_alert.to_dict(),
            "processed_at": self.processed_at
        }
    
    def __str__(self) -> str:
        """Representación legible del dato enriquecido."""
        prob = self.prediction_alert.failure_probability
        return (
            f"{self.risk_level.emoji} [{self.data_original.sensor_id}] "
            f"Valor: {self.data_original.value}{self.data_original.unit} | "
            f"Riesgo: {self.risk_level.value} | "
            f"Prob. Fallo: {prob:.1%}"
        )
