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
        t = threading.Thread(target=Run, daemon=True)
        t.start()

        motor1 = 0
        motor2 = 0

        # motor1 is bottom and motor2 is laser axis

    # Motor bar percentages (0–180° mapped to 0–100%)
    motor1_perc = (motor1 % 180) / 180 * 100
    motor2_perc = (motor2 % 180) / 180 * 100

    # Compass arrow rotation
    theta_deg = 0
    if isinstance(target, str) and "Turret" in target:
        stud_id = target.split()[-1]
        if stud_id in dist_turrets:
            theta_deg = math.degrees(dist_turrets[stud_id][2])  # actual θ

        
    # HTML response
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="2">
  <style>
    .bar-container {{
      width: 300px; 
      height: 12px;
      background: #ccc; 
      border-radius: 6px;
      margin-bottom: 20px;
    }}
    .bar-fill {{
      height: 12px;
      border-radius: 6px;
    }}
    #compass {{
      width: 200px;
      height: 200px;
      border-radius: 50%;
      border: 2px solid black;
      position: relative;
      margin-top: 20px;
    }}
    #arrow {{
      width: 4px;
      height: 90px;
      background: red;
      position: absolute;
      top: 10px;
      left: 98px;
      transform-origin: 50% 90%;
      transform: rotate({theta_deg}deg);
    }}
  </style>
</head>

<body>

  <h2>Laser Turret Control</h2>

  <form method="POST">
    <button name="start" value="go" 
            style="width:160px;height:50px;font-size:18px;">
      START
    </button>
  </form>

  <h3>Status</h3>
  <p><b>Status:</b> {status}</p>
  <p><b>Current Target:</b> {target}</p>
  <p><b>Location:</b> {location}</p>
  <p><b>Motor Angles:</b> {current}</p>
  <p><b>Laser:</b> {laser}</p>

  <!-- =============== MOTOR VISUALIZATION =================== -->
  <h3>Motor Angle Visualization</h3>

  <div>
    <div>Motor 1: <b>{motor1:.1f}</b></div>
    <div class="bar-container">
      <div class="bar-fill" style="width:{motor1_perc:.1f}%; background:#4CAF50;"></div>
    </div>
  </div>

  <div>
    <div>Motor 2: <b>{motor2:.1f}</b></div>
    <div class="bar-container">
      <div class="bar-fill" style="width:{motor2_perc:.1f}%; background:#2196F3;"></div>
    </div>
  </div>

  <!-- =============== COMPASS VISUAL =================== -->
  <h3>Turret Direction</h3>
  <div id="compass">
    <div id="arrow"></div>
  </div>

  <!-- ========================================================= -->

  <h3>Laser Control</h3>
  <form method="POST">
    <button name="laser_on" value="1" style="width:120px;height:40px;">Laser ON</button>
    <button name="laser_off" value="1" style="width:120px;height:40px;">Laser OFF</button>
  </form>

  <h3>Manual Motor Control</h3>
  <form method="POST">
    Motor1: <input type="number" step="0.1" name="m1_angle"><br><br>
    Motor2: <input type="number" step="0.1" name="m2_angle"><br><br>
    <button style="width:120px;height:40px;">Set Angles</button>
  </form>

  <form method="POST">
    <button name="zero" value="1" style="width:140px;height:40px;">ZERO MOTORS</button>
  </form>

</body>
</html>
"""





    conn.send(b"HTTP/1.1 200 OK\r\n")
    conn.send(b"Content-Type: text/html\r\n")
    conn.send(b"Connection: close\r\n\r\n")
    conn.sendall(html.encode())
    conn.close()
