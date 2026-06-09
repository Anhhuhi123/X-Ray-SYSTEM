import socket

try:
    s = socket.create_connection(("127.0.0.1", 5432), timeout=5)
    print("TCP connection to 127.0.0.1:5432 succeeded!")
    s.close()
except Exception as e:
    print("TCP connection failed:", e)

try:
    s = socket.create_connection(("localhost", 5432), timeout=5)
    print("TCP connection to localhost:5432 succeeded!")
    s.close()
except Exception as e:
    print("TCP connection failed:", e)
