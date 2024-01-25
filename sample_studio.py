import sys
from gui import Ui_MainWindow
import numpy as np
import math
import pandas as pd
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog, QShortcut
from PyQt5.QtGui import QKeySequence
import numpy as np
import pyqtgraph as pg
import csv
from scipy.interpolate import interp1d



class SignalGUI(Ui_MainWindow):
    def setupUi(self, MainWindow):
        Ui_MainWindow.setupUi(self, MainWindow)
        
        
class class_sinusoidal():   
    def __init__(self, name="", frequency = 1.0, amplitude = 1.0, phase = 0.0):
        
        self.name = name
        self.frequency = frequency
        self.amplitude = amplitude
        self.phase = phase

        self.resultant_sig = [np.linspace(0, 1, 10000, endpoint=False), [0] * 10000]
        
        self.time_values = np.linspace(0, 1, 10000, endpoint= False)
        
        # Creates a sin function with Sin(2 * pi * F * T + phase) and multiply it with the amplitude
        self.y_axis_values = amplitude * np.sin(2 * math.pi * frequency * self.time_values + phase)

        
    
    def add_sig_to_result(self, sig_to_add):
        for point in range(len(sig_to_add.y_axis_values)):
            self.resultant_sig[1][point] += sig_to_add.y_axis_values[point]
        
    
    def subtract_sig_from_result(self, sig_to_subtract):
        for point in range(len(sig_to_subtract.y_axis_values)):
            self.resultant_sig[1][point] -= sig_to_subtract.y_axis_values[point]


    def reset_resultant_sig(self):
        self.resultant_sig = [np.linspace(0, 1, 10000, endpoint=False), [0] * 10000]




class Signal_sampling_and_recovering(QtWidgets.QMainWindow):
    exported_signal_index = "resultant_signal_from_composer"
    def __init__(self):
        super(Signal_sampling_and_recovering, self).__init__()
        self.gui = SignalGUI()
        self.gui.setupUi(self)
        self.gui.tabWidget.setCurrentIndex(0)

        self.csv_file_path = None

        self.data = None              # Stores the y_axis values
        self.time = None              # Stores the x_axis values
        self.fs = None                # Stores sampling frequency
        self.fmax = None
  
        self.components_freq = []     # List to get the max freq in composed signals
        self.noisy_signal = None      # Stores the noisy signal
  
        self.Time_Values = []         # Stores sampled time values
        self.Samples = []             # Stores sampled values

        self.index_for_nameless = 0   # An index to append to default signal component name in composer
        self.index_for_duplicate = 0  # An index to append to components with similar names
        
        self.composed_result = class_sinusoidal() # Holds an initial dummy signal with no values
        
        self.component_dict = {}      # Dictionary to hold the components of the composed signal

        # Noise dial min, max level and start value
        self.gui.dial_SNR.setMinimum(0)
        self.gui.dial_SNR.setMaximum(100)
        self.gui.dial_SNR.setValue(100)
        self.gui.lbl_snr_level.setText(f"SNR Level: {self.gui.dial_SNR.value() / 2}")
        
        self.gui.horizontalSlider_sample_freq.setEnabled(False)  # Disable the fs slider
        


######################################################### SHORTCUTS #########################################################
        
        
        openShortcut = QShortcut(QKeySequence("ctrl+o"), self)
        openShortcut.activated.connect(self.Open_CSV_File)
        
        switchTabsShortcut = QShortcut(QKeySequence("Ctrl + Tab"), self)
        switchTabsShortcut.activated.connect(self.Switch_Tabs)

        
###################################################### UI CONNECTIONS #######################################################
        
        
        # Connect the fs slider to sampling_points_plot func.
        self.gui.horizontalSlider_sample_freq.valueChanged.connect(self.sampling_points_plot)  
        self.gui.horizontalSlider_sample_freq.valueChanged.connect(self.print_freq_val)  
        
        # Connect the fs slider to sampling_points_plot func.
        self.gui.dial_SNR.valueChanged.connect(self.Add_Noise)
        
        # Composer connections
        self.gui.btn_open_signal.clicked.connect(self.Open_CSV_File)
        self.gui.btn_add_component.clicked.connect(self.Add_Sig_Component)
        self.gui.list_sig_components.currentItemChanged.connect(self.Plot_Sig_Component_From_ListWidget)
        self.gui.btn_remove_component.clicked.connect(self.Remove_Sig_Component)
        self.gui.btn_compose.clicked.connect(self.Save_Composed_Signal)
        self.gui.tabWidget.currentChanged.connect(self.Set_Focus_On_Tab_Change)
        self.gui.field_amplitude.textEdited.connect(self.Plot_Field_Contents)
        self.gui.field_frequency.textEdited.connect(self.Plot_Field_Contents)
        self.gui.field_phase.textEdited.connect(self.Plot_Field_Contents)

        self.link_views()
        self.gui.plot_widget_component.setXRange(0,5)
        self.gui.plot_widget_composed.setXRange(0,5)
        
        
######################################################### Definitions #########################################################
   
   
    #-----------------------------------------------------------------------------------------------------------------------------#
    #                                                       Misc Methods                                                          #
    #-----------------------------------------------------------------------------------------------------------------------------#
    def link_views(self):
        self.gui.plot_widget_restored_signal.setYLink   (self.gui.plot_widget_main_signal)

        self.gui.plot_widget_difference.setXLink(self.gui.plot_widget_main_signal)
        self.gui.plot_widget_difference.setYLink(self.gui.plot_widget_main_signal)



    def Set_Focus_On_Tab_Change(self):
        # Sets focus on the name field in composer or 'Open File' button in viewer 
        if self.gui.tabWidget.currentIndex() == 1:
            self.gui.field_name.setFocus()
        else:
            self.gui.btn_open_signal.setFocus()
            
    def Switch_Tabs(self):
        self.gui.tabWidget.setCurrentIndex(int(not bool(self.gui.tabWidget.currentIndex)))
            
                
    #-----------------------------------------------------------------------------------------------------------------------------#
    #                                                       Viewer Methods                                                        #
    #-----------------------------------------------------------------------------------------------------------------------------#
    
    def print_freq_val(self):
        self.gui.label_sampling_frequency.setText("Sampling Frequency: " + str(self.gui.horizontalSlider_sample_freq.value()))
        

    def Open_CSV_File(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        
        # Path of selected file
        path, _ = QFileDialog.getOpenFileName( self, "Open Data File", "", "CSV Files (*.csv);;DAT Files (*.dat)", options=options)

        # Make all vars = None to add new data
        self.data = None
        self.time = None
        self.fs = None
        self.components_freq = []
        self.noisy_signal = None

        #Load the data from csv
        data = np.genfromtxt(path, delimiter=',')
        
        # Take time values from first column
        time = list(data[1:, 0])

        # Take y values from second column
        amp = list(data[1:, 1])
        
        # Take fs value from third column
        self.fs = int(data[1, 2])
        self.fmax = self.fs

        # Store the data we will use 
        self.data = amp[0:1000]
        self.time = time[0:1000]
        self.noisy_signal=self.data

        self.gui.plot_widget_difference.clear()
        self.gui.plot_widget_main_signal.clear()
        self.gui.plot_widget_restored_signal.clear()

        self.gui.label_original_frequency.setText(f"Max Frequency: {self.fmax}")

        self.gui.dial_SNR.setValue(100)
        self.gui.lbl_snr_level.setText(f"SNR Level: (100)")
        # Plot time and amplitude on main plot
        self.Plot_On_Main(self.time, self.data)



    def Add_Noise(self):       
        # Get the Signal-to-Noise Ratio (SNR) in decibels from the GUI dial
        snr_db = self.gui.dial_SNR.value()
        
        # Set label text to SNR dB value
        self.gui.lbl_snr_level.setText(f"SNR Level: ({snr_db / 2})")
        
        # Define a function to calculate the power of a list of values
        def power(my_list):
            return [x**2 for x in my_list]

        # Calculate the power of the original signal
        power_orig_signal = power(self.data)
        
        # Calculate the average power of the signal
        signal_average_power = np.mean(power_orig_signal)
        
        # Convert the average signal power to decibels
        signal_average_power_db = 10 * np.log10(signal_average_power)
        
        # Calculate the noise power in decibels
        noise_db = signal_average_power_db - snr_db
        
        # Convert the noise power from decibels to watts
        noise_watts = 10 ** (noise_db / 10)
        
        # Generate random noise samples with a mean of 0 and standard deviation based on noise power
        noise = np.random.normal(0, np.sqrt(noise_watts), len(self.data))
        
        # Add the generated noise to the original signal
        self.noisy_signal = self.data + noise
        
        # Plot the noisy signal on the main signal plot_widget in red
        self.gui.plot_widget_main_signal.plot(self.time, self.noisy_signal, pen="r")
        self.sampling_points_plot()
        self.print_freq_val()


    def Plot_On_Main(self, time, amplitude):
        self.gui.plot_widget_main_signal.plot(time, amplitude, pen="r")
        
        # freq_slider_enabled and limits
        self.gui.horizontalSlider_sample_freq.setEnabled(True)
        self.gui.horizontalSlider_sample_freq.setMinimum(1)
        self.gui.horizontalSlider_sample_freq.setMaximum(self.fs * 4)
        self.gui.horizontalSlider_sample_freq.setValue(1)


        
    def sampling_points_plot(self):
        self.gui.plot_widget_main_signal.clear()

        fs = self.gui.horizontalSlider_sample_freq.value()


        self.Samples = []
        self.Time_Values = []
        # Get the sample points

        interpolator = interp1d(self.time, self.noisy_signal, kind= 'linear', fill_value="extrapolate")
        self.Time_Values = np.arange(self.time[0], self.time[-1], 1/fs)
        self.Samples = interpolator(self.Time_Values)

        # Plot the original signal
        self.gui.plot_widget_main_signal.plot(self.time, self.noisy_signal, pen="r", name="Original Signal")
        # Plot the sampled points
        self.gui.plot_widget_main_signal.plot(self.Time_Values, self.Samples, pen=None, symbol='o', symbolSize=5, name="Sampled Points")
        
        self.interploation()


    def interploation(self):
        reconstructed_signal = np.zeros_like(self.time)
        fs = self.gui.horizontalSlider_sample_freq.value()

        for sample_t, sample_val in zip(self.Time_Values, self.Samples):
            # sinc_values = np.sinc(fs * (self.time - sample_t))
            sinc_values = np.sinc(fs * (self.time - sample_t))

            reconstructed_signal += sample_val * sinc_values

        self.gui.plot_widget_restored_signal.clear()
        self.gui.plot_widget_restored_signal.plot(self.time, reconstructed_signal, pen="w")

        if self.fs > 2*self.fmax:
            difference *= (1 - self.fmax / self.fs) 

        difference = self.data - reconstructed_signal

        rms_value = np.sqrt(np.mean(np.square(difference)))
        print(rms_value)

        self.gui.plot_widget_difference.clear()
        self.gui.plot_widget_difference.plot(self.time, difference, pen="g", name="Difference")
         


    #-----------------------------------------------------------------------------------------------------------------------------#
    #                                                       Composer Methods                                                      #
    #-----------------------------------------------------------------------------------------------------------------------------#
    


    def components_freq_adding(self):
        # Append frequency values from freq. field in the composer
        self.components_freq.append(int(self.gui.field_frequency.text()))
    
    def get_max_freq(self):
        # Get the max freq. from components_freq list
        return max(self.components_freq)
    
    # Adds signal component to plot_widget_composed_signal
    def Add_Sig_Component(self):
        self.components_freq_adding()

        # Create signal from fields
        sig_comp = self.Create_Sig_From_Fields()
        
        # Add item to list_sig_component and append to component_dict
        self.gui.list_sig_components.addItem(sig_comp.name)
        self.component_dict[sig_comp.name] = sig_comp
        
        # Add new component to composed signal
        self.composed_result.add_sig_to_result(sig_comp)
        
        # Plot new composed signal
        self.gui.plot_widget_composed.clear()
        self.gui.plot_widget_composed.plot(self.composed_result.resultant_sig[0], self.composed_result.resultant_sig[1], pen = 'r')
        print(sig_comp.name)
        
        # Prepare for new component input
        self.gui.plot_widget_component.clear()
        self.Clear_Input_Fields()
        
        self.gui.field_name.setFocus()
        
    # Adds signal component to plot_widget_composed_signal
    def Remove_Sig_Component(self):
        
        self.gui.plot_widget_component.clear()
        
        # Remove item from component_dict
        comp_to_be_removed = self.component_dict.pop(self.gui.list_sig_components.currentItem().text())
        
        # Remove item from list_sig_component
        self.gui.list_sig_components.takeItem(self.gui.list_sig_components.currentRow())
        
        if len(self.component_dict) == 0:
            self.gui.plot_widget_composed.clear()
            return
        
        
        # Remove selected component from composed signal
        self.composed_result.subtract_sig_from_result(comp_to_be_removed)
        
        # Plot new composed signal
        self.gui.plot_widget_composed.clear()
        self.gui.plot_widget_composed.plot(self.composed_result.resultant_sig[0], self.composed_result.resultant_sig[1], pen = 'r')
        
        self.gui.field_name.setFocus()

        
    
    
    # Returns a class_sinusoidal object with the field inputs 
    def Create_Sig_From_Fields(self):
        name = self.gui.field_name.text()
        freq = self.Return_Zero_At_Empty_String(self.gui.field_frequency.text(), 1)
        amp = self.Return_Zero_At_Empty_String(self.gui.field_amplitude.text(), 1)
        phase = self.Return_Zero_At_Empty_String(self.gui.field_phase.text(), 0)
        
        if name == "":
            name = f"sig_{self.index_for_nameless}"
            self.index_for_nameless +=1
        
        elif name in self.component_dict.keys():
            name = f"{name}_{self.index_for_duplicate}"
            self.index_for_nameless +=1
            
            
                
        new_sig = class_sinusoidal(name, float(freq), float(amp), float(phase))
        return new_sig
        
    # Plots the selected signal component from list_sig_components on plot_widget_component
    def Plot_Sig_Component_From_ListWidget(self):
        self.gui.plot_widget_component.clear()
        
        sig_component = self.component_dict[self.gui.list_sig_components.currentItem().text()]
        self.gui.plot_widget_component.plot(sig_component.time_values, sig_component.y_axis_values, pen = "r")
    
    
    # Plot field contents on plot_widget_component
    def Plot_Field_Contents(self):
        self.gui.plot_widget_component.clear()
        temp_sig = self.Create_Sig_From_Fields()
        self.gui.plot_widget_component.plot(temp_sig.time_values, temp_sig.y_axis_values, pen = "r")
    
    # Clear Input Fields
    def Clear_Input_Fields(self):
        self.gui.field_name.clear()
        self.gui.field_amplitude.clear()
        self.gui.field_frequency.clear()
        self.gui.field_phase.clear()

    # Saves composed signal and opens it in the viewer
    def Save_Composed_Signal(self):
        self.Export_Composed_Signal_As_CSV()
                
        # Reset everything for next composition
        self.gui.plot_widget_composed.clear()
        self.gui.list_sig_components.clear()   
        self.composed_result.reset_resultant_sig()
        self.component_dict = {}
        print(len(self.composed_result.resultant_sig))


    # Exports the signal as a CSV file
    def Export_Composed_Signal_As_CSV(self):
        max_freq = (self.get_max_freq())
        # max_freq = 500
        self.composed_result.resultant_sig.append([max_freq])
        df = pd.DataFrame(self.composed_result.resultant_sig).transpose()
        df.columns = ['Time', 'Amplitude', 'F_Sampling']

        # Specify the base file path
        base_file_path = 'composed_signal_{}.csv'

        # Find the next available index for the filename
        index = 1
        while True:
            self.csv_file_path = base_file_path.format(index)
            try:
                # Try to open the file in 'x' mode to check if it exists
                with open(self.csv_file_path, 'x', newline=''):
                    # File doesn't exist, break the loop
                    break
            except FileExistsError:
                # File with this name already exists, try the next index
                index += 1

        # Open the file in 'w' mode, create a CSV writer object
        with open(self.csv_file_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)

            # Write data to the CSV file
            csv_writer.writerows([df.columns])  # Write column headers
            csv_writer.writerows(df.values)     # Write data rows

        print(f'CSV file "{self.csv_file_path}" created successfully with data in columns.')


    def Return_Zero_At_Empty_String(self, string, value):
        if string == "":
            return f"{value}"
        else:
            return string                           






def window():
    app = QApplication(sys.argv)
    win = Signal_sampling_and_recovering()

    win.show()
    sys.exit(app.exec_())


# main code
if __name__ == "__main__":
    window()
