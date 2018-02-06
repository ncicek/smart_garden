import pdb
import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.PWM as PWM 
import time

#CONSTANTS
NUM_SAMPLES_AVG = 50 #number of readings to average upon any ADC reading

#THRESHOLDS the system will attempt to 



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




#setup io directions and similar init things. gets called at every launch
def setup_io_init():
	PWM.start(PUMP, 0)
	PWM.set_frequency(PUMP, 1000)
	GPIO.setup(HEATER,GPIO.OUT)
	GPIO.setup(LAMP_1,GPIO.OUT)
	GPIO.setup(LAMP_2,GPIO.OUT)
	ADC.setup()
	lamp(False, LAMP_1)
	lamp(False, LAMP_2)
	water_pump(0)
	heater(False)

def read_adc_voltage(pin):
	adc_reading = 0
	for i in range(NUM_SAMPLES_AVG):
		adc_reading += ADC.read(pin)	 #returns float in 0.0-1.0 range
	adc_reading /= NUM_SAMPLES_AVG
	adc_reading *= 1.8	#adc ref is 1.8V
	return (adc_reading)

#enforces hysteresis on output actuators
#acts as a safety mechanism to avoid situations where the output toggles excessively fast and burns out relay contacts
def check_hysterisis():
	#each output actuator needs its own:
	#previous_time
	#previous_state
	#hysterisis_time
	#need to make this OO
	#current_time = time.time()
	#previous_time = #TODO figure this out
	if (previous_status != status):	#if the state has changed
		if (current_time < (previous_time + hysterisis_time)):	#if it has not been that long since the last state change
			#then do not change the state
			return(False)
	return(True)	#otherwise we are good
#Sensors
def read_temp_sensor(sensor_id):
	adc_voltage = read_adc_voltage(sensor_id)
	celcius = adc_to_temp(adc_voltage*4095.0, 6e3)
	return (celcius)

def read_light_sensor(sensor_id):
	adc_voltage = read_adc_voltage(sensor_id)
	lux = adc_to_lux(adc_voltage*4095.0, 18e3)
	return(lux)
	
def read_moisture(sensor_id):
	adc_voltage = read_adc_voltage(sensor_id)
	arb_humidity_value = convert_volt_to_humidity(adc_voltage)
	return (arb_humidity_value)
	
#Actuators	
def heater(status):	 #status == 1 or 0
	if (status):
		GPIO.output(HEATER, GPIO.HIGH)
	else:
		GPIO.output(HEATER, GPIO.LOW)

def lamp(status,id):
	if (status):
		GPIO.output(id, GPIO.LOW)
	else:
		GPIO.output(id, GPIO.HIGH)	

def water_pump(duty):
	PWM.set_duty_cycle(PUMP, duty)
	
def adc_to_temp (ADC, R):
	B = 3470
	T0 = 298.15
	R0 = 10e3
	x = ((ADC*R)/(4095-ADC)/R0)
	log_var = math.log(x,10)
	temp = (1/T0)+((1/B)*log_var)
	temp1 = (1/temp)-273.15
	return(temp1)
	
def adc_to_lux (ADC, R):
	x = (ADC*R)/(4095-ADC)
	log_var = math.log(x,10)
	y = (log_var - 4.96)/(-0.6)
	lux = pow(10,y)
	return(lux)
	
#SCRIPT BEGINS HERE	
setup_io_init()
#loop


pdb.set_trace()


while(1):
	#pid_temp = PID.PID(1,2,3)
	
	if (read_temp_sensor(TEMP_SENSOR_1) > temp_threshold or read_temp_sensor(TEMP_SENSOR_2) > temp_threshold):
		heater(True)
	else:
		heater(False)
		
	if (read_light_sensor(LIGHT_SENSOR_1) > light_threshold):
		lamp(LAMP_1, True)
	else:
		lamp(LAMP_1, False)
		
		
		
		