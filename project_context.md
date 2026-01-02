# Project Name: Flow-Monitor (MVP Semilla Inicia)

## Misión del Producto
Flow-Monitor es un SaaS de monitoreo industrial inteligente diseñado para el sector industrial. Permite la ingesta de datos de sensores en tiempo real, aplica reglas de negocio y predicciones mediante IA para detectar anomalías, y notifica a los tomadores de decisiones a través de canales omnicanal (WhatsApp, Email) para evitar pérdidas operativas.


## Componente Externo: Data Dump (Simulador)
- Una app independiente (Python script) que genera datos "dummy".
- Simula comportamiento de sensores industriales (vibración, temperatura, flujo).
- Inyecta anomalías programadas para probar el sistema.


## Arquitectura del Sistema (3 Capas)

### Capa 1: Ingesta & Adaptadores (The Universal Plugin Layer)
- **Objetivo:** Abstraer la fuente de datos.
- **Componente Clave:** Sistema de Plugins/Drivers.
- **Función:** Recibe datos crudos (JSON, MQTT, Modbus, etc.) y los **normaliza** a un formato estándar interno antes de pasarlos a la Capa 2.

- **Para la Demo:** Se desarrollará un "HTTP-JSON Plugin" específico para recibir los datos del Data Dump.

### Capa 2: Lógica de Negocio & IA (The Intelligence Core)
- **Objetivo:** Procesar el dato normalizado.
- **Motor de Reglas:** Configuración por cliente (ej: "Si temperatura > 90 por 5 min").
- **IA/Predicción:** Modelo (simulado para MVP) que analiza tendencias de la data entrante.
- **Salida:** Determina el "Nivel de Riesgo" (Bajo, Medio, Crítico) y enriquece la data con metadata de predicción.
- **Orquestador de Eventos:** Si se rompe una regla o la IA predice fallo, dispara un evento de alerta.




### Capa 3: Visualización & Notificación (The Action Layer)
- **Dashboard:** Interfaz (Lovable/React) que muestra KPIs y estado en tiempo real.
- **Dispatcher de Notificaciones:** Según el Nivel de Riesgo determinado en la Capa 2, decide el canal (Whatsapp, Email) y envía la alerta.

### Capa 3: Dashboard & Notificaciones (The Value)
- **Objetivo:** Consumir el resultado de la Capa 2.
- **Frontend:** Dashboard o Visualización en tiempo real. Gráficos de línea para temperatura y marcadores de anomalías que muestra KPIs y estado en tiempo real.
- **Omnicanalidad:** Integración con APIs de mensajería (Twilio/Meta API para WhatsApp, SendGrid/SMTP para Email).
- **UX:** El usuario debe ver la alerta en el dashboard y recibirla en su celular simultáneamente.

## Escenario de la Demo (Happy Path)
1. El "Robot Simulador" comienza a enviar datos de temperatura normal (20-40°C).
2. El Dashboard muestra la curva estable en tiempo real.
3. El Robot inyecta una anomalía (subida rápida a 95°C).
4. El sistema detecta el umbral crítico Y la IA marca "Predicción de Fuego".
5. El Dashboard parpadea en rojo.
6. Se envía un WhatsApp al usuario simulado: "ALERTA CRÍTICA: Sensor B sobrecalentado".

## Stack Sugerido
- Lenguaje Backend: Python (ideal para manejo de datos e IA).
- Comunicación entre capas: Colas (RabbitMQ/Redis) o HTTP interno (para MVP rápido).