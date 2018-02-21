#credit: https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
from flask import Flask, jsonify

app = Flask(__name__)

garden_settings = {}

@app.route('/')
def index():
	return "Hello. Server is up :)"

@app.route('/garden/<string:enviornmental_variable>/<string:parameter>', methods=['GET'])
def get_setting(enviornmental_variable, parameter):
	if enviornmental_variable in garden_settings:
		if parameter in garden_settings[enviornmental_variable]:
			return(str(garden_settings[enviornmental_variable][parameter]))
	return 'error'

@app.route('/garden/<string:enviornmental_variable>/<string:mode>/<int:val>', methods=['GET'])
def set_setting(enviornmental_variable, mode, val):
	if mode in ['auto', 'manual'] and enviornmental_variable in garden_settings:	#at least try some input protection
		garden_settings[enviornmental_variable]['control_method'] = mode;
		garden_settings[enviornmental_variable]['setpoint/power'] = val;
	else:
		print("error: failed mode check or variable check")
	return jsonify({'garden_settings': garden_settings})

@app.route('/garden', methods=['GET'])
def get_json():
	return jsonify({'garden_settings': garden_settings})
	
@app.route('/garden/test', methods=['GET'])
def test_number():
	return "12345"
	
@app.route('/garden/reset_settings')
def reset_settings():
	global garden_settings 
	garden_settings = {
		#enviornmental_variables
			#parameters
			
		'temp':{
			'control_method':'manual',	#manual vs auto
			'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
			'sensor_1':10,
			'sensor_2':20
		},
		
		'water':{
			'control_method':'manual',	#manual vs auto
			'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
			'sensor_1':10,
			'sensor_2':20
		},
		
		'light_1':{
			'control_method':'manual',	#manual vs auto
			'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
			'sensor_1':10
		},
		
		'light_2':{
			'control_method':'manual',	#manual vs auto
			'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
			'sensor_1':10
		},
		
		'bug_level':0
	}
	return "Settings reset."
	
if __name__ == '__main__':
	#go
	reset_settings()
	app.run(debug=True, host='0.0.0.0')
	