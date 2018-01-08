import os
import socket
from collections import deque

import asyncore_epoll as asyncore


class RequestHandler(asyncore.dispatcher):
    
    allowed_methods = (
        b'GET', b'HEAD',
    )
    
    statuses = {
        200: 'OK',
        405: 'ERROR'
    }
    
    def __init__(self, sock, static_dir):
        asyncore.dispatcher.__init__(self, sock)
        self.static_dir = static_dir
        self.request = b''
        self.EOR = b'\r\n\r\n'
        self._readable = True
        self.responses = deque()
        self.body = ''
        
    def readable(self):
        return self._readable

    def handle_read(self):
        self.request += self.socket.recv(1024)
        if self.EOR in self.request:
            self.handle_request()
            
    def writable(self):
        return bool(len(self.responses))
        
    def handle_request(self):
        method, path, protocol = self.request.split(b'\n')[0].split(b' ')
        if method not in self.allowed_methods:
            code = 405
        elif not os.path.exists(os.path.join(self.static_dir, path)):
            code = 404
        else:
            code = 200
        self.responses.append('HTTP/1.1, {code} {message}\n'.format(
            code=code, message=self.statuses[code]
        ))
        #self.add_header('Date', 111)
        self.add_header('Content-Length', self.body)
        self.add_empty_line()
        self.add_body()
            
    def add_header(self, name, value):
        if name == 'Date':
            self.responses.popleft(self.add_date(value))
            
    def add_empty_line(self):
        self.responses.append('\n')
        
    def add_body(self):
        self.responses.append('\r\n\r\n')
        
    def handle_write(self):
        response = self.responses.popleft()
        self.send(response)
        
    
class HTTPServer(asyncore.dispatcher):
    
    def __init__(self, address, connections_in_queue, sock=None, map=None):
        asyncore.dispatcher.__init__(self, sock, map)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_port()
        self.bind(address)
        self.listen(connections_in_queue)
        
    def set_reuse_port(self):
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except socket.error:
            pass
        
    def handle_accept(self):
        client_info = self.accept()
        RequestHandler(sock=client_info[0], static_dir='/')
        
        
def main():
    server = HTTPServer(('', 5672), 10)
    asyncore.loop()


if __name__ == '__main__':
    main()