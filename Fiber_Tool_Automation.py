import sys
import subprocess
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QTextBrowser, QMessageBox, 
                             QSpacerItem, QSizePolicy)
from PyQt6.QtGui import QIntValidator, QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression, QTimer
import paramiko
import winsound
import os
import time

class RemoteScriptControl(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.raspberry_pi_ip = '192.168.0.100'
        self.username = 'Asclepion'
        self.password = 'Asclepion'
        self.script_path = '/home/Asclepion/Desktop/git/automation.py'
        self.additional_script_path = '/home/Asclepion/Desktop/git/servo.py'
        self.units_file_path = '/home/Asclepion/Desktop/git/units_to_program.txt'
        self.pid = None
        self.programmed_units = 0
        self.faulty_units = 0
        self.units_to_program = 112
        self.loaded_tags = 112
        self.language = 'en'

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.raspberry_pi_ip, username=self.username, password=self.password)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)

    def update_status(self):
        self.update_programmed_units()
        self.update_faulty_units()

    def update_faulty_units(self):
        try:
            sftp = self.ssh.open_sftp()
            with sftp.open('/home/Asclepion/Desktop/lattepanda_share/faulty_units_count.txt', 'r') as file:
                content = file.read().strip()
                self.faulty_units = int(content) if content else 0
                self.update_faulty_units_display()
        except Exception as e:
            print(f"Failed to update faulty units: {e}")
        finally:
            sftp.close()


    def update_programmed_units(self):
        try:
            sftp = self.ssh.open_sftp()
            with sftp.open('/home/Asclepion/Desktop/lattepanda_share/programmed_units_count.txt', 'r') as file:
                content = file.read().strip()
                self.programmed_units = int(content) if content else 0
                self.update_programmed_units_display()
                self.update_estimated_time()
                if self.programmed_units >= self.units_to_program:
                    self.play_alarm_sound()
                    time.sleep(1)
                    self.play_alarm_sound()
                    time.sleep(2)
                    self.programmed_units = 0
                    self.update_programmed_units_display()
                    self.delete_programmed_units_file()
            if self.programmed_units >= self.units_to_program:
                sftp.remove('/home/Asclepion/Desktop/lattepanda_share/programmed_units_count.txt')
        except Exception as e:
            print(f"Failed to update programmed units: {e}")
        finally:
            sftp.close()


        
    def initUI(self):
        self.setWindowTitle('Remote Script Control')

        self.setFixedSize(300, 400)

        self.layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        
        top_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.language_button = QPushButton('Deutsch', self)
        self.language_button.clicked.connect(self.toggle_language)
        top_layout.addWidget(self.language_button)

        self.layout.addLayout(top_layout)

        self.factory_code_input = QLineEdit(self)
        self.factory_code_input.setPlaceholderText('Enter 16-digit Factory Code')
        
        factory_code_validator = QRegularExpressionValidator(QRegularExpression(r"[A-Za-z0-9]{16}"))
        self.factory_code_input.setValidator(factory_code_validator)
        self.factory_code_input.textChanged.connect(self.convert_factory_code_to_uppercase)
        self.factory_code_input.textChanged.connect(self.check_input_validity)
        self.layout.addWidget(self.factory_code_input)

        self.customer_code_input = QLineEdit(self)
        self.customer_code_input.setPlaceholderText('Enter 4-digit Customer Code')
        self.customer_code_input.setMaxLength(4)
        self.customer_code_input.setValidator(QIntValidator(1000, 9999, self))
        self.customer_code_input.textChanged.connect(self.check_input_validity)
        self.layout.addWidget(self.customer_code_input)

        self.units_input = QLineEdit(self)
        self.units_input.setPlaceholderText('Enter number of units to program (Max 112)')
        self.units_input.setValidator(QIntValidator(1, 112, self))
        self.units_input.textChanged.connect(self.check_input_validity)
        self.layout.addWidget(self.units_input)

        self.loaded_tags_input = QLineEdit(self)
        self.loaded_tags_input.setPlaceholderText('Enter number of loaded tags (optional)')
        self.loaded_tags_input.setValidator(QIntValidator(0, 112, self))
        self.loaded_tags_input.textChanged.connect(self.check_input_validity)
        self.layout.addWidget(self.loaded_tags_input)

        self.start_button = QPushButton('Start Automation', self)
        self.start_button.clicked.connect(self.show_confirmation_dialog)
        self.start_button.setEnabled(False)  
        self.layout.addWidget(self.start_button)

        self.stop_button = QPushButton('Stop Automation', self)
        self.stop_button.clicked.connect(self.confirm_stop_automation)
        self.stop_button.setEnabled(False)  
        self.layout.addWidget(self.stop_button)

        self.emergency_stop_button = QPushButton('Emergency Stop', self)
        self.emergency_stop_button.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.emergency_stop_button.clicked.connect(self.emergency_stop)
        self.emergency_stop_button.setEnabled(False) 
        self.layout.addWidget(self.emergency_stop_button)

        self.status_label = QLabel('Status: Idle', self)
        self.layout.addWidget(self.status_label)

        self.programmed_units_browser = QTextBrowser(self)
        self.programmed_units_browser.setHtml('<b>Programmed Units:</b> 0')
        self.programmed_units_browser.setFixedHeight(30)
        self.layout.addWidget(self.programmed_units_browser)

        self.faulty_units_browser = QTextBrowser(self)
        self.faulty_units_browser.setHtml('<b>Faulty Units:</b> 0')
        self.faulty_units_browser.setFixedHeight(30)
        self.layout.addWidget(self.faulty_units_browser)

        self.estimated_time_label = QLabel('Estimated Time: N/A', self)
        self.layout.addWidget(self.estimated_time_label)

        self.setLayout(self.layout)

    def check_input_validity(self):
        factory_code = self.factory_code_input.text()
        customer_code = self.customer_code_input.text()
        units_text = self.units_input.text()

        if len(factory_code) == 16 and len(customer_code) == 4 and units_text:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.emergency_stop_button.setEnabled(True)
            self.update_estimated_time()  
        else:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.emergency_stop_button.setEnabled(False)
            self.estimated_time_label.setText('Estimated Time: N/A')
    
    def convert_factory_code_to_uppercase(self):
        text = self.factory_code_input.text().upper()
        self.factory_code_input.setText(text)

    def update_estimated_time(self):
        try:
            self.units_to_program = int(self.units_input.text())
            if self.programmed_units >= self.units_to_program:
                estimated_time_text = 'Estimated Time: 0 minutes, 0 seconds' if self.language == 'en' else 'Geschätzte Zeit: 0 Minuten, 0 Sekunden'
            else:
                remaining_units = self.units_to_program - self.programmed_units
                estimated_time_minutes = (remaining_units * 0.53) + 1  
                minutes = int(estimated_time_minutes)
                seconds = int((estimated_time_minutes - minutes) * 60)
                
                if self.language == 'en':
                    estimated_time_text = f'Estimated Time: {minutes} minutes, {seconds} seconds'
                else:
                    estimated_time_text = f'Geschätzte Zeit: {minutes} Minuten, {seconds} Sekunden'
            
            self.estimated_time_label.setText(estimated_time_text)
        except ValueError:
            if self.language == 'en':
                self.estimated_time_label.setText('Estimated Time: N/A')
            else:
                self.estimated_time_label.setText('Geschätzte Zeit: Nicht verfügbar')

    def show_confirmation_dialog(self):
        reply = QMessageBox.question(
            self,
            'Please Ensure Collection Tray is Empty' if self.language == 'en' else 'Bitte stellen Sie sicher, dass der Auffangbehälter leer ist',
            'Please ensure the collection tray is empty before starting automation.' if self.language == 'en' else 'Bitte stellen Sie sicher, dass der Auffangbehälter leer ist, bevor Sie die Automatisierung starten.',
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Ok:
            self.run_script()

    def run_script(self):
        try:
            if not self.units_input.text():
                raise ValueError("Units to program cannot be empty")

            self.units_to_program = int(self.units_input.text())
            self.loaded_tags = int(self.loaded_tags_input.text()) if self.loaded_tags_input.text() else None

            if not (1 <= self.units_to_program <= 112):
                raise ValueError("Units to program must be between 1 and 112")

            if self.loaded_tags is not None:
                if not (0 <= self.loaded_tags <= 112):
                    raise ValueError("Loaded tags must be between 0 and 112")
                if self.units_to_program > self.loaded_tags:
                    raise ValueError("Units to program cannot exceed loaded tags")

            self.check_and_delete_file()
            self.programmed_units = 0  

            command = f'nohup python3 {self.script_path} {self.units_to_program} {self.loaded_tags if self.loaded_tags is not None else 0} > /dev/null 2>&1 & echo $!'
            stdin, stdout, stderr = self.ssh.exec_command(command)
            self.pid = stdout.read().decode().strip()
            stderr_msg = stderr.read().decode()
            if self.pid:
                self.status_label.setText('Status: Automation Running' if self.language == 'en' else 'Status: Automatisierung läuft')
            else:
                self.status_label.setText('Status: Error starting automation' if self.language == 'en' else 'Status: Fehler beim Starten der Automatisierung')
            if stderr_msg:
                print(stderr_msg)  

        except ValueError as e:
            QMessageBox.warning(self, 
                                'Input Error' if self.language == 'en' else 'Eingabefehler',
                                str(e),
                                QMessageBox.StandardButton.Ok)

    def check_and_delete_file(self):
        try:
            sftp = self.ssh.open_sftp()
            try:
                sftp.remove('/home/Asclepion/Desktop/lattepanda_share/programmed_units_count.txt')
                print("Deleted programmed_units_count.txt before starting.")
            except FileNotFoundError:
                print("No programmed_units_count.txt file to delete.")
        except Exception as e:
            print(f"Failed to delete programmed units file: {e}")
        finally:
            sftp.close()

    def confirm_stop_automation(self):
        reply = QMessageBox.question(self,
                                     'Confirmation' if self.language == 'en' else 'Bestätigung',
                                     f'You are about to stop automation and reset the programmed units count to 0. Do you want to proceed?' if self.language == 'en' else f'Sie sind dabei, die Automatisierung zu stoppen und die Anzahl der programmierten Einheiten auf 0 zurückzusetzen. Möchten Sie fortfahren?',
                                     QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Ok:
            self.stop_script_and_start_servo()


    def update_programmed_units_display(self):
        if self.language == 'en':
            self.programmed_units_browser.setHtml(f'<b>Programmed Units:</b> {self.programmed_units}')
        else:
            self.programmed_units_browser.setHtml(f'<b>Programmierte Einheiten:</b> {self.programmed_units}')   

    def update_faulty_units_display(self):
        if self.language == 'en':
            self.faulty_units_browser.setHtml(f'<b>Faulty Units:</b> {self.faulty_units}')
        else:
            self.faulty_units_browser.setHtml(f'<b>Fehlerhafte Einheiten:</b> {self.faulty_units}')   

    def delete_programmed_units_file(self):
        try:
            sftp = self.ssh.open_sftp()
            try:
                sftp.remove('/home/Asclepion/Desktop/lattepanda_share/programmed_units_count.txt')
                print("Deleted programmed_units_count.txt after completion.")
            except FileNotFoundError:
                print("No programmed_units_count.txt file to delete.")
        except Exception as e:
            print(f"Failed to delete programmed units file: {e}")
        finally:
            sftp.close()
    
    def delete_faulty_units_file(self):
        try:
            sftp = self.ssh.open_sftp()
            try:
                sftp.remove('/home/Asclepion/Desktop/lattepanda_share/faulty_units_count.txt')
                print("Deleted faulty_units_count.txt after completion.")
            except FileNotFoundError:
                print("No faulty_units_count.txt file to delete.")
        except Exception as e:
            print(f"Failed to delete faulty units file: {e}")
        finally:
            sftp.close()
       
    def stop_script_and_start_servo(self):
        if self.pid:
            stdin, stdout, stderr = self.ssh.exec_command(f"kill {self.pid}")
            stdout_msg = stdout.read().decode()
            stderr_msg = stderr.read().decode()
            self.pid = None
            if stdout_msg:
                self.status_label.setText('Status: Automation Stopped' if self.language == 'en' else 'Status: Automatisierung gestoppt')
            if stderr_msg:
                print(stderr_msg)
            self.delete_programmed_units_file()
            
        else:
            self.status_label.setText('Status: No automation is running. Starting Servo...' if self.language == 'en' else 'Status: Keine Automatisierung läuft. Starte Servo...')
            self.delete_programmed_units_file()
            self.delete_faulty_units_file()
        self.programmed_units = 0
        self.faulty_units = 0
        self.update_programmed_units_display()
        self.update_faulty_units_display()
        self.faulty_units_browser.setHtml('<b>Faulty Units:</b> 0')
        self.start_servo_script()
        self.update_programmed_units()
        self.update_faulty_units()

    def start_servo_script(self):
        stdin, stdout, stderr = self.ssh.exec_command(f'nohup python3 "{self.additional_script_path}" > /dev/null 2>&1 &')
        stderr_msg = stderr.read().decode()
        if stderr_msg:
            print(stderr_msg) 
        else:
            self.status_label.setText('Status: Servo Started' if self.language == 'en' else 'Status: Servo gestartet')
        
    def emergency_stop(self):
        if self.pid:
            stdin, stdout, stderr = self.ssh.exec_command(f"kill -9 {self.pid}")
            self.pid = None
            self.status_label.setText('Status: Emergency Stop Activated' if self.language == 'en' else 'Status: Not-Aus aktiviert')

    def play_alarm_sound(self):
        duration = 1000 
        freq = 600  
        winsound.Beep(freq, duration)

    def toggle_language(self):
        if self.language == 'en':
            self.language = 'de'
            self.language_button.setText('English')
            self.units_input.setPlaceholderText('Anzahl der zu programmierenden Einheiten eingeben (max. 112)')
            self.loaded_tags_input.setPlaceholderText('Anzahl der geladenen Tags eingeben (optional)')
            self.start_button.setText('Automatisierung starten')
            self.stop_button.setText('Automatisierung stoppen')
            self.emergency_stop_button.setText('Not-Aus')
            self.status_label.setText('Status: Leerlauf')
            self.programmed_units_browser.setHtml('<b>Programmierte Einheiten:</b> 0')
            self.faulty_units_browser.setHtml('<b>Fehlerhafte Einheiten:</b> 0')
            self.estimated_time_label.setText('Geschätzte Zeit: N/A')
        else:
            self.language = 'en'
            self.language_button.setText('Deutsch')
            self.units_input.setPlaceholderText('Enter number of units to program (Max 112)')
            self.loaded_tags_input.setPlaceholderText('Enter number of loaded tags (optional)')
            self.start_button.setText('Start Automation')
            self.stop_button.setText('Stop Automation')
            self.emergency_stop_button.setText('Emergency Stop')
            self.status_label.setText('Status: Idle')
            self.programmed_units_browser.setHtml('<b>Programmed Units:</b> 0')
            self.faulty_units_browser.setHtml('<b>Faulty Units:</b> 0')
            self.estimated_time_label.setText('Estimated Time: N/A')
        self.update_programmed_units_display()
        self.update_faulty_units_display()
        self.update_estimated_time()

    def closeEvent(self, event):
        self.ssh.close()
        event.accept()

def main():
    fiber_tool_path = r'C:\Users\LattePanda\Desktop\Softwares\FiberTool.exe'
    subprocess.Popen(fiber_tool_path)

    app = QApplication(sys.argv)
    ex = RemoteScriptControl()
    ex.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()