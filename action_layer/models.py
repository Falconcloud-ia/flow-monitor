"""
Modelos de datos para Action Layer (Capa 3).
Define estructuras para Dashboard, Notificaciones y Estadísticas.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import uuid


class NotificationChannel(Enum):
    """Canales de notificación disponibles."""
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
    DASHBOARD = "dashboard"


class AlertStatus(Enum):
    """Estado de una alerta enviada."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass
class DashboardReading:
    """
    Lectura formateada para el Dashboard React.
    Estructura JSON final que consume el frontend.
    """
    id: str
    sensor_id: str
    timestamp: str
    value: float
    unit: str
    location: str
    risk_level: str
    risk_emoji: str
    prediction: Dict[str, Any]
    processed_at: str
    
    @classmethod
    def from_enriched_data(cls, enriched_data: Dict[str, Any]) -> "DashboardReading":
        """Crea una lectura de Dashboard desde EnrichedData de Capa 2."""
        data_original = enriched_data.get("data_original", {})
        prediction_alert = enriched_data.get("prediction_alert", {})
        risk_level = enriched_data.get("risk_level", "LOW")
        
        # Mapeo de emojis por nivel de riesgo
        emoji_map = {
            "LOW": "🟢",
            "MEDIUM": "🟡",
            "HIGH": "🟠",
            "CRITICAL": "🔴"
        }
        
        return cls(
            id=str(uuid.uuid4()),
            sensor_id=data_original.get("sensor_id", "UNKNOWN"),
            timestamp=data_original.get("timestamp", datetime.now().isoformat()),
            value=data_original.get("value", 0.0),
            unit=data_original.get("unit", ""),
            location=data_original.get("location", ""),
            risk_level=risk_level,
            risk_emoji=emoji_map.get(risk_level, "⚪"),
            prediction={
                "failure_probability": prediction_alert.get("failure_probability", 0.0),
                "alert_message": prediction_alert.get("alert_message"),
                "recommended_action": prediction_alert.get("recommended_action"),
                "time_to_failure": prediction_alert.get("predicted_time_to_failure")
            },
            processed_at=enriched_data.get("processed_at", datetime.now().isoformat())
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización JSON."""
        return {
            "id": self.id,
            "sensor_id": self.sensor_id,
            "timestamp": self.timestamp,
            "value": self.value,
            "unit": self.unit,
            "location": self.location,
            "risk_level": self.risk_level,
            "risk_emoji": self.risk_emoji,
            "prediction": self.prediction,
            "processed_at": self.processed_at
        }


@dataclass
class AlertNotification:
    """
    Notificación de alerta enviada.
    Registra el envío de alertas por diferentes canales.
    """
    id: str
    timestamp: str
    sensor_id: str
    risk_level: str
    message: str
    channel: NotificationChannel
    status: AlertStatus
    recipient: Optional[str] = None
    error_message: Optional[str] = None
    
    @classmethod
    def create(
        cls,
        sensor_id: str,
        risk_level: str,
        message: str,
        channel: NotificationChannel,
        recipient: Optional[str] = None
    ) -> "AlertNotification":
        """Factory method para crear una nueva notificación."""
        return cls(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            sensor_id=sensor_id,
            risk_level=risk_level,
            message=message,
            channel=channel,
            status=AlertStatus.PENDING,
            recipient=recipient
        )
    
    def mark_sent(self) -> None:
        """Marca la notificación como enviada."""
        self.status = AlertStatus.SENT
    
    def mark_failed(self, error: str) -> None:
        """Marca la notificación como fallida."""
        self.status = AlertStatus.FAILED
        self.error_message = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización JSON."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "sensor_id": self.sensor_id,
            "risk_level": self.risk_level,
            "message": self.message,
            "channel": self.channel.value,
            "status": self.status.value,
            "recipient": self.recipient,
            "error_message": self.error_message
        }


@dataclass
class DashboardStats:
    """
    Estadísticas agregadas para el Dashboard.
    Proporciona KPIs y métricas en tiempo real.
    """
    total_readings: int = 0
    readings_by_risk: Dict[str, int] = field(default_factory=lambda: {
        "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0
    })
    alerts_sent: int = 0
    alerts_by_channel: Dict[str, int] = field(default_factory=lambda: {
        "whatsapp": 0, "email": 0, "sms": 0
    })
    last_update: str = field(default_factory=lambda: datetime.now().isoformat())
    uptime_seconds: float = 0.0
    
    def update_reading(self, risk_level: str) -> None:
        """Actualiza estadísticas con una nueva lectura."""
        self.total_readings += 1
        if risk_level in self.readings_by_risk:
            self.readings_by_risk[risk_level] += 1
        self.last_update = datetime.now().isoformat()
    
    def update_alert(self, channel: str) -> None:
        """Actualiza estadísticas con una nueva alerta enviada."""
        self.alerts_sent += 1
        if channel in self.alerts_by_channel:
            self.alerts_by_channel[channel] += 1
        self.last_update = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización JSON."""
        return {
            "total_readings": self.total_readings,
            "readings_by_risk": self.readings_by_risk.copy(),
            "alerts_sent": self.alerts_sent,
            "alerts_by_channel": self.alerts_by_channel.copy(),
            "last_update": self.last_update,
            "uptime_seconds": self.uptime_seconds
        }
