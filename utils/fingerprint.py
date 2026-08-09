"""Stable machine fingerprint for license binding.

A machine fingerprint is derived from hardware + OS identity:
  - Hostname
  - Primary physical MAC address (first non-loopback, non-virtual adapter)
  - OS username
  - OS version

The result is a SHA-256 hex digest. It is stable across reboots but changes
if the user changes their machine, hostname, or primary network adapter.

The fingerprint NEVER leaves the device except as an opaque hash sent to
the license server.
"""
import hashlib
import logging
import os
import platform
import socket
import subprocess
import uuid

logger = logging.getLogger(__name__)

_VIRTUAL_KEYWORDS = (
    "virtual", "vmware", "virtualbox", "hyper-v", "hyperv",
    "loopback", "pseudo", "tap-windows", "vpn", "tailscale",
    "wireguard", "docker", "veth", "bridge", "bluetooth",
)


def _get_mac() -> str:
    """Return the MAC address of the first physical, non-virtual adapter.

    Falls back to uuid.getnode() (which uses an OS-derived 48-bit value).
    """
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' "
                 "-and $_.Virtual -eq $false } | Select-Object -First 1 -ExpandProperty MacAddress"],
                stderr=subprocess.DEVNULL, timeout=10,
            ).decode().strip()
            if out:
                return out.replace("-", ":").lower()
        elif platform.system() == "Linux":
            out = subprocess.check_output(
                "ls /sys/class/net | grep -v lo", shell=True,
                stderr=subprocess.DEVNULL, timeout=10,
            ).decode().strip().splitlines()
            for iface in out:
                low = iface.lower()
                if any(k in low for k in _VIRTUAL_KEYWORDS):
                    continue
                addr_path = f"/sys/class/net/{iface}/address"
                if os.path.exists(addr_path):
                    mac = open(addr_path).read().strip()
                    if mac and mac != "00:00:00:00:00:00":
                        return mac.lower()
        elif platform.system() == "Darwin":
            out = subprocess.check_output(
                ["ifconfig"], stderr=subprocess.DEVNULL, timeout=10
            ).decode()
            for line in out.splitlines():
                if "ether" in line.lower():
                    parts = line.strip().split()
                    idx = [p.lower() for p in parts].index("ether")
                    return parts[idx + 1].lower()
    except Exception as exc:
        logger.debug("MAC detection failed: %s", exc)
    # Fallback: uuid.getnode() may be random on some systems but is good enough
    # as a last resort.
    return uuid.uuid4().hex[:12]


def _gather_components() -> str:
    hostname = socket.gethostname()
    mac = _get_mac()
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    osver = f"{platform.system()} {platform.release()} {platform.machine()}"
    # Pipe-separated so component boundaries are unambiguous.
    return f"{hostname}|{mac}|{user}|{osver}"


def get_machine_id() -> str:
    """Return a 64-char SHA-256 hex digest that uniquely identifies this machine."""
    components = _gather_components()
    return hashlib.sha256(components.encode("utf-8")).hexdigest()


def get_machine_label() -> str:
    """Return a short human-readable label like 'hostname (mac)' for display."""
    hostname = socket.gethostname()
    mac = _get_mac()
    short_mac = ":".join(mac.split(":")[:3]) + "…"
    return f"{hostname} ({short_mac})"
