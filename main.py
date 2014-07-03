#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  The MIT License (MIT)
#  
#  Copyright (c) 2014 Meneghetti Fabio
#  
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#  
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#  
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

#Python server(v 2.4.0 alpha, pyml)

CONFIG_FILE="pyserver.conf"

import socket, time, os, sys, mimetypes, zlib, struct
from multistream import MultiStream

def readtime(f):
    return struct.unpack("<L", f.read(struct.calcsize("<L")))[0]

def writetime(f, t):
    f.write(struct.pack("<L", long(t)))

try:
    from OpenSSL import SSL
    have_openssl=True
except ImportError:
    have_openssl=False
from threading import Thread, enumerate
from multiprocessing import Process
import pyml
import shared

config=shared.ServerConfiguration(CONFIG_FILE)

pyml.config=config

I="Info"
W="Warn"
E="Err "
D="Dbg "
if config.debug.use_colors:
    colors={
        "I": 34,
        "W": 33,
        "E": 31,
        "D": 0
    }
if config.debug.level in ("D", "I", "W", "E"):
    try:
        DebugFile=open(config.paths.debug, "w" if not config.debug.file_append else "a");
    except:
        print "[INIT] [Debug] Impossibile aprire il file di debug '%s' in scrittura"%(config.paths.debug)
        DebugFile=None
    def debug(level, *msg):
        priority=["D", "I", "W", "E"]
        try:
            if priority.index(level[0]) >= priority.index(config.debug.level):
                t=time.time() 
                t="%s.%04d"%(time.strftime("%d/%m %H:%M:%S"), int((t-int(t))*1000))
                message="[%s %s] %s"%(t, level, msg[0]%msg[1:] if msg else "")
                if DebugFile:
                    DebugFile.write(message+"\n");
                    DebugFile.flush()
                if config.debug.use_colors:
                    message="[%s \x1b[%d;1m%s\x1b[0m] %s"%(t, colors[level[0]], level, msg[0]%msg[1:] if msg else "")
                else:
                    message="[%s %s] %s"%(t, level, msg[0]%msg[1:] if msg else "")
                sys.__stderr__.write(message+"\n")
        except: print("Debug info: messaggio non riconosciuto");
else:
    def debug(level, *msg):
        return

pyml.debug=debug
shared.debug=debug

debug(I, "[INIT] Inizio setup...")

debug(D, "[INIT] Registrazione controlli input/output")

sys.stdout = MultiStream()
sys.stdout.registerUnregisteredDefaultStream(sys.__stdout__)
sys.stdout.registerThread(sys.__stdout__)

sys.stderr = MultiStream()
sys.stderr.registerUnregisteredDefaultStream(sys.__stderr__)
sys.stderr.registerThread(sys.__stderr__)

sys.stdin  = MultiStream()
sys.stdin.registerUnregisteredDefaultStream(sys.__stdin__)
sys.stdin.registerThread(sys.__stdin__)

debug(D, "[INIT] Controllo cartelle/percorsi ...")

if config.cache.use:
    if not os.access(config.paths.cache, os.R_OK | os.W_OK | os.X_OK):
        debug(W, "[INIT] Impossibile accedere alla cartella cache '%s': cache disabilitata", config.paths.cache)
        config.cache.use=False
    debug(D, "[INIT] Cache OK")

if not os.access(config.paths.webdisk, os.R_OK | os.W_OK | os.X_OK):
    debug(E, "[INIT] Impossibile accedere al disco virtuale!")
    exit(1)
debug(D, "[INIT] Disco virtuale OK")

if config.https.use and not (config.paths.https_key and config.paths.https_cert):
    debug(W, "[INIT] Certificato o chiave privata HTTPS non specificato/a/i: HTTPS disabilitato")
    config.https.use=False
elif config.https.use: debug(D, "[INIT] Server SSL OK")
else: debug(D, "[INIT] Server SSL non abilitato")

if config.http.port < 0 or config.http.port > 65535:
    debug(E, "[INIT] Porta HTTP non in [0, 65535] (%d): server HTTP disabilitato", config.http.port)
    config.http.use=False

if config.https.port < 0 or config.https.port > 65535:
    debug(E, "[INIT] Porta HTTPS non in [0, 65535] (%s): server HTTPS disabilitato", config.https.port)
    config.https.use=False

if os.getuid() != 0 or os.geteuid() != 0:
    if config.http.use and config.http.port < 1024:
        debug(W, "[INIT] Porta HTTP < 1024 (%d): potrebbe essere necessario essere root/admin", config.http.port)
    if config.https.use and config.https.port < 1024:
        debug(W, "[INIT] Porta HTTPS < 1024 (%d): potrebbe essere necessario essere root/admin", config.https.port)


class Server(Thread):
    sock=None
    started=False
    port=-1
    def __init__(self, port, backlog, useSSL):
        Thread.__init__(self, target=self.mainloop)
        if useSSL:
            self.ssl=SSL.Context(SSL.SSLv23_METHOD)
            self.ssl.use_privatekey_file(config.paths.https_key)
            self.ssl.use_certificate_file(config.paths.https_cert)
        else:
            self.ssl=None
        self.sock=socket.socket()
        if useSSL: self.sock=SSL.Connection(self.ssl, self.sock)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(False)
        self.sock.bind(("", port))
        self.sock.listen(backlog)
        self.port=port
        if useSSL: debug(I, "[HTTPS] Server sicuro pronto!(Porta: %d)", port)
        else: debug(I, "[HTTP ] Server pronto!(Porta: %d)", (port))
    def mainloop(self):
        self.started=True
        self.clients=[]
        tot=0
        while self.started:
            try:
                client, address=self.sock.accept()
                tot+=1
                debug(I, "[%s] Indirizzo %s:%d connesso", "HTTPS" if self.ssl else "HTTP ", address[0], self.port)
                debug(I, "[%s] %d Client(s) collegato/i", "HTTPS" if self.ssl else "HTTP ", len(self.clients)+1)
                debug(I, "[%s] ID Connessione: %d"%(address[0], tot))
                cl=ClientInit(client, address[0], tot, self.ssl is not None)
                self.clients.append(cl)
                cl.start()
            except socket.error as e:
                if e.errno==11: time.sleep(0.05)
                else:
                    debug(E, "[%s] [FATAL] Errore socket: errno %d"%("HTTPS" if self.ssl else "HTTP ", e.errno))
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
        except BaseException as e:
            shared.createTraceback(e, "[Serv][Thread][Err]")
            self.controller.state=Client.S_ERROR
    def getState(self):
        if self.controller: return self.controller.state
        return -1

class Page:
    def __init__(self, data, size, comp):
        self.__data=data
        self.__size=size
        self.__comp=comp
    def __str__(self): return self.__data
    def compression(self): return self.__comp
    def size(self): return self.__size

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
    compression="identity"
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
                    self.state=self.S_TERMINATED
                    return
                header+=data
        except:
            debug(E, "[%s][%d] Connessione chiusa dal client", addr, dbgnum)
            cl.close()
            return
        self.state=self.S_PARSING
        debug(D, "[%s][%d] Connessione ok, analisi Header", addr, dbgnum)
        header=header[:-4].split("\r\n")
        self.header=shared.generateHeader(header)
        if not self.header("Accept-Charset"):
            debug(D, "[%s][%d] L'Header non contiene l'attributo \"Accept-Charset\". Codifica: ISO-8859-1", addr, dbgnum)
            self.header("Accept-Charset", "ISO-8859-1")
        self.state=self.S_PROCESSING_REQUEST
        self.request=header[0].split(" ")[0]
        debug(I, "[%s][%d] Tipo richiesta: %s", addr, dbgnum, self.request)
        if self.request=="GET": self.elab(header[0][4:-9], False)
        elif self.request=="HEAD": self.elab(header[0][5:-9], False)
        elif self.request=="POST": self.elab(header[0][5:-9], True)
        elif self.request in ("OPTIONS", "PUT", "DELETE", "PATCH", "TRACK"):
            debug(E, "[%s][%d] Richiesta non consentita", addr, dbgnum)
            self.sendError(405)
        else:
            debug(E, "[%s][%d] Richiesta non riconosciuta", addr, dbgnum)
            self.sendError(400)
    def elab(self, rel_page, post=False):
        if "?" in rel_page:
            rel_page, args=rel_page.split("?")[0], rel_page.split("?")[1]
        else:
            args=""
        page=config.paths.webdisk+rel_page
        if page[-1]=="/":
            for e in config.misc.index_search_order:
                if os.path.exists(page+"index"+e):
                    page+="index"+e
                    rel_page+="index"+e
                    break
        if   "gzip"    in self.header("Accept-Encoding"): self.compression = "gzip"
        elif "deflate" in self.header("Accept-Encoding"): self.compression = "deflate"
        page=shared.decodeurl(page)
        cfg=None
        dir=""
        adm=False
        fold=rel_page.split(os.sep)
        for i in range(len(fold)):
            f=fold[i]
            dir=os.path.join(dir, f)
            if os.path.exists(os.path.join(config.paths.webdisk, dir, config.paths.folder_cfg)):
                adm=False
                cfg=shared.readConfig(os.path.join(config.paths.webdisk, dir, config.paths.folder_cfg))
                for e in cfg:
                    adm=adm or cfg[e].is_admin_script
                    if adm: break
                if adm:
                    page=os.path.join(config.paths.webdisk, dir, e)
                    cfg=cfg[e]
                    break
        if adm:
            debug(I, "[%s][%d] Folderscript trovato \"%s\"", self.addr, self.dbgnum, e)
        else:
            debug(D, "[%s][%d] Richiesto file \"%s\"", self.addr, self.dbgnum, rel_page)
            cfg=None
        ispage=ispyml=False
        for e in config.misc.index_search_order:
            try:
                ispage=page.split(".")[-1] in e
                ispyml=ispage and "py" in page.split(".")[-1] 
                if ispage:
                    break
            except:pass
        self.state=self.S_PREPARING
        if os.path.isdir(page):
            debug(I, "[%s][%d] Index file non trovato, invio 404", self.addr, self.dbgnum)
            self.sendError(404)
        elif os.path.exists(page):
            if not cfg:
                cfg=os.path.join(os.path.split(page)[0], config.paths.folder_cfg)
                cfg=shared.readConfig(cfg)[os.path.split(page)[1]]
            if ispage:
                if ispyml:
                    pdata=""
                    if post and cfg.receive_post:
                        self.state=self.S_RECEIVING_POST
                        try:
                            plen=int(self.header("Content-Length"))
                            if plen:
                                debug(I, "[%s][%d] Ricezione dati da POST (%d bytes)", self.addr, self.dbgnum, plen)
                                pdata=""
                                while plen > config.buffers.tcp_receive_buffer:
                                    pdata+=self.cl.recv(config.buffers.tcp_receive_buffer)
                                    plen-=config.buffers.tcp_receive_buffer
                                if plen: pdata+=self.cl.recv(plen)
                            else:
                                debug(I, "[%s][%d] POST vuoto", self.addr, self.dbgnum)
                                pdata=""
                        except:
                            debug(I, "[%s][%d] Ricezione dati da POST (? bytes)", self.addr, self.dbgnum)
                            pdata=""
                            precvd=self.cl.recv(config.buffers.post_undefined_length)
                            while precvd:
                                pdata+=precvd
                                precvd=self.cl.recv(config.buffers.post_undefined_length)
                        debug(D, "[%s][%d] Ricevuti %d bytes da POST", self.addr, self.dbgnum, len(pdata))
                    if cfg.is_admin_script:
                        cfg["request_page"]=os.sep.join(fold[i+1:])
                    pyml.PyMl(page, self.request, args, pdata, self.header, self.cl, cfg)
                    self.state=self.S_TERMINATED
                else:
                    if adm:  debug(I, "[%s][%d] folderscript ignorato: %s non PyMl", self.addr, self.dbgnum, page)
                    if post: debug(I, "[%s][%d] POST ignorato: %s non PyMl", self.addr, self.dbgnum, page)
                    p=self.preparePage(page, rel_page, cfg)
                    self.state=self.S_SENDING
                    if p:
                        debug(I, "[%s][%d] Pagina trovata, invio...(text/html)", self.addr, self.dbgnum)
                        self.cl.send("HTTP/1.1 200 OK\r\nLocation: %s\r\nContent-Length: %d\r\nContent-Type: text/html; charset=%s\r\nContent-Encoding: %s\r\n%sConnection: close\r\n\r\n"%(self.header("Host"), p.size(), self.coding.upper(), p.compression(), shared.generateDate()))
                        if self.request!="HEAD":
                            if self.send(str(p)): return
                    else:
                        debug(E, "[%s][%d] Errore interno, invio 500...", self.addr, self.dbgnum)
                        self.sendError(500)
            else:
                if adm:  debug(I, "[%s][%d] folderscript ignorato: %s non PyMl", self.addr, self.dbgnum, page)
                if post: debug(I, "[%s][%d] POST ignorato: %s non PyMl", self.addr, self.dbgnum, page)
                p=self.prepareFile(page, rel_page, cfg)
                for d in p:
                    if d == False:
                        debug(E, "[%s][%d] Errore interno, invio 500...", self.addr, self.dbgnum)
                        self.sendError(500)
                        break
                    elif type(d)==list:
                        debug(I, "[%s][%d] File trovato, streaming%s...(%s)", self.addr, self.dbgnum, " porzione" if "206" in d[2] else "", d[1])
                        self.cl.send("HTTP/1.1 %s\r\nLocation: %s\r\n%sContent-Type: %s; charset=%s\r\nContent-Encoding: %s\r\n%sConnection: close\r\n\r\n"%(d[2], self.header("Host"), ("Content-Length: %d\r\n"%d[0]) if d[0] >= 0 else "", d[1], self.coding.upper(), d[3], shared.generateDate()))
                        self.state=self.S_STREAMING
                    elif d:
                        if self.send(d): return
        else:
            debug(I, "[%s][%d] File non trovato, invio 404...", self.addr, self.dbgnum)
            self.sendError(404)
        debug(I, "[%s][%d] Client scollegato per fine comunicazione", self.addr, self.dbgnum)
        self.cl.close()
        self.state=self.S_TERMINATED
    def preparePage(self, page, rel, cfg):
        if cfg.force_compression: comp=cfg.force_compression
        else: comp=self.compression
        q=cfg.force_compression_quality
        debug(D, "[%s][%d] Compressione con algoritmo %s.%d", self.addr, self.dbgnum, comp, q)
        try:
            if comp == "identity":
                src=open(page, "r")
                data=src.read()
                src.close()
                return Page(data, len(data), "identity")
            if config.cache.use and (config.cache.on_pages or cfg.force_cache_state == 1) and not cfg.force_cache_state == -1:
                cache_name=rel.replace("_", "__").replace("/", "_")
                recreate=True
                if os.path.exists(os.path.join(config.paths.cache, cache_name)):
                    debug(D, "[%s][%d] Cache file trovato", self.addr, self.dbgnum)
                    fp=open(os.path.join(config.paths.cache, cache_name), "rb")
                    t=readtime(fp)
                    if t > time.time():
                        gzip=fp.read()
                        recreate=False
                    fp.close()
                if recreate:
                    debug(D, "[%s][%d] Cache '%s' scaduta", self.addr, self.dbgnum, rel)
                    src=open(page, "r")
                    data=src.read()
                    src.close()
                    fp=open(os.path.join(config.paths.cache, cache_name), "wb")
                    if cfg.force_cache_validity: t=time.time()+cfg.force_cache_validity
                    else: t=time.time()+config.cache.pages_validity
                    writetime(fp, t)
                    gzip=shared.get_gzip(data, q)
                    fp.write(gzip)
                    fp.close()
            else:
                src=open(page, "r")
                data=src.read()
                src.close()
                gzip=shared.get_gzip(data, q)
            return Page(gzip[10:-8] if comp == "deflate" else gzip, struct.unpack("<L", gzip[-4:])[0], comp)
        except BaseException as e:
            debug(W, "[%s][%d] Errore durante la lettura/compressione dati", self.addr, self.dbgnum)
            shared.createTraceback(e, "[%s][%d][preparePage]"%(self.addr, self.dbgnum))
        return False
    def prepareFile(self, fname, rel, cfg):
        if cfg.force_compression: compr=cfg.force_compression
        else: compr=self.compression
        mime=mimetypes.guess_type(fname)[0] or ""
        size=os.stat(fname).st_size
        if compr == "identity":
            try:
                f=open(fname, "rb")
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
                yield [size, mime, hdr, compr]
                while 1:
                    if min+config.buffers.send_buffer > max:
                        yield f.read()
                        break
                    else:
                        yield f.read(config.buffers.send_buffer)
                        min+=config.buffers.send_buffer
                f.close()
            except BaseException as e:
                shared.createTraceback(e, "[%s][%d][prepareFile]"%(self.addr, self.dbgnum))
                yield False
            raise StopIteration
        q=cfg.force_compression_quality
        cache=False
        recreate=True
        comp=shared.Compressor(q)
        if (size < config.cache.large_files_low_size and config.cache.use and (config.cache.on_files or cfg.force_cache_state == 1) and not cfg.force_cache_state == -1) \
         or \
         (size >= config.cache.large_files_low_size and config.cache.use and (config.cache.on_large_files or cfg.force_cache_state == 1) and not cfg.force_cache_state == -1):
            large = size < config.cache.large_files_low_size
            cache=True
            cache_name=rel.replace("_", "__").replace("/", "_")
            if os.path.exists(os.path.join(config.paths.cache, cache_name)):
                debug(D, "[%s][%d] Cache file trovato", self.addr, self.dbgnum)
                fp=open(os.path.join(config.paths.cache, cache_name), "rb")
                t=readtime(fp)
                if t > time.time():
                    recreate=False
            if recreate:
                debug(D, "[%s][%d] Cache '%s' scaduta", self.addr, self.dbgnum, rel)
                src=open(fname, "rb")
                fp=open(os.path.join(config.paths.cache, cache_name), "wb")
                if cfg.force_cache_validity: t=time.time()+cfg.force_cache_validity
                elif large: t=time.time()+config.cache.lfiles_validity
                else: t=time.time()+config.cache.files_validity
                writetime(fp, t)
                fp.write("\x1f\x8b\x08\x00"+struct.pack("<L", long(time.time()))+"\x00\xff")
        try:
            if cache:
                if recreate:
                    yield [-1, mime, "200 OK", compr]
                    if compr == "gzip": yield "\x1f\x8b\x08\x00"+struct.pack("<L", long(time.time()))+"\x00\xff"
                    while size > 0:
                        data=src.read(config.buffers.send_buffer)
                        data=comp.compress(data)
                        fp.write(data)
                        yield data
                        size-=config.buffers.send_buffer
                    yield comp.finish()
                    if compr == "gzip": yield struct.pack("<LL", comp.crc32, comp.size)
                    src.close()
                else:
                    yield [size, mime, "200 OK", compr]
                    data=fp.read(10)
                    if compr == "gzip": yield data
                    while 1:
                        if size - config.buffers.send_buffer > 8:
                            data=fp.read(config.buffers.send_buffer)
                        else:
                            data=fp.read(size-config.buffers.send_buffer)
                        yield data
                        size-=len(data)
                        if len(data) < config.buffers.send_buffer: break
                    if compr == "gzip": yield fp.read()
                fp.close()
            else:
                fp=open(fname, "rb")
                while 1:
                    yield [-1, mime, "200 OK", compr]
                    if compr == "gzip": yield "\x1f\x8b\x08\x00"+struct.pack("<L", long(time.time()))+"\x00\xff"
                    while size > 0:
                        data=fp.read(config.buffers.send_buffer)
                        data=comp.compress(data)
                        yield data
                        size-=config.buffers.send_buffer
                    yield comp.finish()
                    if compr == "gzip": yield struct.pack("<LL", comp.crc32, comp.size)
        except GeneratorExit:
            pass
        except BaseException as e:
            shared.createTraceback(e, "[%s][%d][prepareFile]"%(self.addr, self.dbgnum))
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
                background-image: url('/pyserverback.png');
                position: fixed;
                background-repeat: no-repeat;
                background-size: cover;
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
        p=Page(template, len(template), "identity")
        self.cl.send("HTTP/1.1 "+s+"\r\nLocation: %s\r\nContent-Length: %d\r\nContent-Type: text/html; charset=%s\r\nContent-Encoding: %s\r\n%sConnection: close\r\n\r\n"%(self.header("Host"), p.size(), self.coding.upper(), p.compression(), shared.generateDate()))
        if self.request!="HEAD": self.cl.send(str(p))
        self.cl.close()
        self.state=self.S_TERMINATED

if config.http.use:
    serv=Server(config.http.port, config.http.backlog, False)
    serv.start()
else: serv=None

if config.https.use and have_openssl:
    sserv=Server(config.https.port, config.https.port, True)
    sserv.start()
else: sserv=None

if not serv and not sserv:
    debug(E, "Almeno uno dei server HTTP/S deve essere attivo: uscita")
    exit(1)

s=serv or sserv
i=""
while 1:
    i=raw_input()
    if i=="quit" or i=="q" or i=="exit": break
    elif i=="http" and serv:
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
    elif i=="discon" or i=="d":
        for x in range(len(s.clients)):
            s.clients[x].controller.state=Client.S_TERMINATED
        print "Tutti i client disconnessi"

if serv: serv.stop()
if sserv: sserv.stop()

for thread in enumerate():
    try:
        thread._Thread__stop()
    except:
        debug(W, "Impossibile terminare il thread '%s'", thread.getName())

if DebugFile: DebugFile.close()

sys.stdout.unregisterAll()
sys.stderr.unregisterAll()
sys.stdin.unregisterAll()

sys.stdout=sys.__stdout__
sys.stderr=sys.__stderr__
sys.stdin=sys.__stdin__


