import socket
import multiprocessing
from lab8 import Stepper, Shifter
import RPi.GPIO as GPIO
from Project import JSON_pull
import math
import time
from Project import my_turret_distances

GPIO.setmode(GPIO.BCM)
GPIO.setup(25, GPIO.OUT)

s = Shifter(data=16, latch=20, clock=21)

newlock = multiprocessing.Lock()
lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(s, lock1, newlock)
m2 = Stepper(s, lock2, newlock)

m1.zero()
m2.zero()

motor1 = 0
motor2 = 0

sock = socket.socket()
sock.bind(('0.0.0.0', 8080))
sock.listen(1)


def parsePOSTdata(data):
    data_dict = {}
    idx = data.find('\r\n\r\n') + 4
    data = data[idx:]
    data_pairs = data.split('&')
    for pair in data_pairs:
        key_val = pair.split('=')
        if len(key_val) == 2:
            data_dict[key_val[0]] = key_val[1]
    return data_dict


turrets, globes = JSON_pull()
dist_globes, dist_turrets = my_turret_distances(turrets, globes)

for stud_id, (dist_r, dist_theta) in dist_turrets.items():
    print(f"turret {stud_id}: delta r = {dist_r:.2f}, delta theta = {dist_theta:.2f} degrees")

for (dist_r, dist_theta, dist_z) in dist_globes:
    print(f"delta r = {dist_r:.2f}, delta theta = {dist_theta:.2f} degrees, delta z = {dist_z:.2f}")


while True:
    conn, addr = sock.accept()
    data = parsePOSTdata(conn.recv(1024).decode())


    if "laser_on" in data:
        GPIO.output(25, GPIO.HIGH)
        print("Laser ON")

    if "laser_off" in data:
        GPIO.output(25, GPIO.LOW)
        print("Laser OFF")

    if "zero" in data:
        print("Zeroing motors...")
        m1.zero()
        m2.zero()
        motor1 = 0
        motor2 = 0

    if "m1_angle" in data:
            angle = float(data["m1_angle"])
            print(f"Moving Motor1 to {angle}")
            m1.goAngle(angle)
            motor1 = angle

    if "m2_angle" in data:
            angle = float(data["m2_angle"])
            print(f"Moving Motor2 to {angle}")
            m2.goAngle(angle)
            motor2 = angle
            

    if "start" in data:
        print("starting")

        motor1 = 0
        motor2 = 0

        # motor1 is bottom and motor2 is laser axis
        for stud_id, (dist_r, dist_theta) in dist_turrets.items():
            if stud_id == "7":
                continue

            GPIO.output(25, GPIO.LOW)
            time.sleep(2)

            motor1 = (180-my_theta+theta)/2
            m1.goAngle(motor1)

            motor2 = 0
            m2.goAngle(motor2)  # Laser faces down to other turrets

            time.sleep(2)

            GPIO.output(25, GPIO.HIGH)
            time.sleep(2)

        for (dist_r, dist_theta, dist_z) in dist_globes:
            GPIO.output(25, GPIO.LOW)
            time.sleep(2)


            motor1 = (180-my_theta+theta)/2
            length = 2*my_r*math.cos(motor1)
            motor2 = math.degrees(math.atan(dist_z, length))

            m1.goAngle(motor1)
            m2.goAngle(motor2)

            time.sleep(2)

            GPIO.output(25, GPIO.HIGH)
            time.sleep(2)

        GPIO.output(25, GPIO.LOW)
        print("Done")

    # HTML response
    html = f"""<!DOCTYPE html>
<html>
<body>
  <h2>Laser Turret Control</h2>

  <form method="POST">
    <button name="start" value="go" style="width:160px;height:50px;font-size:18px;">
      START SWEEP
    </button>
  </form>

  <h3>Laser Manual Control</h3>
  <form method="POST">
    <button name="laser_on" value="1" style="width:140px;height:40px;">Laser ON</button>
    <button name="laser_off" value="1" style="width:140px;height:40px;">Laser OFF</button>
  </form>

  <h3>Motor Manual Control</h3>
  <form method="POST">
    Motor 1 Angle: <input name="m1_angle" type="number" step="0.1"><br><br>
    Motor 2 Angle: <input name="m2_angle" type="number" step="0.1"><br><br>
    <button style="width:120px;height:40px;">Set Angles</button>
  </form>

  <form method="POST">
    <button name="zero" value="1" style="width:160px;height:40px;">
      ZERO MOTORS
    </button>
  </form>

</body>
</html>
"""


    conn.send(b"HTTP/1.1 200 OK\r\n")
    conn.send(b"Content-Type: text/html\r\n")
    conn.send(b"Connection: close\r\n\r\n")
    conn.sendall(html.encode())
    conn.close()
