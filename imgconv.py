# a simple image converter, convert input image to RGB565 format
# useage: python imgconv.py i=inputfile.png, o=out.bin

# how to use out.bin in micropython:
# import struct
# with open('out.bin', 'rb') as f:
#     wh = f.read(4)
#     w, h = struct.unpack('<HH', wh)
#     imgdata = f.read()


import numpy as np
from PIL import Image

import struct

import sys

def conv2rgb565(r, g, b):
    ra = np.array(r)
    ga = np.array(g)
    ba = np.array(b)
    h, w = ra.shape
    out = bytearray(h * w * 2)
    for y in range(h):
        for x in range(w):
            r5 = int(ra[y, x] >> 3) & 0x1f
            g6 = int(ga[y, x] >> 2) & 0x3f
            b5 = int(ba[y, x] >> 3) & 0x1f
            rgb565 = (r5 << 11) | (g6 << 5) | b5
            # save as little ending
            lb = rgb565 & 0xff
            hb = rgb565 >> 8
            out[y * w * 2 + x * 2] = lb
            out[y * w * 2 + (x * 2) + 1] = hb
    return out, w, h


if __name__ == '__main__':
    infile, outfile = None, None
    for k in sys.argv:
        if k.startswith('i='):
            infile = k[2:]
        if k.startswith('o='):
            outfile = k[2:]
    if infile == None or outfile == None:
        print('useage: python imgconv.py i=inputfile.png, o=out.bin')
        print('Abort.')
        exit(1)
    img = Image.open(infile)
    img = img.convert("RGB")
    r, g, b = img.split()

    imgd, w, h = conv2rgb565(r, g, b)

    r = struct.pack('<HH', w, h)

    with open(outfile, 'wb') as f:
        f.write(r)
        f.write(imgd)