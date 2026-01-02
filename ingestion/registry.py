#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   📦 Plugin Registry - Flow-Monitor                          ║
║                     Layer 1: Dynamic Plugin Discovery                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Sistema de registro de plugins para descubrimiento dinámico.
Permite registrar, listar y obtener plugins por nombre.

Author: Flow-Monitor Team
Project: Flow-Monitor (MVP Semilla Inicia)
"""

from typing import Dict, List, Optional, Type

from ingestion.plugins.base import SensorPlugin


class PluginNotFoundError(Exception):
    """Excepción cuando no se encuentra un plugin."""
    pass


class PluginRegistry:
    """
    📦 Registro central de plugins de sensores.
    
    Patrón Singleton que mantiene un registro de todos los plugins
    disponibles para la ingesta de datos.
    
    Example:
        >>> registry = PluginRegistry()
        >>> registry.register(HttpJsonPlugin())
        >>> plugin = registry.get("http-json-plugin")
        >>> reading = plugin.normalize_data(raw_data)
    """
    
    _instance: Optional["PluginRegistry"] = None
    _plugins: Dict[str, SensorPlugin]
    
    def __new__(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = {}
        return cls._instance
    
    def register(self, plugin: SensorPlugin) -> None:
        """
        Registra un plugin en el registro.
        
        Args:
            plugin: Instancia del plugin a registrar
            
        Raises:
            ValueError: Si el plugin ya está registrado
        """
        name = plugin.name
        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' is already registered")
        
        self._plugins[name] = plugin
        print(f"📦 Plugin registrado: {plugin}")
    
    def unregister(self, name: str) -> None:
        """
        Elimina un plugin del registro.
        
        Args:
            name: Nombre del plugin a eliminar
        """
        if name in self._plugins:
            del self._plugins[name]
    
    def get(self, name: str) -> SensorPlugin:
        """
        Obtiene un plugin por nombre.
        
        Args:
            name: Nombre del plugin
            
        Returns:
            Instancia del plugin
            
        Raises:
            PluginNotFoundError: Si el plugin no existe
        """
        if name not in self._plugins:
            available = ", ".join(self._plugins.keys()) or "none"
            raise PluginNotFoundError(
                f"Plugin '{name}' not found. Available: {available}"
            )
        return self._plugins[name]
    
    def get_or_default(self, name: str, default: Optional[str] = None) -> Optional[SensorPlugin]:
        """
        Obtiene un plugin por nombre, o el default si no existe.
        
        Args:
            name: Nombre del plugin
            default: Nombre del plugin por defecto
            
        Returns:
            Instancia del plugin o None
        """
        try:
            return self.get(name)
        except PluginNotFoundError:
            if default:
                return self.get(default)
            return None
    
    def list_plugins(self) -> List[str]:
        """
        Lista todos los plugins registrados.
        
        Returns:
            Lista de nombres de plugins
        """
        return list(self._plugins.keys())
    
    def get_all(self) -> Dict[str, SensorPlugin]:
        """
        Obtiene todos los plugins registrados.
        
        Returns:
            Diccionario nombre -> plugin
        """
        return self._plugins.copy()
    
    def clear(self) -> None:
        """Elimina todos los plugins del registro (útil para tests)."""
        self._plugins.clear()
    
    def __len__(self) -> int:
        return len(self._plugins)
    
    def __contains__(self, name: str) -> bool:
        return name in self._plugins


def get_default_registry() -> PluginRegistry:
    """
    Obtiene el registro de plugins con los plugins por defecto cargados.
    
    Returns:
        PluginRegistry con HttpJsonPlugin preregistrado
    """
    from ingestion.plugins.http_json_plugin import HttpJsonPlugin
    
    registry = PluginRegistry()
    
    # Registrar plugins por defecto
    if "http-json-plugin" not in registry:
        registry.register(HttpJsonPlugin())
    
    return registry
