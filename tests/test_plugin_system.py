#!/usr/bin/env python3
"""Test del sistema de plugins Layer 1."""
import sys
sys.path.insert(0, '/home/falcon/Documentos/flow-monitor')

from datetime import datetime
from ingestion.models import NormalizedReading, ReadingType
from ingestion.plugins.http_json_plugin import HttpJsonPlugin
from ingestion.registry import PluginRegistry

def test_http_json_plugin():
    """Test del HttpJsonPlugin con payload de DataPulse."""
    plugin = HttpJsonPlugin()
    
    # Payload simulando DataPulse
    payload = {
        "sensor_id": "SENSOR_TEMP_01",
        "timestamp": "2025-12-18T00:53:11",
        "value": 35.5,
        "unit": "Celsius",
        "location": "Planta-A/Horno-Principal",
        "_meta": {
            "status": "NORMAL",
            "is_anomaly": False,
            "step": 42,
            "agent": "DataPulse"
        }
    }
    
    # Validación
    assert plugin.validate(payload), "Payload debería ser válido"
    
    # Normalización
    reading = plugin.normalize_data(payload)
    
    assert reading.sensor_id == "SENSOR_TEMP_01"
    assert reading.value == 35.5
    assert reading.unit == "Celsius"
    assert reading.source == "http-json-plugin"
    assert reading.reading_type == ReadingType.TEMPERATURE
    assert reading.metadata.get("agent") == "DataPulse"
    
    print("✅ HttpJsonPlugin: normalize_data() funciona correctamente")
    print(f"   Normalized: {reading}")
    return reading

def test_plugin_registry():
    """Test del registro de plugins."""
    registry = PluginRegistry()
    registry.clear()  # Limpiar para test
    
    plugin = HttpJsonPlugin()
    registry.register(plugin)
    
    assert "http-json-plugin" in registry
    assert len(registry) == 1
    
    retrieved = registry.get("http-json-plugin")
    assert retrieved.name == "http-json-plugin"
    
    print("✅ PluginRegistry: registro y búsqueda funcionan correctamente")

def test_invalid_payload():
    """Test con payload inválido."""
    plugin = HttpJsonPlugin()
    
    invalid_payloads = [
        {},
        {"sensor_id": "S01"},  # Faltan campos
        {"sensor_id": "S01", "value": "not_a_number", "timestamp": "...", "unit": "C"},
    ]
    
    for payload in invalid_payloads:
        assert not plugin.validate(payload), f"Payload debería ser inválido: {payload}"
    
    print("✅ HttpJsonPlugin: validación de payloads inválidos funciona")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 Testing Flow-Monitor Layer 1 Plugin System")
    print("="*60 + "\n")
    
    test_http_json_plugin()
    test_plugin_registry()
    test_invalid_payload()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60 + "\n")
