"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  👁️ Data Observer - Flow-Monitor                             ║
║                 Layer 3: Real-time Data Distribution                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Observa y distribuye datos procesados de Capa 2.
Implementa el patrón Observer para notificar múltiples suscriptores.
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from collections import deque
import threading
import asyncio


from .models import DashboardReading, DashboardStats, AlertNotification
from .notification_dispatcher import NotificationDispatcher


class DataObserver:
    """
    👁️ Data Observer - Gestiona flujo de datos para Dashboard
    
    Recibe datos enriquecidos de Capa 2 y:
    - Los transforma a formato Dashboard
    - Almacena en buffer circular
    - Dispara NotificationDispatcher para alertas
    - Notifica a suscriptores (SSE, WebSocket)
    
    Ejemplo:
        observer = DataObserver()
        observer.add_subscriber(mi_callback)
        
        # Cuando llega data de Capa 2:
        observer.process(enriched_data)
    """
    
    def __init__(
        self,
        max_buffer_size: int = 500,
        notification_dispatcher: Optional[NotificationDispatcher] = None
    ):
        self.max_buffer_size = max_buffer_size
        
        # Buffer circular de lecturas
        self._readings: deque = deque(maxlen=max_buffer_size)
        
        # Alertas generadas
        self._alerts: List[AlertNotification] = []
        
        # Estadísticas
        self._stats = DashboardStats()
        self._start_time = datetime.now()
        
        # Dispatcher de notificaciones
        self._dispatcher = notification_dispatcher or NotificationDispatcher()
        
        # Suscriptores (callbacks para SSE/WebSocket)
        self._subscribers: List[Callable[[DashboardReading], None]] = []
        self._alert_subscribers: List[Callable[[AlertNotification], None]] = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Cola para streaming async
        self._event_queue: asyncio.Queue = None
    
    def process(self, enriched_data: Dict[str, Any]) -> DashboardReading:
        """
        Procesa datos enriquecidos de Capa 2.
        
        Args:
            enriched_data: Diccionario con estructura EnrichedData de Capa 2
            
        Returns:
            DashboardReading formateado para el frontend
        """
        with self._lock:
            # Transformar a formato Dashboard
            reading = DashboardReading.from_enriched_data(enriched_data)
            
            # Guardar en buffer
            self._readings.append(reading)
            
            # Actualizar estadísticas
            self._stats.update_reading(reading.risk_level)
            self._stats.uptime_seconds = (datetime.now() - self._start_time).total_seconds()
            
            # Despachar notificación si es necesario
            notification = self._dispatcher.dispatch(enriched_data)
            if notification:
                self._alerts.append(notification)
                self._stats.update_alert(notification.channel.value)
                
                # Notificar suscriptores de alertas
                for callback in self._alert_subscribers:
                    try:
                        callback(notification)
                    except Exception as e:
                        print(f"Error en alert callback: {e}")
            
            # Notificar suscriptores de datos
            for callback in self._subscribers:
                try:
                    callback(reading)
                except Exception as e:
                    print(f"Error en subscriber callback: {e}")
            
            # Agregar a cola de eventos async si existe
            if self._event_queue:
                try:
                    self._event_queue.put_nowait(reading)
                except asyncio.QueueFull:
                    pass  # Descartar si la cola está llena
            
            return reading
    
    def add_subscriber(self, callback: Callable[[DashboardReading], None]) -> None:
        """Agrega un suscriptor para nuevas lecturas."""
        self._subscribers.append(callback)
    
    def add_alert_subscriber(self, callback: Callable[[AlertNotification], None]) -> None:
        """Agrega un suscriptor para alertas."""
        self._alert_subscribers.append(callback)
    
    def remove_subscriber(self, callback: Callable) -> None:
        """Remueve un suscriptor."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
        if callback in self._alert_subscribers:
            self._alert_subscribers.remove(callback)
    
    def get_readings(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene las últimas lecturas del buffer.
        
        Args:
            limit: Número máximo de lecturas a retornar
            
        Returns:
            Lista de lecturas en formato diccionario
        """
        with self._lock:
            readings_list = list(self._readings)
            return [r.to_dict() for r in readings_list[-limit:]]
    
    def get_readings_by_risk(self, risk_level: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene lecturas filtradas por nivel de riesgo.
        
        Args:
            risk_level: Nivel de riesgo a filtrar (LOW, MEDIUM, HIGH, CRITICAL)
            limit: Número máximo de lecturas
            
        Returns:
            Lista de lecturas filtradas
        """
        with self._lock:
            filtered = [r for r in self._readings if r.risk_level == risk_level]
            return [r.to_dict() for r in filtered[-limit:]]
    
    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene las últimas alertas generadas."""
        with self._lock:
            return [a.to_dict() for a in self._alerts[-limit:]]
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas actuales."""
        with self._lock:
            self._stats.uptime_seconds = (datetime.now() - self._start_time).total_seconds()
            return self._stats.to_dict()
    
    def get_dashboard_data(self, readings_limit: int = 100, alerts_limit: int = 20) -> Dict[str, Any]:
        """
        Obtiene estructura completa de datos para el Dashboard.
        
        Returns:
            Diccionario con readings, alerts y stats
        """
        return {
            "readings": self.get_readings(readings_limit),
            "alerts": self.get_alerts(alerts_limit),
            "stats": self.get_stats()
        }
    
    def create_event_queue(self) -> asyncio.Queue:
        """Crea una cola de eventos para streaming async (SSE)."""
        self._event_queue = asyncio.Queue(maxsize=100)
        return self._event_queue
    
    def clear(self) -> None:
        """Limpia todos los datos."""
        with self._lock:
            self._readings.clear()
            self._alerts.clear()
            self._stats = DashboardStats()
            self._start_time = datetime.now()
            self._dispatcher.clear_history()


# Instancia global singleton para compartir entre módulos
_global_observer: Optional[DataObserver] = None


def get_observer() -> DataObserver:
    """Obtiene la instancia global del DataObserver."""
    global _global_observer
    if _global_observer is None:
        _global_observer = DataObserver()
    return _global_observer


def reset_observer() -> None:
    """Reinicia la instancia global."""
    global _global_observer
    _global_observer = None
