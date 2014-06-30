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


#Utility varie ed eventuali

import time, config, os, sys, zlib, struct, re

I="Info"
W="Warn"
E="Err "
D="Dbg "

def decodeurl(data):
    #Se piu' dell'1% del file contiene caratteri non in [32, 126] viene contrassegnato come binario
    nonc=0
    for c in data:
        if ord(c) < 32 or ord(c) > 126: nonc+=1
    if nonc >= len(data)/100.0: return data
    #application/x-www-form-urlencoded
    out=""
    l=len(data)
    i=0
    while i < l:
        if data[i]=="%":
            if i+2 >= l:
                print "Errore(PyMl formdata-decoder): Stringa malformata"
                return out
            else:
                try:
                    out+=chr(int(data[i+1:i+3], 16))
                except:
                    print "Errore(PyMl formdata-decoder): Stringa malformata"
                    return out
            i+=2
        else: out+=data[i]
        i+=1
    return out

class Dict(dict):
    def __init__(self, e={}):
        dict.__init__(self, e)
    def __getattr__(self, name):
        if name in self: return self[name]
        return ""
    def __getitem__(self, item):
        if item in self: return dict.__getitem__(self, item)
        return ""
    def __setattr__(self, name, val):
        self[name]=val
    def __str__(self):
        out=[]
        for x in self.__el: out+=["%s=%s"%(x, self.__el[x])]
        return "&".join(out)

class ServerConfiguration(Dict):
    def __init__(self, f):
        Dict.__init__(self)
        for cat in config.DEFAULT_CONFIG:
            self[cat]=Dict()
            for elem in config.DEFAULT_CONFIG[cat]:
                self[cat][elem]=config.DEFAULT_CONFIG[cat][elem]
        try:
            fp=open(f)
            d=fp.read().split("\n")
            fp.close()
        except:
            debug(E, "[INIT] [ServConf] File di configurazione non trovato!")
            return
        cc=0
        for i in range(len(d)):
            l=d[i]
            if len(l)==0 or l[0]=="#": pass
            elif l[0]=="[" and l[-1]=="]":
                cc=l[1:-1]
                if cc not in config.DEFAULT_CONFIG:
                    debug(E, "[INIT] [ServConf] %d: La categoria '%s' non appartiene alla configurazione", i+1, cc)
                    return
            else:
                if "=" in l:
                    n, a=l.split("=")
                    if n not in config.DEFAULT_CONFIG[cc]:
                        debug(E, "[INIT] [ServConf] %d: '%s' non appartiene alla categoria '%s'", i+1, n, cc)
                        return
                    t=type(config.DEFAULT_CONFIG[cc][n])
                    if t == bool:
                        if a.lower() in ["vero", "true", "1", "si", "yes"]: a=True
                        elif a.lower() in ["falso", "false", "0", "no"]: a=False
                        else:
                            debug(E, "[INIT] [ServConf] %d: Valore booleano '%s' non valido!", i+1, a)
                            a=config.DEFAULT_CONFIG[cc][n]
                    else:
                        try:
                            if t == list or t == tuple: a=eval(a)
                            else: a=t(a)
                        except:
                            val="stringa"
                            if   t == int:   val="intero"
                            elif t == long:  val="intero(64)"
                            elif t == float: val="decimale"
                            elif t == list or t == tuple: val="lista"
                            else: val="(sconosciuto)"
                            debug(E, "[INIT] [ServConf] %d: Valore %s '%s' non valido!", i+1, val, a)
                            a=config.DEFAULT_CONFIG[cc][n]
                    self[cc][n]=a
                else:
                    debug(E, "[INIT] [ServConf] %d: Non sono consentiti valori senza nome", i+1)
                    return
    def __getattribute__(self, name):
        if name in self: return self[name]
        return Dict()
    def __getitem__(self, item):
        if item in self: return dict.__getitem__(self, item)
        return Dict()

DEFAULT_ATTRIBUTES={
    "receive_post":              [bool, True],
    "force_cache_state":         [int, 0],
    "force_compression":         [str, ""],
    "force_compression_quality": [int, 5],
    "force_cache_validity":      [int, 0]
}

class FileConfiguration(Dict):
    def __init__(self, f):
        Dict.__init__(self)
        try:
            fp=open(f)
            d=fp.read().split("\n")
            fp.close()
        except IOError:
            debug(D, "[FConf] [Info] File di configurazione non presente in '%s'", os.path.split(f)[0])
            return
        cc=0
        for i in range(len(d)):
            l=d[i]
            if len(l)==0 or l[0]=="#": pass
            elif l[0]=="[" and l[-1]=="]":
                cc=l[1:-1]
                self[cc]=Dict()
                for p in DEFAULT_ATTRIBUTES:
                    self[cc][p]=DEFAULT_ATTRIBUTES[p][1]
                self[cc]["list"]=Dict()
            else:
                if "=" in l:
                    n, a=l.split("=")
                    if n in DEFAULT_ATTRIBUTES:
                        if DEFAULT_ATTRIBUTES[n][0] == bool:
                            if a.lower() in ["vero", "true", "1", "si", "yes"]: a=True
                            elif a.lower() in ["falso", "false", "0", "no"]: a=False
                            else:
                                debug(E, "[FConf] [Err] %s: %d: Valore booleano '%s' non valido!", f, i+1, a)
                                a=DEFAULT_ATTRIBUTES[n][1]
                        else:
                            try:
                                a=DEFAULT_ATTRIBUTES[n][0](a)
                            except:
                                val="stringa"
                                if   DEFAULT_ATTRIBUTES[n][0] == int:   val="intero"
                                elif DEFAULT_ATTRIBUTES[n][0] == long:  val="intero(64)"
                                elif DEFAULT_ATTRIBUTES[n][0] == float: val="decimale"
                                else: val="(sconosciuto)"
                                debug(E, "[FConf] [Err] %s: %d: Valore %s '%s' non valido!", f, i+1, val, a)
                                a=DEFAULT_ATTRIBUTES[n][1]
                    self[cc][n]=a
                else:
                    self[cc].list=cat[cc].list+[l]
    def __getattribute__(self, name):
        for cat in self:
            if cat == name: return dict.__getitem__(self, name)
            elif cat.startswith("re:") and re.match(cat[3:], name): return dict.__getitem__(self, cat)
            elif re.match("^"+cat.replace(".", "\\.").replace("*", ".*").replace("?", ".")+"$", name): return dict.__getitem__(self, cat)
        d={}
        for e in DEFAULT_ATTRIBUTES:
            d[e]=DEFAULT_ATTRIBUTES[e][1]
        return Dict(d)
    def __getitem__(self, item):
        for cat in self:
            if cat == item: return dict.__getitem__(self, item)
            elif cat.startswith("re:") and re.match(cat[3:], item): return dict.__getitem__(self, cat)
            elif re.match("^"+cat.replace(".", "\\.").replace("*", ".*").replace("?", ".")+"$", item): return dict.__getitem__(self, cat)
        d={}
        for e in DEFAULT_ATTRIBUTES:
            d[e]=DEFAULT_ATTRIBUTES[e][1]
        return Dict(d)

def readConfig(f):
    try:
        return FileConfiguration(f)
    except Exception as e: print e
    return None

class Header:
    def __init__(self, data):
        self.request=""
        self.data=data
    def __call__(self, field, data=None):
        if field in ["request", "response"] and data: self.request=data
        elif data != None:
            self.data[field]=str(data)
        if self.data.has_key(field): return self.data[field]
        elif field in ["request", "response"]: return self.request
        return ""
    def build(self):
        out="HTTP/1.1 "+self.request+"\r\n"
        for x in self.data:
            out+=x+": "+self.data[x]+"\r\n"
        return out+"\r\n"

def generateHeader(list):
    d={}
    for i in list[1:]:
        p=i.split(": ")
        try: d[p[0]]=p[1]
        except: d[p[0]]=""
    return Header(d)

def generateDate(t=time.time()):
    days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    t=time.gmtime(t)
    return "Date: %s, %d %s %d %d:%d:%d GMT\r\n"%(days[t.tm_wday], t.tm_mday, months[t.tm_mon-1], t.tm_year, t.tm_hour, t.tm_min, t.tm_sec)

def createTraceback(exc, tag):
    t, o, tb=sys.exc_info()
    i=0
    while tb:
        if tb.tb_next: print("%s %s%s: %d: Causato da"%(tag, "-"*i, os.path.split(tb.tb_frame.f_code.co_filename)[1], tb.tb_lineno))
        else: print("%s %s%s: %d: %s"%(tag, "-"*i, os.path.split(tb.tb_frame.f_code.co_filename)[1], tb.tb_lineno, exc.message))
        tb=tb.tb_next
        i+=1

class Compressor:
    def __init__(self, quality=5):
        self.comp=zlib.compressobj(quality, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
        self.crc32=0
        self.size=0
    def compress(self, data):
        out =self.comp.compress(data)
        out+=self.comp.flush(zlib.Z_SYNC_FLUSH)
        self.crc32=zlib.crc32(data, self.crc32) & 0xffffffffL
        self.size+=len(data)
        self.size&=0xffffffffL
        return out
    def finish(self):
        return self.comp.flush(zlib.Z_FINISH)

def get_gzip(data, quality=5):
    comp=Compressor(quality)
    d=comp.compress(data)+comp.finish()
    out = "\x1f\x8b\x08\x00"+struct.pack("<L", long(time.time()))+"\x00\xff"
    out+= d
    out+= struct.pack("<LL", comp.crc32, comp.size)
    return out



