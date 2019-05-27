import socket
import uuid
import re
from threading import Thread


class Server:
    def __init__(self, HOST="", PORT=50000):
        self.META = {
            "SERVER" : ((HOST, PORT)),
        }
        self.FilterWords = [":END:", ":SRV:", ":CMD:"]

        self.sock = None
        self.Users = []
        self.Poll = []
        self.Channel = []

        self.pattrn = re.compile("\/\w (.*?) ")

        self.server()

    ## Server
    def server(self, HOST="", PORT=50000):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as e:
            self.sock = None
            print(e)
            return False

        self.sock.bind((HOST, PORT))
        self.listen(5)

    def listen(self, q = 5):
        while True:
            self.sock.listen(q)
            conn, addr = self.sock.accept()
            user = self.new_user(
                uid=self.gen_uid(),
                sock=conn,
                addr=addr,
            ) 
            self.Users.append(user)
            user["Thread"].start()
            print('Connected by', addr, user["UID"])

    ## User
    def new_user(self, uid, sock, addr):
        usr = dict(
            Thread=Thread(target=self.instance, args=(uid, sock), daemon=True),
            UID=uid, 
            SOCK=sock, 
            ADDR=addr
        )
        return usr

    def gen_uid(self):
        return ("%s"%(uuid.uuid4().hex[:8])).upper()

    def get_user(self, uid):
        for user in self.Users:
            if user["UID"] == uid:
                return user
        return None

    def remove_user(self, uid):
        for user in self.Users:
            if user["UID"] == uid:
                self.Users.remove(user)
                for user in self.Users:
                    try:
                        if not self.response_chat(user["SOCK"], "-SERVER-", "%s is Exited"%(uid)):
                            raise Exception
                    except Exception as e:
                        print(e)
                        user["SOCK"].close()
                        self.remove_user(user["UID"])
                break

    ## instance
    def instance(self, uid, sock):
        run = True
        msg = "Your id is %s\n"%(uid)
        if not (self.response_command(sock, uid) and 
            self.response_declare(sock, msg) and
            self.response_chat(sock, "-SERVER-", msg) and
            self.response_chat(sock, "-SERVER-", " - Current Users - ") and
            not (False in map(lambda x: self.response_chat(sock, "-SERVER-", x), ["%02d - %s"%(idx + 1, u["UID"]) for idx, u in enumerate(self.Users)]))
            #self.response_chat(sock, "-SERVER-", "<CRLF>".join([u["UID"] for u in self.Users]))
        ):
            run = False

        try:
            if run:
                for user in self.Users:
                    if user["UID"] != uid:
                        try:
                            if not self.response_chat(user["SOCK"], "-SERVER-", "%s is Joined"%(uid)):
                                raise Exception
                        except Exception as e:
                            print(e)
                            user["SOCK"].close()
                            self.remove_user(user["UID"])

            while run:
                data = sock.recv(1010)
                if not data: break
                print("[%s] > RAW > %s\n"%(uid, data.decode()))

                # whisper
                if data.decode().startswith("/w "):
                    try:
                        grp = self.pattrn.match(data.decode())
                        if grp:
                            to_uid = grp.group(1)
                            raw_msg = data.decode()
                            msg = self.filter(raw_msg[raw_msg.find(to_uid) + len(to_uid) + 1:])
                            if not self.response_private(sock, to_uid, msg):
                                raise Exception
                        else:
                            self.response_declare(sock, "NO_USER")
                        continue
                    except Exception as e:
                            print(e)
                            
                # user list command
                if data.decode().strip() == "/list":
                    try:
                        if not self.response_chat(sock, "-SERVER-", " - Current Users - "):
                            raise Exception
                        
                        for idx, usr in enumerate(self.Users):
                            self.response_chat(sock, "-SERVER-", "%02d - %s"%(idx + 1, usr["UID"]))
                        continue
                    except Exception as e:
                        print(e)
                        user["SOCK"].close()
                        self.remove_user(user["UID"])
    
                # echo all
                for user in self.Users:
                    if user["UID"] != uid:
                        try:
                            msg = self.filter(data.decode())
                            if not self.response_chat(user["SOCK"], uid, msg):
                                raise Exception
                        except Exception as e:
                            print(e)
                            user["SOCK"].close()
                            self.remove_user(user["UID"])

        except Exception as e:
            self.remove_user(uid)
            print(e)

        sock.close()
        print('Disconnected by', uid)

    def filter(self, msg):
        for word in self.FilterWords:
            msg = msg.replace(word, " ")
        return msg
    
    # send response
    def response_chat(self, sock, uid, msg):
        try:
            ## for start in range(0, len(msg), 1024-15):
            ##     end = start + 1024-15 if len(msg[start:]) > 1024-15 else start + len(msg[start:])
            ##     sock.sendall(("[%s] > %s\n"%(uid, msg[start:])).encode())
            sock.sendall(("[%s] > %s\n"%(uid, msg)).encode())
            return True
        except Exception as e:
            print(e)
            return False

    def response_declare(self, sock, msg):
        try:
            sock.sendall((":SRV:" + msg + ":END:").encode())
            return True
        except Exception as e:
            print(e)
            return False

    def response_command(self, sock, msg):
        try:
            sock.sendall((":CMD:" + msg + ":END:").encode())
            return True
        except Exception as e:
            print(e)
            return False

    def response_private(self, from_sock, to_uid, msg):
        to = self.get_user(to_uid)
        if not to:
            self.response_declare(from_sock, "NO_USER")
            return False
        else:
            return self.response_chat(to["SOCK"], to["UID"], "Private > " + msg)
        
if __name__ == "__main__":
    server = Server()

