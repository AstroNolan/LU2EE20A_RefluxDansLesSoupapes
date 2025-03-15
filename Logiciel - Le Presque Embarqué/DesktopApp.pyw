import subprocess
import sys

required_modules = [
    "customtkinter", 
    "matplotlib", 
    "scipy", 
    "numpy", 
    "pyserial"
]

def install_modules():
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])

install_modules()


import customtkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import serial.tools.list_ports
import numpy as np
from scipy.interpolate import make_interp_spline
import math
import time
import datetime
import threading
import queue
import ast
import os


acquisition = False
resolution = 4
timestamps = np.array([])
tab_resolutions_ctn1 = [np.array([]) for _ in range(8)]
tab_temperature_ctn1 = [np.array([]) for _ in range(8)]
tab_resolutions_ctn2 = [np.array([]) for _ in range(8)]
tab_temperature_ctn2 = [np.array([]) for _ in range(8)]
data_queue = queue.Queue()
customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Reflux dans les Soupapes de l'Extrême")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 1100
        window_height = 580
        position_top = int(screen_height / 2 - window_height / 2)
        position_left = int(screen_width / 2 - window_width / 2)
        self.geometry(f"{window_width}x{window_height}+{position_left}+{position_top}")

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Analyse GUI", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.sidebar_button_1 = customtkinter.CTkButton(self.sidebar_frame, command=self.acquisition_event, text="Start Acquisition", fg_color="red", hover_color="darkred")
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)

        self.slider_label = customtkinter.CTkLabel(self.sidebar_frame, text=f"Résolution : {resolution} bit", anchor="w")
        self.slider_label.grid(row=2, column=0, padx=20, pady=(10, 0))
        self.slider = customtkinter.CTkSlider(self.sidebar_frame, from_=1, to=8, number_of_steps=7, command=self.slider_event, width=140)
        self.slider.set(resolution)
        self.slider.grid(row=3, column=0, padx=20, pady=(5, 10))

        self.sidebar_button_2 = customtkinter.CTkButton(self.sidebar_frame, command=self.export_event, text="Exporter")
        self.sidebar_button_2.grid(row=4, column=0, padx=20, pady=10)
        self.sidebar_button_3 = customtkinter.CTkButton(self.sidebar_frame, command=self.reset_event, text="Réinitialiser")
        self.sidebar_button_3.grid(row=5, column=0, padx=20, pady=10)

        self.direction_label = customtkinter.CTkLabel(self.sidebar_frame, text="Sens du flux d'air :\nAucun", anchor="w")
        self.direction_label.grid(row=6, column=0, padx=20, pady=(10, 0))

        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Apparence :", anchor="w")
        self.appearance_mode_label.grid(row=8, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Clair", "Sombre"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=9, column=0, padx=20, pady=(10, 10))

        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="Mise à l'échelle :", anchor="w")
        self.scaling_label.grid(row=10, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"], command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=11, column=0, padx=20, pady=(10, 20))

        self.tabview = customtkinter.CTkTabview(self)
        self.tabview.grid(row=1, column=1, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.tabview.add("Tensions")
        self.tabview.add("Températures")
        self.create_graph_voltage()
        self.create_graph_temperature()
        self.update_graph_color()

        self.appearance_mode_optionemenu.set("Sombre")
        self.scaling_optionemenu.set("100%")
        self.update_ui()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode("Dark" if new_appearance_mode == "Sombre" else "Light")
        self.update_graph_color()

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def acquisition_event(self):
        global acquisition
        acquisition = not acquisition
        if acquisition:
            self.sidebar_button_1.configure(text="Stop Acquisition", fg_color="green", hover_color="darkgreen")
        else:
            self.sidebar_button_1.configure(text="Start Acquisition", fg_color="red", hover_color="darkred")
    
    def slider_event(self, value):
        global resolution
        self.slider_label.configure(text=f"Résolution : {int(value)} bit")
        resolution = int(value)
    
    def export_event(self):
        global resolution
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        filename = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S.csv")
        filepath = os.path.join(data_dir, filename)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write("Horodatage (s);CTN1 (V);CTN2 (V)")
            file.writelines(f"\n{ts:.1f};{ctn1:.2f};{ctn2:.2f}" for ts, ctn1, ctn2 in zip(timestamps, tab_resolutions_ctn1[resolution-1], tab_resolutions_ctn2[resolution-1]))

    def reset_event(self):
        global timestamps, tab_resolutions_ctn1, tab_resolutions_ctn2, tab_temperature_ctn1, tab_temperature_ctn2
        timestamps = np.array([])
        tab_resolutions_ctn1 = [np.array([]) for _ in range(8)]
        tab_resolutions_ctn2 = [np.array([]) for _ in range(8)]
        tab_temperature_ctn1 = [np.array([]) for _ in range(8)]
        tab_temperature_ctn2 = [np.array([]) for _ in range(8)]
        self.volt_line_ctn1.set_xdata([])
        self.volt_line_ctn1.set_ydata([])
        self.volt_line_ctn2.set_xdata([])
        self.volt_line_ctn2.set_ydata([])
        self.volt_ax.legend(["CTN1", "CTN2"], loc="upper right")
        self.volt_ax.relim()
        self.volt_ax.autoscale_view(tight=True)
        self.voltage_canvas.draw_idle()
        self.temp_line_ctn1.set_xdata([])
        self.temp_line_ctn1.set_ydata([])
        self.temp_line_ctn2.set_xdata([])
        self.temp_line_ctn2.set_ydata([])
        self.volt_ax.legend(["CTN1", "CTN2"], loc="upper right")
        self.temp_ax.legend(["CTN1", "CTN2"], loc="upper right")
        self.direction_label.configure(text="Sens du flux d'air :\nAucun" )
        self.temp_ax.relim()
        self.temp_ax.autoscale_view(tight=True)
        self.temperature_canvas.draw_idle()
    
    def calcul_temperature(self, V, Rf=5000, Vin=5, R0=5000, beta=3700, T0=298.15):
        if V <= 0 or V >= Vin:
            return 0
        Rctn = Rf * (V / (Vin - V))
        T = beta / ((beta / T0) - math.log(Rctn / R0)) - 273.15
        return T

    def update_ui(self):
        global timestamps, tab_resolutions_ctn1, tab_resolutions_ctn2, tab_temperature_ctn1, tab_temperature_ctn2
        while not data_queue.empty():
            container, index, value = data_queue.get()
            if container == "tc":
                timestamps = np.append(timestamps, value)
            elif container == "ctn1":
                tab_resolutions_ctn1[index] = np.append(tab_resolutions_ctn1[index], value)
                tab_temperature_ctn1[index] = np.append(tab_temperature_ctn1[index], self.calcul_temperature(value))
            elif container == "ctn2":
                tab_resolutions_ctn2[index] = np.append(tab_resolutions_ctn2[index], value)
                tab_temperature_ctn2[index] = np.append(tab_temperature_ctn2[index], self.calcul_temperature(value))
        self.update_graph_voltage()
        self.update_graph_temperature()
        self.after(100, self.update_ui)
    
    def create_graph_voltage(self):
        self.volt_fig, self.volt_ax = plt.subplots()
        self.volt_fig.patch.set_alpha(0)
        self.volt_ax.set_facecolor((0, 0, 0, 0))
        self.volt_ax.set_xlabel("Temps (s)")
        self.volt_ax.set_ylabel("Tension (V)")
        self.volt_ax.set_ylim(0, 5)
        self.volt_line_ctn1, = self.volt_ax.plot([], [], label="CTN1")
        self.volt_line_ctn2, = self.volt_ax.plot([], [], label="CTN2")
        self.volt_ax.legend(loc="upper right")
        self.voltage_canvas = FigureCanvasTkAgg(self.volt_fig, self.tabview.tab("Tensions"))
        self.voltage_canvas.draw()
        self.voltage_canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def update_graph_voltage(self):
        global resolution, timestamps, tab_resolutions_ctn1, tab_resolutions_ctn2
        nb_points = 10
        if len(timestamps) > 3:
            x_data = timestamps[-nb_points:]
            y_data_ctn1 = tab_resolutions_ctn1[resolution - 1][-nb_points:]
            y_data_ctn2 = tab_resolutions_ctn2[resolution - 1][-nb_points:]
            spline_ctn1 = make_interp_spline(x_data, y_data_ctn1)
            spline_ctn2 = make_interp_spline(x_data, y_data_ctn2)
            x_smooth = np.linspace(x_data.min(), x_data.max(), 500)
            y_smooth_ctn1 = spline_ctn1(x_smooth)
            y_smooth_ctn2 = spline_ctn2(x_smooth)
            self.volt_line_ctn1.set_xdata(x_smooth)
            self.volt_line_ctn1.set_ydata(y_smooth_ctn1)
            self.volt_line_ctn2.set_xdata(x_smooth)
            self.volt_line_ctn2.set_ydata(y_smooth_ctn2)
            self.volt_ax.legend([f"CTN1 : {y_data_ctn1[-1]:.2f}V", f"CTN2 : {y_data_ctn2[-1]:.2f}V"], loc="upper right")
            self.voltage_comp()
            self.volt_ax.relim()
            self.volt_ax.autoscale_view(tight=True)
            self.voltage_canvas.draw_idle()
        
    def update_graph_voltage_raw(self):
        global resolution, timestamps, tab_resolutions_ctn1, tab_resolutions_ctn2
        nb_points = 10
        if len(timestamps) > 1:
            self.volt_line_ctn1.set_xdata(timestamps[-nb_points:])
            self.volt_line_ctn1.set_ydata(tab_resolutions_ctn1[resolution - 1][-nb_points:])
            self.volt_line_ctn2.set_xdata(timestamps[-nb_points:])
            self.volt_line_ctn2.set_ydata(tab_resolutions_ctn2[resolution - 1][-nb_points:])
            self.volt_ax.relim()
            self.volt_ax.autoscale_view()
            self.voltage_canvas.draw_idle()
    
    def create_graph_temperature(self):
        self.temp_fig, self.temp_ax = plt.subplots()
        self.temp_fig.patch.set_alpha(0)
        self.temp_ax.set_facecolor((0, 0, 0, 0))
        self.temp_ax.set_xlabel("Temps (s)")
        self.temp_ax.set_ylabel("Température (°C)")
        self.temp_ax.set_ylim(20, 40)
        self.temp_line_ctn1, = self.temp_ax.plot([], [], label="CTN1")
        self.temp_line_ctn2, = self.temp_ax.plot([], [], label="CTN2")
        self.temp_ax.legend(loc="upper right")
        self.temperature_canvas = FigureCanvasTkAgg(self.temp_fig, self.tabview.tab("Températures"))
        self.temperature_canvas.draw()
        self.temperature_canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def update_graph_temperature(self):
        global resolution, timestamps, tab_temperature_ctn1, tab_temperature_ctn2
        nb_points = 10
        if len(timestamps) > 3:
            x_data = timestamps[-nb_points:]
            y_data_ctn1 = tab_temperature_ctn1[resolution - 1][-nb_points:]
            y_data_ctn2 = tab_temperature_ctn2[resolution - 1][-nb_points:]
            spline_ctn1 = make_interp_spline(x_data, y_data_ctn1)
            spline_ctn2 = make_interp_spline(x_data, y_data_ctn2)
            x_smooth = np.linspace(x_data.min(), x_data.max(), 500)
            y_smooth_ctn1 = spline_ctn1(x_smooth)
            y_smooth_ctn2 = spline_ctn2(x_smooth)
            self.temp_line_ctn1.set_xdata(x_smooth)
            self.temp_line_ctn1.set_ydata(y_smooth_ctn1)
            self.temp_line_ctn2.set_xdata(x_smooth)
            self.temp_line_ctn2.set_ydata(y_smooth_ctn2)
            self.temp_ax.legend([f"CTN1 : {y_data_ctn1[-1]:.2f}°C", f"CTN2 : {y_data_ctn2[-1]:.2f}°C"], loc="upper right")
            self.temp_ax.relim()
            self.temp_ax.autoscale_view(tight=True)
            self.temperature_canvas.draw_idle()
        
    def update_graph_temperature_raw(self):
        global resolution, timestamps, tab_temperature_ctn1, tab_temperature_ctn2
        nb_points = 10
        if len(timestamps) > 1:
            self.temp_line_ctn1.set_xdata(timestamps[-nb_points:])
            self.temp_line_ctn1.set_ydata(tab_temperature_ctn1[resolution - 1][-nb_points:])
            self.temp_line_ctn2.set_xdata(timestamps[-nb_points:])
            self.temp_line_ctn2.set_ydata(tab_temperature_ctn2[resolution - 1][-nb_points:])
            self.temp_ax.relim()
            self.temp_ax.autoscale_view()
            self.temperature_canvas.draw_idle()
    
    def update_graph_color(self):
        self.voltage_canvas.get_tk_widget().configure(background=self.tabview.tab("Tensions").cget('fg_color'))
        color = "#DCE4EE" if customtkinter.get_appearance_mode() == "Dark" else "#1A1A1A"        
        self.volt_ax.spines['top'].set_color(color)
        self.volt_ax.spines['bottom'].set_color(color)
        self.volt_ax.spines['left'].set_color(color)
        self.volt_ax.spines['right'].set_color(color)
        self.volt_ax.tick_params(axis='x', colors=color)
        self.volt_ax.tick_params(axis='y', colors=color)
        self.volt_ax.xaxis.label.set_color(color)
        self.volt_ax.yaxis.label.set_color(color)
        self.volt_ax.title.set_color(color)
        self.voltage_canvas.draw_idle()
        
        self.temperature_canvas.get_tk_widget().configure(background=self.tabview.tab("Tensions").cget('fg_color'))
        color = "#DCE4EE" if customtkinter.get_appearance_mode() == "Dark" else "#1A1A1A"        
        self.temp_ax.spines['top'].set_color(color)
        self.temp_ax.spines['bottom'].set_color(color)
        self.temp_ax.spines['left'].set_color(color)
        self.temp_ax.spines['right'].set_color(color)
        self.temp_ax.tick_params(axis='x', colors=color)
        self.temp_ax.tick_params(axis='y', colors=color)
        self.temp_ax.xaxis.label.set_color(color)
        self.temp_ax.yaxis.label.set_color(color)
        self.temp_ax.title.set_color(color)
        self.temperature_canvas.draw_idle()

    def voltage_comp(self):
        global resolution, tab_resolutions_ctn1, tab_resolutions_ctn2
        threshold = 0.1
        sens = "Aucun"
        if tab_resolutions_ctn1[resolution - 1][-1] - tab_resolutions_ctn2[resolution - 1][-1] > threshold:
            sens = "CTN 2 ➜ CTN 1"
        elif tab_resolutions_ctn1[resolution - 1][-1] - tab_resolutions_ctn2[resolution - 1][-1] < -threshold:
            sens = "CTN 1 ➜ CTN 2"
        self.direction_label.configure(text=f"Sens du flux d'air :\n{sens}")


class TraitementData:
    def __init__(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
    
    def run(self):
        global acquisition
        port = self.detect_rp2040()
        self.ser = serial.Serial(port, baudrate=115200, timeout=1)
        while True:
            if acquisition:
                tc, ctn1, ctn2 = self.read_usb()
                self.resolutions_update(tc, ctn1, ctn2)
            time.sleep(0.1)
    
    def detect_rp2040(self):
        while True:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                if "2E8A" in port.hwid:
                    return port.device
            time.sleep(0.1)

    def extract_lists(self, received_str):
        try:
            list1, list2 = ast.literal_eval(received_str)
            return list1, list2
        except:
            return None, None

    def read_usb(self):
        try:
            line = self.ser.readline().decode().strip()
            tc = time.time()
            if line:
                ctn1, ctn2 = self.extract_lists(line)
                return tc, ctn1, ctn2
        except:
            time.sleep(0.1)
            self.detect_rp2040()

    def binary_to_decimal(self, binary_list):
        return int(''.join(map(str, binary_list)), 2)
    
    def resolutions_update(self, timestamp, binary_list1, binary_list2):
        data_queue.put(("tc", 0,  timestamp))
        for i in range(8):
            value_ctn1 = self.binary_to_decimal(binary_list1[:i+1] + [0] * (7 - i)) * 5 / 255
            value_ctn2 = self.binary_to_decimal(binary_list2[:i+1] + [0] * (7 - i)) * 5 / 255
            data_queue.put(("ctn1", i, value_ctn1))
            data_queue.put(("ctn2", i, value_ctn2))


if __name__ == "__main__":
    TraitementData()
    app = App()
    app.mainloop()