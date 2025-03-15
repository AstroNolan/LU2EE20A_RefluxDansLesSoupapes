import array
import time
import rp2
import asyncio
from machine import Pin

NUM_LEDS = 1
PIN_NUM = 16
gpio_sel = Pin(8, Pin.OUT)
gpio_clk = Pin(18, Pin.OUT)
gpio_adc = [Pin(i, Pin.IN) for i in range(8)]

@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()

sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(PIN_NUM))
sm.active(1)

ar = array.array("I", [0 for _ in range(NUM_LEDS)])

def pixels_show():
    sm.put(ar, 8)
    time.sleep_ms(10)

def pixels_set(i, color):
    ar[i] = (color[1] << 16) + (color[0] << 8) + color[2]

def wheel(pos):
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

async def rainbow_cycle(wait):
    while True:
        for j in range(255):
            color = wheel(j)
            pixels_set(0, color)
            pixels_show()
            await asyncio.sleep(wait)

async def read_gpio(timeout=0.02):
    gpio_sel.value(0)
    await asyncio.sleep(timeout)
    gpio_clk.value(1)
    await asyncio.sleep(timeout)
    gpio_clk.value(0)
    await asyncio.sleep(timeout)
    etats_s1 = [pin.value() for pin in gpio_adc]
    await asyncio.sleep(timeout)
    gpio_sel.value(1)
    await asyncio.sleep(timeout)
    gpio_clk.value(1)
    await asyncio.sleep(timeout)
    gpio_clk.value(0)
    await asyncio.sleep(timeout)
    etats_s2 = [pin.value() for pin in gpio_adc]
    await asyncio.sleep(timeout)
    return list(reversed(etats_s1)), list(reversed(etats_s2))

async def generate_clock(freq=2000):
    period = 1 / freq
    half_period = period / 2
    while True:
        gpio_clk.value(1)
        await asyncio.sleep(half_period)
        gpio_clk.value(0)
        await asyncio.sleep(half_period)

async def main():
    asyncio.create_task(rainbow_cycle(0.01))
    # asyncio.create_task(generate_clock(2000))
    while True:
        etats = await read_gpio()
        print(time.time(), etats)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        pixels_set(0, (0, 0, 0))
        pixels_show()