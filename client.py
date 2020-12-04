from rdt import socket

SERVER_ADDR = '127.0.0.1'
SERVER_PORT = 5553

MESSAGE = ''
client = socket()
client.connect((SERVER_ADDR,SERVER_PORT))
client.send(MESSAGE)