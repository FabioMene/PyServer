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

# Parser PyMl

import os, sys, shared, copy, struct, zlib, time
from multistream import NullFile

config={}

class Document(shared.Dict):
    def __init__(self, page, req, args, post, hdr):
        shared.Dict.__init__(self)
        self.request=req
        self.url=page+"?"+args
        if args=="": args={}
        else:
            t={}
            for s in args.split("&"):
                v=s.split("=")
                if len(v)==1: t[v[0]]=""
                else: t[v[0]]=shared.decodeurl(v[1])
            args=t
        self.args=shared.Dict(args)
        if not post:
            self.rawpost=""
            post={}
        else:
            t={}
            self.rawpost=post
            for s in post.split("&"):
                v=s.split("=")
                if len(v)==1: t[v[0]]=""
                else: t[v[0]]=shared.decodeurl(v[1])
            post=t
        self.post=shared.Dict(post)
        self.header=hdr

class Stream(shared.Dict):
    def __init__(self, client, req):
        shared.Dict.__init__(self)
        self.__request=req
        self.socket=client
        self.__wait=True
        self.queued_data=""
        self.queued_data_size=0
        self.__comptype="identity"
        self.__compdata=None
        self.header=shared.Header({"Content-Encoding": "identity", "Content-Type": "text/html;charset=utf-8"})
        self.header.request="200 OK"
        self.n_is_br=True
        self.__hdrsent=False
    def write_plain(self, data, final=False):
        segm=self.__compress(data, final)
        self.__send(segm)
    def write(self, data, final=False):
        if not data:
            self.__send("")
            return 0
        if data[-1] == "\n": data=data[:-1]
        segm=""
        i, l=0, len(data)
        while i < l:
            add=1
            if data[i]=="\\":
                add=2
                if i == l-1:
                    return "Errore(PyMl Parser): Sequenza \"\\\" non terminata<br />"
                elif data[i+1] == "\n": pass
                elif data[i+1] == "n": segm+="\n"
                elif data[i+1] == "t": segm+="\t"
                elif data[i+1] == "\\": segm+="\\"
                elif data[i+1] == "\"": segm+="\""
                elif data[i+1] == "\'": segm+="\'"
                elif data[i+1] == "x":
                    if i+4 >= l:
                        return "Errore(PyMl Parser): Sequenza esadecimale \"\\xnn\" non terminata<br />"
                    try:
                        segm+=chr(int(data[i+2:i+4], 16))
                        add=4
                    except:
                        return "Errore(PyMl Parser): Sequenza esadecimale \"\\x%s\" non valida<br />"%(data[i+2:i+4])
                elif data[i+1] >= "0" and data[i+1] <= "9":
                    if i+4 >= l:
                        return "Errore(PyMl Parser): Sequenza ottale \"\\nnn\" non terminata<br />"
                    try:
                        segm+=chr(int(data[i+1:i+4], 8))
                        add=4
                    except:
                        return "Errore(PyMl Parser): Sequenza ottale \"\\%s\" non valida<br />"%(data[i+1:i+4])
                else:
                    return "Errore(PyMl Parser): Sequenza \"%s\" non valida<br />"%(data[i+1])
            else: segm+=data[i]
            i+=add
        if self.n_is_br: segm=segm.replace("\n", "<br />")
        l=len(segm)
        segm=self.__compress(segm, final)
        self.__send(segm)
        return l
    def __send(self, data):
        if self.__wait:
            self.queued_data+=data
            self.queued_data_size+=len(data)
        else:
            if not self.__hdrsent:
                if not self.header("Date"): self.header("Date", shared.generateDate()[6:-2])
                self.socket.send(self.header.build())
                self.__hdrsent=True
                if self.__comptype == "gzip" and self.__request != "HEAD":
                    self.socket.send("\x1f\x8b\x08\x00"+struct.pack("<L", long(time.time()))+"\x00\xff") #GZIP Header (deflate, unknown, mtime)
            if self.__request != "HEAD":
                while self.queued_data:
                    self.socket.send(self.queued_data[:config.buffers.send_buffer])
                    self.queued_data=self.queued_data[config.buffers.send_buffer:]
                self.queued_data=""
                self.queued_data_size=0
                while data:
                    self.socket.send(data[:config.buffers.send_buffer])
                    data=data[config.buffers.send_buffer:]
    def setCompressMode(self, comp, quality=5):
        if self.__hdrsent: return
        self.__comptype=comp
        self.__compdata=None
        if   comp == "identity": pass
        elif comp == "deflate":
            self.__compdata=zlib.compressobj(quality)
        elif comp == "gzip":
            self.__compdata=[zlib.compressobj(quality, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0), 0, 0]
        else:
            raise ValueError("Tipo di compressione '%s' non supportata"%comp)
        self.header("Content-Encoding", comp)
    def __compress(self, data, final=False):
        if self.__comptype   == "identity": return data
        elif self.__comptype == "deflate":
            out=self.__compdata.compress(data)
            if final:
                out+=self.__compdata.flush(zlib.Z_FINISH)
            return out
        elif self.__comptype == "gzip":
            out=self.__compdata[0].compress(data)
            self.__compdata[1]+=len(data)
            self.__compdata[2]=zlib.crc32(data, self.__compdata[2]) & 0xffffffffL
            if final:
                out+=self.__compdata[0].flush(zlib.Z_FINISH)
                out+=struct.pack("<LL", self.__compdata[2], self.__compdata[1] & 0xffffffffL)
            return out
    def setWait(self, mode):
        self.__wait=mode
    def flush(self):
        if self.__comptype   == "identity": return
        elif self.__comptype == "deflate":
            out=self.__compdata.flush(zlib.Z_SYNC_FLUSH)
        elif self.__comptype == "gzip":
            out=self.__compdata[0].flush(zlib.Z_SYNC_FLUSH)
        self.__send(out)
    def finish(self):
        self.__send(self.__compress("", True))
    #~ def setCharset(self, ch):
        #~ try:
            #~ test="test".encode(ch)
        #~ except:
            #~ raise ValueError("Codifica '%s' non supportata"%ch)
        #~ hdr=self.header("Content-Type").split(";")
        #~ m=False
        #~ for i in range(len(hdr)):
            #~ if "charset=" in hdr[i]:
                #~ hdr[i]="charset="+ch
                #~ m=True
        #~ if not m: hdr.append("charset="+ch)
        #~ self.header("Content-Type", ";".join(hdr))
    def set_n_is_br(self, mode): self.n_is_br=mode

class PyMl_Exit_Request(BaseException):
    def __init__(self):
        pass

class PyMl:
    def __init__(self, file, req, args, post, inheader, client, configuration):
        self.env={}
        self.document=Document(file, req, args, post, inheader)
        self.stream=Stream(client, req)
        
        null=NullFile()
        sys.stdout.registerThread(self.stream)
        sys.stderr.registerThread(self.stream)
        sys.stdin.registerThread(null)
        
        self.stream.header("Location", inheader("Host") or "")
        if "gzip" in inheader("Accept-Encoding"): self.stream.setCompressMode("gzip")
        elif "deflate" in inheader("Accept-Encoding"): self.stream.setCompressMode("deflate")
        else: self.stream.setCompressMode("identity")
        self.configuration=configuration
        self.script_wd=os.path.split(file)[0]
        f=open(file)
        cont=f.readlines()
        f.close()
        for x in range(len(cont)):
            cont[x]=cont[x].replace("\n", "").replace("\r", "")
        segm=[]
        self.line=1
        self.running=True
        for l in cont:
            if not self.running:
                break
            if "<?py" in l and "?>" in l:
                before, expr, after=self.get_expression(l)
                self.stream.write_plain(before)
                self.exec_segment(expr)
                self.stream.write_plain(after)
            elif "<?py" in l:
                segm=[l]
            elif "?>" in l:
                segm.append(l)
                segm="\n".join(segm)
                before, expr, after=self.get_expression(segm)
                self.stream.write_plain(before)
                self.exec_segment(expr)
                self.stream.write_plain(after)
                segm=[]
            elif segm!=[]: segm.append(l)
            else: self.stream.write_plain(l+"\n")
            self.line+=1
        self.stream.finish()
        self.stream.header("Content-Length", self.stream.queued_data_size)
        self.stream.setWait(False)
        self.stream.write("", True)
        sys.stdout.unregisterThread()
        sys.stderr.unregisterThread()
        sys.stdin.unregisterThread()
    def get_expression(self, expr):
        bf=ex=af=""
        for x in range(len(expr)):
            bf+=expr[x]
            if bf[-4:]=="<?py": break
        if bf==expr: return (expr, "", "")
        bf=bf[:-4]
        for x in range(x+1, len(expr)):
            ex+=expr[x]
            if ex[-2:]=="?>": break
        if bf+ex==expr: return (bf, ex, "")
        return (bf, ex[:-2], expr[x+1:])
    def exec_segment(self, segm):
        segm=self.indentify(segm)
        cwd=os.getcwd()
        os.chdir(self.script_wd)
        argv=copy.deepcopy(sys.argv)
        sys.argv=[]
        err=""
        try:
            self.execute(segm)
        except BaseException as e:
            if type(e) == PyMl_Exit_Request:
                self.running=False
            else:
                err=str(e)
        os.chdir(cwd)
        sys.argv=copy.deepcopy(argv)
        if err: self.stream.write_plain("Errore(PyMl Parser): %d: %s<br />"%(self.line, err))
        import sys as private_sys
        quit=exit=private_sys.exit
        del private_sys
    def exit(self):
        raise PyMl_Exit_Request()
    def execute(donotdelete, segmenttonotdelete):
        document=donotdelete.document
        configuration=donotdelete.configuration
        stream=donotdelete.stream
        for x in donotdelete.env:
            exec("%s = donotdelete.env[\"%s\"]"%(x, x))
        quit=donotdelete.exit
        exit=donotdelete.exit
        # # # # # # # # # # # # #
        exec(segmenttonotdelete)
        # # # # # # # # # # # # #
        for x in dir():
            if x=="x" or x=="donotdelete" or x=="segmenttonotdelete" or x=="outtonotdelete" or x=="document" or x=="stream" or x=="quit" or x=="exit": pass
            else: exec("donotdelete.env[\"%s\"] = %s"%(x, x))
        donotdelete.document=document
        donotdelete.stream=stream
    def indentify(self, segm):
        out=""
        ind=0
        for x in segm:
            if x!="\n": break
            segm=segm[1:]
        for x in segm:
            if x!=" ": break
            ind+=1
        for x in segm.split("\n"):
            out+=x[ind:]+"\n"
        return out
