import pdb
import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.PWM as PWM 
from datetime import datetime, time
import time as timer
import logging
import sys
import math
from subprocess import call, check_output
import urllib.request
import json


#CONSTANTS
NUM_SAMPLES_AVG = 25 #number of readings to average upon any ADC reading
LIGHT_THRESHOLD = 100
ADC_DELAY = 0.01
TEMP_THRESHOLD = 21.5

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

server_URL = "http://jdbens.mooo.com"

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
		'level':0
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
	logger.setLevel(logging.DEBUG)
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
	assert sensor_id in [MOISTURE_SENSOR_1,MOISTURE_SENSOR_1]
	adc_voltage = read_adc_voltage(sensor_id)
	arb_humidity_value = adc_to_humidity(adc_voltage)
	logger.debug("read soil moisture %s %d units" %(sensor_id, arb_humidity_value))
	return (arb_humidity_value)
	
#Actuators	
def heater(status):	 #status == 1 or 0
	if (status):
		GPIO.output(HEATER, GPIO.HIGH)
		logger.info("heater on")
	else:
		GPIO.output(HEATER, GPIO.LOW)
		logger.info("heater off")

def lamp(status,id):
	if (status):
		GPIO.output(id, GPIO.LOW)
		logger.info("lamp %s on" %id)
	else:
		GPIO.output(id, GPIO.HIGH)	
		logger.info("lamp %s off" %id)

def water_pump(duty):	#PWM duty cycle is between 0-100
	KICK_START_THRESHOLD = 40	#min duty cycle that the pump can startup at
	DECAY_COEFF = 0.9 #between 0-1.0
	ITR_TIME = 0.3 #seconds
	if (duty <= 0):
		PWM.set_duty_cycle(PUMP, 0)
		logger.info('water pump off. setting duty to %d'%0)
	elif (duty > KICK_START_THRESHOLD):
		PWM.set_duty_cycle(PUMP, duty)
		logger.info('water pump on. setting duty to %d'%duty)
	else:
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
	return ADC
	
def handle_watering():
	WATER_TIMER_INTERVAL = 12*60*60 #12hrs
	
	handle_watering.current_time = vars(handle_watering).setdefault('current_time',-1)	#init static var
	handle_watering.previous_time = vars(handle_watering).setdefault('previous_time',-1)	#init static var
	
	if handle_watering.current_time > (handle_watering.previous_time + WATER_TIMER_INTERVAL):		
		previous_time = current_time;
		water_pump(50);
	else:
		water_pump(0);

def handle_lighting():
	#auto mode
	if (garden_settings["light_1"]["control_method"] == "auto") or (garden_settings["light_2"]["control_method"] == "auto"):
		now = datetime.now()
		now_time = now.time()
		print(now_time)
		if now_time >= time(8,00) and now_time <= time(10+12,00):	#during the daytime, toggle lamp based on thresholds
		
			if (garden_settings[light_1][sensor_1] < LIGHT_THRESHOLD):
				lamp(True, LAMP_1)
			else:
				lamp(False, LAMP_1)
				
			if (garden_settings[light_2][sensor_1] < LIGHT_THRESHOLD):
				lamp(True, LAMP_2)
			else:
				lamp(False, LAMP_2)	
			
		else:	#at nighttime, let plants catch some ZZZs
			lamp(False, LAMP_1)	
			lamp(False, LAMP_2)	
	#manual mode
	else:	
		lamp(garden_settings["light_1"]["setpoint/power"]>0, LAMP_1)
		lamp(garden_settings["light_2"]["setpoint/power"]>0, LAMP_2)
		
def handle_heating():
	#auto mode
	if garden_settings["heater"]["control_method"] == "auto":
		if (garden_settings[temp][sensor_1] > TEMP_THRESHOLD or garden_settings[temp][sensor_2] > TEMP_THRESHOLD):
			heater(True)
		else:
			heater(False)
	#manual mode	
	else:	
		heater(garden_settings["heater"]["setpoint/power"]>0)

	
#take a pic, send to server and return bug state
def check_for_bug():
	#curl -F "file=@image.jpg" http://localhost:5000/garden/upload

	call(["fswebcam","--no-banner","-r 1280x720","bug.jpg"])	 #take pic
	bug_response = check_output(["curl","-F","file=@bug.jpg","http://localhost:5000/garden/upload"])	#upload to server
	if bug_response == "detected worm":
		garden_settings["bugs"]["level"] = 100
		return True
	elif bug_response == "no worm detected":
		garden_settings["bugs"]["level"] = 0
		return False
	else:
		raise



def sync_with_server():
	#upload sensor data
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/temp/sensor_1/" + str(garden_settings["temp"]["sensor_1"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/temp/sensor_2/" + str(garden_settings["temp"]["sensor_2"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/water/sensor_1/" + str(garden_settings["water"]["sensor_1"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/water/sensor_2/" + str(garden_settings["water"]["sensor_2"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/light_1/sensor_1/" + str(garden_settings["light_1"]["sensor_1"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/light_2/sensor_1/" + str(garden_settings["light_2"]["sensor_1"])).read()
	urllib.request.urlopen(server_URL + "/garden_RESTful_write" + "/bugs/level/" + str(garden_settings["bug_level"])).read()
	
	#download json response
	json_response = urllib.request.urlopen(server_URL + "/garden").read().decode()
	json_response_dict = json.loads(json_response)["garden_settings"]	#parse to dict

	#update local garden_settings dict with values from response
	garden_settings["temp"]["control_method"] = json_response_dict["temp"]["control_method"]
	garden_settings["temp"]["setpoint/power"] = json_response_dict["temp"]["setpoint/power"]
	garden_settings["water"]["control_method"] = json_response_dict["water"]["control_method"]
	garden_settings["water"]["setpoint/power"] = json_response_dict["water"]["setpoint/power"]
	garden_settings["light_1"]["control_method"] = json_response_dict["light_1"]["control_method"]
	garden_settings["light_2"]["setpoint/power"] = json_response_dict["light_2"]["setpoint/power"]
		
	
def read_all_sensors():
	#read all sensors and update the garden_settings dictionary
	garden_settings[temp][sensor_1] = read_temp_sensor(TEMP_SENSOR_1)
	garden_settings[temp][sensor_2] = read_temp_sensor(TEMP_SENSOR_2)
	garden_settings[water][sensor_1] = read_moisture_sensor(MOISTURE_SENSOR_1)
	garden_settings[water][sensor_2] = read_moisture_sensor(MOISTURE_SENSOR_2)
	garden_settings[light_1][sensor_1] = read_light_sensor(LIGHT_SENSOR_1)
	garden_settings[light_2][sensor_1] = read_light_sensor(LIGHT_SENSOR_2)
	
#SCRIPT BEGINS HERE	

logger = set_up_logging()
logger.info("Starting up garden program")

setup_io_init()

#main loop
while(1):
	read_all_sensors()
	sync_with_server()
	
	handle_heating()
	handle_lighting()
	check_for_bug()
	#handle_watering()
	