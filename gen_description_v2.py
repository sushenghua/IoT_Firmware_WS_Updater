 #
 # FirmwareUpdater parse message from protocol layer and response
 # Copyright (c) 2023 Shenghua Su
 #

import config
import os
import sys
import getopt
import struct
import re
import ctypes

def parse_args():
    helpstr = 'python gen_description.py -m <macroHeaderFile> -b <binFile>'
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hm:b:", ["help", "macroHeaderFile=", "binFile="])
        parse_ok = True
        mhf = ''
        bf = ''
        for opt, arg in opts:
            print('opt', opt)
            if opt in ("-h", "--help"):
                print(helpstr)
            elif opt in ("-m", "--macroheaderfile"):
                if not arg:
                    print("macro header file required")
                    parse_ok = False
                else:
                    mhf = arg
            elif opt in ("-b", "--binfile"):
                if not arg:
                    print('bin file required')
                    parse_ok = False
                else:
                    bf = arg
        if len(mhf) == 0 or len(bf) == 0:
            print('arg missed, use following:')
            print(helpstr)
            parse_ok = False
        return parse_ok, mhf, bf
    except getopt.GetoptError:
        print('invalid format, use following:')
        print(helpstr)
        return False, None, None
        

def check_files_exist(mhf, bf):
    if not os.path.exists(mhf):
        print('\x1b[6;30;41m Error: \x1b[0m macro header file not found: %s' %(mhf))
        sys.exit()

    if not os.path.exists(bf):
        print('\x1b[6;30;41m Error: \x1b[0m bin file not found: %s' %(bf))
        sys.exit()

def extract_defines(header_file_path):
    # Define a regular expression pattern to match #define macros.
    # This pattern aims to match:
    # - #define keyword (possibly with leading whitespaces)
    # - macro name
    # - (optionally) the value assigned to the macro
    pattern = re.compile(r'^\s*#define\s+([A-Za-z_]\w*)\s*(.*)?')

    defines = {}
    with open(header_file_path, 'r') as f:
        for line in f:
            match = pattern.match(line)
            if match:
                macro_name, macro_value = match.groups()
                defines[macro_name] = macro_value.strip('\"') if macro_value else None

    return defines

def gen_descriptions(macro_header_file, bin_file):

    defines = extract_defines(macro_header_file)
    if 'FIRMWARE_NAME' not in defines:
        print('\x1b[6;30;41m Error: \x1b[0m FIRMWARE_NAME missed in: %s' %(macro_header_file))
        sys.exit()
    if 'FIRMWARE_VERSION_STR' not in defines:
        print('\x1b[6;30;41m Error: \x1b[0m FIRMWARE_VERSION_STR missed in: %s' %(macro_header_file))
        sys.exit()
    if 'BOARD_VERSION_STR' not in defines:
        print('\x1b[6;30;41m Error: \x1b[0m BOARD_VERSION_STR missed in: %s' %(macro_header_file))
        sys.exit()

    fmw_name = defines['FIRMWARE_NAME']
    fmw_ver  = defines['FIRMWARE_VERSION_STR']
    bd_ver   = defines['BOARD_VERSION_STR']

    print(config.FIRMWARES_FILE_FOLDER)
    print(fmw_name)
    print(fmw_ver)
    print(bd_ver)

    file_stat = os.stat(bin_file)
    if file_stat.st_size == 0 :
        print('\x1b[6;30;41m Error: \x1b[0m firmware bin file empty: %s' %(bin_file))
        sys.exit()

    target_path = ''.join([config.FIRMWARES_FILE_FOLDER, '/', fmw_name, '/', bd_ver])
    if not os.path.exists(target_path):
        os.system('mkdir' + ' -p ' + target_path)

    target_bin_file = ''.join([target_path, '/', fmw_name, '.bin'])
    os.system('cp ' + bin_file + ' ' + target_bin_file)

    target_des_file = ''.join([target_path, '/', fmw_name, '.des'])
    with open(target_des_file, mode = 'wb') as file:
        # data = 
        # cache = bytearray()
        # cache.append(version)
        # cache.append(file_stat.st_size)
        # file.write(cache)

        # file.write(struct.pack('H', version))
        # file.write(struct.pack('I', file_stat.st_size))
        file.write(struct.pack('=I{}s'.format(len(fmw_ver)), file_stat.st_size, fmw_ver.encode('utf-8')))
        print("\x1b[6;30;42m Done \x1b[0m version: {}, size: {}".format(fmw_ver, file_stat.st_size))

    # for test purpose
    return target_des_file, fmw_ver, bd_ver

def versionStrToVersionInt(versionStr):
    vs = versionStr.split('.')
    vs = reversed(vs)
    weight = 1
    version = 0
    for v in vs:
        version += int(v) * weight
        weight *= 100
    return version

def test(des_file, fmw_ver, bd_ver):
    with open(des_file, 'rb') as f:
        b = bytearray(f.read())
        print('content size:', len(b))
        print('raw:', repr(b))
        content = struct.unpack('=I{}s'.format(len(b)-ctypes.sizeof(ctypes.c_int)), b)
        print(content)
        print('version int:', versionStrToVersionInt(content[1].decode('utf-8')))
        print('firmware version:', fmw_ver)
        print('board version:', bd_ver)


ok, mhf, bf = parse_args()
if ok:
    check_files_exist(mhf, bf)
    des_file, fmw_ver, bd_ver = gen_descriptions(mhf, bf)
    test(des_file, fmw_ver, bd_ver)
