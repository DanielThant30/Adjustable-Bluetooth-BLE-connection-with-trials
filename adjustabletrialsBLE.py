import tkinter
from tkinter import *
import random
import pandas as pd

# ---------------- BLE imports ---------------- #
import asyncio
import threading
from bleak import BleakScanner, BleakClient

# ---------------- BLE CONFIG ---------------- #
TARGET_NAME = "Somato"
WRITE_CHAR_UUID = "19b10001-e8f2-537e-4f6c-d104768a1214"

ble_client = None
ble_connected = False
ble_loop = asyncio.new_event_loop()

disconnect_requested = False
ble_status_message = "DISCONNECTED"
ble_monitor_future = None


# ---------------- BLE FUNCTIONS ---------------- #

def handle_ble_future(fut, op_name="BLE operation"):
    global ble_connected, ble_status_message, ble_client, disconnect_requested
    try:
        fut.result()
    except Exception as e:
        ble_connected = False
        if disconnect_requested:
            ble_status_message = "DISCONNECTED"
        else:
            ble_status_message = "POWER CUT"
        print(f"{op_name} failed:", e)


async def ble_monitor():
    global ble_client, ble_connected, ble_status_message, disconnect_requested

    while True:
        await asyncio.sleep(1.0)

        if ble_client is None:
            break

        try:
            if not ble_client.is_connected:
                ble_connected = False
                if disconnect_requested:
                    ble_status_message = "DISCONNECTED"
                else:
                    ble_status_message = "POWER CUT"
                print("BLE monitor detected disconnect")
                break
        except Exception as e:
            ble_connected = False
            if disconnect_requested:
                ble_status_message = "DISCONNECTED"
            else:
                ble_status_message = "POWER CUT"
            print("BLE monitor error / disconnect:", e)
            break


def start_ble_monitor():
    global ble_monitor_future
    if ble_monitor_future is None or ble_monitor_future.done():
        ble_monitor_future = asyncio.run_coroutine_threadsafe(ble_monitor(), ble_loop)


async def ble_connect():
    global ble_client, ble_connected, disconnect_requested, ble_status_message

    ble_connected = False
    disconnect_requested = False
    ble_status_message = "SCANNING..."
    print("Scanning for BLE devices...")

    try:
        devices = await BleakScanner.discover(timeout=5.0)
    except Exception as e:
        ble_status_message = "BLE SCAN FAILED"
        print("BLE scan failed:", e)
        return

    for d in devices:
        if d.name == TARGET_NAME:
            try:
                # Put disconnected callback in constructor
                ble_client = BleakClient(d.address, disconnected_callback=on_disconnect)
                await ble_client.connect()

                # Give ArduinoBLE time to settle
                await asyncio.sleep(0.5)

                if not ble_client.is_connected:
                    ble_status_message = "BLE CONNECTION FAILED"
                    print("BLE connection failed")
                    return

                ble_connected = True
                ble_status_message = "CONNECTED"
                print("BLE connected to", d.address)

                start_ble_monitor()
                return

            except Exception as e:
                ble_status_message = "BLE CONNECT FAILED"
                print("BLE connect failed:", e)
                return

    ble_status_message = "Missing..."
    print("Target device not found")


def on_disconnect(client):
    global ble_connected, ble_status_message, ble_client, disconnect_requested
    ble_connected = False
    ble_client = None

    if disconnect_requested:
        ble_status_message = "DISCONNECTED"
        print("BLE disconnected (requested)")
    else:
        ble_status_message = "POWER CUT"
        print("BLE disconnected unexpectedly")


def start_ble_loop():
    asyncio.set_event_loop(ble_loop)
    ble_loop.run_forever()


threading.Thread(target=start_ble_loop, daemon=True).start()


root = Tk()
root.geometry("750x750")

# ---------------- BYTE DEFINITIONS ---------------- #
byteBaseline = (0).to_bytes(1, "big")   #  0 = 5Hz
byte5Hz      = (1).to_bytes(1, "big")   #  1 = 10Hz
byte10Hz     = (2).to_bytes(1, "big")   #  2 = 20Hz
byte20Hz     = (3).to_bytes(1, "big")   #  3 = OFF

active = 3  # OFF by default


def bt_check():
    btStatus.config(text=ble_status_message)
    root.after(500, bt_check)


def ConnectBLE():
    global disconnect_requested, ble_status_message
    disconnect_requested = False
    ble_status_message = "CONNECTING..."
    fut = asyncio.run_coroutine_threadsafe(ble_connect(), ble_loop)
    fut.add_done_callback(lambda f: handle_ble_future(f, "BLE connect"))


def DisconnectBLE():
    global ble_client, ble_connected, disconnect_requested, ble_status_message, ble_monitor_future

    disconnect_requested = True

    if ble_client is None:
        ble_connected = False
        ble_status_message = "DISCONNECTED"
        print("No BLE client to disconnect.")
        return

    async def do_disconnect():
        global ble_connected, ble_client
        try:
            if ble_client is not None and ble_client.is_connected:
                await ble_client.disconnect()
            ble_connected = False
            ble_client = None
            print("Disconnected (requested).")
        except Exception as e:
            ble_connected = False
            print("BLE disconnect failed:", e)

    if ble_monitor_future is not None and not ble_monitor_future.done():
        ble_monitor_future.cancel()

    ble_status_message = "DISCONNECTING..."
    fut = asyncio.run_coroutine_threadsafe(do_disconnect(), ble_loop)
    fut.add_done_callback(lambda f: handle_ble_future(f, "BLE disconnect"))


def Activate(mode):
    global active
    active = mode

    if not ble_connected or ble_client is None:
        print("BLE not connected")
        return

    data = {
        0: byteBaseline,
        1: byte5Hz,
        2: byte10Hz,
        3: byte20Hz
    }.get(mode, byte20Hz)

    async def write_char():
        await ble_client.write_gatt_char(
            WRITE_CHAR_UUID,
            data,
            response=False
        )

    fut = asyncio.run_coroutine_threadsafe(write_char(), ble_loop)
    fut.add_done_callback(lambda f: handle_ble_future(f, "Manual BLE write"))
    print("Sent mode (manual button):", mode)


# ---------------- TRIAL ---------------- #

OFF_MODE = 3  # 3 = OFF

stimOrder = []
stimText = []
rawText = []
trial_idx = 0
trial_active = False


def strike(s: str) -> str:
    
    return "".join('\u0336\u0336' + ch + '\u0336\u0336' for ch in s)


def mode_to_text(m: int) -> str:
    # 0=5Hz, 1=10Hz, 2=20Hz, 3=OFF
    return {0: "5", 1: "10", 2: "20", 3: "OFF"}.get(m, str(m))


def SendArduinoMode(mode_int: int):
    if not ble_connected or ble_client is None:
        print("BLE not connected (trial send blocked)")
        return

    m = int(mode_int) & 0xFF
    data = (m).to_bytes(1, "big")

    async def write_char():
        await ble_client.write_gatt_char(WRITE_CHAR_UUID, data, response=False)

    fut = asyncio.run_coroutine_threadsafe(write_char(), ble_loop)
    fut.add_done_callback(lambda f: handle_ble_future(f, "Trial BLE write"))
    print("Sent Arduino mode (trial):", m)


def GenerateTrials():
    global stimOrder, stimText, rawText, trial_idx, trial_active

    # --- USER INPUT total trials ---
    try:
        total_trials = int(trialEntry.get())
    except:
        total_trials = 20

    if total_trials <= 0:
        total_trials = 20

    
    if total_trials % 4 != 0:
        total_trials = (total_trials // 4) * 4

    if total_trials == 0:
        total_trials = 20

    N_PER_COND = total_trials // 4

    stimOrder = [0]*N_PER_COND + [1]*N_PER_COND + [2]*N_PER_COND + [3]*N_PER_COND
    random.shuffle(stimOrder)

    rawText = [mode_to_text(m) for m in stimOrder]
    stimText = rawText[:]

    trial_idx = 0
    trial_active = False

    orderLabel.config(text="  ".join(stimText))
    trialNumber2.config(text=str(trial_idx + 1))
    currentTrialLabel.config(text="Ready — Trial 1")

    StimTrialButton.config(state="normal")
    Next2Button.config(state="disabled")
    EndButton.config(state="disabled")

    print(f"Total trials requested: {trialEntry.get()}  -> using: {len(stimOrder)}")
    print("Generated stimOrder:", stimOrder)


def StimulateTrial():
    global trial_active

    if not stimOrder:
        GenerateTrials()

    if trial_idx >= len(stimOrder):
        return

    m = stimOrder[trial_idx]
    SendArduinoMode(m)

    stimText[trial_idx] = strike(rawText[trial_idx])
    orderLabel.config(text=" ".join(stimText))

    currentTrialLabel.config(text=f"Trial {trial_idx + 1} — {mode_to_text(m)}")

    trial_active = True
    StimTrialButton.config(state="disabled")
    Next2Button.config(state="normal")
    EndButton.config(state="normal")


def NextTrial():
    global trial_idx, trial_active

    if not trial_active:
        return

    trial_idx += 1

    if trial_idx >= len(stimOrder):
        Ending()
        return

    m = stimOrder[trial_idx]
    SendArduinoMode(m)

    stimText[trial_idx] = strike(rawText[trial_idx])
    orderLabel.config(text=" ".join(stimText))

    trialNumber2.config(text=str(trial_idx + 1))
    currentTrialLabel.config(text=f"Trial {trial_idx + 1} — {mode_to_text(m)}")


def Ending():
    global trial_active, trial_idx

    SendArduinoMode(OFF_MODE)
    trial_active = False

    Next2Button.config(state="disabled")
    EndButton.config(state="disabled")

    if stimOrder and trial_idx >= len(stimOrder) - 1:
        currentTrialLabel.config(text="Finished")
        StimTrialButton.config(state="disabled")
        trialNumber2.config(text="Finished")
    else:
        currentTrialLabel.config(text=f"Ready — Trial {trial_idx + 1}")
        StimTrialButton.config(state="normal")


# ---------------- UI ---------------- #

Label(root, text="BLE Status:", font=("Helvetica", 10)).place(x=300, y=10)
btStatus = Label(root, text="DISCONNECTED", font=("Helvetica", 16))
btStatus.place(x=300, y=30)

Button(root, text="Connect BLE", command=ConnectBLE).place(x=100, y=20)
Button(root, text="Disconnect BLE", command=DisconnectBLE).place(x=520, y=20)

Button(root, text="5 Hz",  command=lambda: Activate(0), width=15).place(x=100, y=100)
Button(root, text="10 Hz", command=lambda: Activate(1), width=15).place(x=300, y=100)
Button(root, text="20 Hz", command=lambda: Activate(2), width=15).place(x=500, y=100)
Button(root, text="OFF",   command=lambda: Activate(3), width=15).place(x=300, y=160)

Label(root, text="Trial Control:", font=("Helvetica", 16)).place(x=300, y=260)

Label(root, text="Trial:", font=("Helvetica", 10)).place(x=600, y=285)
trialNumber2 = Label(root, text="—", font=("Helvetica", 13))
trialNumber2.place(x=600, y=305)

currentTrialLabel = Label(root, text="Waiting…", font=("Helvetica", 14))
currentTrialLabel.place(x=260, y=310)

StimTrialButton = Button(root, text="Stimulate trial", command=StimulateTrial, height=2, width=18)
StimTrialButton.place(x=100, y=350)

Next2Button = Button(root, text="Next", command=NextTrial, height=2, width=18, state="disabled")
Next2Button.place(x=300, y=350)

EndButton = Button(root, text="Ending", command=Ending, height=2, width=18, state="disabled")
EndButton.place(x=500, y=350)


Label(root, text="Total Trials:", font=("Helvetica", 10)).place(x=20, y=430)
trialEntry = Entry(root, width=6)
trialEntry.place(x=110, y=430)
trialEntry.insert(0, "20")


Button(root, text="Generate", command=GenerateTrials).place(x=170, y=426)
Label(root, text="Note: Trials are multiples of 4", font=("Helvetica", 10, "bold")).place(x=240, y=430)
Label(root, text="Trial order:", font=("Helvetica", 10)).place(x=20, y=470)
orderLabel = Label(root, text="(no order yet)", font=("Helvetica", 12), wraplength=710, justify="left")
orderLabel.place(x=20, y=500)


GenerateTrials()

# status polling
root.after(500, bt_check)

root.mainloop()