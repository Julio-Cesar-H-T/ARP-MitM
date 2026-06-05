# 🕵️ ARP Spoofing — Ataque Man-in-the-Middle mediante ARP

## 🎯 Objetivo del Laboratorio

Demostrar cómo un atacante en la misma red puede posicionarse entre una víctima y su gateway mediante el envenenamiento de las tablas ARP, interceptando y pudiendo modificar todo el tráfico de red sin que la víctima lo detecte.

---

## 📋 Objetivo del Script

El script `ARP_MitM.py` envía ARP Replies falsos de forma continua y bidireccional:
- Le dice a la **víctima** que la MAC del gateway es la del atacante.
- Le dice al **gateway** que la MAC de la víctima es la del atacante.

Todo el tráfico entre víctima y gateway pasa entonces por Kali, que lo reenvía transparentemente gracias al IP forwarding activado.

### Parámetros usados

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `INTERFACE` | `ens4.10` | Subinterfaz VLAN 10 de Kali |
| `IP_VICTIMA` | `192.168.10.100` | IP de VPC-1 asignada por DHCP |
| `IP_GATEWAY` | `192.168.10.254` | Subinterfaz E0/0.10 de R1 |
| `INTERVALO` | `2 s` | Tiempo entre ciclos de envenenamiento |

### Requisitos para utilizar la herramienta

```bash
# Habilitar IP Forwarding ANTES de ejecutar (obligatorio)
sudo sysctl -w net.ipv4.ip_forward=1

# Verificar
cat /proc/sys/net/ipv4/ip_forward   # debe devolver 1

# Dependencias
pip install scapy

# Ejecución con privilegios
sudo python3 ARP_MitM.py
```

---

## 🔧 Documentación del Funcionamiento del Script

### Flujo de ejecución

```
1. Verificar que IP forwarding esté activo (falla si no)
2. Resolver MACs reales:
     ARP Request broadcast → víctima responde con su MAC
     ARP Request broadcast → gateway responde con su MAC
3. Bucle infinito de envenenamiento (cada 2 segundos):
     → ARP Reply a víctima:
          "192.168.10.254 tiene MAC <Kali>"
     → ARP Reply a gateway:
          "192.168.10.100 tiene MAC <Kali>"
4. Al recibir Ctrl+C:
     → Restaurar ARP real (5 paquetes cada uno)
     → Salir limpiamente
```

### Estructura del paquete ARP de envenenamiento

```
[ Ethernet Header ]
  DA: <MAC víctima>       (unicast directo)
  SA: <MAC Kali ens4.10>

[ ARP ]
  Hardware Type : 0x0001  (Ethernet)
  Protocol Type : 0x0800  (IPv4)
  Operation     : 0x0002  (Reply)
  Sender MAC    : <MAC Kali>      ← suplantamos al gateway
  Sender IP     : 192.168.10.254  ← IP del gateway
  Target MAC    : <MAC víctima>
  Target IP     : 192.168.10.100
```

### Flujo de tráfico durante el ataque

```
NORMAL:
  VPC-1 ──────────────────────► R1 ──► Internet

BAJO ATAQUE:
  VPC-1 ──► Kali ──► R1 ──► Internet
             ▲
         intercepta,
         reenvía,
         puede modificar
```

### Impacto esperado

- La tabla ARP de VPC-1 muestra la MAC de Kali como gateway.
- La tabla ARP de R1 muestra la MAC de Kali como VPC-1.
- Kali puede capturar credenciales, sesiones HTTP, etc.

---

## 🗺️ Documentación de la Red

### Topología

```
        [ R1 — IOU L3 ]
        192.168.10.254 (VLAN 10)
        192.168.20.254 (VLAN 20)
               |
           e0/0 (trunk)
               |
        [ SW-1 — IOL L2 ]
         e0/1       e0/2       e0/3
          |           |           |
       [SW-3]       [SW-2]   [Atacante Kali]
       VLAN 10      VLAN 20   ens4.10 → 192.168.10.50
       VPC-1,4      VPC-2,3
```

### Interfaces y VLANs

| Dispositivo | Interfaz | Modo | VLAN / IP |
|-------------|----------|------|-----------|
| R1 | E0/0.10 | subinterfaz | 192.168.10.254/24 |
| SW-1 | E0/3 | access VLAN 10 | Atacante |
| Kali | ens4 | física | — |
| Kali | ens4.10 | subinterfaz VLAN 10 | 192.168.10.50/24 |
| VPC-1 | eth0 | access VLAN 10 | 192.168.10.100 (DHCP) |

### Direccionamiento IP

| Dispositivo | IP | Rol |
|-------------|-----|-----|
| R1 (Gateway) | 192.168.10.254 | Gateway VLAN 10 |
| Kali | 192.168.10.50 | Atacante / MitM |
| VPC-1 | 192.168.10.100 | Víctima |

---

## 📸 Capturas de Pantalla

> Insertar capturas en esta sección:

1. **`img/01_arp_antes.png`** — Tabla ARP de VPC-1 antes del ataque (`show arp`). MAC del gateway es la real de R1.
2. **`img/02_script_corriendo.png`** — Terminal Kali con el script activo mostrando ciclos de envenenamiento.
3. **`img/03_arp_envenenada.png`** — Tabla ARP de VPC-1 durante el ataque. MAC del gateway ahora es la de Kali.
4. **`img/04_tcpdump_kali.png`** — `tcpdump -i ens4.10` en Kali mostrando tráfico de VPC-1 interceptado.
5. **`img/05_arp_restaurada.png`** — Tabla ARP de VPC-1 tras detener el script. MAC del gateway vuelve a ser la real.

---

## 🛡️ Contra-medidas

### Dynamic ARP Inspection (DAI)

```
! Habilitar DHCP Snooping (base de DAI)
SW-1(config)# ip dhcp snooping
SW-1(config)# ip dhcp snooping vlan 10,20

! Puerto confiable (hacia R1)
SW-1(config)# interface Ethernet0/0
SW-1(config-if)# ip dhcp snooping trust

! Habilitar DAI en las VLANs
SW-1(config)# ip arp inspection vlan 10,20

! Verificación
SW-1# show ip arp inspection
SW-1# show ip arp inspection vlan 10
```

### ARP estático en dispositivos críticos

```
! En el gateway, entrada ARP estática para la víctima
R1(config)# arp 192.168.10.100 <MAC-real-VPC1> arpa
```

### Verificación del ataque

```
! En VPC-1 (VPCS):
show arp
→ Si la MAC de 192.168.10.254 es la de Kali → ataque activo

! En R1:
show arp
→ Si la MAC de 192.168.10.100 es la de Kali → ataque activo
```

> **Nota:** DAI requiere que DHCP Snooping esté activo para poblar su tabla de vinculaciones IP-MAC. En un lab sin DHCP Snooping, se pueden definir entradas ARP de acceso de forma estática con `ip arp inspection filter`.
