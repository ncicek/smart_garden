import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC

#ABSTRACT PINS INTO BOARD CONNECTOR NAMES
RELAY1 = "P9_11"
RELAY2 = "P9_13"
RELAY3 = "P9_15"
RELAY4 = "P9_17"
FET1 = "P9_24"
FET2 = "P9_23"
RES_SENSOR_1 = "P9_33"
RES_SENSOR_2 = "P9_39"
RES_SENSOR_3 = "P9_37"
RES_SENSOR_4 = "P9_35"
VOLT_SENSOR_1 = "P9_38"
VOLT_SENSOR_2 = "P9_40"

#ABSTRACT BOARD CONNECTOR NAMES INTO PERIHPERALS
HEATER = RELAY1
LAMP_1 = RELAY2
LAMP_2 = RELAY3
PUMP = FET1
TEMP_SENSOR_1 = RES_SENSOR_1
TEMP_SENSOR_2 = RES_SENSOR_2
LIGHT_SENSOR_1 = RES_SENSOR_3
LIGHT_SENSOR_2 = RES_SENSOR_4
MOISTURE_SENSOR_1 = VOLT_SENSOR_1
MOISTURE_SENSOR_2 = VOLT_SENSOR_2




#setup io directions and similar init things. gets called at every launch
def setup_io_init():
	GPIO.setup(HEATER,GPIO.OUT)
	GPIO.setup(PUMP,GPIO.OUT)
	
	ADC.setup()

def read_adc_voltage(pin):
	return (ADC.read(pin)*1.8)
	
#Sensors
def read_temp_sensor(sensor_id):
	adc_voltage = read_adc_voltage(sensor_id)
	celcius = convert_volt_to_celcius(adc_voltage)
	return (celcius)

def read_light_sensor(sensor_id):
	adc_voltage = read_adc_voltage(sensor_id)
	lux = convert_volt_to_lux(adc_voltage)
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

def lamp(status,id):	#status == 1 or 0, id = PIN_MAP(LAMP_1, LAMP_2)
	if (status):
		GPIO.output(id, GPIO.HIGH)
	else:
		GPIO.output(id, GPIO.LOW)	

def water_pump(status):
	if (status):
		GPIO.output(PUMP, GPIO.HIGH)
	else:
		GPIO.output(PUMP, GPIO.LOW)		
	
	
#SCRIPT BEGINS HERE	
setup_io_init()
#loop
while(1):
	if (read_temp_sensor > temp_threshold):
		heater(True)