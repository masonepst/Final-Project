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
        t = threading.Thread(target=Run, daemon=True)
        t.start()

        motor1 = 0
        motor2 = 0

        # motor1 is bottom and motor2 is laser axis

    
    motor1_perc = (motor1 % 180) / 180 * 100
    motor2_perc = (motor2 % 180) / 180 * 100 

        
    refresh = "<meta http-equiv='refresh' content='2'>" if current_page == "run" and status == "Running" else ""


# ================= HTML =================
    if current_page == "main":
        html = f"""
        <!DOCTYPE html>
        <html>
        <body>
        <h2>Laser Turret Control</h2>
        <form method='POST'><button style='width:220px;height:70px;font-size:22px;' name='start'>START</button></form>
        <form method='POST'><button style='width:220px;height:60px;font-size:20px;' name='goto_calib'>CALIBRATION</button></form>
        </body>
        </html>
        """


    elif current_page == "run":
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>{refresh}</head>
        <body>
        <h2>RUN STATUS</h2>
        <p>Status: {status}</p>
        <p>Target: {target}</p>
        <p>Location: {location}</p>
        <p>Motors: {current}</p>
        <p>Laser: {laser}</p>
        <form method='POST'><button style='width:200px;height:50px;font-size:18px;' name='goto_main'>BACK</button></form>
        </body>
        </html>
        """


    else:
        html = f"""
        <!DOCTYPE html>
        <html>
        <body>
        <h2>CALIBRATION</h2>
        <form method='POST'>
        Motor1: <input type='number' step='0.1' name='m1_angle'><br><br>
        Motor2: <input type='number' step='0.1' name='m2_angle'><br><br>
        <button style='width:200px;height:45px;font-size:18px;'>SET ANGLES</button>
        </form>
        <br>
        <form method='POST'>
        <button style='width:200px;height:45px;font-size:18px;' name='laser_on'>LASER ON</button>
        <button style='width:200px;height:45px;font-size:18px;' name='laser_off'>LASER OFF</button>
        </form>
        <br>
        <form method='POST'><button style='width:200px;height:45px;font-size:18px;' name='zero'>ZERO MOTORS</button></form>
        <br>
        <form method='POST'><button style='width:200px;height:45px;font-size:18px;' name='goto_main'>BACK</button></form>
        </body>
        </html>
        """






    conn.send(b"HTTP/1.1 200 OK\r\n")
    conn.send(b"Content-Type: text/html\r\n")
    conn.send(b"Connection: close\r\n\r\n")
    conn.sendall(html.encode())
    conn.close()
