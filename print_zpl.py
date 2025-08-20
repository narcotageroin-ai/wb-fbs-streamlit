import socket, os

def send_zpl_to_printer(host: str, port: int, zpl: bytes):
    """Send raw ZPL bytes to a networked printer (e.g., Zebra)"""
    with socket.create_connection((host, port), timeout=10) as s:
        s.sendall(zpl)
