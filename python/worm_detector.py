#Garden server
#runs bug detection server and mobile app server

import numpy as np
import os
import six.moves.urllib as urllib
import sys
import tarfile
import tensorflow as tf
import zipfile
import pdb
from collections import defaultdict
from io import StringIO
from PIL import Image
from object_detection.utils import ops as utils_ops
import os
from flask import Flask, jsonify,send_from_directory, request,redirect,url_for
from werkzeug.utils import secure_filename
import time


if tf.__version__ < '1.4.0':
  raise ImportError('Please upgrade your tensorflow installation to v1.4.* or later!')

sys.path.append("..")


from utils import label_map_util

from utils import visualization_utils as vis_util



def run_inference_for_single_image(image, graph):
  with graph.as_default():
    with tf.Session() as sess:
      # Get handles to input and output tensors
      ops = tf.get_default_graph().get_operations()
      all_tensor_names = {output.name for op in ops for output in op.outputs}
      tensor_dict = {}
      for key in [
          'num_detections', 'detection_boxes', 'detection_scores',
          'detection_classes', 'detection_masks'
      ]:
        tensor_name = key + ':0'
        if tensor_name in all_tensor_names:
          tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(
              tensor_name)
      if 'detection_masks' in tensor_dict:
        # The following processing is only for single image
        detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
        detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
        # Reframe is required to translate mask from box coordinates to image coordinates and fit the image size.
        real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
        detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
        detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
        detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
            detection_masks, detection_boxes, image.shape[0], image.shape[1])
        detection_masks_reframed = tf.cast(
            tf.greater(detection_masks_reframed, 0.5), tf.uint8)
        # Follow the convention by adding back the batch dimension
        tensor_dict['detection_masks'] = tf.expand_dims(
            detection_masks_reframed, 0)
      image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

      # Run inference
      output_dict = sess.run(tensor_dict,
                             feed_dict={image_tensor: np.expand_dims(image, 0)})

      # all outputs are float32 numpy arrays, so convert types as appropriate
      output_dict['num_detections'] = int(output_dict['num_detections'][0])
      output_dict['detection_classes'] = output_dict[
          'detection_classes'][0].astype(np.uint8)
      output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
      output_dict['detection_scores'] = output_dict['detection_scores'][0]
      if 'detection_masks' in output_dict:
        output_dict['detection_masks'] = output_dict['detection_masks'][0]
  return output_dict


# In[20]:

def findWorm(image_path):
	image = Image.open(image_path)
	# the array based representation of the image will be used later in order to prepare the
	# result image with boxes and labels on it.
	image_np = load_image_into_numpy_array(image)
	# Expand dimensions since the model expects images to have shape: [1, None, None, 3]
	image_np_expanded = np.expand_dims(image_np, axis=0)
	# Actual detection.
	output_dict = run_inference_for_single_image(image_np, detection_graph)
	# Visualization of the results of a detection.
	detection_scores = output_dict['detection_scores'];
	return detection_scores
  
 
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
		if file.filename == '':
			return 'not found1'
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			print(filename)
			path_to_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
			file.save(path_to_file)
			print("save complete")
			detection_scores = findWorm(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			return str(detection_scores)


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
		return 'error'
	return jsonify({'garden_settings': garden_settings})

@app.route('/garden_RESTful_write/<string:enviornmental_variable>/<string:param>/<string:val>', methods=['GET'])
def set_setting_RESTful(enviornmental_variable, param, val):
	if enviornmental_variable in garden_settings:
		if param in garden_settings[enviornmental_variable]:
			garden_settings[enviornmental_variable][param] = float(val);
	else:
		print("error: failed restful dict check")
		return 'error'
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
	return "Settings reset."
	
def load_image_into_numpy_array(image):
  (im_width, im_height) = image.size
  return np.array(image.getdata()).reshape(
      (im_height, im_width, 3)).astype(np.uint8)
	  

@app.route('/garden/time', methods=['GET'])
def get_time():
	return str(int(time.time()))


if __name__ == '__main__':
	MODEL_NAME = 'worm_graph'
	MODEL_FILE = MODEL_NAME + '.tar.gz'
	PATH_TO_CKPT = MODEL_NAME + '/frozen_inference_graph.pb'
	PATH_TO_LABELS = os.path.join('training', 'object-detection.pbtxt')
	NUM_CLASSES = 1
	detection_graph = tf.Graph()
	with detection_graph.as_default():
		od_graph_def = tf.GraphDef()
		with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
			serialized_graph = fid.read()
			od_graph_def.ParseFromString(serialized_graph)
			tf.import_graph_def(od_graph_def, name='')
	label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
	categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
	category_index = label_map_util.create_category_index(categories)
# Size, in inches, of the output images.
	IMAGE_SIZE = (12, 8)
	reset_settings()
	app.run(debug=True, host='0.0.0.0',threaded=True)

