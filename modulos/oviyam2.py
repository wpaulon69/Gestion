#!/usr/bin/env python3
"""
Modulo Oviyam2 / Orthanc - Consulta configuracion de timeout de sesion.
Ejecuta localmente en el servidor (tiene acceso a red privada 10.1.96.x).
"""
import asyncio
import aiohttp
import re


async def obtener_configuracion_oviyam2(config):
    """
    Obtiene el timeout de sesion de Oviyam2/Orthanc.
    Retorna dict con: disponible, session_timeout, error
    """
    oviyam2_config = config.get("oviyam2", {})

    host = oviyam2_config.get("host", "10.1.96.115")
    port = oviyam2_config.get("port", 8080)
    user = oviyam2_config.get("user", "esperanza")
    password = oviyam2_config.get("password", "Visor")
    timeout = oviyam2_config.get("timeout", 10)

    url = f"http://{host}:{port}/oviyam2/config.html"
    auth = aiohttp.BasicAuth(user, password)

    result = {
        "disponible": False,
        "session_timeout": None,
        "error": None
    }

    try:
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            async with session.get(url, auth=auth) as resp:
                if resp.status == 200:
                    html = await resp.text()

                    # Patrones para extraer el timeout (en minutos)
                    patterns = [
                        # Espanol - en tabla o input
                        r'Tiempo de sesi[oó]n\s*[:\\-]?\s*(\d+)',
                        r'Tiempo de sesi[oó]n\s*</?[^>]*>\s*(\d+)',
                        r'<td[^>]*>\s*Tiempo de sesi[oó]n\s*</td>\s*<td[^>]*>\s*(\d+)',
                        # Ingles
                        r'Session timeout\s*[:\\-]?\s*(\d+)',
                        r'Session Timeout\s*[:\\-]?\s*(\d+)',
                        r'<td[^>]*>\s*Session\s*Timeout\s*</td>\s*<td[^>]*>\s*(\d+)',
                        # Inputs
                        r'<input[^>]*name=["\']?session\.?timeout["\']?[^>]*value=["\']?(\d+)',
                        r'<input[^>]*id=["\']?session\.?timeout["\']?[^>]*value=["\']?(\d+)',
                        # JSON embebido
                        r'"sessionTimeout"\s*:\s*(\d+)',
                        r'"SessionTimeout"\s*:\s*(\d+)',
                        r'"timeout"\s*:\s*(\d+)',
                    ]

                    for pattern in patterns:
                        matches = re.findall(pattern, html, re.IGNORECASE)
                        if matches:
                            try:
                                result["session_timeout"] = int(matches[0])
                                result["disponible"] = True
                                break
                            except (ValueError, IndexError):
                                continue

                    if not result["disponible"]:
                        result["error"] = "No se encontro el valor de 'Tiempo de sesion' en la respuesta"

                elif resp.status == 401:
                    result["error"] = "No autorizado (401) - credenciales invalidas"
                elif resp.status == 403:
                    result["error"] = "Acceso prohibido (403)"
                else:
                    result["error"] = f"HTTP {resp.status}"

    except asyncio.TimeoutError:
        result["error"] = "Timeout conectando a Oviyam2"
    except aiohttp.ClientConnectorError as e:
        result["error"] = f"Error de conexion: {e}"
    except Exception as e:
        result["error"] = f"Error inesperado: {type(e).__name__}: {e}"

    return result