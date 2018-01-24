#Sensors
def read_temp_sensor(sensor_id):
	if (sensor_id == 0):

	elif (sensor_id == 1):
	
	return (celcius)

def read_light_sensor(sensor_id):
	if (sensor_id == 0):

	elif (sensor_id == 1):
	
	return(lux)
	
def read_moisture(sensor_id):
	if (sensor_id == 0):

	elif (sensor_id == 1):
	
	return (arb_humidity_value)
	
#Actuators	
def heater(status):
	if (status):
		#turn on
	else
		#turn off

def lamp(status):
	if (status):
		#turn on
	else
		#turn off	

def water_pump(status):
	if (status):
		#turn on
	else
		#turn off		
	
	
def relay(relay_id, status):
	
	
#loop
while(1):
	if (read_temp_sensor > temp_threshold):
		heater(True)