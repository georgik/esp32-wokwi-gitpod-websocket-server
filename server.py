#!/usr/bin/env python3

import asyncio
import base64
import json
import sys
import os
import subprocess
import websockets
import webbrowser
import time
from gdbserver import GDBServer


PORT = 9012
GDB_PORT = 9333

def base64_file(path: str):
    with open(path, 'rb') as file:
        return base64.b64encode(file.read()).decode('ascii')

gdb_server = GDBServer()

async def handle_client(websocket, path):
    msg = await websocket.recv()
    print("Client connected! {}".format(msg))
    arch="xtensa-esp32-espidf"
    if (os.getenv('ESP_BOARD') == "esp32c3"):
        arch="riscv32imc-esp-espidf"
    # Send the simulation payload
    await websocket.send(json.dumps({
        "type": "start",
        "elf": base64_file('target/{}/debug/{}'.format(arch, os.getenv('CURRENT_PROJECT'))),
        "espBin": [
            [os.getenv('ESP_BOOTLOADER_OFFSET', 0x0000), base64_file('bootloader.bin')],
            [os.getenv('ESP_PARTITION_TABLE_OFFSET', 0x8000), base64_file('partition-table.bin')],
            [os.getenv('ESP_APP_OFFSET', 0x10000), base64_file('app.bin')],
        ]
    }))

    gdb_server.on_gdb_message = lambda msg: websocket.send(
        json.dumps({"type": "gdb", "message": msg}))
    gdb_server.on_gdb_break = lambda: websocket.send(
        json.dumps({"type": "gdbBreak"}))

    while True:
        msg = await websocket.recv()
        msgjson = json.loads(msg)
        if msgjson["type"] == "uartData":
            sys.stdout.buffer.write(bytearray(msgjson["bytes"]))
            sys.stdout.flush()
        elif msgjson["type"] == "gdbResponse":
            await gdb_server.send_response(msgjson["response"])
        else:
            print("> {}".format(msg))

start_server = websockets.serve(handle_client, "127.0.0.1", PORT)
asyncio.get_event_loop().run_until_complete(start_server)

board = os.getenv('WOKWI_PROJECT_ID')

if(os.getenv('USER') == "gitpod"):
    gp_url = subprocess.getoutput("gp url {}".format(PORT))
    gp_url = gp_url[8:]
    url = "https://wokwi.com/_alpha/wembed/{}?partner=espressif&port={}&data=demo&_host={}".format(board,PORT,gp_url)
else:
    url = "https://wokwi.com/_alpha/wembed/{}?partner=espressif&port={}&data=demo".format(board,PORT)
print("Please, open the following URL: {}".format(url))
if(os.getenv('USER') == "gitpod"):
    time.sleep(2)
    open_preview = subprocess.getoutput("gp preview \"{}\"".format(url))
else:
    webbrowser.open(url)

asyncio.get_event_loop().run_until_complete(gdb_server.start(GDB_PORT))
asyncio.get_event_loop().run_forever()