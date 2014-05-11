B"H.

copy/pipe to/from HTTP.

Inspired by skypipe (https://github.com/progrium/skypipe), and in turn, by unix pipes (https://en.wikipedia.org/wiki/Pipeline_%28Unix%29).
The name is a play on uucp (https://en.wikipedia.org/wiki/UUCP).
This program is not the program which used to be used within academic networks 
	within the UK back in the day 
	(http://web.archive.org/web/20071108200443/http://www.ust.hk/itsc/unix/UNIXhelp1.3/Pages/tasks/ftp3.html)
	:-).

hcp receives data which HTTP clients upload,
and
cph sends data for HTTP clients to download.
They are part of the 'hhcp' multicall executable.


Example usage:
	- client to server

		u@client$ printf 'We want Moshiach Now\n' | curl --data-binary @- http://localhost:8000/

		u@server$ hcp -I 2>/dev/null
		> We want Moshiach Now

	- server to client

		u@server$ printf 'We want Moshiach Now\n' | cph 2>/dev/null

		u@client$ curl -L http://localhost:8000/
		> We want Moshiach Now


Features:
	- built-in server (for one-off usage)
	- CGI mode (for use in something bigger)
	- append to/read from file
	- HTTP status line/mime type/POST-field settings
	- HTML user-interface for non-developer usability
	- etc.


Some ideas of use cases:
	- One-off file transfer
		$ cph -f <file>
	- Web API emulation
		# notice -- not tested on live API instance, so this may not be the way the real API works :-S
		# for Wikipedia api endpoint at http://en.wikipedia.org/w/api.php?action=edit
		# get the text which is to be edited when emulating the Wikipedia "edit" api
		$ hcp -I -m text -f logfile.log -s '204 No content'
	- <whatever good ideas you think of>
		$ hhcp <  your idea here :-)  >


Enjoy :-).


Currently licensed BSD.
