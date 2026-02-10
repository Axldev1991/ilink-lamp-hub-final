
# Bitácora de Ingeniería Inversa: Lámpara iLink "My Light"

Este documento detalla el proceso técnico seguido para lograr controlar una lámpara Bluetooth genérica china (identificada como "My Light") de la cual no existía documentación pública clara sobre su protocolo.

## 1. Identificación del Dispositivo
Al escanear el entorno, se encontraron dos interfaces para el mismo dispositivo físico:
*   **BLE (Bluetooth Low Energy):** `A8:D2:CD:C7:9C:AC` ("My Light app").
*   **Bluetooth Classic (SPP/Audio):** `AC:9C:C7:CD:D2:A8` ("My Light").

La aplicación oficial vinculada es **iLink** (`com.jwtian.smartbt`).

## 2. Fase de Exploración (BLE)
Usando herramientas como `gatttool` y la librería `bleak`, mapeamos los servicios. El punto crítico fue el servicio vendor-specific:
*   **Servicio:** `0000a032-0000-1000-8000-00805f9b34fb`
*   **Característica de Escritura:** `0000a040-0000-1000-8000-00805f9b34fb` (Handle 0x000b).

## 3. Pruebas de Protocolos Estándar
Intentamos enviar comandos de protocolos conocidos para luces chinas sin éxito:
*   **Triones/MagicHome:** `0x56`, `0x71`.
*   **Genéricos:** `0xAA`, `0x7E`, `0xEB`.
*   **Variaciones iLink comunes:** Estructuras tipo `0x55 [longitud] [comando] [sub-comando] [RGB] [checksum]`.

Ninguno de estos hizo que la lámpara reaccionara, incluso probando a través del puerto serie (SPP) en Bluetooth Classic.

## 4. El Hallazgo Clave
La solución no vino de pruebas a ciegas, sino de una búsqueda profunda de "OSINT" sobre el paquete de la aplicación Android. Encontramos una implementación de un componente de **Home Assistant** (`ilink_light`) que mencionaba el soporte para dispositivos con el SDK de "Jieli" (JL).

El protocolo real resultó ser más complejo de lo habitual:
1.  **Encabezado específico:** No usa solo `0x55`, sino `0x55 0xAA`.
2.  **Bytes de Modo:** 
    *   `0x01` para comandos de sistema (Encendido, Apagado, Brillo).
    *   `0x03` para comandos de color (RGB).
3.  **Lógica de Checksum (CRC):**
    `CRC = (0xFF - (suma_de_todos_los_bytes & 0xFF)) & 0xFF`

## 5. Implementación Final
Con el protocolo decodificado, desarrollamos:
*   `ilink_app.py`: Una aplicación gráfica (GUI) en Python/Tkinter para controlar colores, luz blanca (modo natural), audio y el estado del Bluetooth del sistema.
    *   **Optimización**: Conexión persistente y cola de comandos compactada para respuesta instantánea.

## 6. Comandos Útiles
*   **Encender:** `55 aa 01 08 05 01 f1`
*   **Apagar:** `55 aa 01 08 05 00 f2`
*   **Blanco Puro (Nivel 3):** `55 aa 01 08 09 03 ee`
*   **Rojo:** `55 aa 03 08 02 ff 00 00 f4`

---
**Resultado:** Control total del dispositivo desde Linux, evitando el uso de la app móvil y permitiendo integración con scripts locales.
