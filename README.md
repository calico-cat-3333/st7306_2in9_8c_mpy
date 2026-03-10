# MicroPython driver for Osptek ST7306 2.9 inch 8 color Reflective LCD

适用于鱼鹰光电 ST7306 2.9 寸 8 色反射式液晶屏的 MicroPython 驱动，兼容 framebuf.FrameBuffer.

- 使用修正过的初始化序列，显示清晰。
- 局部刷新支持。
- 带有基于查找表的快速 Bayer 抖动支持。
- 使用 framebuf.GS4_HMSB 格式的缓冲区当作 RGB111 格式的缓冲区用。在实际发送数据前转换为 ST7306 要求的数据格式。每次转换两行数据并发送。
- 使用 micropython.viper 和大量位运算提升关键函数的速度，为此牺牲了部分代码可读性。

## TODO

- [ ] TE support
- [ ] rotation support
- [ ] 3 write for 24 bit mode support
- [ ] adjust voltage, support low framerate
