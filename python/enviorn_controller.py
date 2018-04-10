#takes one argument: mode=logger or server

import pdb
import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.PWM as PWM 
from datetime import datetime, time
import time as timer
import logging
import sys
import math
#from subprocess import call, check_output
import subprocess
import urllib.request
import json
import csv
from PIL import Image
import numpy as np

#CONSTANTS
LOGGER_INTERVAL = 1.0 #used in logger mode seconds
PUMP_TIMER_INTERVAL = 2 #seconds to keep on pump for one cycle
WATER_TIMER_INTERVAL = 1*60*60 #12hrs


NUM_SAMPLES_AVG = 15 #number of readings to average upon any ADC reading
ADC_DELAY = 0.005

#ABSTRACT PINS INTO BOARD CONNECTOR NAMES
RELAY1 = "P9_11"
RELAY2 = "P9_13"
RELAY3 = "P9_15"
RELAY4 = "P9_17"
FET1 = "P9_42"
FET2 = "P9_23"
RES_SENSOR_1 = "P9_33"
RES_SENSOR_2 = "P9_39"
RES_SENSOR_3 = "P9_37"
RES_SENSOR_4 = "P9_35"
VOLT_SENSOR_1 = "P9_38"
VOLT_SENSOR_2 = "P9_40"
try:
	image_ref = Image.open('bug.jpg')
	image_ref = np.asarray(image_ref.convert('L'))
	image_ref = image_ref.astype(np.int16)
except FileNotFoundError:
	image_ref = None
#ABSTRACT BOARD CONNECTOR NAMES INTO PERIHPERALS
HEATER = RELAY2
LAMP_1 = RELAY3
LAMP_2 = RELAY4
PUMP = FET1
#from top to bottom header position on board
TEMP_SENSOR_1 = RES_SENSOR_2
TEMP_SENSOR_2 = RES_SENSOR_3
LIGHT_SENSOR_1 = RES_SENSOR_4
LIGHT_SENSOR_2 = RES_SENSOR_1
MOISTURE_SENSOR_1 = VOLT_SENSOR_2
MOISTURE_SENSOR_2 = VOLT_SENSOR_1

#RESISTOR DIVIDER CALIBRATION
RESISTOR_CALIBRATION = {TEMP_SENSOR_1:17.412E3,
						TEMP_SENSOR_2:17.484E3,
						LIGHT_SENSOR_1:6.011E3,
						LIGHT_SENSOR_2:6.009E3
}

#track states for logging garbage way
actuator_state = {
	'heater':False,
	'lamp_1':False,
	'lamp_2':False,
	'pump':False
}

server_URL = "http://192.168.1.105	:5000"

current_time = timer.time()
previous_time = timer.time()
previous_pump_time = 0
day_counter = 0
displaced_water_litres = 0

garden_settings = {
	#enviornmental_variables
		#parameters
		
	'temp':{
		'control_method':'auto',	#manual vs auto
		'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
		'sensor_1':10,
		'sensor_2':20
	},
	
	'water':{
		'control_method':'auto',	#manual vs auto
		'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
		'sensor_1':10,
		'sensor_2':20
	},
	
	'light_1':{
		'control_method':'auto',	#manual vs auto
		'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
		'sensor_1':10
	},
	
	'light_2':{
		'control_method':'auto',	#manual vs auto
		'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
		'sensor_1':10
	},
	
	'bugs':{
		'worm_level':0,
		'spider_level':0
	}
}

def set_up_logging():
	output_format = logging.Formatter('%(asctime)s %(pathname)s [%(process)d]: %(levelname)s %(message)s')
	# File handler
	file_handler = logging.FileHandler('garden.log')
	file_handler.setLevel(logging.DEBUG)
	file_handler.setFormatter(output_format)
		
	stdout_handler = logging.StreamHandler(sys.stdout)
	stdout_handler.setLevel(logging.DEBUG)
	stdout_handler.setFormatter(output_format)

	# Combined logger used elsewhere in the script
	logger = logging.getLogger('garden-log')
	logger.setLevel(logging.ERROR)
	logger.addHandler(file_handler)	#log to both display and file
	logger.addHandler(stdout_handler)

	return logger
	
#setup io directions and similar init things. gets called at every launch
def setup_io_init():
	logger.info("Initializing IO")
	PWM.start(PUMP, 0)
	PWM.set_frequency(PUMP, 1000)
	water_pump(0)
	GPIO.setup(HEATER,GPIO.OUT)
	GPIO.setup(LAMP_1,GPIO.OUT)
	GPIO.setup(LAMP_2,GPIO.OUT)	
	lamp(False, LAMP_1)
	lamp(False, LAMP_2)
	heater(False)
	ADC.setup()

def read_adc_voltage(pin):
	adc_reading = 0
	for i in range(NUM_SAMPLES_AVG):
		adc_reading += ADC.read(pin)	 #returns float in 0.0-1.0 range
		timer.sleep(ADC_DELAY)
	adc_reading /= NUM_SAMPLES_AVG
	adc_reading *= 1.8	#adc ref is 1.8V
	logger.debug("read ADC %d volts" %adc_reading)
	return (adc_reading)

#Sensors
def read_temp_sensor(sensor_id):
	assert sensor_id in [TEMP_SENSOR_1,TEMP_SENSOR_2]
	adc_voltage = read_adc_voltage(sensor_id)
	celcius = adc_to_temp(adc_voltage*4095.0/1.8, RESISTOR_CALIBRATION[sensor_id])
	logger.debug("read temp_sensor %s %dC" %(sensor_id, celcius))
	return (celcius)

def read_light_sensor(sensor_id):
	assert sensor_id in [LIGHT_SENSOR_1,LIGHT_SENSOR_2]
	adc_voltage = read_adc_voltage(sensor_id)
	lux = adc_to_lux(adc_voltage*4095.0/1.8, RESISTOR_CALIBRATION[sensor_id])
	logger.debug("read light_sensor %s %d lux" %(sensor_id, lux))
	return(lux)
	
def read_moisture_sensor(sensor_id):
	assert sensor_id in [MOISTURE_SENSOR_1,MOISTURE_SENSOR_2]
	adc_voltage = read_adc_voltage(sensor_id)
	arb_humidity_value = adc_to_humidity(adc_voltage)
	logger.debug("read soil moisture %s %d units" %(sensor_id, arb_humidity_value))
	return (arb_humidity_value)
	
#Actuators	
def heater(status):	 #status == 1 or 0
	if (status):
		actuator_state['heater'] = True;
		GPIO.output(HEATER, GPIO.HIGH)
		logger.info("heater on")
	else:
		actuator_state['heater'] = False;
		GPIO.output(HEATER, GPIO.LOW)
		logger.info("heater off")


def lamp(status,id):
	if id == LAMP_1:
		idx = 'lamp_1'
	elif id == LAMP_2:
		idx = 'lamp_2'
	else:
		raise
		
	actuator_state[idx] = status;
	
	if (status):
		GPIO.output(id, GPIO.LOW) #relay inputs are active low
		logger.info("lamp %s on" %id)
	else:
		GPIO.output(id, GPIO.HIGH)	
		logger.info("lamp %s off" %id)

def water_pump(duty):	#PWM duty cycle is between 0-100
	KICK_START_THRESHOLD = 40	#min duty cycle that the pump can startup at
	DECAY_COEFF = 0.9 #between 0-1.0
	ITR_TIME = 0.3 #seconds
	if (duty <= 0):
		actuator_state['pump'] = False;
		PWM.set_duty_cycle(PUMP, 0)
		logger.info('water pump off. setting duty to %d'%0)
	elif (duty > KICK_START_THRESHOLD):
		actuator_state['pump'] = True;
		PWM.set_duty_cycle(PUMP, duty)
		logger.info('water pump on. setting duty to %d'%duty)
	else:
		actuator_state['pump'] = True;
		#ramp down sequence starts with high duty cycle to overcome motor stiction and quickly ramps down to the desired duty cycle
		logger.info('water pump on. ramping down to %d'%duty)
		while (ramp_down_duty > duty):
			PWM.set_duty_cycle(PUMP, ramp_down_duty)
			ramp_down_duty = ramp_down_duty * DECAY_COEFF	# decay iteratively
			timer.sleep(ITR_TIME)	#wait a bit	
			logger.debug('ramp_down duty %d'%ramp_down_duty)
		PWM.set_duty_cycle(PUMP, duty)	
		logger.debug('ramp_down duty %d'%duty)
	
def adc_to_temp (ADC, R):
	B = 3470
	T0 = 298.15
	R0 = 10e3
	x = ((ADC*R)/(4095-ADC)/R0)
	log_var = math.log(x,10)	
	temp = (1/T0)+((1/B)*log_var)
	temp1 = (1/temp)-273.15
	logger.debug('adc to temp conversion. adc=%d temp =%dC'%(ADC, temp1))
	return(temp1)
	
def adc_to_lux (ADC, R):
	x = (ADC*R)/(4095-ADC)
	log_var = math.log(x,10)
	y = (log_var - 4.96)/(-0.6)
	lux = pow(10,y)
	logger.debug('adc to lux conversion. adc=%d lux =%d lux'%(ADC, lux))
	return(lux)
	
def adc_to_humidity(ADC):
	return ADC*100/1.8
	
def handle_watering():
	global current_time #YOLO
	global previous_time #YOLO
	global previous_pump_time
	global day_counter
	global displaced_water_litres
	
	current_time = timer.time() 
	if math.floor((current_time - start_time) / (60*60*24)):
		day_counter = day_counter + 1;
		displaced_water_litres = 0 #reset water displacement every day

	if current_time > (previous_time + WATER_TIMER_INTERVAL):	
		if (garden_settings['water']['sensor_1'] < garden_settings['water']['setpoint/power']) and (garden_settings['water']['sensor_2'] < garden_settings['water']['setpoint/power']):
			if displaced_water_litres < 0.3:
				previous_time = current_time
				actuator_state['pump'] = True	
		
	if actuator_state['pump'] and (current_time < (previous_time + PUMP_TIMER_INTERVAL)):
		previous_pump_time = current_time
		water_pump(50)
		displaced_water_litres = displaced_water_litres + (4.5 * PUMP_TIMER_INTERVAL * .8 / 60.0) #.8 is a fudge factor to account for power limit
	else:
		actuator_state['pump'] = False
		water_pump(0)

def handle_lighting():
	#auto mode
	if (garden_settings["light_1"]["control_method"] == "auto") or (garden_settings["light_2"]["control_method"] == "auto"):
		now = datetime.now()
		now_time = now.time()
		#print(now_time)
		#print(time(10+4+12-24,00))
		if ~(now_time >= time(8+4,00) and now_time <= time(7+4+12,00)):	#during the daytime, toggle lamp based on thresholds
			if (garden_settings['light_1']['sensor_1'] < garden_settings['light_1']['setpoint/power']):
				lamp(True, LAMP_1)
			else:
				lamp(False, LAMP_1)
				
			if (garden_settings['light_2']['sensor_1'] < garden_settings['light_2']['setpoint/power']):
				lamp(True, LAMP_2)
			else:
				lamp(False, LAMP_2)	
			
		else:	#at nighttime, let plants catch some ZZZs
			print("nightitme")
			lamp(False, LAMP_1)	
			lamp(False, LAMP_2)	
	#manual mode
	else:	
		lamp(garden_settings["light_1"]["setpoint/power"]>0, LAMP_1)
		lamp(garden_settings["light_2"]["setpoint/power"]>0, LAMP_2)
		
def handle_heating():
	#auto mode
	if garden_settings["temp"]["control_method"] == "auto":
		if (garden_settings["temp"]["sensor_1"] > garden_settings['temp']['setpoint/power'] or garden_settings['temp']['sensor_2'] > garden_settings['temp']['setpoint/power']):
			heater(False)
		else:
			heater(True)
	#manual mode	
	else:	
		heater(garden_settings["temp"]["setpoint/power"]>0)

	
#take a pic, send to server and return bug state
def check_for_bug():
	global image_ref
	logger.debug('checking for bug')
	#curl -F "file=@image.jpg" http://localhost:5000/garden/upload

	logger.debug('fswebcam')
	subprocess.check_output(["fswebcam","--no-banner","-r 640x480","bug.jpg"])	 #take pic
	image_curr = Image.open('bug.jpg')
	image_curr = np.asarray(image_curr.convert('L'))
	image_test = image_curr.astype(np.int16) #this array will be sent to be compared with the previous image
	#pdb.set_trace()
	if check_diff_in_img(image_test,image_ref):
		logger.debug('curling')
		print("writing file to server")
		bug_response = subprocess.check_output(["curl","-F","file=@bug.jpg",server_URL+"/garden/upload"])	#upload to server
		bug_response = bug_response.decode('UTF-8')
		logger.debug('got curl response')
		print(bug_response)
		if bug_response == "OK":
			print("ok")
		else:
			raise
	image_ref = image_test
		
def sync_time_from_server():
	received_time = urllib.request.urlopen(server_URL + "/garden/time").read().decode()
	received_time = str(received_time)
	logger.debug("Setting time to: " + received_time)
	#["sudo", "date", "-s", "Thu Aug  9 21:31:26 UTC 2012"]
	#date -s '@2147483647'
	subprocess.call(["date","-s","@" + received_time])	 #take pic
	

def sync_with_server():
	logger.debug('syncing with server')
	logger.debug('uploading sensors')
	print(server_URL + "/garden_RESTful_write" + "/temp/sensor_1/" + str(garden_settings["temp"]["sensor_1"]))
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/temp/sensor_1/" + str(garden_settings["temp"]["sensor_1"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/temp/sensor_2/" + str(garden_settings["temp"]["sensor_2"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/water/sensor_1/" + str(garden_settings["water"]["sensor_1"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/water/sensor_2/" + str(garden_settings["water"]["sensor_2"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/light_1/sensor_1/" + str(garden_settings["light_1"]["sensor_1"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/light_2/sensor_1/" + str(garden_settings["light_2"]["sensor_1"])).read()
	#urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/bugs/spider_level/" + str(garden_settings["bugs"]["spider_level"])).read()
	#urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/bugs/worm_level/" + str(garden_settings["bugs"]["worm_level"])).read()
	
	#download json response
	logger.debug('downloading setpoints')
	json_response = urllib.request.urlopen(server_URL + "/garden").read().decode()
	json_response_dict = json.loads(json_response)["garden_settings"]	#parse to dict

	#update local garden_settings dict with values from response
	logger.debug('refresh local dict')
	garden_settings["temp"]["control_method"] = json_response_dict["temp"]["control_method"]
	garden_settings["temp"]["setpoint/power"] = json_response_dict["temp"]["setpoint/power"]
	garden_settings["water"]["control_method"] = json_response_dict["water"]["control_method"]
	garden_settings["water"]["setpoint/power"] = json_response_dict["water"]["setpoint/power"]
	garden_settings["light_1"]["setpoint/power"] = json_response_dict["light_1"]["setpoint/power"]
	garden_settings["light_1"]["control_method"] = json_response_dict["light_1"]["control_method"]
	garden_settings["light_2"]["setpoint/power"] = json_response_dict["light_2"]["setpoint/power"]
	garden_settings["light_2"]["control_method"] = json_response_dict["light_2"]["control_method"]
	garden_settings["bugs"]["spider_level"] = json_response_dict["bugs"]["spider_level"]
	garden_settings["bugs"]["worm_level"] = json_response_dict["bugs"]["worm_level"]
	
		
def check_diff_in_img(img1,img2): 
	diff = img1 - img2 
	diff = np.absolute(diff)
	J = 0
	rows = diff.shape[0]
	columns = diff.shape[1]
	J = np.sum(diff) #sums up all elements in difference image
	threshold = 0.1*(rows*columns*255)
	if (J >= threshold):
		return 1
	else:
		return 0


def read_all_sensors():
	#read all sensors and update the garden_settings dictionary
	garden_settings["temp"]["sensor_1"] = read_temp_sensor(TEMP_SENSOR_1)
	garden_settings["temp"]["sensor_2"] = read_temp_sensor(TEMP_SENSOR_2)
	garden_settings["water"]["sensor_1"] = read_moisture_sensor(MOISTURE_SENSOR_1)
	garden_settings["water"]["sensor_2"] = read_moisture_sensor(MOISTURE_SENSOR_2)
	garden_settings["light_1"]["sensor_1"] = read_light_sensor(LIGHT_SENSOR_1)
	garden_settings["light_2"]["sensor_1"] = read_light_sensor(LIGHT_SENSOR_2)
	
def pretty(d, indent=0):
   for key, value in d.items():
      print('\t' * indent + str(key))
      if isinstance(value, dict):
         pretty(value, indent+1)
      else:
        print('\t' * (indent+1) + str(value))

def flatten(current, key, result):
    if isinstance(current, dict):
        for k in current:
            new_key = "{0}.{1}".format(key, k) if len(key) > 0 else k
            flatten(current[k], new_key, result)
    else:
        result[key] = current
    return result

def csv_handler():
	with open(filename,'a', newline='') as csvfile:
		csvwriter = csv.writer(csvfile)
		time = str(timer.time())
		time_pretty = str(datetime.now())
		for i in actuator_state:
			actuator_state[i] = 1 if actuator_state[i] == True else 0	#convert bools to 1/0 for excel
			
		row = [time, time_pretty, garden_settings["temp"]["sensor_1"], garden_settings["temp"]["sensor_2"], garden_settings["water"]["sensor_1"], garden_settings["water"]["sensor_2"], garden_settings["light_1"]["sensor_1"], garden_settings["light_2"]["sensor_1"], actuator_state['heater'], actuator_state['lamp_1'], actuator_state['lamp_2'], actuator_state['pump'], displaced_water_litres ]
		print(row)
		
		csvwriter.writerow(row)
		 
#SCRIPT BEGINS HERE	

		
logger = set_up_logging()
logger.info("Starting up garden program")

#init csv
filename = "garden_log_" + str(datetime.now()) + ".csv"
with open(filename,'w', newline='') as csvfile:
	csvwriter = csv.writer(csvfile)
	csvwriter.writerow(['time(s)','time pretty','temp_sensor_1','temp_sensor_2','water_sensor_1','water_sensor_2','light_1_sensor','light_2_sensor','heater_state','lamp_1_state','lamp_2_state','pump_state','displaced_water_litres'])

setup_io_init()
start_time = timer.time()
#pdb.set_trace()
mode = sys.argv
mode = mode[1]
camera_timer = timer.time()
print("current time is: " + str(timer.time()))
if mode == 'server':
	logger.info("Server mode")

	sync_time_from_server()
	#main loop
	while(True):
		read_all_sensors()
		sync_with_server()
		
		handle_heating()
		handle_lighting()
		#pretty(garden_settings)
		csv_handler()
		#print(garden_settings['light_1']['setpoint/power'])
		if (timer.time() - camera_timer >= 3): #take a picture every 3 seconds
			check_for_bug()
			camera_timer = timer.time()
		#handle_watering()
		
elif mode == 'logger':
	#explicitly set automode params here for logger mode:
	garden_settings["temp"]["control_method"] = "auto"
	garden_settings["temp"]["setpoint/power"] = 30
	garden_settings["light_1"]["control_method"] = "auto"
	garden_settings["light_1"]["setpoint/power"] = 100
	garden_settings["light_2"]["control_method"] = "auto"
	garden_settings["light_2"]["setpoint/power"] = 100
	garden_settings["water"]["control_method"] = "auto"
	garden_settings["water"]["setpoint/power"] = 68.8
	
	logger.info("Logger mode")

	starttime=timer.time()
	while True:
		#print ('tick')
		read_all_sensors()
		handle_heating()
		handle_lighting()
		handle_watering()
		csv_handler()
		timer.sleep(LOGGER_INTERVAL - ((timer.time() - starttime) % LOGGER_INTERVAL))

elif mode == 'pdb':
	pdb.set_trace()
else:
	print("No mode specified")
	
