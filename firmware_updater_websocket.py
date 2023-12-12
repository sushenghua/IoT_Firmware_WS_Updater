 #
 # FirmwareUpdater parse message from protocol layer and response
 # Copyright (c) 2023 Shenghua Su
 #

import config
import os
import sys
import struct
import json
import hashlib
import tornado.web as web
import tornado.websocket as websocket
import tornado.ioloop as ioloop
from struct import *
from ctypes import *

class Firmwares(object):
    def __new__(cls):
        """ creates a singleton object, if it is not created,
        or else returns the previous singleton object"""
        if not hasattr(cls, 'instance'):
            cls.instance = super(Firmwares, cls).__new__(cls)
            cls.instance.load_firmwares()
        return cls.instance

    def _versionStrToVersionInt(self, versionStr):
        vs = versionStr.split('.')
        vs = reversed(vs)
        weight = 1
        version = 0
        for v in vs:
            version += int(v) * weight
            weight *= 100
        return version

    def load_firmwares(self):
        self.firmwares = {}
        if not os.path.exists(config.FIRMWARES_FILE_FOLDER):
            print('\x1b[6;30;41m Error: \x1b[0m firmware folder not found: %s' %(config.FIRMWARES_FILE_FOLDER))
            # sys.exit("program stopped")

        # iterate all firmware folders under firmwares root dir
        for firmware_name in os.listdir(config.FIRMWARES_FILE_FOLDER):
            firmware_path = ''.join([config.FIRMWARES_FILE_FOLDER, '/', firmware_name])

            board_versions = {}
            # iterate all version folders under current firmware folder
            for board_version in os.listdir(firmware_path):

                # try to pick out bin file and des file
                bdv_path = ''.join([firmware_path, '/', board_version])
                files = os.listdir(bdv_path)

                bin_file = ''
                des_file = ''
                for f in files:
                    if f.endswith('.bin'):   bin_file = ''.join([bdv_path, '/', f])
                    elif f.endswith('.des'): des_file = ''.join([bdv_path, '/', f])

                # file existence test
                if not os.path.exists(des_file):
                    print('\x1b[6;30;41m Error: \x1b[0m description file not found: %s' %(des_file))
                    sys.exit("program stopped")

                if not os.path.exists(bin_file):
                    print('\x1b[6;30;41m Error: \x1b[0m firmware file not found: %s' %(bin_file))
                    sys.exit("program stopped")

                # firmware dictionary
                firmware = {}

                # description file
                with open (des_file, mode = 'rb') as file:
                    file_description_bytes = bytearray(file.read())
                    if len(file_description_bytes) == 0 :
                        print('\x1b[6;30;41m Error: \x1b[0m firmware description file empty: %s' %(des_file))
                        sys.exit("program stopped")
                    size, versionStr = struct.unpack('I{}s'.format(len(file_description_bytes)-sizeof(c_int)), file_description_bytes)
                    versionStr = versionStr.decode('utf-8')
                    versionInt = self._versionStrToVersionInt(versionStr)
                    description = struct.pack('=II', versionInt, size)

                    print("fmw: {}, bdv: {}, version: {}, versionInt: {}, size: {}".format(firmware_name, board_version, 
                                                                                           versionStr, versionInt, size))
                    firmware['size'] = size
                    firmware['version_int'] = versionInt
                    firmware['version_str'] = versionStr
                    firmware['description'] = description

                # print 'board version: {}, firmware: {}'.format(board_version, firmware)

                # binary file
                with open (bin_file, mode = 'rb') as file:
                    file_content = bytearray(file.read())
                    file_size = len(file_content)
                    # print "cached file size: {}".format(file_size)
                    if file_size == 0 :
                        print('\x1b[6;30;41m Error: \x1b[0m firmware file empty: %s' %(bin_file))
                        sys.exit("program stopped")
                    if file_size != size:
                        print('\x1b[6;30;41m Error: \x1b[0m firmware file size: %s mismatch with description size: %s' %(file_size, size))
                        sys.exit("program stopped")
                    firmware['file_content'] = file_content

                # md5
                md5 = hashlib.md5()
                md5.update(file_content)
                md5_digest = md5.digest()
                md5_size = md5.digest_size
                firmware['md5_digest'] = md5_digest
                firmware['md5_size'] = md5_size

                # save firmware to board_versions dict
                board_versions[board_version] = firmware

            # save board_versions to root firmwars dict
            self.firmwares[firmware_name] = board_versions


class FirmwareUpdater(websocket.WebSocketHandler):

    def __init__(self, application, request, **kwargs):
        websocket.WebSocketHandler.__init__(self, application, request, **kwargs)
        self._load_firmwares()
        self._setup_websocket()

    def _load_firmwares(self):
        f = Firmwares()
        self._fmws = f.firmwares

    def _setup_websocket(self):
        # self._ws = websocket.WebSocketHandler()
        # self._ws.check_origin = self._check_origin
        # self._ws.open = self._on_open
        # self._ws.on_close = self._on_close
        # self._ws.on_message = self._on_message
        pass

    def check_origin(self):
        return True

    def open(self):
        print("connection from client established")
        pass

    def on_close(self):
        print("disconnection from client")
        pass

    def on_message(self, msg):
        if isinstance(msg, str):   
            self.on_text_msg(msg)
        elif isinstance(msg, bytes):
            self.on_binary_msg(msg)
        else:
            raise ValueError('unknown message type')

    def _on_get_ver_info(self, fmw, bdv, retfmt):
        if fmw in self._fmws and bdv in self._fmws[fmw]:
            self._fmw = fmw
            self._bdv = bdv
            firmware = self._fmws[fmw][bdv]
            if retfmt == 'json':
                ret = json.dumps({'ver': firmware['version_str'], 'sz': firmware['size']})
                self.write_message(ret)
            elif retfmt == 'bin':
                ret = firmware['description']
                self.write_message(bytes(ret))
        else:
            self._fmw = None
            self._bdv = None
            ret = json.dumps({'err': 'unsupported'})

    def _on_get_data_block(self, block):
        if not self._fmw: return
        firmware = self._fmws[self._fmw][self._bdv]
        if block[0] < config.VERIFY_CMD:
            ret_bytesarray = bytearray([(block[0] >> i & 0xff) for i in (0,8,16,24)])
            # print(unpack('I', ret_bytesarray), ret_bytesarray)
            ret_bytesarray = ret_bytesarray + firmware['file_content'][block[0] : block[0]+block[1]]
            # print(unpack('I', ret_bytesarray[:4]), ret_bytesarray[:4])
            # segment = slice(block[0], block[0] + block[1])
            # print('ret size', len(firmware['file_content'][block[0] : block[0]+block[1]]))
            self.write_message(bytes(ret_bytesarray))
        else:
            # print 'require verify bytes'
            self.write_message(bytes(firmware['md5_digest']))

    def on_text_msg(self, msg):
        # print(f"rx text msg: {msg}")
        try:
            jmsg = json.loads(msg)
            if 'cmd' not in jmsg: return
            if jmsg['cmd'] == 'ver_info':
                if 'fmw' in jmsg and 'bdv' in jmsg:
                    retfmt = jmsg['retfmt'] if 'retfmt' in jmsg else 'bin'
                    self._on_get_ver_info(fmw=jmsg['fmw'], bdv=jmsg['bdv'], retfmt=retfmt)
            elif jmsg['cmd'] == 'data_block':
                if 'index' in jmsg and 'amount' in jmsg:
                    self._on_get_data_block( ( int(jmsg['index']), int(jmsg['amount']) ) )
        except Exception as e:
            print(f'err occurred: {type(e)}')

    def on_binary_msg(self, msg):
        # print(f'rx binary msg: {msg}')
        self._on_get_data_block(unpack('II', msg))


def start_app():
    app = web.Application([
        (r'/', FirmwareUpdater)
    ])
    app.listen(4040)
    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    start_app()
