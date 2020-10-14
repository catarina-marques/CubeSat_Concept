import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
import datetime
import time
import ftplib
from io import BytesIO
PAGE="""\
<html>
<head>
<title>Raspberry Pi - CubeSat Streaming</title>
<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js"></script>
<script>
$(document).ready(function(){
  $("button").click(function(){
    $.post("demo_test_post.asp",
    {
      myposttext: "localdate"
    },
    function(result){
        window.open(
            "https://twitter.com/intent/tweet?hashtags=cubesat&text=I just captured this beautiful picture from the Concept Cubesat at UC!&url=http://catarinamarques.eu/" + result + "&via=cubesat_uc",
            "twitterwindow",
            "height=450, width=550, toolbar=0, location=0, menubar=0, directories=0, scrollbars=0"
        );
    });
  });
});
</script>
</head>
<body>
<center><h1>Raspberry Pi - CubeSat Streaming</h1></center>
<center><img src="stream.mjpg" width="640" height="480"></center>
<center><button>Tweet a captured moment!</button></center>
</body>
</html>
"""


class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

    def do_POST(self):
        #take picture
        date = datetime.datetime.now().strftime("_%d_%m_%Y_%H_%M_%S")
        location = "/home/pi/cubesat_captured_pics/cubesat" + date + ".jpg"
        camera.capture(location, use_video_port=True)
        session = ftplib.FTP('ftp.catarinamarques.eu', 'catarinamarques.eu', '***********')
        file = open(location, 'rb')  # file to send
        imagename = 'cameraimage' + date + '.jpg'
        session.storbinary('STOR ' + imagename , file)  # send the file
        file.close()  # close file and FTP
        #make html page with url of picture
        htmlstring = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>The HTML5 Herald</title>
  <meta name="description" content=" ">
  <meta name="author" content="Catarina">
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@esa" />
<meta name="twitter:creator" content="@cubesat_uc" />
<meta property="og:url" content="https://www.esa.int/Education/CubeSats_-_Fly_Your_Satellite/Fly_Your_Satellite!_programme" />
<meta property="og:title" content="A CubeSat Concept" />
<meta property="og:description" content="CubeSat Latest Capture" />
<meta property="og:image" content="http://catarinamarques.eu/''' + imagename + '''" />
</head>
<body>
    <center><p>CubeSat Concept Capture</p></center>
  <center><img src="http://catarinamarques.eu/''' + imagename + '''"></img></center>
</body>
</html>'''
        bytehtml = htmlstring.encode()
        bio = BytesIO(bytehtml)
        htmlpage = 'twittercard' + date + '.html'
        session.storbinary('STOR ' + htmlpage, bio)
        session.quit()
        #read what was sent. 
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        self.send_response(200)
        self.end_headers()
        #send response with url of new image
        response = BytesIO()
        responsestring = htmlpage
        byteresponse = responsestring.encode()
        response.write(byteresponse)
        #response.write(body)
        self.wfile.write(response.getvalue())


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

with picamera.PiCamera(resolution='640x480', framerate=40) as camera:
    output = StreamingOutput()

    camera.start_recording(output, format='mjpeg')
    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        camera.stop_recording()