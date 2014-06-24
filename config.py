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

# File di configurazione per PyServer (>= 2.0.1)

#Abilita/disabilita debug
#Livelli: D, I, W, E
DEBUG="I"
DEBUG_COLORS=False
DEBUG_FILE="PyServer.log"
DEBUG_FILE_APPEND_MODE=False

#Priorita' ricerca index
INDEX_ORDER=[".pyml", ".pyhtml", ".html", ".htm"]

#Percorso file
WEBDISK_PATH="webdisk"

#Comportamento alla mancanza di Content-Length in POST
POST_UNDEFINED_LENGTH_CHUNK_SIZE=128
POST_RECEIVE_BUFFER_SIZE=16384

#dimensione uploads
FILE_UPLOAD_CHUNK_SIZE=2048

#Configurazione porte
HTTP_PORT=8080
HTTP_BACKLOG=256

HTTPS_ENABLED=False
HTTPS_PORT=8443
HTTPS_BACKLOG=128
HTTPS_KEY=""
HTTPS_CERT=""

