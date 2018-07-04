import os
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.process import fork_processes
from tornado.options import parse_command_line, define, options

from app import app

define("port", default=5000, help="run on the given port", type=int)

if __name__ == "__main__":
    parse_command_line()
    if os.name == 'posix':
        fork_processes(0)
    http_server = HTTPServer(WSGIContainer(app), xheaders=True)
    http_server.listen(options.port)
    IOLoop.instance().start()
