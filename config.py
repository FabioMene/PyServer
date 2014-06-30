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

# Configurazione di default

DEFAULT_CONFIG={
    # debug
    "debug": {
        "level":       "I",   # livello di debug: D (Debug), I (Info), W (Attenzione), E (Errore)
        "use_colors":  False, # Utilizza colorazione livelli su terminali vt100 (o compatibili)
        "file_append": False  # Accoda il debug al file (config.paths.debug) invece che sovrascriverlo
    },

    #Percorso file
    "paths": {
        "debug":      "PyDebug.log",                   # File di debug
        "webdisk":    "webdisk",                       # HD Virtuale
        "folder_cfg": ".pyserver.folder_options.conf", # nome dei file di configurazione cartella
        "cache":      "tmp",                           # Posizione copie cache
        "https_key":  "",                              # Chiave privata SSL
        "https_cert": ""                               # Certificato pubblico SSL
    },

    #Comportamento alla mancanza di Content-Length in POST
    "buffers": {
        "post_undefined_length": 128,  # Content-Length in POST non definito
        "send_buffer":           2048, # Buffer di invio
        "tcp_receive_buffer":    32768 # Buffer di ricezione (Non dovrebbe essere superiore a 65536)
    },

    #Caching pagine e file
    "cache": {
        "use":                  True,        # Abilita cache
        "on_pages":             True,        # Abilita caching delle pagine. Puo' essere bypassato con opt->force_cache_state
        "pages_validity":       300,         # Validita' delle copie cache delle pagine in secondi dalla creazione
        "on_files":             True,        # Abilita caching dei file. Puo' essere bypassato con opt->force_cache_state
        "files_validity":       300,         # Validita' delle copie cache dei file in secondi dalla creazione
        "on_large_files":       False,       # Abilita caching dei file grandi. Puo' essere bypassato con opt->force_cache_state
        "large_files_low_size": 1024*1024*4, # Dimensione sopra la quale un file viene considerato grande
        "lfiles_validity":      600,         # Validita' delle copie cache dei file grandi in secondi dalla creazione
    },

    #Un po di misc non fa mai male!
    "misc": {
        "index_search_order": [".pyml", ".pyhtml", ".htm", ".html"] # Ordine di ricerca del file index
    },

    #Configurazione porte
    "http": {
        "use":     True, # Usa HTTP
        "port":    8080, # Porta HTTP
        "backlog": 256   # Coda di accettazione
    },

    "https": {
        "use":     False, # Usa HTTPS
        "port":    8443,  # Porta HTTPS
        "backlog": 128    # Coda di accettazione
    }
}
