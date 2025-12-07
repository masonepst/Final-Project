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

# Shared dictionary to store status visible to HTML
manager = multiprocessing.Manager()
status = manager.dict()
status["target"] = "Idle"
status["location"] = "(r=?, θ=?, z=?)"
status["angles"] = "Motor1=0°, Motor2=0°"
status["laser"] = "OFF"
status["sweep"] = "IDLE"


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


# ---------------------------------------------------
# SWEEP FUNCTION — RUNS IN BACKGROUND PROCESS
# ---------------------------------------------------
def do_sweep(status):

    status["sweep"] = "STARTED"

    # ---------------- TURRETS -------------------
    for stud_id, (dist_r, dist_theta) in dist_turrets.items():

        if stud_id == "7":
            continue

        status["target"] = f"Turret {stud_id}"
        status["location"] = f"(r={dist_r:.2f}, θ={dist_theta:.2f}, z=N/A)"

        GPIO.output(25, GPIO.LOW)
        status["laser"] = "OFF"
        time.sleep(1)

        motor1 = dist_theta
        motor2 = 0

        status["angles"] = f"Motor1={motor1:.1f}°, Motor2={motor2:.1f}°"
        m1.goAngle(motor1)
        m2.goAngle(motor2)

        time.sleep(1)

        GPIO.output(25, GPIO.HIGH)
        status["laser"] = "ON"
        time.sleep(1)

    # ---------------- GLOBES -------------------
    for (dist_r, dist_theta, dist_z) in dist_globes:

        status["target"] = "Globe"
        status["location"] = f"(r={dist_r:.2f}, θ={dist_theta:.2f}, z={dist_z:.2f})"

        GPIO.output(25, GPIO.LOW)
        status["laser"] = "OFF"
        time.sleep(1)

        motor2 = math.degrees(math.atan2(dist_z, dist_r))
        motor1 = dist_theta

        status["angles"] = f"Motor1={motor1:.1f}°, Motor2={motor2:.1f}°"
        m1.goAngle(motor1)
        m2.goAngle(motor2)

        time.sleep(1)

        GPIO.output(25, GPIO.HIGH)
        status["laser"] = "ON"
        time.sleep(1)

    GPIO.output(25, GPIO.LOW)
    status["laser"] = "OFF"

    status["sweep"] = "FINISHED"
    status["target"] = "Idle"
    status["location"] = "(r=?, θ=?, z=?)"


# ---------------------------------------------------
# MAIN WEB SERVER LOOP
# ---------------------------------------------------
while True:
    conn, addr = sock.accept()

    request = conn.recv(2048).decode()
    data = parsePOSTdata(request)

    # IF START BUTTON PRESSED → launch process (non-blocking)
    if "start" in data:
        p = multiprocessing.Process(target=do_sweep, args=(status,))
        p.start()

    # Build HTML page
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="1"> 
</head>
<body>
  <h2>Laser Turret Control</h2>

  <form method="POST">
    <button name="start" value="go" 
      style="width:160px;height:50px;font-size:18px;">
      START SWEEP
    </button>
  </form>

  <h3>Status</h3>
  <p><b>Sweep Status:</b> {status["sweep"]}</p>
  <p><b>Current Target:</b> {status["target"]}</p>
  <p><b>Location:</b> {status["location"]}</p>
  <p><b>Motor Angles:</b> {status["angles"]}</p>
  <p><b>Laser:</b> {status["laser"]}</p>

</body>
</html>
"""

    conn.send(b"HTTP/1.1 200 OK\r\n")
    conn.send(b"Content-Type: text/html\r\n")
    conn.send(b"Connection: close\r\n\r\n")
    conn.sendall(html.encode())
    conn.close()
