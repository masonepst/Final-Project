import socket
import multiprocessing
from lab8 import Stepper, Shifter
import RPi.GPIO as GPIO
from Project import JSON_pull
import math
import time
from Project import my_turret_distances
import threading

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

motor = "None"
target = "None"
location = "None"
current = "motor1=0, motor2=0"
laser = "OFF"
status = "Idle"
current_page = "main"

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
dist_globes, dist_turrets, my_r, my_theta = my_turret_distances(turrets, globes)
for stud_id, (dist_r, dist_theta, theta, r) in dist_turrets.items():
    print(f"turret {stud_id}: delta r = {dist_r:.2f}, delta theta = {dist_theta:.2f} degrees")

for (dist_r, dist_theta, dist_z, theta, r) in dist_globes:
    print(f"delta r = {dist_r:.2f}, delta theta = {dist_theta:.2f} degrees, delta z = {dist_z:.2f}")

def Run():
    global motor, target, location, current, laser, motor1, motor2, status
    status = "Running"

    motor = "Started"
    print("started")

    for stud_id, (dist_r, dist_theta, theta, r) in dist_turrets.items():
            if stud_id == "7":
                continue
            target = f"Turret {stud_id}"
            location = f"(r={r:.2f}, theta ={dist_theta:.2f}, z=N/A)"

            GPIO.output(25, GPIO.LOW)
            laser = "OFF"
            time.sleep(2)

            motor1 = (180 - math.degrees(my_theta) + math.degrees(theta)) / 2
            m1.goAngle(motor1)

            motor2 = 0
            m2.goAngle(motor2)

            current = f"Motor1 = {motor1:.1f}, Motor2 = {motor2:.1f}"

            

            time.sleep(2)

            GPIO.output(25, GPIO.HIGH)
            laser = "ON"
            time.sleep(2)

    for (dist_r, dist_theta, dist_z, theta, r) in dist_globes:
        target = f"Globe: [{r}, {dist_theta}, {dist_z}]"
        location = f"(r={r:.2f}, theta={dist_theta:.2f}, z={dist_z:.2f})"
       
        GPIO.output(25, GPIO.LOW)
        laser = "OFF"
        time.sleep(2)

        motor1 = (180 - math.degrees(my_theta) + math.degrees(theta)) / 2
        length = 2 * my_r * math.cos(math.radians(motor1))
        motor2 = math.degrees(math.atan(dist_z / length))

        current = f"Motor1={motor1:.1f}, Motor2={motor2:.1f}"
        m1.goAngle(motor1)
        m2.goAngle(motor2)

        time.sleep(2)

        GPIO.output(25, GPIO.HIGH)
        laser = "ON"
        time.sleep(2)

    GPIO.output(25, GPIO.LOW)
    laser = "OFF"

    status = "DONE"
    target = "DONE"
    print("Done")


while True:
    conn, addr = sock.accept()
    data = parsePOSTdata(conn.recv(1024).decode())

    if "goto_main" in data:
        current_page = "main"


    if "goto_run" in data:
        current_page = "run"


    if "goto_calib" in data:
        current_page = "calib"


    if "laser_on" in data:
        GPIO.output(25, GPIO.HIGH)
        laser ="ON"
        print("Laser ON")

    if "laser_off" in data:
        GPIO.output(25, GPIO.LOW)
        laser = "OFF"
        print("Laser OFF")

    if "zero" in data:
        print("Zeroing motors...")
        m1.zero()
        m2.zero()
        motor1 = 0
        motor2 = 0
        current = f"Motor1={motor1:.1f}, Motor2={motor2:.1f}"

    if "m1_angle" in data:
            angle = float(data["m1_angle"])
            print(f"Moving Motor1 to {angle}")
            m1.goAngle(angle)
            motor1 = angle
            current = f"motor1={motor1:.1f}, motor2={motor2:.1f}"

    if "m2_angle" in data:
            angle = float(data["m2_angle"])
            print(f"Moving Motor2 to {angle}")
            m2.goAngle(angle)
            motor2 = angle
            current = f"motor1={motor1:.1f}, motor2={motor2:.1f}"

    if "start" in data:
        current_page = "run"
        t = threading.Thread(target=Run, daemon=True)
        t.start()

        motor1 = 0
        motor2 = 0

        # motor1 is bottom and motor2 is laser axis

    
    motor1_perc = (motor1 % 180) / 180 * 100
    motor2_perc = (motor2 % 180) / 180 * 100 


    base_style = """
    <style>
      body {
        margin: 0;
        font-family: Arial, sans-serif;
        background: #0f172a;
        color: #e5e7eb;
        height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
      }
      .card {
        background: #020617;
        padding: 30px;
        width: 420px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        text-align: center;
      }
      h1 {
        margin-top: 0;
        margin-bottom: 20px;
      }
      button {
        width: 100%;
        height: 56px;
        font-size: 18px;
        border-radius: 12px;
        border: none;
        margin: 10px 0;
        cursor: pointer;
      }
      .primary {
        background: #2563eb;
        color: white;
      }
      .secondary {
        background: #334155;
        color: white;
      }
      .bar {
        background: #1e293b;
        height: 12px;
        border-radius: 6px;
        margin-bottom: 14px;
      }
      .fill1 {
        background: #22c55e;
        height: 12px;
        border-radius: 6px;
      }
      .fill2 {
        background: #38bdf8;
        height: 12px;
        border-radius: 6px;
      }
      input {
        width: 100%;
        padding: 10px;
        font-size: 16px;
        border-radius: 10px;
        border: none;
        margin-bottom: 12px;
      }
      .label {
        text-align: left;
        font-size: 14px;
        margin-bottom: 4px;
      }
    </style>
    """

    refresh = "<meta http-equiv='refresh' content='2'>" if current_page == "run" and status == "Running" else ""

    if current_page == "main":
        html = f"""
<!DOCTYPE html>
<html>
<head>
{base_style}
</head>
<body>
  <div class="card">
    <h1>Turret Sweep</h1>

    <form method="POST">
      <button class="primary" name="start">START</button>
    </form>

    <form method="POST">
      <button class="secondary" name="goto_calib">CALIBRATION</button>
    </form>
  </div>
</body>
</html>
"""

    elif current_page == "run":
        html = f"""
<!DOCTYPE html>
<html>
<head>
{refresh}
{base_style}
</head>
<body>
  <div class="card">
    <h1>Turret Sweep</h1>

    <p><b>Status:</b> {status}</p>
    <p><b>Target:</b> {target}</p>
    <p><b>Location:</b> {location}</p>
    <p><b>Laser:</b> {laser}</p>

    <p>Motor 1: {motor1:.1f}</p>
    <div class="bar">
      <div class="fill1" style="width:{motor1_perc:.1f}%"></div>
    </div>

    <p>Motor 2: {motor2:.1f}</p>
    <div class="bar">
      <div class="fill2" style="width:{motor2_perc:.1f}%"></div>
    </div>

    <form method="POST">
      <button class="secondary" name="goto_main">BACK</button>
    </form>
  </div>
</body>
</html>
"""

    else:  # calibration
        html = f"""
<!DOCTYPE html>
<html>
<head>
{base_style}
</head>
<body>
  <div class="card">
    <h1>Calibration</h1>

    <form method="POST">
      <div class="label">Motor 1 Angle</div>
      <input type="number" step="0.1" name="m1_angle">

      <div class="label">Motor 2 Angle</div>
      <input type="number" step="0.1" name="m2_angle">

      <button class="primary">SET ANGLES</button>
    </form>

    <form method="POST">
      <button class="secondary" name="laser_on">LASER ON</button>
    </form>

    <form method="POST">
      <button class="secondary" name="laser_off">LASER OFF</button>
    </form>

    <form method="POST">
      <button class="secondary" name="zero">ZERO MOTORS</button>
    </form>

    <form method="POST">
      <button class="secondary" name="goto_main">BACK</button>
    </form>
  </div>
</body>
</html>
"""







    conn.send(b"HTTP/1.1 200 OK\r\n")
    conn.send(b"Content-Type: text/html\r\n")
    conn.send(b"Connection: close\r\n\r\n")
    conn.sendall(html.encode())
    conn.close()
