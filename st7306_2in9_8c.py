import framebuf
import struct
import time
import micropython

class COLOR111:
    BLACK = 0b000
    BLUE = 0b001
    GREEN = 0b010
    CYAN = 0b011
    RED = 0b100
    MAGENTA = 0b101
    YELLOW = 0b110
    WHITE = 0b111

def get_time(f, *args, **kwargs):
    myname = f.__name__
    def new_func(*args, **kwargs):
        t = time.ticks_us()
        result = f(*args, **kwargs)
        delta = time.ticks_diff(time.ticks_us(), t)
        print('Function {} Time = {:6.3f}ms, framerate={:6.3f}fps'.format(myname, delta/1000, 1000000/delta))
        return result
    return new_func

class ST7306_2IN9_8C(framebuf.FrameBuffer):
    def __init__(self, spi, dc, cs, rst, te=None, rot=0, osc_51mhz=True, framerates=(1, 5), power_mode=True, inversion=False):
        # spi, cs, dc, rst, te: device and pin, te still wip
        # rot: rotation
        # osc_51mhz: True: 51 MHz, False: 32 MHz
        # framerates: framerate for (HPM, LPM)
            # HPM: osc_51mhz = True: 0: 25.5, 1: 51; osc_51mhz = False: 0: 16, 1: 32
            # LPM: 0: 0.25, 1: 0.5, 2: 1, 3: 2, 4: 4, 5: 8
        # power_mode: True: HPM, Flase: LPM
        # inversion: True: enable, False: disable
        self.spi = spi
        self.cs = cs
        self.cs.value(1)
        self.dc = dc
        self.dc.value(0)
        self.rst = rst
        self.rst.value(1)
        self.te = te

        self.rotation = rot

        self.LCD_HEIGHT = 480
        self.LCD_WIDTH = 210

        if self.rotation % 2 == 0:
            self.height = self.LCD_HEIGHT
            self.width = self.LCD_WIDTH
        else:
            self.height = self.LCD_WIDTH
            self.width = self.LCD_HEIGHT

        self.buffer = bytearray(self.height * self.width // 2) # 2 pixel pre byte
        self.wbuf = bytearray(self.width + 2) # 这个屏幕要求一次性必须写入 24 bit ，每次写入的 24 bit 为两行的 4 pixel, 暂时使用 4 次写入模式，即每 byte 的后 2 bti 被忽略，但是每 byte 刚好 2 pixel
        #self.wbuf = bytearray((self.width + 2) // 4 * 3) # 3 write for 24 bit
        self.wbuf_mv = memoryview(self.wbuf)
        super().__init__(self.buffer, self.width, self.height, framebuf.GS4_HMSB)
        self.fill(0)

        self.lcd_init(te != None, rot, osc_51mhz, framerates, power_mode, inversion)

    def reset(self):
        time.sleep_ms(50)
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(120)

    def _spi_write_cmd(self, cmd):
        self.cs.off()
        self.dc.off()
        self.spi.write(cmd)
        self.cs.on()

    def _spi_write_data(self, data):
        self.cs.off()
        self.dc.on()
        self.spi.write(data)
        self.cs.on()

    def _spi_write(self, cmd=None, data=None):
        self.cs.off()
        if cmd != None:
            self.dc.off()
            self.spi.write(cmd)
        if data != None:
            self.dc.on()
            self.spi.write(data)
        self.cs.on()

    @micropython.viper
    def _convert(self, r: int, width: int, inbuf: ptr8, wbuf: ptr8):
        w2 = width >> 1
        row1 = (r * w2)
        row2 = ((r + 1) * w2)
        for i in range(w2):
            k = i * 2 + 2 # extra 2 pixels in the start of a line
            p1 = inbuf[row1 + i] << 1
            p2 = inbuf[row2 + i] << 1
            wbuf[k] = ~((p1 & 0xE0) | ((p2 >> 3) & 0x1C))
            wbuf[k + 1] = ~(((p1 << 4) & 0xE0) | ((p2 << 1) & 0x1C))

    @micropython.viper
    def _convert_3b(self, r: int, width: int, inbuf: ptr8, wbuf: ptr8):
        w2 = width >> 1
        row1 = (r * w2)
        row2 = ((r + 1) * w2)
        w2 = w2 >> 1
        for i in range(w2):
            k = i * 3
            p1 = inbuf[row1 + i * 2] << 1
            p2 = inbuf[row2 + i * 2] << 1
            wbuf[k] = (p1 & 0xE0) | ((p2 >> 3) & 0x1C) | ((p1 >> 2) & 0x03)
            wbuf[k + 1] = ((p1 << 6) & 0x80) | ((p2 << 3) & 0x70)
            p1 = inbuf[row1 + i * 2 + 1] << 1
            p2 = inbuf[row2 + i * 2 + 1] << 1
            wbuf[k + 1] = wbuf[i * 3 + 1] | ((p1 >> 4) & 0x0E) | (p2 >> 7)
            wbuf[k + 2] = ((p2 << 1) & 0xC0) | ((p1 << 2) & 0x38) | ((p2 >> 1) & 0x07)

    @get_time
    def flush(self):
        xs = 4
        xe = 56
        ys = 0
        ye = self.height // 2 - 1
        self._spi_write_cmd(b'\x2A')
        self._spi_write_data(bytes([xs, xe]))
        self._spi_write_cmd(b'\x2B')
        self._spi_write_data(bytes([ys, ye]))
        self._spi_write_cmd(b'\x2C')
        self.cs.off()
        self.dc.on()
        for i in range(self.height // 2):
            self._convert(i * 2, self.width, self.buffer, self.wbuf)
            self.spi.write(self.wbuf)
        self.cs.on()

    @micropython.viper
    def _convert_part(self, r: int, xs: int, width: int, inbuf: ptr8, wbuf: ptr8):
        w2 = int(self.width) >> 1
        aw2 = width >> 1
        x2 = xs >> 2
        row1 = (r * w2)
        row2 = ((r + 1) * w2)
        for i in range(aw2):
            k = i * 2
            p1 = inbuf[row1 + i + x2] << 1
            p2 = inbuf[row2 + i + x2] << 1
            wbuf[k] = ~((p1 & 0xE0) | ((p2 >> 3) & 0x1C))
            wbuf[k + 1] = ~(((p1 << 4) & 0xE0) | ((p2 << 1) & 0x1C))

    @get_time
    def flush_part(self, x=0, y=0, w=210, h=480):
        if y % 2 != 0:
            y -= 1
            h += 1
        if h % 2 != 0:
            h += 1
        xofs = x % 4
        if xofs != 0:
            x -= xofs
            w += xofs
        wofs = w % 4
        if wofs != 0:
            w += (4 - wofs)
        print(x, y, w, h)

        xe = 56 - x // 4
        xs = xe - w // 4 + 1
        ys = y // 2
        ye = ys + h // 2 - 1
        self._spi_write_cmd(b'\x2A')
        self._spi_write_data(bytes([xs, xe]))
        self._spi_write_cmd(b'\x2B')
        self._spi_write_data(bytes([ys, ye]))
        self._spi_write_cmd(b'\x2C')
        self.cs.off()
        self.dc.on()
        for i in range(h // 2):
            self._convert_part(y + i * 2, x, w, self.buffer, self.wbuf)
            self.spi.write(self.wbuf_mv[:w])
        self.cs.on()

    def lcd_init(self, te_enable=False, rot=0, osc_51mhz=True, framerates=(1, 5), power_mode=True, inversion=False):
        # rot: rotation
        # osc_51mhz: True: 51 MHz, False: 32 MHz
        # framerates: framerate for (HPM, LPM)
            # HPM: osc_51mhz = True: 0: 25.5, 1: 51; osc_51mhz = False: 0: 16, 1: 32
            # LPM: 0: 0.25, 1: 0.5, 2: 1, 3: 2, 4: 4, 5: 8
        # power_mode: True: HPM, Flase: LPM
        # inversion: True: enable, False: disable
        self.reset()

        self._spi_write_cmd(b'\xD6') #  NVM Load Control
        self._spi_write_data(b'\x17\x02')
        self._spi_write_cmd(b'\xD1') # Booster Enable
        self._spi_write_data(b'\x01')
        self._spi_write_cmd(b'\xC0') # Gate Voltage Control
        self._spi_write_data(b'\x0E\x0A') #  VGH=15V VGL=-10V
        self._spi_write_cmd(b'\xC1') # VSHP Setting
        self._spi_write_data(b'\x41\x41\x41\x41') # VSHP1/2/3/4=5V
        self._spi_write_cmd(b'\xC2') # VSLP Setting
        self._spi_write_data(b'\x32\x32\x32\x32') # VSLP1/2/3/4=1V
        self._spi_write_cmd(b'\xC4') # VSHN Setting
        self._spi_write_data(b'\x46\x46\x46\x46') # VSHN1/2/3/4=-3.9V
        self._spi_write_cmd(b'\xC5') # VSLN Setting
        self._spi_write_data(b'\x46\x46\x46\x46') # VSLN1/2/3/4=-0.4V
        self._spi_write_cmd(b'\xB2') # Frame Rate Control
        self._spi_write_data(bytes([((framerates[0] << 4) | framerates[1]) & 0x17])) # HPM ; LPM
        self._spi_write_cmd(b'\xB3') # Update Period Gate EQ Control in HPM
        self._spi_write_data(b'\xE5\xF6\x05\x46\x77\x77\x77\x77\x76\x45')
        self._spi_write_cmd(b'\xB4') # Update Period Gate EQ Control in LPM
        self._spi_write_data(b'\x05\x46\x77\x77\x77\x77\x76\x45') # LPM EQ Control
        self._spi_write_cmd(b'\xB7') # Source EQ Enable
        self._spi_write_data(b'\x13')
        self._spi_write_cmd(b'\xB0') # Gate Line Setting
        self._spi_write_data(b'\x78') # 480 line
        self._spi_write_cmd(b'\x11') # Sleep-out
        time.sleep_ms(120)

        self._spi_write_cmd(b'\xD8') # OSC Setting
        if osc_51mhz:
            self._spi_write_data(b'\x80\xE9') # 51Hz
        else:
            self._spi_write_data(b'\xA6\xE9') # 32Hz

        self._spi_write_cmd(b'\xC9') # Source Voltage Select
        self._spi_write_data(b'\x00') # VSHP1; VSLP1 ; VSHN1 ; VSLN1

        # todo: rotation support
        self._spi_write_cmd(b'\x36') # Memory Data Access Control
        self._spi_write_data(b'\x48')

        self._spi_write_cmd(b'\x3A') # Data Format Select
        # 8 color, data up down switch off, rgb111
        self._spi_write_data(b'\x30') # 4 write for 24 bit
       # self._spi_write_data(b'\x31') # 3 write for 24 bit


        self._spi_write_cmd(b'\xB9') # Gamma Mode Setting
        self._spi_write_data(b'\x20') # Mono

        self._spi_write_cmd(b'\xB8') # Panel Setting
        self._spi_write_data(b'\x09') # column inversion, 2 line interval, One Line Interlace

        if te_enable:
            self._spi_write_cmd(b'\x35') # TE Setting
            self._spi_write_data(b'\x00') # 0x00:  V-Blanking only. 0x01: both V-Blanking and H-Blanking
        else:
            self._spi_write_cmd(b'\x34') # Disable TE output

        self._spi_write_cmd(b'\xD0') # Enable Auto Power down
        self._spi_write_data(b'\xFF')

        self.power_mode(power_mode) # set HPM or LPM
        self.inversion_mode(inversion) # set inversion
        self.display_on() # Display on

        time.sleep_ms(100)

    def display_on(self):
        self._spi_write_cmd(b'\x29') # Display ON

    def display_off(self):
        self._spi_write_cmd(b'\x28') # Display OFF

    def sleep_mode(self, value):
        if value:
            self._spi_write_cmd(b'\x10') # sleep in
        else:
            self._spi_write_cmd(b'\x11') # sleep out

    def inversion_mode(self, value):
        if value:
            self._spi_write_cmd(b'\x21') # inversion on
        else:
            self._spi_write_cmd(b'\x20') # inversion off

    def power_mode(self, value):
        if value:
            self._spi_write_cmd(b'\x38') # HPM ON
        else:
            self._spi_write_cmd(b'\x39') # LPM ON

    def soft_reset(self):
        self._spi_write_cmd(b'\x01') # soft reset
