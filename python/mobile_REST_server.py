import os
from flask import Flask, jsonify,send_from_directory, request,redirect,url_for
from werkzeug.utils import secure_filename
from PIL import Image
import pdb
UPLOAD_FOLDER = 'pics/' #directory which contains all the saved files from clients
ALLOWED_EXTENSIONS = set([ 'png', 'jpg', 'jpeg',]) #self exploratory

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



garden_settings = {}

@app.route('/')
def index():
	return "Hello. Server is up :)"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS	

#example of curl command to upload a local image:
#curl -v -F "file=@image.jpg" http://localhost:5000/garden/upload
@app.route('/garden/upload', methods=['GET', 'POST'])
def upload_file():
	if request.method == 'POST':
		# check if the post request has the file part
		if 'file' not in request.files:
			return 'not found'
		file = request.files['file']
		# if user does not select file, browser also
		# submit a empty part without filename
		if file.filename == '':
			return 'not found1'
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			return 'file uploaded successfully'


@app.route('/garden/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

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
