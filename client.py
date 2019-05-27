from tkinter import *
from threading import Thread
from random import randint
import socket
import time
import re

class Chat:
    def __init__(self, HOST="127.0.0.1", PORT=30000):
        self.root = Tk()
        self.root.title("Chat")
        self.root.geometry("400x550")
        self.root.resizable(False, False)

        self.HOST=HOST
        self.PORT=PORT
        self.my_id = ""
        self.notice = ""
        self.pattrn = re.compile("\[(.*?)\]")

        self.Users = []

        self.component = {
            "Scroll": Scrollbar(self.root),
            "Textarea":  Text(self.root),
            "chat_input" : Entry(self.root),
            "INV_Label" : Label(self.root)
        }

        self.component["chat_input"].pack(side=BOTTOM, fill=BOTH)
        self.component["Scroll"].pack(side=RIGHT, fill=Y)
        self.component["Textarea"].pack(side=LEFT, fill=Y)

        self.component["Scroll"].config(command=self.component["Textarea"].yview)
        self.component["Textarea"].config(yscrollcommand=self.component["Scroll"].set)
        self.component["chat_input"].bind("<Return>", self.send)
        self.component["Textarea"].after(200, self.update)
        self.component["Textarea"].configure(state="disabled")

        self.get_ui("Textarea").tag_config("send", background="#F4D03F")
        self.get_ui("Textarea").tag_config("CID000000", background="#7F3FCB", foreground="#FFFFFF")
        self.get_ui("Textarea").bind("<FocusIn>", lambda e: self.get_ui("chat_input").focus_set())
        self.get_ui("chat_input").bind("<Tab>", self.auto_compleations)
        self.get_ui("chat_input").focus_set()
        
        self.sock = None
        self.retry = 0

        try:
            self.connect(HOST, PORT)
            self.new_text("[-SERVER-] > Connected\n")
        except Exception as e:
            self.sock = None
            self.background(500, self.retry_connect)
            print(e)

    def run(self):
        self.root.mainloop()

    def retry_connect(self):
        if self.sock == None and self.retry < 3:
            try:
                self.new_text("[-SERVER-] > Retry... (%d/3)\n"%(self.retry + 1))
                self.connect(self.HOST, self.PORT)
                self.new_text("[-SERVER-] > Connected\n")
            except Exception as e:
                self.sock = None
                print(e)
            self.retry += 1

            if self.sock == None:
                self.background(1000, self.retry_connect)
            
    def background(self, time, func):
        self.component["INV_Label"].after(time, func)

    def refresh(self):
        self.component["Textarea"].after(200, self.update)

    def get_ui(self, item):
        return self.component[item]

    def auto_compleations(self, event):  
        ui = self.get_ui("chat_input")
        if ui.get().startswith("/w "):
            txt = ui.get()
            if len(txt) >= len("/w USERHASH"):
                for idx, user in enumerate(self.Users):
                    if user["ID"] == txt[3:11] and idx < len(self.Users) - 1:
                        self.get_ui("chat_input").delete(0, 'end')
                        self.get_ui("chat_input").insert(0, txt.replace(txt[3:11], self.Users[idx + 1]["ID"]))
                        self.get_ui("chat_input").selection_clear()
                        break
                    elif idx == len(self.Users) - 1:
                        self.get_ui("chat_input").delete(0, 'end')
                        self.get_ui("chat_input").insert(0, txt.replace(txt[3:11], self.Users[0]["ID"]))
                        self.get_ui("chat_input").selection_clear()
                        break
                        
            else:
                if 0 < len(self.Users):
                    self.get_ui("chat_input").delete(0, 'end')
                    self.get_ui("chat_input").insert(0, "/w "+ self.Users[0]["ID"])
                    self.get_ui("chat_input").selection_clear()

    def get_user_color(self, uid):
        for user in self.Users:
            if uid == user["ID"]:
                return user["COLOR"]
        return "CID000000"

    def parse(self, data):
        grp = self.pattrn.match(data.decode())
        uid = None
        if grp:
            uid = grp.group(1)

            is_new = True
            for user in self.Users:
                if user["ID"] == uid:
                    is_new = False
            if is_new:
                r, g, b = randint(0, 255), randint(0, 255), randint(0, 255)
                bcid = "%02X%02X%02X"%(r, g, b)
                if (0.299 * r + 0.587 * g + 0.114 * b)/255 > 0.5:
                    fcid = "#000000"
                else:
                    fcid = "#FFFFFF"
                self.get_ui("Textarea").tag_config("CID" + bcid, background="#" + bcid, foreground=fcid)
                self.Users.append(dict(ID=uid, COLOR="CID" + bcid))
        
        # parsing server command
        if (data.decode().find(":CMD:") == 0) and (data.decode().find(":END:") != -1):
            self.my_id = data.decode()[data.decode().find(":CMD:") + 5:data.decode().find(":END:")]
            data = data.decode()[data.decode().find(":END:") + 5:].encode()
            print(self.my_id)

        # parsing server message
        if (data.decode().find(":SRV:") == 0) and (data.decode().find(":END:") != -1):
            self.notice = data.decode()[data.decode().find(":SRV:") + 5:data.decode().find(":END:")]
            data = data.decode()[data.decode().find(":END:") + 5:].encode()
            print(self.notice)

        if len(data) > 0:
            return data, uid
        else:
            return False, None

    def new_text(self, msg, tag=None, line_wrap=False):
        ui = self.get_ui("Textarea")
        start_pos = int(ui.index("end").split(".")[0]) - 1
        start = "%s.%s"%(str(start_pos), "0")
        end = "%s.%s"%(str(start_pos + 1), "end")

        ui.configure(state="normal")
        ui.insert("end", msg)
        ui.yview_pickplace("end")
        ui.configure(state="disabled")

        if tag:
            if line_wrap: tail = " lineend" 
            else: tail = ""
            ui.tag_add(tag, start, end + tail)

    def update(self):
        if self.sock:
            while True:
                try:
                    data = self.sock.recv(1024)
                    if not data:
                        break

                    print(data)
                    raw_msg, uid = self.parse(data)
                    if not raw_msg:
                        continue

                    for msg in raw_msg.decode().split("\n"):
                        if msg == "":
                            continue
                        cid = self.get_user_color(uid)
                        self.new_text(msg.replace("\n", "").replace("<CRLF>", "\n") + "\n", cid, True)
                except socket.timeout as e:
                    break
        self.refresh()

    def send(self, event):
        msg = self.get_ui("chat_input").get()
        if msg and self.sock:
            self.get_ui("chat_input").delete(0, 'end')
            try:
                self.sock.sendall(msg.encode())
                self.new_text("[---ME---] > " + msg.replace("\n", "") + "\n", tag="send", line_wrap=True)
            except Exception as e:
                print(e)

    def connect(self, HOST="127.0.0.1", PORT=50000):
        try:
            self.sock.close()
        except Exception as e:
            pass
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))
        self.sock.settimeout(0.1)
        return self.sock
        
if __name__ == "__main__":
    # try:
        # chat = Chat("192.168.0.242", 50000)
    chat = Chat("127.0.0.1", 50000)
    chat.run()
    # except Exception as e:
    #     print(e)
