import json
import requests
import math

def JSON_pull():

	url = "http://172.20.10.3:8000/positions.json" #Actual url "http://192.168.1.254:8000/positions.json"
	response = requests.get(url)

	data = response.json()

	if "turrets" in data:
		turrets = data["turrets"]
	else:
		turrets = []

	if "globes" in data:
		globes = data["globes"]
	else:
		globes = []

	for stud_id, coords in turrets.items(): #items needed if turrets is a dict {}
	    r = coords["r"]
	    theta = coords["theta"]
	    print(f"{stud_id}: r = {r} cm, theta = {theta} rad")

	for coords in globes:
		r = coords["r"]
		theta = coords["theta"]
		z = coords["z"]
		print(f"Globe: r = {r} cm, theta = {theta} rad, z = {z} cm")

	return turrets, globes

def my_turret_distances(turrets, globes):
	dist_turrets = {}
	dist_globes = []

	my_turret = turrets["7"]
	my_r = float(my_turret["r"])
	my_theta = float(my_turret["theta"])
	my_z = 0 # Height of motor

	for stud_id, coords in turrets.items():
		if stud_id == str(7):
			continue

		r = float(coords["r"])
		theta = float(coords["theta"])
		dist_r = r - my_r
		dist_theta = 57.29578*(theta - my_theta)
		dist_turrets[stud_id] = (dist_r, dist_theta)

	for coords in globes:
		r = float(coords["r"])
		theta = float(coords["theta"])
		z = float(coords["z"])
		x_my = my_r * math.cos(my_theta)
		y_my = my_r * math.sin(my_theta)

		x_globe = r * math.cos(theta)
		y_globe = r * math.sin(theta)

		dx = x_globe - x_my
		dy = y_globe - y_my
		dist_r = math.hypot(dx, dy)
		dist_theta = 57.29578*(theta - my_theta)
		dist_z = z - my_z
		dist_globes.append((dist_r, dist_theta, dist_z))

	return dist_globes, dist_turrets



