"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                 📢 Notification Dispatcher - Flow-Monitor                    ║
║                    Layer 3: Omnichannel Alert System                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Despacha notificaciones según el nivel de riesgo detectado.
Soporta múltiples canales: WhatsApp (Twilio), Email, SMS.

Para el MVP, simula el envío con prints en consola.
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import json

from .models import AlertNotification, NotificationChannel, AlertStatus


class TwilioMock:
    """
    Mock de la API de Twilio para WhatsApp.
    En producción, esto usaría twilio.rest.Client.
    """
    
    def __init__(self, account_sid: str = "MOCK_SID", auth_token: str = "MOCK_TOKEN"):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.messages_sent: List[Dict[str, Any]] = []
    
    def send_whatsapp(self, to: str, message: str) -> Dict[str, Any]:
        """
        Simula envío de mensaje WhatsApp.
        
        En producción:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=message,
                from_='whatsapp:+14155238886',
                to=f'whatsapp:{to}'
            )
        """
        result = {
            "sid": f"SM{datetime.now().strftime('%Y%m%d%H%M%S')}MOCK",
            "to": to,
            "body": message,
            "status": "sent",
            "timestamp": datetime.now().isoformat()
        }
        self.messages_sent.append(result)
        
        # ╔═══════════════════════════════════════════════════════════════════╗
        # ║                    📱 TWILIO WHATSAPP MOCK                        ║
        # ╚═══════════════════════════════════════════════════════════════════╝
        print("\n" + "═" * 70)
        print("📱 [TWILIO MOCK] ENVIANDO WHATSAPP")
        print("═" * 70)
        print(f"   📞 Para: {to}")
        print(f"   📝 Mensaje: {message}")
        print(f"   ✅ Status: {result['status']}")
        print(f"   🆔 SID: {result['sid']}")
        print("═" * 70 + "\n")
        
        return result


class EmailMock:
    """
    Mock de servicio de Email (SendGrid/SMTP).
    """
    
    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Simula envío de email."""
        result = {
            "message_id": f"EMAIL{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "to": to,
            "subject": subject,
            "status": "sent",
            "timestamp": datetime.now().isoformat()
        }
        
        print("\n" + "─" * 70)
        print("📧 [EMAIL MOCK] ENVIANDO EMAIL")
        print("─" * 70)
        print(f"   📬 Para: {to}")
        print(f"   📋 Asunto: {subject}")
        print(f"   📝 Cuerpo: {body[:100]}...")
        print("─" * 70 + "\n")
        
        return result


class NotificationDispatcher:
    """
    🔔 Dispatcher de Notificaciones - Capa 3
    
    Evalúa el nivel de riesgo y envía notificaciones por el canal apropiado:
    - CRITICAL → WhatsApp (inmediato) + Email
    - HIGH → Email
    - MEDIUM/LOW → Solo Dashboard (sin notificación externa)
    
    Ejemplo:
        dispatcher = NotificationDispatcher()
        dispatcher.configure_recipient("+56912345678", "operador@empresa.cl")
        
        notification = dispatcher.dispatch(enriched_data)
        if notification:
            print(f"Alerta enviada: {notification.message}")
    """
    
    def __init__(
        self,
        whatsapp_recipient: str = "+56900000000",
        email_recipient: str = "alerts@flowmonitor.demo"
    ):
        self.whatsapp_recipient = whatsapp_recipient
        self.email_recipient = email_recipient
        
        # Servicios mock
        self._twilio = TwilioMock()
        self._email = EmailMock()
        
        # Historial de notificaciones
        self._notifications: List[AlertNotification] = []
        self._notification_callbacks: List[Callable[[AlertNotification], None]] = []
        
        # Estadísticas
        self._stats = {
            "whatsapp_sent": 0,
            "email_sent": 0,
            "total_dispatched": 0
        }
    
    def configure_recipient(self, whatsapp: str, email: str) -> None:
        """Configura los destinatarios de las notificaciones."""
        self.whatsapp_recipient = whatsapp
        self.email_recipient = email
    
    def add_callback(self, callback: Callable[[AlertNotification], None]) -> None:
        """Agrega un callback para cuando se envíe una notificación."""
        self._notification_callbacks.append(callback)
    
    def dispatch(self, enriched_data: Dict[str, Any]) -> Optional[AlertNotification]:
        """
        Evalúa el nivel de riesgo y despacha notificaciones apropiadas.
        
        Args:
            enriched_data: Datos enriquecidos de Capa 2 (formato dict)
            
        Returns:
            AlertNotification si se envió una alerta, None si no
        """
        risk_level = enriched_data.get("risk_level", "LOW")
        data_original = enriched_data.get("data_original", {})
        prediction = enriched_data.get("prediction_alert", {})
        
        sensor_id = data_original.get("sensor_id", "UNKNOWN")
        value = data_original.get("value", 0)
        unit = data_original.get("unit", "")
        location = data_original.get("location", "")
        
        notification = None
        
        if risk_level == "CRITICAL":
            notification = self._dispatch_critical(
                sensor_id=sensor_id,
                value=value,
                unit=unit,
                location=location,
                prediction=prediction
            )
        elif risk_level == "HIGH":
            notification = self._dispatch_high(
                sensor_id=sensor_id,
                value=value,
                unit=unit,
                location=location,
                prediction=prediction
            )
        
        if notification:
            self._notifications.append(notification)
            self._stats["total_dispatched"] += 1
            
            # Ejecutar callbacks
            for callback in self._notification_callbacks:
                try:
                    callback(notification)
                except Exception as e:
                    print(f"Error en callback: {e}")
        
        return notification
    
    def _dispatch_critical(
        self,
        sensor_id: str,
        value: float,
        unit: str,
        location: str,
        prediction: Dict[str, Any]
    ) -> AlertNotification:
        """Despacha alerta CRÍTICA via WhatsApp + Email."""
        
        # Construir mensaje de emergencia
        prob = prediction.get("failure_probability", 0) * 100
        alert_msg = prediction.get("alert_message", "Anomalía crítica detectada")
        action = prediction.get("recommended_action", "Verificar inmediatamente")
        
        whatsapp_message = (
            f"🔴 ALERTA CRÍTICA - Flow-Monitor\n\n"
            f"📍 Sensor: {sensor_id}\n"
            f"📊 Valor: {value}{unit}\n"
            f"📌 Ubicación: {location}\n"
            f"⚠️ {alert_msg}\n"
            f"🎯 Prob. Fallo: {prob:.1f}%\n\n"
            f"💡 Acción: {action}"
        )
        
        # Enviar WhatsApp
        self._twilio.send_whatsapp(self.whatsapp_recipient, whatsapp_message)
        self._stats["whatsapp_sent"] += 1
        
        # También enviar email
        email_subject = f"🔴 ALERTA CRÍTICA: {sensor_id} - {value}{unit}"
        self._email.send_email(self.email_recipient, email_subject, whatsapp_message)
        self._stats["email_sent"] += 1
        
        # Crear registro de notificación
        notification = AlertNotification.create(
            sensor_id=sensor_id,
            risk_level="CRITICAL",
            message=whatsapp_message,
            channel=NotificationChannel.WHATSAPP,
            recipient=self.whatsapp_recipient
        )
        notification.mark_sent()
        
        return notification
    
    def _dispatch_high(
        self,
        sensor_id: str,
        value: float,
        unit: str,
        location: str,
        prediction: Dict[str, Any]
    ) -> AlertNotification:
        """Despacha alerta HIGH via Email."""
        
        prob = prediction.get("failure_probability", 0) * 100
        alert_msg = prediction.get("alert_message", "Nivel de riesgo elevado")
        action = prediction.get("recommended_action", "Monitorear de cerca")
        
        email_message = (
            f"🟠 ALERTA ALTA - Flow-Monitor\n\n"
            f"Sensor: {sensor_id}\n"
            f"Valor: {value}{unit}\n"
            f"Ubicación: {location}\n"
            f"Mensaje: {alert_msg}\n"
            f"Probabilidad de Fallo: {prob:.1f}%\n\n"
            f"Acción Recomendada: {action}"
        )
        
        email_subject = f"🟠 Alerta Alta: {sensor_id} - {value}{unit}"
        self._email.send_email(self.email_recipient, email_subject, email_message)
        self._stats["email_sent"] += 1
        
        notification = AlertNotification.create(
            sensor_id=sensor_id,
            risk_level="HIGH",
            message=email_message,
            channel=NotificationChannel.EMAIL,
            recipient=self.email_recipient
        )
        notification.mark_sent()
        
        return notification
    
    def get_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna las últimas notificaciones enviadas."""
        return [n.to_dict() for n in self._notifications[-limit:]]
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del dispatcher."""
        return {
            **self._stats,
            "twilio_messages": len(self._twilio.messages_sent)
        }
    
    def clear_history(self) -> None:
        """Limpia el historial de notificaciones."""
        self._notifications.clear()
        self._twilio.messages_sent.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                 📢 Notification Dispatcher Demo                              ║
║                    Layer 3 - Flow-Monitor                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    dispatcher = NotificationDispatcher(
        whatsapp_recipient="+56912345678",
        email_recipient="operador@planta.cl"
    )
    
    # Simular datos enriquecidos de Capa 2
    test_data_critical = {
        "data_original": {
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T01:00:00",
            "value": 95.0,
            "unit": "°C",
            "location": "Planta-A/Horno-1"
        },
        "risk_level": "CRITICAL",
        "prediction_alert": {
            "failure_probability": 0.85,
            "alert_message": "🔥 Predicción de Fuego Inminente",
            "recommended_action": "Detener operación y activar enfriamiento de emergencia",
            "predicted_time_to_failure": "~5 minutos"
        },
        "processed_at": "2025-12-18T01:00:01"
    }
    
    test_data_high = {
        "data_original": {
            "sensor_id": "SENSOR_TEMP_02",
            "value": 78.0,
            "unit": "°C",
            "location": "Planta-B/Motor-3"
        },
        "risk_level": "HIGH",
        "prediction_alert": {
            "failure_probability": 0.55,
            "alert_message": "Temperatura elevada",
            "recommended_action": "Revisar sistema de enfriamiento"
        }
    }
    
    test_data_low = {
        "data_original": {
            "sensor_id": "SENSOR_TEMP_03",
            "value": 35.0,
            "unit": "°C",
            "location": "Planta-A/Bomba-1"
        },
        "risk_level": "LOW",
        "prediction_alert": {
            "failure_probability": 0.05
        }
    }
    
    print("📊 Procesando alertas...\n")
    
    # Dispatch de diferentes niveles
    print("1️⃣  Despachando alerta CRITICAL:")
    result1 = dispatcher.dispatch(test_data_critical)
    
    print("\n2️⃣  Despachando alerta HIGH:")
    result2 = dispatcher.dispatch(test_data_high)
    
    print("\n3️⃣  Despachando alerta LOW (sin notificación externa):")
    result3 = dispatcher.dispatch(test_data_low)
    print("   → Sin notificación externa (solo Dashboard)\n")
    
    # Mostrar estadísticas
    print("═" * 70)
    print("📈 ESTADÍSTICAS:")
    stats = dispatcher.get_stats()
    print(f"   ├─ WhatsApp enviados: {stats['whatsapp_sent']}")
    print(f"   ├─ Emails enviados: {stats['email_sent']}")
    print(f"   └─ Total despachados: {stats['total_dispatched']}")
    
    print("\n✅ Demo completada.")
