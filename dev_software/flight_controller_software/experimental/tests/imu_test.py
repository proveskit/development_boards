import board
import busio
from adafruit_lsm6ds import lsm6dsox
import adafruit_lsm303_accel
import adafruit_lis2mdl
import time

i2c=busio.I2C(board.SCL1,board.SDA1)
lsm6ds=lsm6dsox.LSM6DSOX(i2c,address=0x6b)
lsm303 = adafruit_lsm303_accel.LSM303_Accel(i2c)
lis2mdl = adafruit_lis2mdl.LIS2MDL(i2c)

while True:
    print("lsm6ds Acceleration: X:%.2f, Y: %.2f, Z: %.2f m/s^2" % (lsm6ds.acceleration))
    print("lsm6ds Gyro X:%.2f, Y: %.2f, Z: %.2f degrees/s" % (lsm6ds.gyro))
    print("lsm303 Acceleration (m/s^2): X=%0.3f Y=%0.3f Z=%0.3f"%lsm303.acceleration)
    print("lsm303 Magnetometer (micro-Teslas)): X=%0.3f Y=%0.3f Z=%0.3f"%lis2mdl.magnetic)
    time.sleep(2)