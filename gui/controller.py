# gui/controller.py OK

import serial
import serial.tools.list_ports
import threading
import time


class CNCController:
    def __init__(self, app_instance):
        self.ser = None
        self.is_connected = False
        self.command_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.app = app_instance

    def get_serial_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect(self, port, baud=9600):
        try:
            self.ser = serial.Serial(port, baud, timeout=2)
            time.sleep(1.5)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            start_time = time.time()
            while time.time() - start_time < 5:
                self.ser.write(b"?\n")
                response = self.ser.readline().decode("utf-8").strip()
                if "Ready" in response:
                    self.is_connected = True
                    return True, "Kết nối thành công!"
                time.sleep(0.5)
            self.disconnect()
            return False, "Không nhận được tín hiệu 'Ready' từ Arduino sau 5 giây."
        except serial.SerialException as e:
            return False, f"Lỗi Serial: {e}"
        except Exception as e:
            return False, f"Lỗi không xác định: {e}"

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.is_connected = False
        self.ser = None

    def send_interrupt_command(self, command="!"):
        if not self.is_connected:
            return
        try:
            with self.write_lock:
                self.ser.write((command + "\n").encode())
        except Exception as e:
            print(f"Lỗi khi gửi lệnh ngắt: {e}")

    def send_command(self, command, callback=None):
        if not self.is_connected:
            if callback:
                self.app.after(0, callback, False, "Not Connected")
            return "NOT_CONNECTED"

        def task():
            if not self.command_lock.acquire(blocking=False):
                if not command.startswith("E") and not command.startswith("S"):
                    self.app.update_status("Lỗi: Máy đang bận!")
                    if callback:
                        self.app.after(0, callback, False, "Busy")
                    return
            try:
                if not command.startswith("E") and not command.startswith("S"):
                    self.app.update_status(f"Đang chạy: {command}")

                with self.write_lock:
                    self.ser.reset_input_buffer()
                    self.ser.write((command + "\n").encode())

                response = ""
                while self.is_connected:
                    line = self.ser.readline().decode("utf-8").strip()
                    if line:
                        response = line
                        if "OK" in response:
                            if callback:
                                self.app.after(0, callback, True, response)
                            break

                if "OK" not in response and callback:
                    self.app.after(0, callback, False, "No 'OK' received")

            except Exception as e:
                self.app.update_status(f"Lỗi giao tiếp: {e}")
                if callback:
                    self.app.after(0, callback, False, str(e))
            finally:
                if self.command_lock.locked():
                    self.command_lock.release()

        threading.Thread(target=task, daemon=True).start()
