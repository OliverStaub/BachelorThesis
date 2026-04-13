#!/usr/bin/env python3
"""Send SIGNAL NEWNYM to Tor control port to get a fresh circuit."""
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(("127.0.0.1", 9051))
    s.sendall(b"AUTHENTICATE\r\n")
    s.recv(1024)
    s.sendall(b"SIGNAL NEWNYM\r\n")
    s.recv(1024)
