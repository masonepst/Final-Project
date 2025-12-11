import socket
import multiprocessing
# Keep the motor control code (Stepper, Shifter)
from lab8 import Stepper, Shifter
import RPi.GPIO as GPIO
# import Project is removed, as it contained JSON_pull and my_turret_distances
import math
import time

# --- Setup ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(25, GPIO.OUT)  # GPIO 25 likely controls the laser

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


# --- HTTP Data Parsing Function ---
def parsePOSTdata(data):
    # This function is necessary to read button presses/input from the browser
    data_dict = {}
    idx = data.find('\r\n\r\n') + 4
    data = data[idx:]
    data_pairs = data.split('&')
    for pair in data_pairs:
        key_val = pair.split('=')
        if len(key_val) == 2:
            data_dict[key_val[0]] = key_val[1]
    return data_dict


# --- JSON Code Removed Here ---
# Removed: turrets, globes = JSON_pull()
# Removed: dist_globes, dist_turrets, my_r, my_theta = my_turret_distances(turrets, globes)
# Removed: All printing loops for turrets and globes distances

# --- Main Web Server Loop ---
while True:
    conn, addr = sock.accept()
    data = parsePOSTdata(conn.recv(1024).decode())

    # --- Manual Laser Control ---
    if "laser_on" in data:
        GPIO.output(25, GPIO.HIGH)
        print("Laser ON")

    if "laser_off" in data:
        GPIO.output(25, GPIO.LOW)
        print("Laser OFF")

    # --- Motor Zeroing ---
    if "zero" in data:
        print("Zeroing motors...")
        m1.zero()
        m2.zero()
        motor1 = 0
        motor2 = 0

    # --- Manual Motor 1 Control ---
    if "m1_angle" in data:
        try:
            angle = float(data["m1_angle"])
            print(f"Moving Motor1 to {angle}")
            m1.goAngle(angle)
            motor1 = angle
        except ValueError:
            print("Invalid angle for Motor 1")

    # --- Manual Motor 2 Control ---
    if "m2_angle" in data:
        try:
            angle = float(data["m2_angle"])
            print(f"Moving Motor2 to {angle}")
            m2.goAngle(angle)
            motor2 = angle
        except ValueError:
            print("Invalid angle for Motor 2")

    # --- Automated 'start' Sweep Removed/Modified ---
    # Since the JSON data for turret and globe locations is gone,
    # the 'start' block now just prints a message and performs motor zeroing.
    # You will need to rewrite the logic inside this block if you want the
    # motors to sweep without relying on the external JSON data.
    if "start" in data:
        print("START SWEEP button pressed. (Automated sweep requires external data which was removed.)")
        # Example of what you could do instead of the complex JSON sweep:
        # Perform a simple test sweep for 5 seconds
        # m1.goAngle(45)
        # m2.goAngle(10)
        # time.sleep(5)
        # m1.goAngle(0)
        # m2.goAngle(0)
        GPIO.output(25, GPIO.LOW) # Turn laser off when done
        print("Done")


    # --- HTML Response (Kept the original HTML) ---
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

    # --- Send HTTP Response ---
    conn.send(b"HTTP/1.1 200 OK\r\n")
    conn.send(b"Content-Type: text/html\r\n")
    conn.send(b"Connection: close\r\n\r\n")
    conn.sendall(html.encode())
    conn.close()