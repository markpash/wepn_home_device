# simple echo server used for port forwarding test

import socket

HOST = ''
PORT = 50007

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))

s.listen(1)

conn, addr = s.accept()

print ('Connected by ', addr)

while 1:
    data = conn.recv(32)
    if not data:
        break
    conn.sendall(data)

conn.close()
