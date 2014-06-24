#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The MIT License (MIT)
# 
# Copyright (c) 2014 Meneghetti Fabio
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

#
#Python server(v 2.2.1, pyml)

import socket, time, gzip, os, md5, sys, mimetypes
try:
    from OpenSSL import SSL
    have_openssl=True
except:
    have_openssl=False
from threading import Thread, enumerate

import pyml
import config
import shared

I="Info"
W="Warn"
E="Err "
D="Dbg "
if config.DEBUG_COLORS:
    colors={
        "I": 34,
        "W": 33,
        "E": 31,
        "D": 0
    }
if config.DEBUG in ["D", "I", "W", "E"]:
    try:
        DebugFile=open(config.DEBUG_FILE, "w" if not config.DEBUG_FILE_APPEND_MODE else "a");
    except:
        DebugFile=None
    def debug(level, *msg):
        priority=["D", "I", "W", "E"]
        try:
            if priority.index(level[0]) >= priority.index(config.DEBUG): 
                message="[%.4f %s] %s"%(time.time(), level, msg[0]%msg[1:] if msg else "")
                if DebugFile:
                    DebugFile.write(message+"\n");
                    DebugFile.flush()
                if config.DEBUG_COLORS:
                    message="[%.4f \x1b[%d;1m%s\x1b[0m] %s"%(time.time(), colors[level[0]], level, msg[0]%msg[1:] if msg else "")
                else:
                    message="[%.4f %s] %s"%(time.time(), level, msg[0]%msg[1:] if msg else "")
                sys.__stderr__.write(message+"\n")
        except: print("Debug info: messaggio non riconosciuto");
else:
    def debug(level, *msg):
        return

EXT=config.INDEX_ORDER
PREFIX=config.WEBDISK_PATH

class Server(Thread):
    sock=None
    started=False
    port=-1
    def __init__(self, port, backlog, useSSL):
        Thread.__init__(self, target=self.mainloop)
        if useSSL:
            self.ssl=SSL.Context(SSL.SSLv23_METHOD)
            self.ssl.use_privatekey_file(config.HTTPS_KEY)
            self.ssl.use_certificate_file(config.HTTPS_CERT)
        else:
            self.ssl=None
        self.sock=socket.socket()
        if useSSL: self.sock=SSL.Connection(self.ssl, self.sock)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(False)
        self.sock.bind(("", port))
        self.sock.listen(backlog)
        self.port=port
        if useSSL: debug(I, "Server sicuro pronto!(Porta: %d)", port)
        else: debug(I, "Server pronto!(Porta: %d)", (port))
    def mainloop(self):
        self.started=True
        self.clients=[]
        tot=0
        while self.started:
            try:
                client, address=self.sock.accept()
                tot+=1
                debug(I, "[%s] Indirizzo %s:%d connesso", "SSL " if self.ssl else "Serv", address[0], self.port)
                debug(I, "[%s] %d Client(s) collegato/i", "SSL " if self.ssl else "Serv", len(self.clients))
                debug(I, "[%s] ID Connessione: %d"%(address[0], tot))
                cl=ClientInit(client, address[0], tot, self.ssl is not None)
                self.clients.append(cl)
                cl.start()
            except socket.error as e:
                if e.errno==11: time.sleep(0.05)
                else:
                    debug(E, "[Serv] [FATAL] Errore socket: errno %d"%e.errno)
                    os.abort()
            for c in self.clients:
                s=c.getState()
                if s==Client.S_TERMINATED or s==Client.S_ERROR:
                    self.clients.remove(c)
    def getClients(self):
        return self.clients
    def stop(self):
        self.started=False
        self.sock.close()
        for thread in enumerate():
            if thread.isAlive():
                try:
                    thread._Thread__stop()
                except:
                    print(str(thread.getName()) + ": Errore: Impossibile terminare il thread")

class ClientInit(Thread):
    def __init__(self, cl, addr, num, ssl):
        Thread.__init__(self, target=self.main)
        self.cl=cl
        self.addr=addr
        self.num=num
        self.ssl=ssl
        self.controller=None
    def main(self):
        self.controller=Client(self.cl, self.addr, self.num, self.ssl)
        try:
            self.controller.start()
        except Exception as e:
            t, o, tb=sys.exc_info()
            i=0
            while tb:
                if tb.tb_next: print("[Serv][Thread][Err] %s%s: %d: Causato da"%("-"*i, os.path.split(tb.tb_frame.f_code.co_filename)[1], tb.tb_lineno))
                else: print("[Serv][Thread][Err] %s%s: %d: %s"%("-"*i, os.path.split(tb.tb_frame.f_code.co_filename)[1], tb.tb_lineno, e.message))
                tb=tb.tb_next
                i+=1
            self.controller.state=Client.S_ERROR
    def getState(self):
        if self.controller: return self.controller.state
        return -1

class File:
    def __init__(self, data, size, mime, comp):
        self.__data=data
        self.__mime=mime
        self.__size=size
        self.__comp=comp
    def __str__(self): return self.__data
    def mime(self): return self.__mime
    def compression(self): return self.__comp
    def size(self): return self.__size

class Header:
    def __init__(self, data):
        self.data=data
    def __call__(self, field, data=None):
        if data:
            self.data[field]=data
        if self.data.has_key(field): return self.data[field]
        return ""

class Client:
    S_OK=0
    S_PARSING=1
    S_PROCESSING_REQUEST=2
    S_RECEIVING_POST=3
    S_PREPARING=4
    S_SENDING=5
    S_STREAMING=6
    S_ERROR=7
    S_TERMINATED=8
    state=S_OK
    coding="ISO-8859-1"
    days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    def __init__(self, cl, addr, dbgnum, ssl):
        self.cl=cl
        self.addr=addr
        self.dbgnum=dbgnum
        self.ssl=ssl
    def start(self):
        cl=self.cl
        addr=self.addr
        dbgnum=self.dbgnum
        header=""
        try:
            while header[-4:]!="\r\n\r\n":
                data=cl.recv(1);
                if data=="":
                    debug(W, "[%s][%d] Nessun dato ricevuto!", addr, dbgnum)
                    return
                header+=data
        except:
            debug(E, "[%s][%d] Connessione chiusa dal client", addr, dbgnum)
            cl.close()
            return
        self.state=self.S_PARSING
        debug(D, "[%s][%d] Connessione ok, analisi Header", addr, dbgnum)
        header=header[:-4].split("\r\n")
        self.header=self.generateHeader(header)
        if not self.header("Accept-Charset"):
            debug(D, "[%s][%d] L'Header non contiene l'attributo \"Accept-Charset\". Codifica: ISO-8859-1", addr, dbgnum)
            self.header("Accept-Charset", "ISO-8859-1")
        self.state=self.S_PROCESSING_REQUEST
        self.request=header[0].split(" ")[0]
        debug(I, "[%s][%d] Tipo richiesta: %s", addr, dbgnum, self.request)
        if self.request=="GET": self.elab(header[0][4:-9])
        elif self.request=="HEAD": self.elab(header[0][5:-9])
        elif self.request=="POST":
            self.state=self.S_RECEIVING_POST
            try:
                plen=int(self.header("Content-Length"))
                if plen:
                    debug(I, "[%s][%d] Ricezione dati da POST (%d bytes)", addr, dbgnum, plen)
                    pdata=""
                    while plen > config.POST_RECEIVE_BUFFER_SIZE:
                        pdata+=cl.recv(config.POST_RECEIVE_BUFFER_SIZE)
                        plen-=config.POST_RECEIVE_BUFFER_SIZE
                    if plen: pdata+=cl.recv(plen)
                else:
                    debug(I, "[%s][%d] POST vuoto", addr, dbgnum)
                    pdata=""
            except:
                debug(I, "[%s][%d] Ricezione dati da POST (? bytes)", addr, dbgnum)
                pdata=""
                precvd=cl.recv(config.POST_UNDEFINED_LENGTH_CHUNK_SIZE)
                while precvd:
                    pdata+=precvd
                    precvd=cl.recv(config.POST_UNDEFINED_LENGTH_CHUNK_SIZE)
            debug(D, "[%s][%d] Ricevuti %d bytes da POST", addr, dbgnum, len(pdata))
            self.elab(header[0][5:-9], pdata);
        elif self.request in ("OPTIONS", "PUT", "DELETE", "PATCH", "TRACK"):
            debug(E, "[%s][%d] Richiesta non consentita", addr, dbgnum)
            self.sendError(405)
        else:
            debug(E, "[%s][%d] Richiesta non riconosciuta", addr, dbgnum)
            self.sendError(400)
    def elab(self, page, post=False):
        if "?" in page:
            page, args=page.split("?")[0], page.split("?")[1]
        else:
            args=""
        page=PREFIX+page
        if page[-1]=="/":
            for e in EXT:
                if os.path.exists(page+"index"+e):
                    page+="index"+e
                    break
            if page[-1]=="/":
                self.sendError(404)
                return
        debug(D, "[%s][%d] Richiesto file \"%s\"", self.addr, self.dbgnum, page)
        ispage=False
        for e in EXT:
            try:
                ispage=page.split(".")[-1] in e
                if ispage: break
            except:pass
        self.state=self.S_PREPARING
        page=shared.decodeurl(page)
        if os.path.exists(page):
            if ispage:
                p=self.preparePage(page, args, post, "gzip")
                self.state=self.S_SENDING
                if p:
                    debug(I, "[%s][%d] Pagina trovata, invio...(%s)", self.addr, self.dbgnum, p.mime())
                    self.cl.send("HTTP/1.1 200 OK\r\nLocation: %s\r\nContent-Length: %d\r\nContent-Type: %s; charset=%s\r\nContent-Encoding: %s\r\n%sConnection: closed\r\n\r\n"%(self.header("Host"), p.size(), p.mime(), self.coding.upper(), p.compression(), self.generateDate()))
                    if self.request!="HEAD":
                        if self.send(str(p)): return
                else:
                    debug(I, "[%s][%d] Errore interno, invio 500...", self.addr, self.dbgnum)
                    self.sendError(500)
            else:
                p=self.prepareFile(page)
                for d in p:
                    if not d:
                        debug(I, "[%s][%d] Errore interno, invio 500...", self.addr, self.dbgnum)
                        self.sendError(500)
                        break
                    elif type(d)==list:
                        debug(I, "[%s][%d] File trovato, streaming%s...(%s)", self.addr, self.dbgnum, " porzione" if "206" in d[2] else "", d[1])
                        self.cl.send("HTTP/1.1 %s\r\nLocation: %s\r\nContent-Length: %d\r\nContent-Type: %s; charset=%s\r\nContent-Encoding: %s\r\n%sConnection: closed\r\n\r\n"%(d[2], self.header("Host"), d[0], d[1], self.coding.upper(), "identity", self.generateDate()))
                        self.state=self.S_STREAMING
                    else:
                        if self.send(d): return
        else:
            debug(I, "[%s][%d] File non trovato, invio 404...", self.addr, self.dbgnum)
            self.sendError(404)
        debug(I, "[%s][%d] Client scollegato per fine comunicazione", self.addr, self.dbgnum)
        self.cl.close()
        self.state=self.S_TERMINATED
    def preparePage(self, page, args, pdata, comp):
        try:
            ext=page.split(".")[-1]
            if ext=="pyml" or ext=="pyhtml": data=pyml.PyMl(page, args, pdata, self.header, prefix=PREFIX).output
            elif ext=="html" or ext=="htm": data=open(page).read()
            else: return False
            md=str(md5.md5(page).hexdigest())
            if comp=="gzip":
                fp=gzip.open("tmp/"+md, "wb")
                fp.write(data)
                fp.close()
                fp=open("tmp/"+md, "rb")
                data=fp.read()
                fp.close()
                os.remove("tmp/"+md)
            elif comp=="identity": pass
            return File(data, len(data), "text/html", comp)
        except IOError:
            return False
    def prepareFile(self, fname):
        try:
            mime=mimetypes.guess_type(fname)[0]
            f=open(fname, "rb")
            size=os.path.getsize(fname)
            min=0
            max=size-1
            hdr="200 OK"
            if self.header("Range"):
                m, M=tuple(self.header("Range").split("=")[1].split("-"))
                if m=="" and M=="": pass
                elif m=="":
                    max=int(M)
                    min=size-max
                elif M=="":
                    min=int(m)
                else:
                    min=int(m)
                    max=int(M)
                debug(I, "[%s][%d] Richiesta porzione file: %s-%s"%(self.addr, self.dbgnum, m, M))
                hdr="206 Partial Content"
            f.seek(min, 0)
            yield [size, mime, hdr]
            while 1:
                if min+config.FILE_UPLOAD_CHUNK_SIZE > max:
                    yield f.read()
                    break
                else:
                    yield f.read(config.FILE_UPLOAD_CHUNK_SIZE)
                    min+=config.FILE_UPLOAD_CHUNK_SIZE
            f.close()
        except Exception as e:
            print e
            yield False
        raise StopIteration
    def send(self, data):
        try:
            self.cl.send(data)
            return False
        except socket.error as e:
            if e.errno==104: debug(W, "[%s][%d] Connessione resettata dal peer", self.addr, self.dbgnum)
            elif e.errno==32: debug(W, "[%s][%d] Pipe interrotta", self.addr, self.dbgnum)
            elif e.errno==110: debug(W, "[%s][%d] Time-out connessione", self.addr, self.dbgnum)
            else: debug(E, "[%s][%d] Errore sconosciuto: %d", self.addr, self.dbgnum, e.errno)
            self.cl.close()
            self.state=self.S_TERMINATED
            return True
    def generateHeader(self, header):
        d={}
        for i in header[1:]:
            p=i.split(": ")
            try: d[p[0]]=p[1]
            except: d[p[0]]=""
        return Header(d)
    def generateDate(self):
        t=time.gmtime(time.time())
        return "Date: %s, %d %s %d %d:%d:%d GMT\r\n"%(self.days[t.tm_wday], t.tm_mday, self.months[t.tm_mon-1], t.tm_year, t.tm_hour, t.tm_min, t.tm_sec)
    def sendError(self, code):
        template="""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
        <title>Errore HTTP %d</title>
        <style>
            body{
                font-family: helvetica, sans, arial;
            }
        </style>
    </head>
    <body>
        <h1>Errore HTTP %d</h1>
        <h4>%s</h4>
    </body>
</html>"""
        s=""
        if code==403:
            d="403 Unauthorized"
            template=template%(403, 403, "Non sei autorizzato per vedere questa pagina/file!")
        elif code==404:
            s="404 Not Found"
            template=template%(404, 404, "File non trovato!")
        elif code==400:
            s="400 Bad Request"
            template=template%(400, 400, "Il browser ha inviato una richiesta non valida")
        elif code==405:
            s="405 Method Not Allowed"
            template=template%(405, 405, "Il metodo richiesto dal browser non è consentito")
        else:
            s="500 Internal Server Error"
            template=template%(500, 500, "Errore Server: ci scusiamo per il disagio")
        p=File(template, len(template), "text/html", "identity")
        self.cl.send("HTTP/1.1 "+s+"\r\nLocation: %s\r\nContent-Length: %d\r\nContent-Type: %s; charset=%s\r\nContent-Encoding: %s\r\n%sConnection: closed\r\n\r\n"%(self.header("Host"), p.size(), p.mime(), self.coding.upper(), p.compression(), self.generateDate()))
        if self.request!="HEAD": self.cl.send(str(p))
        self.cl.close()
        self.state=self.S_TERMINATED

serv=Server(config.HTTP_PORT, config.HTTP_BACKLOG, False)
serv.start()

if config.HTTPS_ENABLED and have_openssl:
    sserv=Server(config.HTTPS_PORT, config.HTTPS_BACKLOG, True)
    sserv.start()
else: sserv=None

s=serv
i=""
while 1:
    i=raw_input()
    if i=="quit" or i=="q" or i=="exit": break
    elif i=="http" and sserv:
        s=serv
        print "Selezionato il server HTTP"
    elif i=="https" and sserv:
        s=sserv
        print "Selezionato il server HTTPS"
    elif i=="clients" or i=="c":
        l=s.getClients()
        print("%d client(s) collegato/i"%len(l))
        for c in l:
           sys.stdout.write("ID: %d Host: %s Stato: "%(c.num, c.addr))
           st=c.getState()
           if   st==Client.S_OK:                 print "Attesa dati"
           elif st==Client.S_PARSING:            print "Analisi Header"
           elif st==Client.S_PROCESSING_REQUEST: print "Analisi richiesta"
           elif st==Client.S_RECEIVING_POST:     print "Ricezione dati POST"
           elif st==Client.S_PREPARING:          print "Preparazione file"
           elif st==Client.S_SENDING:            print "Invio file"
           elif st==Client.S_STREAMING:          print "Streaming"
           elif st==Client.S_ERROR:              print "Errore nel Thread"
           elif st==Client.S_TERMINATED:         print "Thread terminato"
           else:                                 print "Thread non avviato"
    elif i=="disconn" or i=="d":
        print "Tutti i client disconnessi"
        for x in range(len(s.clients)):
            s.clients[x].controller.state=Client.S_TERMINATED
s.stop()
if DebugFile: DebugFile.close()
exit(0)

