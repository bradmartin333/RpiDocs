#!/usr/bin/python3

# Adapted from https://github.com/e-tinkers/simple_httpserver/blob/master/simple_webserver.py

import RPi.GPIO as GPIO
import os
import threading
import Adafruit_DHT
from time import sleep
from http.server import BaseHTTPRequestHandler, HTTPServer

running = True
temp_humidity_str = "Loading DHT11..."
host_name = "0.0.0.0"  # Change this to your Raspberry Pi IP address
host_port = 8080  # Cam feed running on port 8000


class pGPIO:
    def __init__(self, pin, state, alias):
        self.pin = pin
        self.state = state
        self.alias = alias


GPIO_list = [
    pGPIO(2, 0, ""),
    pGPIO(3, 0, ""),
    pGPIO(4, 0, ""),
    pGPIO(5, 0, ""),
    pGPIO(6, 0, ""),
    pGPIO(9, 0, ""),
    pGPIO(10, 0, ""),
    pGPIO(11, 0, ""),
    pGPIO(12, 0, ""),
    pGPIO(13, 0, ""),
    pGPIO(16, 0, ""),
    pGPIO(18, 0, ""),
    pGPIO(19, 0, ""),
    pGPIO(20, 0, "scope LED"),
    pGPIO(21, 0, ""),
    pGPIO(22, 0, ""),
    pGPIO(23, 0, ""),
    pGPIO(24, 0, ""),
    pGPIO(25, 0, ""),
    pGPIO(26, 0, ""),
    pGPIO(27, 1, "DHT11"),
]

def find_gpio_by_pin(pin_number):
  for gpio in GPIO_list:
    if gpio.pin == pin_number:
      return gpio
  return None  # Return None if not found

class MyServer(BaseHTTPRequestHandler):
    global temp_humidity_str

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _redirect(self, path):
        self.send_response(303)
        self.send_header("Content-type", "text/html")
        self.send_header("Location", path)
        self.end_headers()

    def do_GET(self):
        # Update GPIO output
        if "shutdown" in self.path:
            os.popen("sudo shutdown -h now")
        elif "=" in self.path:
            post_data = self.path[1:].split("=")
            gpio_pin = int(post_data[0])
            GPIO.output(
                find_gpio_by_pin(gpio_pin).pin,
                GPIO.HIGH if post_data[1] == "On" else GPIO.LOW,
            )

        # Get GPIO states
        for i in range(len(GPIO_list)):
            GPIO_list[i].state = GPIO.input(GPIO_list[i].pin)

        html = """
            <html>
            <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
            .dot[state*="1"] {{
              background-color: #32a852;
            }}
            .dot[state*="0"] {{
              background-color: #c7c7c7;
            }}
            .dot {{
              height: 10px;
              width: 10px;
              border-radius: 50%;
              display: inline-block;
            }}
            </style>
            </head>
            <body style="width:960px; margin: 20px auto;">
            <p>CPU Temp = {} &emsp; GPU Temp = {}</p>
            <p>{}</p>
            """
        for i in range(len(GPIO_list)):
            html += """
            <form action="/" method="POST">
                GPIO {0}
                <span class="dot" state="{1}"></span>
                <input type="submit" name="{0}" value="On">
                <input type="submit" name="{0}" value="Off">
                {2}
            </form>""".format(
                str(GPIO_list[i].pin), GPIO_list[i].state, GPIO_list[i].alias
            )

        html += """
            </body>
            </html>"""

        cpu_temp = os.popen("cat /sys/class/thermal/thermal_zone0/temp").read()
        gpu_temp = os.popen("vcgencmd measure_temp").read()
        self.do_HEAD()

        self.wfile.write(
            html.format(
                str(round(int(cpu_temp) / 1000, 1)) + " C", gpu_temp[5:-3] + " C",
                temp_humidity_str
            ).encode("utf-8")
        )

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])  # Get the size of data
        post_data = self.rfile.read(content_length).decode("utf-8")  # Get the data
        self._redirect("/" + post_data)


def poll_dht11():
    global running
    global temp_humidity_str

    sensor = Adafruit_DHT.DHT11
    while running:
        try:
            humidity, temperature = Adafruit_DHT.read_retry(sensor, 17)
            if humidity is not None and temperature is not None:
                temp_humidity_str = 'Room Temp = {0:0.1f} C &emsp; Humidity = {1:0.1f} %'.format(temperature, humidity)
            else:
                temp_humidity_str = "DHT11 error"
        except RuntimeError as error:
            temp_humidity_str = "DHT11 error (1)"
            sleep(2.0)
            continue
        except Exception as error:
            temp_humidity_str = "DHT11 error (2)"
            raise error
        sleep(2.0)


if __name__ == "__main__":
    # GPIO setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for i in range(len(GPIO_list)):
        GPIO.setup(GPIO_list[i].pin, GPIO.OUT)
    for gpio in GPIO_list:
        if (gpio.state == 1):
            GPIO.output(gpio.pin, GPIO.HIGH)

    http_server = HTTPServer((host_name, host_port), MyServer)
    print("Server Starts - %s:%s" % (host_name, host_port))
    dht11_thread = threading.Thread(target=poll_dht11)
    dht11_thread.start()

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()

    print("Server Stop")
    running = False
    dht11_thread.join()
