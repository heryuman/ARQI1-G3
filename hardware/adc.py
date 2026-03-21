import spidev

_spi = None

def init_adc():
    global _spi
    _spi = spidev.SpiDev()
    _spi.open(0, 0)
    _spi.max_speed_hz = 1350000

def read_mcp3208(channel):
    cmd1 = 0b00000110 | ((channel & 0b100) >> 2)
    cmd2 = (channel & 0b011) << 6
    r = _spi.xfer2([cmd1, cmd2, 0])
    return ((r[1] & 0x0F) << 8) | r[2]

def close_adc():
    if _spi is not None:
        _spi.close()
