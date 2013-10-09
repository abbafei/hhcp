#!/usr/bin/env python2
import cgi
import email
import email.parser
import wsgiref
import wsgiref.simple_server
import urlparse
import urllib
import sys
import os
import os.path
import contextlib
import getopt





def hcp_state():
    state = {'done':  False, 'exit': 0}
    def handle_http_request(environ, start_response):
        if state['done']:
            return
        rm = environ['REQUEST_METHOD']
        if rm == 'GET':
            start_response('200 ok Boruch Hashem', [('Content-Type', 'text/html')])
            yield '''<html><head></head><body>
            <form action="/" enctype="multipart/form-data" method="POST">
                <input type="file" name="zachinalach" />
                <input type="submit" />
            </form>
            </html>'''
        elif rm == 'POST':
            start_response('302 Found', [('Location', 'data:text/plain,File received. Yasher Koach!')])
            state['done'] = True
            if 'multipart/form-data' in environ['CONTENT_TYPE']:
                '''
                def reader(f, length=None, chunk_size=512):
                    if length is None:
                        return iter(lambda: f.read(chunk_size), '')
                    else:
                        def wl():
                            r = 0
                            while r < length:
                                rs = ((length % chunk_size) if (chunk_size > (length - r)) else chunk_size)
                                yield f.read(rs)
                                r += rs
                        return wl()


                fpsr = email.parser.FeedParser()
                fpsr.feed('Content-Type: {ct}\r\n\r\n'.format(ct=environ['CONTENT_TYPE']))
                for c in reader(environ['wsgi.input'], length=(int(environ['CONTENT_LENGTH']) if (('CONTENT_LENGTH' in environ) and (environ['CONTENT_LENGTH'] != "")) else None)):
                    fpsr.feed(c)
                m = fpsr.close()
                if m.is_multipart:
                    for p in m.walk():
                        pname = p.get_param('name', failobj="", header='Content-Disposition')
                        if (email.utils.collapse_rfc2231_value(pname) == 'zachinalach') and (not p.is_multipart()):
                            with os.fdopen(sys.stdout.fileno(), 'wb') as f:
                                for l in email.iterators.body_line_iterator(p, decode=True):
                                    f.write(l)
                '''
                fs = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)['zachinalach']
                if fs.file:
                    with os.fdopen(sys.stdout.fileno(), 'wb') as f:
                        try:
                            for c in wsgiref.util.FileWrapper(fs.file):
                                f.write(c)
                        except IOError as e:
                            if e.errno in (9, 32):
                                sys.stderr.write('{0}\n'.format(str(e)))
                                state['exit'] = 2
                            else:
                                raise
    return (lambda k: state[k], handle_http_request)


def cph_state(ifile=None):
    state = {'done':  False, 'exit': 0}
    if ifile and ((not os.path.exists(ifile)) or os.path.isdir(ifile)):
        raise IOError('{0} is not an acceptable file.'.format(ifile))
    file_name_frag = urllib.quote_plus('file' if ifile is None else os.path.basename(ifile))
    clen = (os.path.getsize(ifile) if ifile is not None and os.path.isfile(ifile) else None)

    def handle_http_request(environ, start_response):
        if state['done']:
            return
        rm = environ['REQUEST_METHOD']
        if rm == 'GET':
            sn = environ['PATH_INFO']
            if sn == '{0}{1}'.format('/', file_name_frag):
                start_response('200 ok Boruch Hashem', [('Content-Type', 'application/octet-stream')] + ([] if clen is None else [('Content-Length', str(clen))]))
                state['done'] = True
                try:
#                    with contextlib.closing(wsgiref.util.FileWrapper(os.fdopen(sys.stdin.fileno(), 'rb') if ifile is None else open(ifile, 'rb'))) as wf:
#                        for c in wf:
#                            yield c
                    #return (environ['wsgi.file_wrapper'] if 'wsgi.file_wrapper' in environ else wsgiref.util.FileWrapper)(os.fdopen(sys.stdin.fileno(), 'rb') if ifile is None else open(ifile, 'rb'))
                    return wsgiref.util.FileWrapper(os.fdopen(sys.stdin.fileno(), 'rb') if ifile is None else open(ifile, 'rb'))
                finally:
                    pass
            else:
                start_response('302 Found', [('Location', '{0}{1}'.format(wsgiref.util.application_uri(environ), file_name_frag))])
                return ()
    return (lambda k: state[k], handle_http_request)


hcp = hcp_state()[1]
cph = cph_state()[1]

if not sys.stdout.isatty():
    application = hcp
elif not sys.stdin.isatty():
    application = cph
else:
    application = hcp

app = application


if __name__ == '__main__':
    get_optval = lambda params, n, default_val=None: ((params[0][tuple(i[0] for i in params[0]).index(n)][1]) if (n in frozenset(i[0] for i in params[0])) else default_val)
    get_optflag = lambda params, n: (n in frozenset(i[0] for i in params[0]))
    get_optparam = lambda params, i, default_val=None: (params[1][i] if (len(params[1]) > i) else default_val)


    progname = os.path.basename(sys.argv[0])
    if progname == 'hcp':
        called_as = 'hcp'
    elif progname == 'cph':
        called_as = 'cph'
    else:
        called_as = None
    if called_as is None:
        if len(sys.argv) > 1:
            if sys.argv[1] in ('hcp', 'cph'):
                called_as = sys.argv[1]
                params = sys.argv[1:]
    else:
        params = sys.argv

    if called_as is None:
        sys.stdout.write('Usage: {0} <cmd>\n\tcmd: "hcp" or "cph"\nOr create a symlink to this file named as <cmd>.\n\n'.format(sys.argv[0]))
    else:
        if called_as == 'hcp':
            default_port = 8000
            if (len(params) > 1) and (params[1] in ('-h', '--help', '/?')):
                sys.stdout.write('Usage: {0} [port [host]]\n\tDefault port: {default_port}\n\n'.format(params[0], default_port=str(default_port)))
            else:
                cp = hcp_state()
                host = (params[2] if (len(params) > 2) else "")
                portnum = (int(params[1]) if (len(params) > 1) else default_port)
                s = wsgiref.simple_server.make_server(host, portnum, cp[1])
                sys.stderr.write('Listening on {host}:{port}...\n'.format(host=(host if bool(len(host)) else '<default_host>'), port=str(portnum)))
                while not cp[0]('done'):
                    s.handle_request()
                exit(cp[0]('exit'))
        elif called_as == 'cph':
            default_port = 8000
            if (len(params) > 1) and (params[1] in ('-h', '--help', '/?')):
                sys.stdout.write('Usage: {0} [-p <port>] [-h <host>] [<input_file>]\n\t-p: port to listen with (default port: {default_port})\n\t-h: host to listen with\n\t<input_file>: path to input file\n\n'.format(params[0], default_port=str(default_port)))
            else:
                optparams = getopt.gnu_getopt(params[1:], 'p:h:')
                ifile = get_optparam(optparams, 0, None)
                host = get_optval(optparams, '-h', "")
                portnum = int(get_optval(optparams, '-p', default_port))
                cp = cph_state(ifile=ifile)
                s = wsgiref.simple_server.make_server(host, portnum, cp[1])
                sys.stderr.write('Listening on {host}:{port}...\n'.format(host=(host or '<default_host>'), port=str(portnum)))
                while not cp[0]('done'):
                    s.handle_request()
                exit(cp[0]('exit'))
