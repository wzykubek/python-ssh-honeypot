#!/usr/bin/env python
import argparse
import threading
import socket
import sys
import traceback
import logging
import paramiko
from binascii import hexlify
import paramiko

HOST_KEY = paramiko.RSAKey(filename='server.key')
SSH_BANNER = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.1"

UP_KEY = '\x1b[A'.encode()
DOWN_KEY = '\x1b[B'.encode()
RIGHT_KEY = '\x1b[C'.encode()
LEFT_KEY = '\x1b[D'.encode()
BACK_KEY = '\x7f'.encode()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='ssh_honeypot.log')


def handle_cmd(cmd, chan, ip):
    response = ""
    if cmd.startswith("ls"):
        response = "root.txt"
    elif cmd.startswith("pwd"):
        response = "/root"
    elif cmd.startswith("whoami"):
        response = "root"
    elif cmd.startswith("cat root.txt"):
        response = "Flag:NDQgNjUgNjYgNjkgNmUgNjkgNzQgNjUgNmMgNzkgMjAgNmUgNmYgNzQgMjAgNjEgMjAgNDggNmYgNmUgNjUgNzkgNzAgNmYgNzQ="
    else:
        response = f"{cmd}: command not found"

    if response != '':
        logging.info('Response from honeypot ({}) - Command: '.format(ip, response))
        response = response + "\r\n"
    chan.send(response)


class BasicSshHoneypot(paramiko.ServerInterface):

    client_ip = None

    def __init__(self, client_ip):
        self.client_ip = client_ip
        self.event = threading.Event()
        


    def check_channel_request(self, kind, catchall):
        logging.info('client called check_channel_request ({}): {}'.format(
                    self.client_ip, kind))
        print(f"Self: {self}, Kind: {kind}, Catchall: {catchall}")
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED

    def get_allowed_auths(self, username):
        logging.info('client called get_allowed_auths ({}) with username {}'.format(
                    self.client_ip, username))
        return "password"#publickey

    def check_auth_password(self, username, password):
        print(f"Username:{username},Password:{password}, IP:{self.client_ip}")
        if username == "root":
            logging.info('successful login ({}): username: {}, password: {}'.format(
                self.client_ip, username, password))
            return paramiko.AUTH_SUCCESSFUL 
        else:
            logging.info('failed login ({}): username: {}, password: {}'.format(
                self.client_ip, username, password))
            return paramiko.AUTH_FAILED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_exec_request(self, channel, command):
        command_text = str(command.decode("utf-8"))

        logging.info('client sent command via check_channel_exec_request ({}): {}'.format(
                    self.client_ip, username, command))
        return True


def handle_connection(client, addr):

    client_ip = addr[0]
    logging.info('New connection from: {}'.format(client_ip))
    print('New connection is here from: {}'.format(client_ip))

    try:
        transport = paramiko.Transport(client)
        transport.add_server_key(HOST_KEY)
        transport.local_version = SSH_BANNER # Change banner to appear more convincing
        server = BasicSshHoneypot(client_ip)
        try:
            transport.start_server(server=server)

        except paramiko.SSHException:
            print('*** SSH negotiation failed.')
            raise Exception("SSH negotiation failed")

        # wait for auth
        chan = transport.accept(100)
        if chan is None:
            print('*** No channel (from '+client_ip+').')
            raise Exception("No channel")
        
        chan.settimeout(100)

        if transport.remote_mac != '':
            logging.info('Client mac ({}): {}'.format(client_ip, transport.remote_mac))

        if transport.remote_compression != '':
            logging.info('Client compression ({}): {}'.format(client_ip, transport.remote_compression))

        if transport.remote_version != '':
            logging.info('Client SSH version ({}): {}'.format(client_ip, transport.remote_version))
            
        if transport.remote_cipher != '':
            logging.info('Client SSH cipher ({}): {}'.format(client_ip, transport.remote_cipher))

        server.event.wait(100)
        if not server.event.is_set():
            logging.info('** Client ({}): never asked for a shell'.format(client_ip))
            raise Exception("No shell request")
     
        try:
            chan.send("Welcome to Ubuntu 20.04 LTS (GNU/Linux 4.15.0-128-generic x86_64)\r\n\r\n")
            run = True
            while run:
                chan.send("$ ")
                command = ""
                while not command.endswith("\r"):
                    transport = chan.recv(1024)
                    #print(client_ip+"- received:",transport)
                    # Echo input to psuedo-simulate a basic terminal
                    if(
                        transport != UP_KEY
                        and transport != DOWN_KEY
                        and transport != LEFT_KEY
                        and transport != RIGHT_KEY
                        and transport != BACK_KEY
                    ):
                        chan.send(transport)
                        command += transport.decode("utf-8")
                
                chan.send("\r\n")
                command = command.rstrip()
                print(f"{client_ip} : {command}")
                logging.info('Command received ({}): {}'.format(client_ip, command))

                if command == "exit":
                    logging.info("Connection closed (via exit command): " + client_ip + "\n")
                    run = False

                else:
                    handle_cmd(command, chan, client_ip)

        except Exception as err:
            print('!!! Exception1: {}: {}'.format(err.__class__, err))
            try:
                transport.close()
            except Exception:
                pass

        chan.close()

    except Exception as err:
        print('!!! Exception2: {}: {}'.format(err.__class__, err))
        try:
            transport.close()
        except Exception:
            pass


def start_server(port, bind):
    """Init and run the ssh server"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind, port))
    except Exception as err:
        print('*** Bind failed: {}'.format(err))
        traceback.print_exc()
        sys.exit(1)

    
    while True:
        try:
            sock.listen(100)
            print('Listening for connection on port {} ...'.format(port))
            client, addr = sock.accept()
        except Exception as err:
            print('*** Listen/accept failed: {}'.format(err))
            traceback.print_exc()
        new_thread = threading.Thread(target=handle_connection, args=(client, addr))
        new_thread.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run an SSH honeypot server')
    parser.add_argument("--port", "-p", help="The port to bind the ssh server to (default 2222)", default=2222, type=int, action="store")
    parser.add_argument("--bind", "-b", help="The address to bind the ssh server to", default="", type=str, action="store")
    args = parser.parse_args()
    start_server(args.port, args.bind)

