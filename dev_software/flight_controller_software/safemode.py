print("I am in safemode. Help!")
import microcontroller
import time
time.sleep(10)
microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
microcontroller.reset()
    