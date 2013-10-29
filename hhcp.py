#!/usr/bin/env python2
import cgi
import wsgiref
import wsgiref.simple_server
import urllib
import sys
import os
import os.path
import getopt
import email.header
import email.message
import StringIO
import random
import string





def stdin_filepath(in_path='/dev/stdin', in_f=sys.stdin):
    try:
        with open(in_path) as f:
            is_stdin = os.path.sameopenfile(f.fileno(), in_f.fileno())
        if is_stdin:
            lp = os.path.realpath(in_path)
            with open(lp) as f:
                pass
            return lp
        else:
            return None
    except IOError as e:
        if e.errno in (2, 6):
            return False




def hcp_state(di_file=None):
    state = {'done':  False, 'exit': 0}
    field_name = 'zachinalach'
    def handle_http_request(environ, start_response):
        if state['done']:
            return
        rm = environ['REQUEST_METHOD']
        if rm == 'GET':
            start_response('200 ok Boruch Hashem', [('Content-Type', 'text/html')])
            yield '''<html><head></head><body>
            <form action="{html_app_uri}" enctype="multipart/form-data" method="POST">
                <input type="file" name="{html_field_name}" />
                <input type="submit" />
            </form>
            </html>'''.format(**dict(('html_{0}'.format(k), cgi.escape(v, True)) for k, v in {'app_uri': "{0}/send".format(environ['SCRIPT_NAME']), 'field_name': field_name}.iteritems()))
        elif rm == 'POST':
            start_response('302 Found', [('Location', 'data:text/plain,File received.')])
            state['done'] = True
            m = email.message.Message()
            m.add_header('Content-Type', environ['CONTENT_TYPE'])
            content_type = m.get_content_type()
            fz = (lambda fs: (fs[field_name].file if ((content_type == 'multipart/form-data') and fs[field_name].file) else (StringIO.StringIO(fs.getfirst(field_name)) if (content_type == 'application/x-www-form-urlencoded') else StringIO.StringIO(''))))(fs=cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ))
            with (os.fdopen(sys.stdout.fileno(), 'wb') if (di_file is None) else open(di_file, 'ab')) as f:
                try:
                    for c in wsgiref.util.FileWrapper(fz):
                        f.write(c)
                except IOError as e:
                    if e.errno in (9, 32):
                        sys.stderr.write('{0}\n'.format(str(e)))
                        state['exit'] = 2
                    else:
                        raise
    return (lambda k: state[k], handle_http_request)


def cph_state(di_file=None):
    state = {'done':  False, 'exit': 0}
    if di_file and ((not os.path.exists(di_file)) or os.path.isdir(di_file)):
        raise IOError('{0} is not an acceptable file.'.format(di_file))
    file_name_frag = urllib.quote_plus(os.path.basename((stdin_filepath() or 'file{0}'.format(''.join(random.choice(string.digits) for _ in range(7)))) if (di_file is None) else di_file))
    clen = (os.path.getsize(di_file) if (di_file is not None) and os.path.isfile(di_file) else None)

    def handle_http_request(environ, start_response):
        if state['done']:
            return
        rm = environ['REQUEST_METHOD']
        if rm == 'GET':
            sn = environ['PATH_INFO']
            if sn == '/{0}'.format(file_name_frag):
                start_response('200 ok Boruch Hashem', [('Content-Type', 'application/octet-stream')] + ([] if clen is None else [('Content-Length', str(clen))]))
                state['done'] = True
                try:
                    return wsgiref.util.FileWrapper(os.fdopen(sys.stdin.fileno(), 'rb') if (di_file is None) else open(di_file, 'rb'))
                finally:
                    pass
            else:
                app_uri = wsgiref.util.application_uri(environ)
                start_response('302 Found', [('Location', '{0}{1}{http_filename}'.format(app_uri, ('' if app_uri.endswith('/') else '/'), http_filename=str(email.header.Header(file_name_frag))))])
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
    get_optval = lambda params, n, default_val=None, to=(lambda val: val): (to(params[0][tuple(i[0] for i in params[0]).index(n)][1]) if (n in frozenset(i[0] for i in params[0])) else default_val)
    get_optflag = lambda params, n: (n in frozenset(i[0] for i in params[0]))
    get_optparam = lambda params, i, default_val=None: (params[1][i] if (len(params[1]) > i) else default_val)

    prog_names = ('hcp', 'cph')
    default_port = 8000

    basename = os.path.basename(sys.argv[0])
    is_called_as_subcommand = ((len(sys.argv) > 1) and (sys.argv[1] in prog_names) and (basename not in prog_names))
    run_name = (sys.argv[1] if is_called_as_subcommand else basename)
    params = ((' '.join(sys.argv[:1]) if is_called_as_subcommand else sys.argv[0]),) + tuple(sys.argv[(2 if is_called_as_subcommand else 1):])

    if run_name in prog_names:
        optparams = getopt.gnu_getopt(params[1:], 'p:n:f:ch')
        di_file = get_optval(optparams, '-f', None)
        host = get_optval(optparams, '-n', "")
        portnum = get_optval(optparams, '-p', default_port, int)
        do_help = get_optflag(optparams, '-h')
        is_cgi = get_optflag(optparams, '-c')

        if do_help:
            if run_name == 'hcp':
                help_msg = 'Usage: {0} [-p <port>] [-n <host>] [-f <output_file>]\n\t-p: port to listen with (default port: {default_port})\n\t-h: host to listen with\n\t<output_file>: path to output file (to be appended to)\n\n'
            else:
                help_msg = 'Usage: {0} [-p <port>] [-n <host>] [-f <input_file>]\n\t-p: port to listen with (default port: {default_port})\n\t-h: host to listen with\n\t<input_file>: path to input file\n\n'
            sys.stdout.write(help_msg.format(params[0], default_port=str(default_port)))
        else:
            cp = (hcp_state if (run_name == 'hcp') else cph_state)(di_file=di_file)
            if is_cgi:
                if di_file is not None:
                    wsgiref.handlers.CGIHandler().run(cp[1])
                else:
                    raise Exception('cannot run in cgi mode without a file')
            else:
                s = wsgiref.simple_server.make_server(host, portnum, cp[1])
                sys.stderr.write('Listening on {host}:{port}...\n'.format(host=host, port=str(portnum)))
                while not cp[0]('done'):
                    s.handle_request()
            exit(cp[0]('exit'))
    else:
        sys.stderr.write('Usage: {0} <cmd>\n\tcmd: {prog_names}\nOr create a symlink to this file named as <cmd>.\n\n'.format(sys.argv[0], prog_names=' or '.join('"{0}"'.format(i) for i in prog_names)))
        exit(2)
