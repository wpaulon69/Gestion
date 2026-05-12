# Informe de Análisis: Acceso a Reglas de Firewall OPNsense para Usuario IA_Monitor

## Resumen Ejecutivo
Este documento analiza las capacidades actuales del usuario `IA_Monitor` para acceder y modificar las reglas de firewall en el sistema OPNsense del SAMCo Esperanza, identifica las limitaciones encontradas y propone un plan de mejoras para lograr el acceso necesario.

## Estado Actual del Acceso OPNsense

### Configuración Actual
- **IP del OPNsense:** 10.175.6.203
- **Usuario API:** IA_Monitor (implícito en la configuración)
- **API Key:** v4f9BW...KBX4
- **API Secret:** z8kfgfRhtCJYU4FXn993+ruklqnVpkehYYNa4g5EnWqM1+oiG3naafDHHDA8KnDqt+luwj23PdFz1m+W

### Pruebas de Acceso Realizadas
1. **Conectividad básica:** ✓ Exitosa (endpoint `/api/core/get_version` y similares devuelven 200 cuando existen)
2. **Acceso a interfaces:** ✓ Exitosa (endpoint `/api/interfaces/overview/interfacesInfo` devuelve datos completos)
3. **Acceso a reglas de firewall:** ✗ Fallido (endpoint `/api/firewall/filter/get` devuelve 403 Forbidden)
4. **Acceso a endpoints de agregación:** ✗ Fallido (endpoints `/api/firewall/filter/addItem`, `/api/firewall/filter/setItem` devuelven 404 Not Found)

### Análisis de la Respuesta 403 Forbidden
El error 403 indica que:
- La autenticación es exitosa (las credenciales son válidas)
- El usuario está autenticado pero no tiene permisos suficientes para acceder al recurso solicitado
- Esto es un problema de autorización, no de autenticación

## Fortalezas Identificadas
1. El sistema de auditoría ya puede acceder a información crítica de OPNsense (interfaces, estado general)
2. Las credenciales API están funcionando correctamente
3. El módulo `modulos/opnsense.py` está bien estructurado y maneja errores apropiadamente
4. La conectividad de red al OPNsense es estable desde el servidor de auditoría

## Debilidades y Limitaciones
1. **Permisos insuficientes:** El usuario API `IA_Monitor` no tiene asignados los privilegios necesarios para acceder a las reglas de firewall
2. **Falta de granularidad en permisos:** OPNsense utiliza un sistema de privilegios basado en roles/usuarios que requiere configuración específica
3. **Error en el módulo actual:** Aunque se puede acceder a interfaces, hay un bug en el procesamiento de datos que causa `'int' object has no attribute 'get'`
4. **Dependencia de configuración externa:** Los cambios requeridos deben hacerse en la interfaz web de OPNsense, no solo en el código

## Plan de Mejoras

### Fase 1: Diagnóstico y Configuración de Permisos (Inmediata)
1. **Acceder a la interfaz web de OPNsense** (https://10.175.6.203) como administrador
2. **Navegar a:** System → Access → Users → IA_Monitor (o crear el usuario si no existe)
3. **Asignar los siguientes privilegios:**
   - `firewall:filter:edit` (para ver y modificar reglas)
   - `firewall:filter:view` (solo para ver, si se prefiere acceso de solo lectura inicialmente)
   - `system:settings:firewall` (para acceder a configuración de firewall)
4. **Verificar que el usuario esté en un grupo con estos privilegios o asignarlos directamente**
5. **Probar nuevamente el acceso desde el script de auditoría**

### Fase 2: Corrección del Módulo OPNsense (Corto plazo)
1. **Fixear el error actual** en `modulos/opnsense.py`:
   - La función `obtener_estado_interfaces` está recibiendo un formato de respuesta inesperado
   - Según la respuesta vista, el endpoint devuelve un objeto con `{total, rowCount, current, rows}`
   - El código actual asume que `data` es directamente el diccionario de interfaces
2. **Implementar nuevas funciones** para acceso a reglas de firewall:
   - `obtener_reglas_firewall(config)` - para obtener las reglas actuales
   - `agregar_regla_firewall(config, regla)` - para agregar nuevas reglas
   - `modificar_regla_firewall(config, numero_regla, regla)` - para modificar existentes
   - `eliminar_regla_firewall(config, numero_regla)` - para eliminar reglas
3. **Agregar manejo de errores específico** para respuestas 403 (permiso denegado) vs 404 (endpoint no encontrado)

### Fase 3: Integración con el Dashboard (Mediano plazo)
1. **Actualizar `auditar.py`** para llamar a las nuevas funciones de firewall
2. **Mejorar el reporte JSON** para incluir:
   - Número total de reglas de firewall
   - Estado de las reglas (activas/inactivas)
   - Resumen por tipo de regla (bloquear, permitir, NAT, etc.)
   - Última modificación de reglas
3. **Actualizar el dashboard HTML/JS** para mostrar:
   - Panel de estado del firewall OPNsense
   - Gráfico de tendencia de reglas agregadas/eliminadas
   - Alertas si se detectan cambios no autorizados

### Fase 4: Automatización y Monitoreo (Largo plazo)
1. **Implementar detección de cambios** en las reglas de firewall:
   - Comparar versión actual con versión anterior
   - Generar alertas en Zabbix o mediante notificaciones cuando se detecten cambios
2. **Crear reportes de cumplimiento** mensuales:
   - Revisión de reglas obsoletas o duplicadas
   - Verificación de que las reglas sigan el principio de menor privilegio
3. **Integrar con el sistema de alertas existente** para notificar cambios críticos en tiempo real

## Estimación de Esfuerzo
- **Fase 1:** 2-4 horas (requiere acceso administrativo a OPNsense web)
- **Fase 2:** 4-6 horas (desarrollo y pruebas)
- **Fase 3:** 6-8 horas (integración y actualización de dashboard)
- **Fase 4:** 8-12 horas (automatización avanzada)

## Riesgos y Consideraciones
1. **Riesgo de bloqueo:** Al modificar reglas de firewall hay riesgo de cortar el acceso al propio OPNsense o a servicios críticos
   - **Mititación:** Implementar un modo de prueba/simulación primero, usar horarios de baja actividad para cambios
2. **Dependencia de privilegios:** Sin los permisos adecuados en OPNsense, ningún código funcionará
   - **Mititación:** La Fase 1 es crítica y debe completarse antes de continuar
3. **Compatibilidad de versiones:** Las APIs de OPNsense pueden cambiar entre versiones
   - **Mititación:** Usar versionamiento en las llamadas API y agregar detección de versión

## Conclusión
El usuario `IA_Monitor` actualmente **no tiene acceso** para ver o editar las reglas de firewall debido a limitaciones de permisos configuradas en OPNsense, no por limitaciones técnicas del sistema de auditoría. 

Con la configuración adecuada de privilegios en la interfaz web de OPNsense (Fase 1), seguido de las correcciones de código y extensiones propuestas, el sistema podrá cumplir con el objetivo de monitorear y gestionar las reglas de firewall como parte de la auditoría unificada de SAMCo Esperanza.

Se recomienda iniciar inmediatamente con la Fase 1, ya que es el requisito previo indispensable para todas las demás fases.