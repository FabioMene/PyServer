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

# La classe MultiStream e' un interfaccia file che permette di associare un input/output
# ad ogni thread con riferimento allo stesso thread

import threading

class MultiStream:
    def __init__(self):
        self.bindings={}
        self.unregistered=None
    def __repr__(self):
        return "<open multifile (%d threads) at 0x%x>"%(len(self.bindings), id(self))
    def registerThread(self, file):
        self.bindings[threading.currentThread().getName()] = file
    def registerThreadName(self, name, file):
        self.bindings[name] = file
    def unregisterThread(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            del self.bindings[name]
    def unregisterThreadName(self, name):
        if name in self.bindings:
            del self.bindings[name]
    def unregisterAll(self): self.bindings.clear()
    def registerUnregisteredDefaultStream(self, file):
        self.unregistered = file
    def unregisterUnregisteredDefaultStream(self):
        self.unregistered = file
    @property
    def filename(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            return self.bindings[name].filename
        elif self.unregistered: return self.unregistered.filename
        return ""
    def write(self, data):
        name=threading.currentThread().getName()
        if name in self.bindings:
            return self.bindings[name].write(data)
        elif self.unregistered: return self.unregistered.write(data)
        return 0
    def read(self, size=-1):
        name=threading.currentThread().getName()
        if name in self.bindings:
            return self.bindings[name].read(size)
        elif self.unregistered: return self.unregistered.read(size)
        return ""
    def readline(self, size=-1):
        name=threading.currentThread().getName()
        if name in self.bindings:
            return self.bindings[name].readline(size)
        elif self.unregistered: return self.unregistered.readline(size)
        return ""
    def readlines(self, size=-1):
        name=threading.currentThread().getName()
        if name in self.bindings:
            return self.bindings[name].readlines(size)
        elif self.unregistered: return self.unregistered.readlines(size)
        return []
    @property
    def closed(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            return self.bindings[name].closed
        elif self.unregistered: return self.unregistered.closed
        return True
    def close(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            self.bindings[name].close()
        elif self.unregistered: self.unregistered.close()
    def flush(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            self.bindings[name].flush()
        elif self.unregistered: self.unregistered.flush()
    def fileno(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            return self.bindings[name].fileno()
        elif self.unregistered: return self.unregistered.fileno()
        raise AttributeError()
    def rewind(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            self.bindings[name].rewind()
        elif self.unregistered: self.unregistered.rewind()
    def readable(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            self.bindings[name].readable()
        elif self.unregistered: self.unregistered.readable()
    def writable(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            self.bindings[name].writable()
        elif self.unregistered: self.unregistered.writeable()
    def seekable(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            self.bindings[name].seekable()
        elif self.unregistered: self.unregistered.seekable()
    def seek(self, pos, whence=0):
        name=threading.currentThread().getName()
        if name in self.bindings:
            self.bindings[name].seek(pos, whence)
        elif self.unregistered: self.unregistered.seek(pos, whence)
    def tell(self):
        name=threading.currentThread().getName()
        if name in self.bindings:
            return self.bindings[name].tell()
        elif self.unregistered: self.unregistered.tell()
        return 0L

class NullFile:
    def __init__(self):
        self._closed=False
    def __repr__(self):
        return "<NullFile at 0x%x>"%(id(self))
    def filename(self): return ""
    def write(self, data): return len(data)
    def read(self, size=-1): return ""
    def readline(self, size=-1): return "\n"
    def readlines(self, size=-1): return []
    def closed(self): return self._closed
    def close(self): self._closed=True
    def flush(self): pass
    def fileno(self): raise AttributeError()
    def rewind(self): pass
    def readable(self): return True
    def writable(self): return True
    def seekable(self): return True
    def seek(self, pos, whence=0): pass
    def tell(self): return 0L
