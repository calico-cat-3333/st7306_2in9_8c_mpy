# MicroPython driver for Osptek ST7306 2.9 inch 8 color Reflective LCD

适用于鱼鹰光电 ST7306 2.9 寸 8 色反射式液晶屏的 MicroPython 驱动，兼容 framebuf.FrameBuffer.

- 使用修正过的初始化序列，显示清晰。
- 局部刷新支持。
- 旋转屏幕支持（目前不支持在运行中改变，需要在创建屏幕对象时指定）
- 带有基于查找表的快速 Bayer 抖动支持。
- 带有 Sierra Lite 误差扩散抖动支持（速度较慢）
- 使用 framebuf.GS4_HMSB 格式的缓冲区当作 RGB111 格式的缓冲区用。在实际发送数据前转换为 ST7306 要求的数据格式。每次转换两行数据并发送。
- 使用 micropython.viper 和大量位运算提升关键函数的速度，为此牺牲了部分代码可读性。

在 RP2350 上测试，竖屏全屏刷屏耗时约 41 毫秒，横屏全屏刷屏耗时约 37 毫秒。

## 使用

```python
import machine
import time
import framebuf

import st7306_2in9_8c

spi = machine.SPI(0, baudrate=40000000, polarity=0, phase=0, sck=machine.Pin(2), mosi=machine.Pin(3), miso=None)

rst = machine.Pin(4, machine.Pin.OUT)
dc = machine.Pin(5, machine.Pin.OUT)
cs = machine.Pin(6, machine.Pin.OUT)

disp = st7306_2in9_8c.ST7306_2IN9_8C(spi, dc, cs, rst, rot=0)

disp.fill(0b111)

disp.rect(100, 0, 200, 100, 0, True)
disp.rect(0, 278, 212, 202, 0, True)

for i in range(8):
    disp.line(25 + i * 5, 0, 124 + i * 5, 99, i)
    disp.text('Hello World!', 3, 110 + i * 25, i)
    disp.rect(100, 105 + i * 25, 20, 20, i, True)
    disp.rect(125, 105 + i * 25, 20, 20, i)
    disp.ellipse(160, 115 + i * 25, 10, 10, i, True)
    disp.ellipse(185, 115 + i * 25, 10, 10, i)

    disp.flush()

disp.rect(0, 0, disp.width, disp.height, st7306_2in9_8c.COLOR111.RED)
disp.flush()
```

## API 文档

### 颜色定义 (COLOR111)

```python
class COLOR111:
    BLACK = 0b000
    BLUE = 0b001
    GREEN = 0b010
    CYAN = 0b011
    RED = 0b100
    MAGENTA = 0b101
    YELLOW = 0b110
    WHITE = 0b111
```

### ST7306_2IN9_8C 类

#### 构造函数 `ST7306_2IN9_8C(spi, dc, cs, rst, te=None, rot=0, osc_51mhz=True, framerates=(1, 5), power_mode=True, inversion=False)`

参数：

- `spi`：`machine.SPI` 对象
- `dc`：数据/命令控制引脚
- `cs`：片选引脚
- `rst`：复位引脚
- `te`：（尚未实现）撕裂效应（Tearing Effect）引脚，用于同步刷新，若不需要则设为 `None`
- `rot`：旋转角度：0、1、2、3，分别对应 0°、90°、180°、270°。默认 0
- `osc_51mhz`：振荡器频率：`True` 为 51 MHz，`False` 为 32 MHz。影响帧率。
- `framerates`：(HPM 帧率, LPM 帧率) 元组。HPM 值：0或1；LPM 值：0~5。具体对应关系见下方说明
- `power_mode`：电源模式：`True` = HPM，`False` = LPM
- `inversion`：反转显示：`True` 启用反转，`False` 正常

帧率参数对应关系：

注意：目前初始化序列下，仅 51 Hz 帧率完全正常，其他帧率或多或少都会出现闪屏现象，该问题可能需要通过调整初始化序列中的电压参数来解决（尚未完成）。

- HPM 帧率：
  - `osc_51mhz=True` 时：0 → 25.5 Hz，1 → 51 Hz
  - `osc_51mhz=False` 时：0 → 16 Hz，1 → 32 Hz
- LPM 帧率：
  - 0 → 0.25 Hz，1 → 0.5 Hz，2 → 1 Hz，3 → 2 Hz，4 → 4 Hz，5 → 8 Hz

#### `reset()`

执行硬件复位（拉低 RST 引脚至少 50ms）。

#### `flush()`

将整个屏幕缓冲区的内容刷新到显示屏。

#### `flush_part(x=0, y=0, w=None, h=None)`

刷新屏幕的指定矩形区域。

参数：

 - `x, y`：矩形区域左上角坐标。
 - `w, h`：矩形区域宽度和高度，若为 `None`，则默认为屏幕剩余部分。

该方法会自动对齐到硬件块边界。

#### `display_on()`

开启显示（发送命令 `0x29`）。

#### `display_off()`

关闭显示（发送命令 `0x28`）。

#### `sleep_mode(value)`

控制睡眠模式：

- `value=True`：进入睡眠（发送命令 `0x10`）
- `value=False`：退出睡眠（发送命令 `0x11`）

#### `inversion_mode(value)`

控制反转显示：

- `value=True`：启用反转（发送命令 `0x21`）
- `value=False`：关闭反转（发送命令 `0x20`）

#### `power_mode(value)`

切换电源模式：

- `value=True`：HPM（发送命令 `0x38`）
- `value=False`：LPM（发送命令 `0x39`）

#### `soft_reset()`

软件复位显示屏（发送命令 `0x01`）。

#### `blit_buffer_rgb565(buffer, x, y, w, h, dither=0)`

将 RGB565 格式的图像缓冲区绘制到屏幕指定位置，可选用抖动算法提高显示质量。

参数：

- `buffer`：包含 RGB565 数据的缓冲区
- `x, y`：目标矩形左上角坐标（允许负值，超出的部分将被裁剪）
- `w, h`：源矩形的宽度和高度
- `dither`：抖动算法选择：
  - 0 - 无抖动（直接量化）
  - 1 - Bayer 4x4 抖动（标准）
  - 2 - Bayer 4x4 抖动（线性 RGB 优化）
  - 3 - Sierra Lite 抖动（误差扩散，较慢但质量高）

#### 继承自 FrameBuffer 的方法

由于继承自 `framebuf.FrameBuffer`，该类支持所有标准帧缓冲区操作，具体请参考 [framebuf 文档](https://docs.micropython.org/en/latest/library/framebuf.html)

## TODO

- [ ] TE 刷屏支持
- [x] 旋转屏幕支持
- [ ] "3 write for 24 bit" mode support
- [ ] 调整电压以消除低帧率时闪屏的问题

## 参考

ST7306 数据手册：[https://admin.osptek.com/uploads/ST_7306_V0_1_c30c3541a3.pdf](https://admin.osptek.com/uploads/ST_7306_V0_1_c30c3541a3.pdf)

Arduino 驱动：[https://github.com/GeekYang945/esp32_st7306_driver](https://github.com/GeekYang945/esp32_st7306_driver)

另一个 Arduino 驱动：[https://github.com/FT-tele/ST7306_8color_lvgl](https://github.com/FT-tele/ST7306_8color_lvgl)
