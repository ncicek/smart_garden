from subprocess import call

#calls fswebcam, takes a pic, and returns the path to that pic
def take_photo():
	photo_filename = a.bmp
	call(["fswebcam","--no-banner","-r 1280x720",photo_filename])
	return photo_filename