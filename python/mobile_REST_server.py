from flask import Flask, jsonify

app = Flask(__name__)

garden_settings = {
	'temp':{
		'control_method':'manual',	#manual vs auto
		'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
		'current_sensor_reading':{'sensor1':10, 'sensor2': 20}
	},
	
	'water':{
		'control_method':'manual',	#manual vs auto
		'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
		'current_sensor_reading':{'sensor1':10, 'sensor2': 20}
	},
	
	'light_1':{
		'control_method':'manual',	#manual vs auto
		'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
		'current_sensor_reading':10
	},
	
	'light_2':{
		'control_method':'manual',	#manual vs auto
		'setpoint/power':0,	#interpreted as setpoint if auto mode, or power if manual mode
		'current_sensor_reading':10
	},
	
	'bug_level':0
}

@app.route('/')
def index():
	return "Hello. Server is up :)"

@app.route('/garden', methods=['GET'])
def get_settings():
	return jsonify({'garden_settings': garden_settings})
	
@app.route('/garden/<string:enviornmental_variable>/<string:mode>/<int:val>', methods=['GET'])
def set_setting(enviornmental_variable, mode, val):
	if mode in ['auto', 'manual'] and enviornmental_variable in garden_settings:	#at least try some input protection
		garden_settings[enviornmental_variable]['control_method'] = mode;
		garden_settings[enviornmental_variable]['setpoint'] = val;
	else:
		print("error: failed mode check or variable check")
	return jsonify({'garden_settings': garden_settings})

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0')
	