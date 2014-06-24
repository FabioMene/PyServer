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


#interprete Python Markup Language

import os, sys, shared, copy

class FakeStdout:
    def __init__(self):
        self.stream=""
        self.substbr=False
    def write(self, orig_data):
        if orig_data[-1]=="\n": orig_data=orig_data[:-1]
        if self.substbr:
            orig_data=orig_data.replace("\n", "<br />")
        segm=""
        i, l=0, len(orig_data)
        while i < l:
            add=1
            if orig_data[i]=="\\":
                add=2
                if i == l-1:
                    return "Errore(PyMl Parser): %d: Sequenza \"\\\" non terminata<br />"%(self.line)
                elif orig_data[i+1] == "\n": pass
                elif orig_data[i+1] == "n": segm+="\n"
                elif orig_data[i+1] == "t": segm+="\t"
                elif orig_data[i+1] == "\\": segm+="\\"
                elif orig_data[i+1] == "\"": segm+="\""
                elif orig_data[i+1] == "\'": segm+="\'"
                elif orig_data[i+1] == "x":
                    if i+4 >= l:
                        return "Errore(PyMl Parser): Sequenza esadecimale \"\\xnn\" non terminata<br />"
                    try:
                        segm+=chr(int(orig_data[i+2:i+4], 16))
                        add=4
                    except:
                        return "Errore(PyMl Parser): Sequenza esadecimale \"\\x%s\" non valida<br />"%(orig_data[i+2:i+4])
                elif orig_data[i+1] >= "0" and orig_data[i+1] <= "9":
                    if i+4 >= l:
                        return "Errore(PyMl Parser): Sequenza ottale \"\\nnn\" non terminata<br />"
                    try:
                        segm+=chr(int(orig_data[i+1:i+4], 8))
                        add=4
                    except:
                        return "Errore(PyMl Parser): Sequenza ottale \"\\%s\" non valida<br />"%(orig_data[i+1:i+4])
                else:
                    return "Errore(PyMl Parser): Sequenza \"%s\" non valida<br />"%(orig_data[i+1])
            else: segm+=orig_data[i]
            i+=add
        self.stream+=segm
    def flush(self): pass

class Dict(dict):
    def __init__(self, e):
        dict.__init__(self, e)
    def __getattr__(self, name):
        if name in self: return self[name]
        return ""
    def __str__(self):
        out=[]
        for x in self.__el: out+=["%s=%s"%(x, self.__el[x])]
        return "&".join(out)

class Document:
    _sbr=False
    def __init__(self, page, args, post, hdr):
        self.url=page+"?"+args
        if args=="": args={}
        else:
            t={}
            for s in args.split("&"):
                v=s.split("=")
                if len(v)==1: t[v[0]]=""
                else: t[v[0]]=shared.decodeurl(v[1])
            args=t
        self.args=Dict(args)
        if not post:
            self.request="GET"
            post={}
        else:
            t={}
            self.rawpost=post
            self.request="POST"
            for s in post.split("&"):
                v=s.split("=")
                if len(v)==1: t[v[0]]=""
                else: t[v[0]]=shared.decodeurl(v[1])
            post=t
        self.post=Dict(post)
        self.header=hdr
    def substbr(self, val=None):
        if val!=None:
            self._sbr=val
            self.stdout.substbr=self._sbr
        return self._sbr
    def setstdout(self, v):
        self._stdout=v
        self._stdout.substbr=self._sbr
    def getstdout(self):
        return self._stdout
    stdout=property(getstdout, setstdout)
class PyMl:
    __all__=["output"]
    def __init__(self, fn, args, post, header, **data):
        self.data=Dict(data)
        self.env={}
        self.document=Document(fn, args, post, header)
        self.output=""
        self.script_wd=os.path.split(fn)[0]
        f=open(fn)
        cont=f.readlines()
        f.close()
        for x in range(len(cont)):
            cont[x]=cont[x].replace("\n", "").replace("\r", "")
        segm=[]
        self.line=1
        for l in cont:
            if "<?py" in l and "?>" in l:
                before, expr, after=self.get_expression(l)
                self.output+=before
                self.output+=self.exec_segment(expr)
                self.output+=after
            elif "<?py" in l:
                segm=[l]
            elif "?>" in l:
                segm.append(l)
                segm="\n".join(segm)
                before, expr, after=self.get_expression(segm)
                self.output+=before
                self.output+=self.exec_segment(expr)
                self.output+=after
                segm=[]
            elif segm!=[]: segm.append(l)
            else: self.output+=l+"\n"
            self.line+=1
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
        f=FakeStdout()
        self.document._stdout=f
        try:
            self.execute(segm, f)
            err=""
        except Exception as e:
            err=str(e)
        os.chdir(cwd)
        sys.argv=copy.deepcopy(argv)
        out=""
        if err: out+="Errore(PyMl Parser): %d: %s<br />"%(self.line, err)
        return out+f.stream
    def execute(donotdelete, segmenttonotdelete, outtonotdelete):
        for x in donotdelete.env:
            exec("%s = donotdelete.env[\"%s\"]"%(x, x))
        import sys
        sys.stdout=outtonotdelete
        del sys
        document=donotdelete.document
        exec(segmenttonotdelete)
        for x in dir():
            if x=="x" or x=="donotdelete" or x=="segmenttonotdelete" or x=="outtonotdelete" or x=="document": pass
            else: exec("donotdelete.env[\"%s\"] = %s"%(x, x))
        import sys
        sys.stdout=sys.__stdout__
        del sys
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
