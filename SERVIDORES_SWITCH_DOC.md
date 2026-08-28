# Switch SERVIDORES (10.175.6.225, SG3428X) — Documentación actualizada

**Fecha:** 2026-08-20  
**Ubicación:** Rack de servidores  
**Modelo:** TP-Link SG3428X (24 puertos RJ45 + 4 SFP+ 10G)

---

## ✅ ESTADO ACTUAL — YA CONECTADO

| Puerto | Dispositivo | IP | LAG | Estado |
|--------|-------------|-----|-----|--------|
| **5** | **IBM x3400 PBS** | 10.175.6.2 | **LAG-SRV-PBS** | ✅ **Conectado y operativo** |
| **6** | **IBM x3400 PBS** | 10.175.6.2 | **LAG-SRV-PBS** | ✅ **Conectado y operativo** |

> **LAG-SRV-PBS** configurado en LACP (2 puertos) con profile `Trunk_a_principal` (VLAN 1 native + VLAN 30 + VLAN_Wifi tagged).

---

## 📋 PLANIFICADO — PENDIENTE DE CABLEADO/MIGRACIÓN

### Proxmox Hosts (4 hosts × 2 NICs = 8 puertos)

| Puerto(s) | Host Proxmox | IP | Origen actual | LAG | Estado |
|-----------|--------------|-----|---------------|-----|--------|
| **1, 2** | hpdl360 | 10.175.6.20 | Pepe P11 | LAG-SRV-HPDL360 | ⏳ Pendiente migración |
| **3, 4** | dellr610 | 10.175.6.4 | Rack-Medio P5 | LAG-SRV-DELLR610 | ⏳ Pendiente migración |
| **7, 8** | dellr610-2 | 10.175.6.14 | Rack-Medio P7 | LAG-SRV-DELLR610-2 | ⏳ Pendiente migración |
| **9, 10** | msi-i5 | 10.175.6.6 | (nuevo cableado desde Lab) | LAG-SRV-MSI | ⏳ Pendiente cableado |

> Todos los LAGs: **LACP (802.3ad)**, 2 puertos cada uno, profile `Trunk_a_principal`.

### Uplink 10G a Principal

| Puerto | Conexión | Tipo | Profile |
|--------|----------|------|---------|
| **25 (SFP+)** | Principal P25 (SFP+) | Fibra 10G | Trunk_a_principal |

### Puertos libres para crecimiento

| Puertos | Cantidad | Uso sugerido |
|---------|----------|--------------|
| 11-24 (RJ45) | 14 | Nuevo Proxmox, NAS adicional, backup targets |
| 26-28 (SFP+) | 3 | Uplink 10G redundante, Storage 10G, enlace a otro rack |

---

## 🔗 TOPOLOGÍA COMPLETA ACTUALIZADA

```
OPNsense (10.175.6.203)
    │ P1 (Trunk)
    ▼
PRINCIPAL (10.175.6.236, SG3428X)
    ├─ LAG1 (23,24) ───► CARLITOS (10.175.6.235)
    ├─ LAG2 (21,22) ───► RACK-MEDIO (10.175.6.186)
    ├─ P1 ─────────────► OPNsense
    ├─ P20 ─────────────► Switch/AP downstream
    └─ P25 (SFP+ 10G) ─► SERVIDORES (10.175.6.225) ◄─── ✅ NUEVO
                              │
                              ├─ LAG-SRV-PBS (5,6) ──────► IBM x3400 PBS (10.175.6.2)
                              ├─ LAG-SRV-HPDL360 (1,2) ──► hpdl360 (10.175.6.20)
                              ├─ LAG-SRV-DELLR610 (3,4) ──► dellr610 (10.175.6.4)
                              ├─ LAG-SRV-DELLR610-2 (7,8) ► dellr610-2 (10.175.6.14)
                              ├─ LAG-SRV-MSI (9,10) ──────► msi-i5 (10.175.6.6)
                              └─ P25 SFP+ 10G ───────────► Principal
```

---

## ❌ RACK-MEDIO (10.175.6.186) — NO SE LIBERA

**Dispositivos que PERMANECEN en Rack-Medio:**

| Puerto | Dispositivos críticos |
|--------|----------------------|
| 9 | **omvesperanza NAS (10.175.6.10)** — 34 volúmenes, cámaras graban aquí |
| 15 | 6 PCs Consultorios/Clínicas |
| 17 | Maternidad, Admi-Ivana |
| 18 | Labo-técnicos, Router Arnet, TP-Link switch, ~15 dispositivos |
| 19 | **20+ PCs**: Admisión, Compras, Facturación, Administración, Reloj, Router WiFi |
| 23 | delli5-03 (Proxmox viejo, aún en uso) |

**Lo que SÍ se libera de Rack-Medio:**
- ✅ DELL-r610-1 (P5) → Va a Servidores P3,P4
- ✅ DELL-r610-2 (P7) → Va a Servidores P7,P8

---

## 📁 ARCHIVOS GENERADOS

1. **`/home/sectorial/gestion/mapa_switchs_servidores_clean.csv`** — CSV limpio para importar a Google Sheets
2. **`/home/sectorial/gestion/actualizar_mapa_switchs_google.py`** — Script para añadir hoja "Servidores" a la planilla "Mapa Switchs" en Google Drive

---

## 🚀 PRÓXIMOS PASOS

### Para actualizar la planilla de Google Drive:
```bash
cd /home/sectorial/gestion
# Editar el script y poner las rutas correctas a:
# - google_client_secret.json
# - ~/.config/gdrive/token.json
python3 actualizar_mapa_switchs_google.py
```
> Requiere navegador para OAuth (se abre ventana de autorización).

### Migración física pendiente:
1. Recablear hpdl360 (desde Pepe P11) → Servidores P1,P2
2. Recablear dellr610 (desde Rack-Medio P5) → Servidores P3,P4
3. Recablear dellr610-2 (desde Rack-Medio P7) → Servidores P7,P8
4. Cablear msi-i5 (desde Lab) → Servidores P9,P10
5. Verificar LACP activo en todos los bond0 de los hosts Proxmox
6. Conectar fibra 10G Principal P25 ↔ Servidores P25

### Swap Pepe → Principal:
- Principal ya configurado idéntico a Pepe (LAGs, perfiles, descriptions)
- Cambio físico cuando estés listo

---

## 📝 NOTAS IMPORTANTES

- **PBS (IBM x3400)** ya está en Servidores P5,P6 con LACP funcionando
- **omvesperanza NAS** se queda en Rack-Medio P9 (no se mueve)
- **Rack-Medio** sigue siendo switch de agregación para 35+ dispositivos de departamentos
- **Dell X1026P (10.175.6.223)** se guarda como respaldo cuando Servidores esté 100% operativo