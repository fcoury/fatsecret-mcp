# Referencia Técnica: FatSecret MCP Meta-Tool

Este documento detalla la arquitectura y los mecanismos internos del servidor MCP de FatSecret (v0.2.0).

## Arquitectura de Comunicación

El servidor utiliza el **Model Context Protocol (MCP)** sobre un transporte de **Stdio (Standard Input/Output)**. La comunicación se realiza mediante mensajes JSON-RPC 2.0.

### El Patrón Meta-Tool
A diferencia de los servidores MCP convencionales, este sistema implementa un **Proxy de Ejecución**:
- **Reducción de Contexto**: Solo expone dos herramientas iniciales (`discovery` y `execute`).
- **Registro Interno**: Mantiene un `toolRegistry` privado en TypeScript que mapea nombres de herramientas a manejadores (handlers) y esquemas.

## Seguridad y Autenticación

El servidor gestiona de forma transparente la autenticación **OAuth 1.0a (3-Legged)**, necesaria para acceder a datos privados del usuario.

### Firmas HMAC-SHA1
Cada petición protegida requiere una firma generada a partir de:
1.  **Consumer Key & Secret** (API del Desarrollador).
2.  **Access Token & Secret** (Token del Usuario).
3.  **Base String**: Combinación de método HTTP, URL y parámetros ordenados alfabéticamente.
4.  **Signing Key**: Unión de los secrets codificados.

## Flujo de Datos

1.  **Solicitud**: El Cliente MCP envía una llamada a `execute(tool, arguments)`.
2.  **Validación**: El servidor busca la `tool` en el registro interno.
3.  **Procesamiento de Fechas**: El servidor detecta parámetros de fecha y los convierte al formato FatSecret (días desde 1970-01-01).
4.  **Llamada API**: Se construye la petición REST firmada y se envía a `platform.fatsecret.com`.
5.  **Respuesta**: Se devuelve el JSON crudo o procesado al Cliente.

## Restricciones Técnicas
- **Standard vs Premier**: El servidor está optimizado para API Keys estándar. Se han omitido métodos como `barcode.v2` por requerir licencias de pago (Error 10).
- **Timeouts**: Las peticiones a FatSecret suelen responder en <500ms debido a la baja latencia del transporte Stdio.
