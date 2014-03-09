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
import email.utils
import email.errors
import StringIO
import random
import string
import re
import mimetypes





def http_validator(v):
    ec = email.header.Header(v).encode()

    if re.search(r'(\r?\n[\S\n\r]|\r[\S\r])', ec):
        raise Exception('http header input error in "{h}"'.format(h=v))
    else:
        return ec


html_validator = (lambda v: cgi.escape(v, True))


def validator(prefix, validator_fn, inparams):
    return dict(('{0}_{1}'.format(prefix, k), validator_fn(v)) for k, v in inparams.iteritems())


def stdin_filepath(in_path='/dev/stdin', in_f=sys.stdin):
    try:
        with open(in_path) as f:
            is_stdin = os.path.sameopenfile(f.fileno(), in_f.fileno())
        if is_stdin:
            lp = os.path.realpath(in_path)
            with open(lp) as f:
                if f.isatty():
                    lp = None
            return lp
        else:
            return None
    except IOError as e:
        if e.errno in (2, 6):
            return False




def hcp_state(di_file=None, keep_listening=False, raw_format=False):
    state = {'done':  False, 'exit': 0}
    field_name = 'zachinalach'
    def handle_http_request(environ, start_response):
        if state['done']:
            return
        rm = environ['REQUEST_METHOD']
        if (rm == 'GET') and (not raw_format):
            start_response('200 ok Boruch Hashem', [('Content-Type', 'text/html')])
            yield '''<html><head></head><body>
            <form action="{html_app_uri}" enctype="multipart/form-data" method="POST">
                <input type="file" name="{html_field_name}" />
                <input type="submit" />
            </form>
            </html>'''.format(**validator('html', html_validator, {'app_uri': "{0}/send".format(environ['SCRIPT_NAME']), 'field_name': field_name}))
        elif rm == 'POST':
            rcvd_msg_body = 'File received.\r\n'
            rcvd_msg_content_type = 'text/plain'
            if raw_format:
                start_response('200 ok Boruch Hashem', [('Content-Type', rcvd_msg_content_type)])
            else:
                start_response('302 Found', [('Location', 'data:{ct},{0}'.format(rcvd_msg_body, ct=rcvd_msg_content_type))])
            if not keep_listening:
                state['done'] = True
            content_length = (int(environ['CONTENT_LENGTH']) if (('CONTENT_LENGTH' in environ) and (re.match(r'\d+$', environ['CONTENT_LENGTH']))) else None)
            if ('CONTENT_TYPE' in environ) and (not raw_format):
                ctcm = email.message.Message()
                ctcm.add_header('Content-Type', environ['CONTENT_TYPE']) # TODO: find better way to get mime type from the Content-Type header?
                content_type = ctcm.get_content_type()
            else:
                content_type = 'application/octet-stream'
            ctf = {'multipart/form-data': (lambda fs, field_name: fs[field_name].file), 'application/x-www-form-urlencoded': (lambda fs, field_name: (lambda a: (StringIO.StringIO(a) if (a is not None) else None))(fs.getfirst(field_name)))}
            fr = (ctf[content_type](fs=cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ), field_name=field_name) if (content_type in ctf) else environ['wsgi.input'])
            with (os.fdopen(sys.stdout.fileno(), 'wb') if (di_file is None) else open(di_file, 'ab')) as fw:
                try:
                    if fr is None:
                        pass
                    elif content_length is None:
                        fi = wsgiref.util.FileWrapper(fr)
                        for c in fi:
                            fw.write(c)
                    else:
                        amt_read = 0
                        chunk_size = 8192
                        while amt_read < content_length:
                            read_size = (content_length - amt_read if (content_length - amt_read < chunk_size) else chunk_size)
                            fw.write(fr.read(read_size))
                            amt_read += read_size
                except IOError as e:
                    if e.errno in (9, 32):
                        sys.stderr.write('{0}\n'.format(str(e)))
                        state['exit'] = 2
                    else:
                        raise
                if raw_format:
                    yield rcvd_msg_body
    return (lambda k: state[k], handle_http_request)


def cph_state(di_file=None, content_type=None, raw_format=False, keep_listening=False):
    state = {'done':  False, 'exit': 0}
    if di_file and ((not os.path.exists(di_file)) or os.path.isdir(di_file)):
        raise IOError('{0} is not an acceptable file.'.format(di_file))
    file_name_frag = os.path.basename((stdin_filepath() or 'file{0}'.format(''.join(random.choice(string.digits) for _ in range(7)))) if (di_file is None) else di_file)
    di_file_url = urllib.quote_plus(file_name_frag)
    clen = (os.path.getsize(di_file) if (di_file is not None) and os.path.isfile(di_file) else None)
    http_validator(di_file_url)

    def handle_http_request(environ, start_response):
        if state['done']:
            return
        rm = environ['REQUEST_METHOD']
        if rm == 'GET':
            sn = (environ['PATH_INFO'] if ('PATH_INFO' in environ) else '')
            if (len(sn) > 0) and (sn[0] == '/') and (sn[1:] == '{0}'.format(di_file_url)):
                start_response('200 ok Boruch Hashem', [('Content-Type', (lambda t: ('application/octet-stream' if (t is None) else http_validator(t)))(mimetypes.guess_type(di_file, strict=True)[0] if ((di_file is not None) and (content_type == 'ext')) else content_type))] + ([('Content-Disposition', 'attachment; filename="{http_f}"; filename*={http_fs}'.format(**validator('http', http_validator, dict(f=file_name_frag.decode('ascii', errors='ignore').replace('"', ''), fs=email.utils.encode_rfc2231(file_name_frag, 'UTF-8')))))] if (not raw_format) else []) + ([] if (clen is None) else [('Content-Length', str(clen))]))
                if not keep_listening:
                    state['done'] = True
                try:
                    return wsgiref.util.FileWrapper(os.fdopen(sys.stdin.fileno(), 'rb') if (di_file is None) else open(di_file, 'rb'))
                finally:
                    pass
            else:
                app_uri = wsgiref.util.application_uri(environ)
                # email.header.Header should raise email.errors.HeaderParseError if malicious input
                start_response('302 Found', [('Location', '{http_u}{http_s}{http_filename}'.format(**validator('http', http_validator, dict(u=app_uri, s=('' if app_uri.endswith('/') else '/'), filename=di_file_url))))])
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
        main_paramspec = 'p:n:f:chkI'
        optparams = getopt.gnu_getopt(params[1:], (main_paramspec if (run_name == 'hcp') else main_paramspec + 'm:'))
        di_file = get_optval(optparams, '-f', None) # stdout if not provided
        host = get_optval(optparams, '-n', "")
        portnum = get_optval(optparams, '-p', default_port, int)
        do_help = get_optflag(optparams, '-h')
        is_cgi = get_optflag(optparams, '-c') # CGI instead of "standalone"
        keep_listening = get_optflag(optparams, '-k')
        raw_format = get_optflag(optparams, '-I')

        if do_help:
            if run_name == 'hcp':
                help_msg = 'Usage: {0} [-p <port>] [-n <host>] [-f <output_file>] [-c] [-k]\n\t-p: port to listen with (default port: {default_port})\n\t-h: host to listen with\n\t<output_file>: path to output file (to be appended to)\n\t-c: CGI mode (requires a file name to be provided), standalone server is used if not specified\n\t-k: keep listening for additional requests after the file is requested (useful for clients that request files multiple times before fetching)\n\t-I: set content-type to interpret post-data with application/octet-stream (the raw post-data itself is output, instead of post params)\n\n'
            else:
                help_msg = 'Usage: {0} [-p <port>] [-n <host>] [-f <input_file>] [-m <mime_type>] [-c] [-k] [-I]\n\t-p: port to listen with (default port: {default_port})\n\t-h: host to listen with\n\t<input_file>: path to input file\n\t-c: CGI mode (requires a file name to be provided), standalone server is used if not specified\n\t-k: keep listening for additional requests after the file is requested (useful for clients that request files multiple times before fetching)\n\t-m: mime content type to provide for file requests ("ext" to try to guess type based on file extension, if input file name is provided); default is "application/octet-stream"\n\t-I: view inline (prevents Content-Disposition header from being set to "attachment")\n\n'
            sys.stdout.write(help_msg.format(params[0], default_port=str(default_port)))
        else: 
            state_kwparams = {'di_file': di_file, 'keep_listening': keep_listening, 'raw_format': raw_format}
            if (run_name == 'cph'):
                content_type = get_optval(optparams, '-m', None)
                state_kwparams['content_type'] = content_type
            cp = (hcp_state if (run_name == 'hcp') else cph_state)(**state_kwparams)
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
