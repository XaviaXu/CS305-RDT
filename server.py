from rdt import socket


SERVER_ADDR = '127.0.0.1'
SERVER_PORT = 5553
server = socket()
server.bind((SERVER_ADDR,SERVER_PORT))
while True:
    conn,client = server.accept()
    while True:
        data = conn.recv(2048)
        if not data:
            break
            conn.send(data)
        conn.close()