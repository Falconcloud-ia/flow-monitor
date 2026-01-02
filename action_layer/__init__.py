"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🎯 Action Layer - Flow-Monitor                            ║
║                      Layer 3: Frontend & Notificator                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Capa de Visualización y Notificación del sistema Flow-Monitor.
Consume datos enriquecidos de la Capa 2 (Intelligence Core) y:
- Los presenta en un Dashboard en tiempo real
- Envía notificaciones según el nivel de riesgo (WhatsApp, Email)

Components:
    - NotificationDispatcher: Gestiona envío de alertas omnicanal
    - DataObserver: Observa y distribuye datos procesados
    - DashboardAPI: Endpoints para el frontend React

Author: Flow-Monitor Team
Project: Flow-Monitor (MVP Semilla Inicia)
"""

from .models import (
    DashboardReading,
    AlertNotification,
    DashboardStats,
    NotificationChannel,
    AlertStatus
)
from .notification_dispatcher import NotificationDispatcher
from .data_observer import DataObserver

__all__ = [
    "DashboardReading",
    "AlertNotification", 
    "DashboardStats",
    "NotificationChannel",
    "AlertStatus",
    "NotificationDispatcher",
    "DataObserver",
]

__version__ = "1.0.0"
