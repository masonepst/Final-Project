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

# -------------------------------------------------
# STATUS VARIABLES FOR HTML
# -------------------------------------------------
current_target = "Idle"
current_location = "(r=?, θ=?, z=?)"
current_angles = "Motor1=0°, Motor2=0°"
laser_status = "OFF"
sweep_status = "IDLE"
# -------------------------------------------------

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

    if "start" in data:

        sweep_status = "STARTED"
        print("Sweep STARTED")

        motor1 = 0
        motor2 = 0

        # ---------------------------------------
        # SWEEP THROUGH TURRETS
        # ---------------------------------------
        for stud_id, (dist_r, dist_theta) in dist_turrets.items():

            if stud_id == "7":
                continue

            current_target = f"Turret {stud_id}"
            current_location = f"(r={dist_r:.2f}, θ={dist_theta:.2f}, z=N/A)"

            GPIO.output(25, GPIO.LOW)
            laser_status = "OFF"
            time.sleep(2)

            motor1 = dist_theta
            motor2 = 0

            current_angles = f"Motor1={motor1:.1f}°, Motor2={motor2:.1f}°"

            m1.goAngle(motor1)
            m2.goAngle(motor2)

            time.sleep(2)

            GPIO.output(25, GPIO.HIGH)
            laser_status = "ON"
            time.sleep(2)

        # ---------------------------------------
        # SWEEP THROUGH GLOBES
        # ---------------------------------------
        for (dist_r, dist_theta, dist_z) in dist_globes:

            current_target = "Globe"
            current_location = f"(r={dist_r:.2f}, θ={dist_theta:.2f}, z={dist_z:.2f})"

            GPIO.output(25, GPIO.LOW)
            laser_status = "OFF"
            time.sleep(2)

            motor2 = math.degrees(math.atan2(dist_z, dist_r))
            motor1 = dist_theta

            current_angles = f"Motor1={motor1:.1f}°, Motor2={motor2:.1f}°"

            m1.goAngle(motor1)
            m2.goAngle(motor2)

            time.sleep(2)

            GPIO.output(25, GPIO.HIGH)
            laser_status = "ON"
            time.sleep(2)

        GPIO.output(25, GPIO.LOW)
        laser_status = "OFF"

        print("Sweep FINISHED")
        sweep_status = "FINISHED"
        current_target = "Finished"
        current_location = "(r=?, θ=?, z=?)"
        current_angles = f"Motor1={motor1:.1f}°, Motor2={motor2:.1f}°"

    # -------------------------------------------------
    # HTML RESPONSE
    # -------------------------------------------------
    html = f"""<!DOCTYPE html>
<html>
<body>
  <h2>Laser Turret Control</h2>

  <form method="POST">
    <button name="start" value="go" style="width:160px;height:50px;font-size:18px;">
      START SWEEP
    </button>
  </form>

  <h3>Status</h3>
  <p><b>Sweep Status:</b> {sweep_status}</p>
  <p><b>Current Target:</b> {current_target}</p>
  <p><b>Location:</b> {current_location}</p>
  <p><b>Motor Angles:</b> {current_angles}</p>
  <p><b>Laser:</b> {laser_status}</p>

</body>
</html>
"""

    conn.send(b"HTTP/1.1 200 OK\r\n")
    conn.send(b"Content-Type: text/html\r\n")
    conn.send(b"Connection: close\r\n\r\n")
    conn.sendall(html.encode())
    conn.close()
