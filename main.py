import sys
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget, QFrame, QApplication, QPushButton, QBoxLayout, QHBoxLayout, QComboBox, QTextEdit, \
    QVBoxLayout, QCheckBox
from serial import Serial
from serial.tools.list_ports import comports
from PyQt6.QtGui import QGuiApplication

class MySerial(QObject):
    opened = pyqtSignal()
    closed = pyqtSignal()
    data = pyqtSignal(bytes)

    def __init__(self, parent=None, serial:Serial=None):
        super(MySerial, self).__init__(parent)

        self.serial = serial
        self.is_open = False
        self.thread = threading.Thread()
        self.thread.run = self.thread_entry

    def set_dtr(self, b):
        self.serial.setDTR(b)

    def set_rts(self, b):
        self.serial.setRTS(b)

    def start(self):
        self.thread.start()

    def close(self):
        self.serial.close()

    def thread_entry(self):
        while True:
            if self.serial.is_open:
                data = self.serial.read_all()
                if len(data) > 0:
                    self.data.emit(data)
                time.sleep(0.01)
            else:
                break
        self.closed.emit()


class SerialPortSelector(QWidget):

    open_port = pyqtSignal(str, int)
    close_port = pyqtSignal()

    def __init__(self, *args):
        super(SerialPortSelector, self).__init__(*args)

        self.disabled = False

        self.init_ui()
        self.add_ports()

    def init_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        self.ports_list_combobox = QComboBox()
        layout.addWidget(self.ports_list_combobox)

        self.baud_rate_combobox = QComboBox()
        self.baud_rate_combobox.addItems(['300', '600', '1200', '2400', '4800', '9600', '19200', '38400', '43000', '56000', '57600', '115200'])
        self.baud_rate_combobox.setCurrentText('115200')
        self.baud_rate_combobox.setEditable(True)
        layout.addWidget(self.baud_rate_combobox)

        self.open_btn = QPushButton('打开')
        self.open_btn.clicked.connect(self.handle_open_port)
        layout.addWidget(self.open_btn)

        self.refresh_btn = QPushButton('刷新')
        self.refresh_btn.clicked.connect(self.add_ports)
        layout.addWidget(self.refresh_btn)

    def add_ports(self):
        self.ports_list_combobox.clear()
        for port in comports(False):
            self.ports_list_combobox.addItem(port.name, port)

    def handle_open_port(self):
        if self.disabled:
            self.close_port.emit()
        else:
            port = self.ports_list_combobox.currentText()
            if port == "":
                return
            baud_rate = int(self.baud_rate_combobox.currentText())
            self.open_port.emit(port, baud_rate)

    def set_disable(self, b):
        self.disabled = b
        self.ports_list_combobox.setDisabled(b)
        self.baud_rate_combobox.setDisabled(b)
        if self.disabled:
            self.open_btn.setText('关闭')
        else:
            self.open_btn.setText('打开')

class ControlBar(QWidget):

    dtr = pyqtSignal(bool)
    rts = pyqtSignal(bool)

    def __init__(self, parent):
        super(ControlBar, self).__init__(parent)

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        self.dtr_btn = QCheckBox('DTR')
        self.dtr_btn.clicked.connect(self.handle_dtr)
        self.rts_btn = QCheckBox('RTS')
        self.rts_btn.clicked.connect(self.handle_rts)

        layout.addWidget(self.dtr_btn)
        layout.addWidget(self.rts_btn)

    def handle_dtr(self, checked):
        self.dtr.emit(checked)

    def handle_rts(self, checked):
        self.rts.emit(checked)


    def reset(self):
        self.dtr_btn.setChecked(False)
        self.rts_btn.setChecked(False)
        self.dtr.disconnect()
        self.rts.disconnect()

class SendText(QWidget):
    def __init__(self, parent=None):
        super(SendText, self).__init__(parent)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.text = QTextEdit()
        layout.addWidget(self.text)

        layout2 = QHBoxLayout()
        layout.addLayout(layout2)

        self.combo = QComboBox()
        self.combo.addItem('不自动加换行符')
        self.combo.addItem('结尾自动加\\r\\n')
        self.combo.addItem('结尾自动加\\r')
        self.combo.addItem('结尾自动加\\n')
        self.send_btn = QPushButton('发送')

        layout2.addWidget(self.combo)
        layout2.addWidget(self.send_btn)

class SerialMan(QFrame):
    def __init__(self):
        super(SerialMan, self).__init__()
        self.setWindowTitle('SerialMan')

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.serial_port_selector = SerialPortSelector(self)
        self.serial_port_selector.open_port.connect(self.handle_open_port)
        self.serial_port_selector.close_port.connect(self.handle_close_port)
        layout.addWidget(self.serial_port_selector)

        self.control_bar = ControlBar(self)
        layout.addWidget(self.control_bar)

        self.text = QTextEdit(self)
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

        self.send_text = SendText()
        layout.addWidget(self.send_text)

    def handle_open_port(self, port, baud_rate):
        serial = Serial(port, baud_rate)
        self.serial = MySerial(self, serial)
        self.serial.data.connect(self.handle_data)
        self.serial.start()
        self.serial_port_selector.set_disable(True)

        self.control_bar.dtr.connect(self.serial.set_dtr)
        self.control_bar.rts.connect(self.serial.set_rts)

        self.serial.closed.connect(lambda: self.serial_port_selector.set_disable(False))

    def handle_close_port(self):
        self.control_bar.reset()
        self.serial.close()

    def handle_data(self, data):
        self.text.append(str(data, 'utf-8', errors='ignore'))

app = QApplication([])

window = SerialMan()
window.show()

app.exec()
