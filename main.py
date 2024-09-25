import time
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
import tkinter as tk
from tkinter import messagebox
import serial.tools.list_ports

client = None  # Start uden en forbundet client

# Finder tilgængelige COM-porte
def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

# Opret forbindelse til ATV320
def connect_to_drive():
    global client
    selected_port = com_port_var.get()
    if selected_port and selected_port != "No Ports Available":
        client = ModbusSerialClient(port=selected_port)
        client.connect()
        if client.connected:
            print(f"Connected to drive on {selected_port}")
            status_label.config(text=f"Connected to {selected_port}", fg="green")
        else:
            messagebox.showerror("Connection Error", f"Failed to connect to {selected_port}")
    else:
        messagebox.showerror("Port Error", "No COM port selected")

# Modbus-adresser og kommandoer
CONTROL_WORD_ADDRESS = 8501
SPEED_REFERENCE_ADDRESS = 8602
SPEED_FEEDBACK_ADDRESS = 8604  # Feedback for faktisk hastighed
READY_COMMAND = 0x0001
FORWARD_COMMAND = 0x0003
REVERSE_COMMAND = 0x0005
STOP_COMMAND = 0x0000
RESET_COMMAND = 0x0008  # Reset fejlkode

SPEED_UPDATE_INTERVAL = 1000  # 1000 ms = 1 sekund
KEEP_ALIVE_INTERVAL = 3000  # 3000 ms = 3 sekunder

# GUI-funktioner til styring af frekvensomformeren
def start_forward():
    if client and client.connected:
        try:
            speed_value = int(speed_input.get())
            client.write_register(SPEED_REFERENCE_ADDRESS, speed_value)
            client.write_register(CONTROL_WORD_ADDRESS, READY_COMMAND)
            client.write_register(CONTROL_WORD_ADDRESS, FORWARD_COMMAND)
            status_label.config(text="Running forward", fg="green")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid speed value.")
    else:
        messagebox.showerror("Connection Error", "No drive connected.")

def start_reverse():
    if client and client.connected:
        try:
            speed_value = int(speed_input.get())
            client.write_register(SPEED_REFERENCE_ADDRESS, speed_value)
            client.write_register(CONTROL_WORD_ADDRESS, READY_COMMAND)
            client.write_register(CONTROL_WORD_ADDRESS, REVERSE_COMMAND)
            status_label.config(text="Running reverse", fg="orange")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid speed value.")
    else:
        messagebox.showerror("Connection Error", "No drive connected.")

def stop_drive():
    if client and client.connected:
        client.write_register(CONTROL_WORD_ADDRESS, STOP_COMMAND)
        status_label.config(text="Drive stopped", fg="red")
    else:
        status_label.config(text="No drive connected", fg="red")

def reset_fault():
    if client and client.connected:
        client.write_register(CONTROL_WORD_ADDRESS, STOP_COMMAND)
        client.write_register(CONTROL_WORD_ADDRESS, RESET_COMMAND)
        status_label.config(text="Fault reset", fg="blue")
        print("Fault reset sent")
    else:
        messagebox.showerror("Connection Error", "No drive connected.")

def update_speed_feedback():
    if client and client.connected:
        try:
            result = client.read_holding_registers(SPEED_FEEDBACK_ADDRESS, 1)
            if result.isError():
                raise ModbusIOException("Modbus error during speed feedback read")

            speed_feedback = result.registers[0]

            if speed_feedback > 32767:
                speed_feedback = speed_feedback - 65536

            speed_feedback_label.config(text=f"Speed: {speed_feedback} RPM")
            print(f"Speed: {speed_feedback} RPM")

        except Exception as e:
            print(f"Error reading speed feedback: {e}")

    root.after(SPEED_UPDATE_INTERVAL, update_speed_feedback)

# Funktion for keep-alive
def keep_alive():
    if client and client.connected:
        try:
            # Læs en registreringsværdi for at holde forbindelsen aktiv
            client.read_holding_registers(CONTROL_WORD_ADDRESS, 1)
            print("Keep-alive signal sent")
        except Exception as e:
            print(f"Error during keep-alive: {e}")
    # Planlæg næste keep-alive kald
    root.after(KEEP_ALIVE_INTERVAL, keep_alive)

def on_closing():
    if client and client.connected:
        stop_drive()
        client.close()
    root.destroy()

# Funktion til at indsætte tal i hastighedsindgangen
def insert_number(number):
    current_value = speed_input.get()
    speed_input.delete(0, tk.END)
    speed_input.insert(0, current_value + str(number))

# Funktion til at rydde hastighedsindgangen
def clear_entry():
    speed_input.delete(0, tk.END)

# Opret GUI-vinduet
root = tk.Tk()
root.title("ATV320 Controller")

# Valg af COM-port
com_port_var = tk.StringVar()

available_ports = list_serial_ports()
if available_ports:
    com_port_var.set(available_ports[0])
else:
    com_port_var.set("No Ports Available")

com_port_menu = tk.OptionMenu(root, com_port_var, available_ports)
com_port_menu.grid(row=0, column=0, padx=10, pady=10)

connect_button = tk.Button(root, text="Connect", font=("Arial", 12), command=connect_to_drive)
connect_button.grid(row=0, column=1, padx=10, pady=10)

# Hastighedsinput
tk.Label(root, text="Set Speed:", font=("Arial", 12)).grid(row=1, column=0, padx=10, pady=10)
speed_input = tk.Entry(root, font=("Arial", 12), width=6)
speed_input.grid(row=1, column=1, padx=10, pady=10)

# Numeriske knapper
button_values = [
    ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
    ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
    ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
    ('0', 3, 1)
]

for (text, row, col) in button_values:
    tk.Button(root, text=text, font=("Arial", 12), width=6, height=2, command=lambda t=text: insert_number(t)).grid(row=row + 1, column=col + 2, padx=10, pady=10)

tk.Button(root, text='Clear', font=("Arial", 12), width=6, height=2, command=clear_entry).grid(row=4, column=2, padx=0, pady=0)
tk.Button(root, text='Enter', font=("Arial", 12), width=6, height=2, command=lambda: speed_input.focus()).grid(row=4, column=4, padx=0, pady=0)

# Forward-knap
forward_button = tk.Button(root, text="Forward", font=("Arial", 12), width=10, height=2, command=start_forward)
forward_button.grid(row=2, column=0, padx=10, pady=10)

# Reverse-knap
reverse_button = tk.Button(root, text="Reverse", font=("Arial", 12), width=10, height=2, command=start_reverse)
reverse_button.grid(row=2, column=1, padx=10, pady=10)

# Stop-knap
stop_button = tk.Button(root, text="Stop", font=("Arial", 12), width=10, height=2, command=stop_drive)
stop_button.grid(row=3, column=0, padx=10, pady=10)

# Reset-knap til at nulstille fejl
reset_button = tk.Button(root, text="Reset", font=("Arial", 12), width=10, height=2, command=reset_fault)
reset_button.grid(row=3, column=1, padx=10, pady=10)

# Statuslabel
status_label = tk.Label(root, text="Not Connected", font=("Arial", 12), fg="red")
status_label.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

# Hastighedsfeedbacklabel
speed_feedback_label = tk.Label(root, text="Speed: 0 RPM", font=("Arial", 12), fg="blue")
speed_feedback_label.grid(row=0, column=2, columnspan=3, padx=10, pady=10)

# Sørg for at lukke forbindelsen, når vinduet lukkes
root.protocol("WM_DELETE_WINDOW", on_closing)

# Start keep-alive og hastighedsfeedback opdatering
root.after(SPEED_UPDATE_INTERVAL, update_speed_feedback)
root.after(KEEP_ALIVE_INTERVAL, keep_alive)

# Start GUI-event loop
root.mainloop()