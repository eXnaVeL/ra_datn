# app.py OK

import customtkinter
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import json
import os
from datetime import datetime

# Import các module đã tạo
from controller import CNCController
from gui.dialogs import EditWaypointDialog
from gui.delay_dialogs import DelayEditDialog
from gui import widgets


class App(customtkinter.CTk):
    # ==========================================================
    # HẰNG SỐ CHUYỂN ĐỔI
    # ==========================================================
    DEG_TO_PULSE_FACTOR = 40.0

    # CẬP NHẬT: Hằng số tốc độ mặc định và giới hạn
    # Base steps per second for motor (tương ứng với 500us delay)
    BASE_MOTOR_SPEED_PPS = 2000
    MIN_SPEED_PERCENT = 10
    MAX_SPEED_PERCENT = 300
    SPEED_STEP_PERCENT = 10

    # CẬP NHẬT: Tốc độ mặc định cho jogging khi bấm nút (có thể khác với slider)
    JOG_BUTTON_ANGLE = 1.0  # Góc di chuyển mỗi lần bấm nút jog

    def __init__(self):
        super().__init__()
        self.title("CNC Control Panel")
        self.geometry("1280x720")
        self._center_window(1280, 720)

        self.controller = CNCController(self)

        # Biến trạng thái
        self.is_running_program = False
        self.program_index = 0
        self.current_position = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        self.last_used_port = tk.StringVar()
        self.is_homed = False
        self.is_homing = False
        self.is_returning_home = False
        self.motor_power_on = True
        self.jog_active = False  # Trạng thái cho di chuyển bằng phím
        self.last_command_sent = ""  # Lưu lệnh cuối cùng để callback biết
        self.move_mode = tk.StringVar(value="COORDINATE")

        # Biến cho Waypoints (lưu bằng độ)
        self.waypoints = []
        self.selected_waypoint_index = None

        # Biến cho danh sách chương trình (lưu bằng độ)
        self.programs = {}
        self.selected_program_name = None

        # Biến cho các entry và slider
        self.target_coord_entry = {axis: tk.StringVar(
            value="0.0") for axis in ["X", "Y", "Z"]}
        self.manual_pos_entry = {axis: tk.StringVar(
            value="0.0") for axis in ["X", "Y", "Z"]}
        self.speed_percentage_var = tk.IntVar(value=100)
        self.repeat_program_var = tk.BooleanVar(value=False)
        self.soft_limits = {axis: tk.StringVar(
            value="0.0") for axis in ["X", "Y", "Z"]}
        self.limit_locked = {axis: tk.BooleanVar(
            value=False) for axis in ["X", "Y", "Z"]}

        self._create_widgets()

        self.load_settings()
        self._load_default_programs()

        self.update_ui_state()
        self.update_position_labels()
        self._send_speed_to_arduino()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _center_window(self, width, height):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    def _degrees_to_pulses(self, degrees):
        return round(degrees * self.DEG_TO_PULSE_FACTOR)

    def _pulses_to_degrees(self, pulses):
        return pulses / self.DEG_TO_PULSE_FACTOR

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1, minsize=300)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)

        connection_frame = customtkinter.CTkFrame(self, height=70)
        connection_frame.grid(row=0, column=0, columnspan=2,
                              padx=10, pady=10, sticky="ew")
        widgets.create_connection_widgets(connection_frame, self)

        left_frame = customtkinter.CTkFrame(self, width=300)
        left_frame.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="ns")
        widgets.create_manual_control_widgets(left_frame, self)

        right_frame = customtkinter.CTkFrame(self)
        right_frame.grid(row=1, column=1, padx=(5, 10), pady=5, sticky="nsew")

        self.tab_view = customtkinter.CTkTabview(right_frame)
        self.tab_view.pack(expand=True, fill="both", padx=5, pady=5)

        self.program_tab = self.tab_view.add("Program")
        self.programs_list_tab = self.tab_view.add("Saved Programs")
        self.settings_tab = self.tab_view.add("Settings")

        self.program_tab.grid_columnconfigure(0, weight=1)
        self.program_tab.grid_rowconfigure(1, weight=1)
        self.programs_list_tab.grid_columnconfigure(0, weight=1)
        self.programs_list_tab.grid_rowconfigure(1, weight=1)
        self.settings_tab.grid_columnconfigure(0, weight=1)
        self.settings_tab.grid_rowconfigure(0, weight=0)
        self.settings_tab.grid_rowconfigure(1, weight=1)
        self.settings_tab.grid_rowconfigure(2, weight=0)

        widgets.create_program_widgets(self.program_tab, self)
        widgets.create_programs_tab_widgets(self.programs_list_tab, self)
        widgets.create_settings_widgets(self.settings_tab, self)

        self.status_label = customtkinter.CTkLabel(
            self, text="Not connected.", height=30, fg_color=("gray81", "gray20"), corner_radius=6)
        self.status_label.grid(row=2, column=0, columnspan=2,
                               padx=10, pady=(5, 10), sticky="ew")

    def _reset_machine_state(self, except_homing=False):
        self.is_running_program = False
        self.is_returning_home = False
        if not except_homing:
            self.is_homing = False
        self.program_index = 0
        self.update_status(
            "Trạng thái máy đã được reset. Sẵn sàng nhận lệnh mới.")
        self.update_program_status_label()

    def refresh_ports(self):
        ports = self.controller.get_serial_ports()
        self.port_combobox.configure(values=ports)
        if ports:
            self.port_combobox.set(ports[0])
        else:
            self.port_combobox.set("")

    def toggle_connection(self):
        if self.controller.is_connected:
            self.controller.disconnect()
            self.update_status("Đã ngắt kết nối.")
        else:
            port = self.port_combobox.get()
            if not port:
                messagebox.showerror("Lỗi", "Vui lòng chọn một cổng COM.")
                return
            self.update_status(f"Đang kết nối tới {port}...")
            success, message = self.controller.connect(port)
            if success:
                self.update_status(message)
                self.last_used_port.set(port)
                self._send_speed_to_arduino()
            else:
                self.update_status(f"Lỗi kết nối: {message}")
        self.update_ui_state()

    def start_homing(self):
        self._reset_machine_state()
        self.is_homing = True
        self.update_ui_state()
        self.controller.send_command("H", self._homing_callback)

    def _homing_callback(self, success, response):
        self.is_homing = False
        if success and "complete" in response:
            self.is_homed = True
            self.current_position = {"X": 0.0, "Y": 0.0, "Z": 0.0}
            self.update_status("Homing hoàn tất. Máy đã ở vị trí gốc.")
        elif "stopped" in response:
            self.update_status("Homing đã bị dừng bởi người dùng.")
        else:
            self.is_homed = False
            self.update_status("Homing thất bại.")
        self.update_ui_state()
        self.update_position_labels()

    def stop_machine(self):
        self._reset_machine_state()
        self.controller.send_interrupt_command()
        self.update_status("LỆNH DỪNG KHẨN CẤP ĐÃ ĐƯỢC GỬI!")
        self.update_ui_state()

    def toggle_motor_power(self):
        self.motor_power_on = not self.motor_power_on
        command = "E1" if self.motor_power_on else "E0"
        self.controller.send_command(command)
        self.update_ui_state()

    def toggle_move_mode(self):
        if self.move_mode.get() == "COORDINATE":
            self.move_mode.set("SEQUENTIAL")
        else:
            self.move_mode.set("COORDINATE")
        self.update_ui_state()

    _speed_send_timer = None

    def _send_speed_to_arduino(self):
        if not self.controller.is_connected:
            return

        current_percent = self.speed_percentage_var.get()
        target_speed_pps = self.BASE_MOTOR_SPEED_PPS * \
            (current_percent / 100.0)

        if target_speed_pps > 0:
            delay_us = int(1_000_000 / target_speed_pps)
        else:
            delay_us = 1_000_000

        if not self.controller.command_lock.locked():
            self.controller.send_command(f"S{delay_us}")
            self.update_status(
                f"Đã đặt tốc độ: {current_percent}% ({delay_us}µs).")
        else:
            self.update_status(
                "Máy đang bận, không thể thay đổi tốc độ ngay lập tức.")

    def _schedule_send_speed(self):
        if self._speed_send_timer:
            self.after_cancel(self._speed_send_timer)

        self._speed_send_timer = self.after(50, self._send_speed_to_arduino)

    def increase_speed(self):
        current_percent = self.speed_percentage_var.get()
        new_percent = min(current_percent +
                          self.SPEED_STEP_PERCENT, self.MAX_SPEED_PERCENT)
        self.speed_percentage_var.set(new_percent)
        self.speed_percentage_label.configure(
            text=f"Current Speed: {new_percent}%")
        self._schedule_send_speed()

    def decrease_speed(self):
        current_percent = self.speed_percentage_var.get()
        new_percent = max(current_percent -
                          self.SPEED_STEP_PERCENT, self.MIN_SPEED_PERCENT)
        self.speed_percentage_var.set(new_percent)
        self.speed_percentage_label.configure(
            text=f"Current Speed: {new_percent}%")
        self._schedule_send_speed()

    def jog_axis(self, axis, direction):
        if not self.controller.is_connected or self.is_homing or self.is_running_program or self.is_returning_home:
            self.update_status("Máy đang bận hoặc chưa kết nối/homed.")
            return

        self._reset_machine_state()

        jog_angle = self.JOG_BUTTON_ANGLE * direction

        target_pos_deg = self.current_position[axis] + jog_angle
        if not self._check_soft_limit(axis, target_pos_deg):
            self.update_status(
                f"Dừng di chuyển do chạm giới hạn mềm tại {axis}={self.current_position[axis]:.2f}°.")
            messagebox.showwarning(
                "Soft Limit", f"Di chuyển tới {axis}={target_pos_deg:.2f}° sẽ vượt qua giới hạn mềm.")
            return

        steps_to_send = self._degrees_to_pulses(jog_angle)
        command = f"{axis}{steps_to_send}"
        self.last_command_sent = command
        self.controller.send_command(
            command, callback=lambda s, r: self._jog_single_command_callback(s, r, axis, jog_angle))

    def _jog_single_command_callback(self, success, response, axis_moved, angle_moved):
        """Callback cho một lệnh jog đơn lẻ (từ nút)."""
        if success:
            self.current_position[axis_moved] += angle_moved
            self.update_position_labels()
            self.update_status(f"Jog {axis_moved} hoàn tất.")
        else:
            self.update_status(f"Lỗi jog: {response}")

    def coordinate_move(self):
        self._reset_machine_state()
        try:
            target_deg = {axis: float(self.target_coord_entry[axis].get()) for axis in [
                "X", "Y", "Z"]}
            command_or_queue = self._create_move_command(target_deg)

            if not command_or_queue:
                self.update_status(
                    "Vị trí đích trùng với vị trí hiện tại hoặc vượt giới hạn.")
                return

            if isinstance(command_or_queue, str):  # COORDINATE mode
                self.last_command_sent = command_or_queue
                self.controller.send_command(
                    command_or_queue, callback=lambda s, r: self._handle_move_command_completion(s, r, target_deg))
            else:  # SEQUENTIAL mode, command_or_queue là dictionary các bước
                sequential_commands_queue = []
                axes_order = ["X", "Y", "Z"]
                for axis in axes_order:
                    steps = command_or_queue[axis]
                    if steps != 0:
                        current_axis_target_pos_deg = self.current_position[axis] + self._pulses_to_degrees(
                            steps)
                        sequential_commands_queue.append(
                            (axis, steps, current_axis_target_pos_deg))

                if sequential_commands_queue:
                    self._handle_move_command_completion(
                        True, "Starting sequential move", target_deg, sequential_commands_queue)
                else:
                    self.update_status("Không có di chuyển cần thiết.")

        except ValueError:
            messagebox.showerror(
                "Lỗi", "Vui lòng nhập giá trị số hợp lệ cho góc (độ).")

    def return_to_home(self):
        self._reset_machine_state()
        self.is_returning_home = True
        target_deg = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        command_or_queue = self._create_move_command(target_deg)

        if not command_or_queue:
            self.update_status("Máy đã ở vị trí gốc.")
            self.is_returning_home = False
            return

        if isinstance(command_or_queue, str):  # COORDINATE mode
            self.last_command_sent = command_or_queue
            self.controller.send_command(
                command_or_queue, callback=lambda s, r: self._handle_move_command_completion(s, r, target_deg))
        else:  # SEQUENTIAL mode
            sequential_commands_queue = []
            axes_order = ["X", "Y", "Z"]
            for axis in axes_order:
                steps = command_or_queue[axis]
                if steps != 0:
                    current_axis_target_pos_deg = self.current_position[axis] + self._pulses_to_degrees(
                        steps)
                    sequential_commands_queue.append(
                        (axis, steps, current_axis_target_pos_deg))

            if sequential_commands_queue:
                self._handle_move_command_completion(
                    True, "Starting sequential move", target_deg, sequential_commands_queue)
            else:
                self.update_status("Không có di chuyển cần thiết.")
                self.is_returning_home = False  # Reset cờ nếu không có di chuyển

    def _create_move_command(self, target_pos_deg):
        angle_diff_x = target_pos_deg["X"] - self.current_position["X"]
        angle_diff_y = target_pos_deg["Y"] - self.current_position["Y"]
        angle_diff_z = target_pos_deg["Z"] - self.current_position["Z"]

        steps_x = self._degrees_to_pulses(angle_diff_x)
        steps_y = self._degrees_to_pulses(angle_diff_y)
        steps_z = self._degrees_to_pulses(angle_diff_z)

        if not self._check_soft_limit("X", target_pos_deg["X"]) or \
           not self._check_soft_limit("Y", target_pos_deg["Y"]) or \
           not self._check_soft_limit("Z", target_pos_deg["Z"]):
            messagebox.showwarning(
                "Soft Limit", "Di chuyển sẽ vượt qua giới hạn mềm đã đặt.")
            return None

        if steps_x == 0 and steps_y == 0 and steps_z == 0:
            return None

        if self.move_mode.get() == "COORDINATE":
            command = "M"
            if steps_x != 0:
                command += f" X{steps_x}"
            if steps_y != 0:
                command += f" Y{steps_y}"
            if steps_z != 0:
                command += f" Z{steps_z}"
            return command
        else:  # SEQUENTIAL Mode
            return {"X": steps_x, "Y": steps_y, "Z": steps_z}

    def _handle_move_command_completion(self, success, response, original_target_pos_deg, sequential_commands_queue=None):
        if success:
            if sequential_commands_queue and len(sequential_commands_queue) > 0:
                next_command_tuple = sequential_commands_queue.pop(0)
                axis_to_move = next_command_tuple[0]
                steps_to_move = next_command_tuple[1]
                current_axis_target_pos_deg = next_command_tuple[2]

                self.current_position[axis_to_move] = current_axis_target_pos_deg
                self.update_position_labels()

                self.update_status(f"Di chuyển trục {axis_to_move}...")
                self.last_command_sent = f"{axis_to_move}{steps_to_move}"
                self.controller.send_command(self.last_command_sent,
                                             callback=lambda s, r: self._handle_move_command_completion(s, r, original_target_pos_deg, sequential_commands_queue))
            elif sequential_commands_queue is not None and len(sequential_commands_queue) == 0:
                self.current_position = original_target_pos_deg.copy()
                self.update_status(
                    f"Di chuyển tới {original_target_pos_deg} hoàn tất.")
                self.is_returning_home = False
                self.update_ui_state()
                self.update_position_labels()
            else:
                self.current_position = original_target_pos_deg.copy()
                self.update_status(
                    f"Di chuyển tới {original_target_pos_deg} hoàn tất.")
                self.is_returning_home = False
                self.update_ui_state()
                self.update_position_labels()

        else:  # Lệnh thất bại
            self.update_status(f"Di chuyển thất bại: {response}")
            self.is_returning_home = False
            self.update_ui_state()
            if self.is_running_program:
                self.is_running_program = False
                self.update_program_status_label(
                    f"Lỗi ở bước {self.program_index + 1}. Chương trình đã dừng.")
                messagebox.showerror(
                    "Lỗi chương trình", f"Di chuyển tới điểm {self.program_index + 1} thất bại: {response}")

    def add_waypoint(self, name=None, pos=None, wp_type="position", duration_ms=0):
        insert_index = len(self.waypoints)
        if self.selected_waypoint_index is not None:
            insert_index = self.selected_waypoint_index + 1

        if wp_type == "position":
            if pos is None:
                pos = self.current_position.copy()
            pos = {axis: float(val) for axis, val in pos.items()}
            if name is None:
                name = f"Waypoint {insert_index + 1}"
            self.waypoints.insert(
                insert_index, {"name": name, "pos": pos, "type": "position"})
        elif wp_type == "delay":
            if name is None:
                name = f"Delay {duration_ms / 1000}s"
            self.waypoints.insert(
                insert_index, {"name": name, "type": "delay", "duration_ms": duration_ms})

        self.selected_waypoint_index = insert_index
        self._redraw_waypoints_list()

    def add_home_waypoint(self):
        self.add_waypoint("Home", {"X": 0.0, "Y": 0.0, "Z": 0.0})

    def add_manual_waypoint(self):
        try:
            pos_deg = {axis: float(self.manual_pos_entry[axis].get()) for axis in [
                "X", "Y", "Z"]}
            self.add_waypoint(
                f"Manual {pos_deg['X']:.1f},{pos_deg['Y']:.1f},{pos_deg['Z']:.1f}", pos_deg)
        except ValueError:
            messagebox.showerror(
                "Lỗi", "Vui lòng nhập giá trị số hợp lệ cho góc (độ).")

    def add_delay_waypoint(self):
        delay_ms = simpledialog.askinteger(
            "Add Delay (ms)", "Enter delay time in milliseconds (e.g., 500 for 0.5s):", parent=self, minvalue=1)
        if delay_ms is not None:
            self.add_waypoint(wp_type="delay", duration_ms=delay_ms)

    def duplicate_selected_waypoint(self):
        if self.selected_waypoint_index is None:
            messagebox.showinfo(
                "Thông báo", "Vui lòng chọn một điểm dừng để nhân bản.")
            return

        original_wp = self.waypoints[self.selected_waypoint_index]

        duplicated_wp = json.loads(json.dumps(original_wp))

        if duplicated_wp.get("type", "position") == "position":
            duplicated_wp["name"] = f"{original_wp['name']} (Copy)"
        else:
            duplicated_wp["name"] = f"{original_wp['name']} (Copy)"

        insert_index = self.selected_waypoint_index + 1
        self.waypoints.insert(insert_index, duplicated_wp)
        self.selected_waypoint_index = insert_index
        self._redraw_waypoints_list()
        self.update_status(f"Đã nhân bản '{original_wp['name']}'.")

    def delete_waypoint(self):
        if self.selected_waypoint_index is not None:
            del self.waypoints[self.selected_waypoint_index]
            self.selected_waypoint_index = None
            self._redraw_waypoints_list()

    def clear_waypoints(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa tất cả các điểm dừng?"):
            self.waypoints = []
            self.selected_waypoint_index = None
            self._redraw_waypoints_list()

    def move_waypoint_up(self):
        if self.selected_waypoint_index is not None and self.selected_waypoint_index > 0:
            idx = self.selected_waypoint_index
            self.waypoints[idx], self.waypoints[idx -
                                                1] = self.waypoints[idx-1], self.waypoints[idx]
            self.selected_waypoint_index -= 1
            self._redraw_waypoints_list()

    def move_waypoint_down(self):
        if self.selected_waypoint_index is not None and self.selected_waypoint_index < len(self.waypoints) - 1:
            idx = self.selected_waypoint_index
            self.waypoints[idx], self.waypoints[idx +
                                                1] = self.waypoints[idx+1], self.waypoints[idx]
            self.selected_waypoint_index += 1
            self._redraw_waypoints_list()

    def edit_selected_waypoint(self):
        if self.selected_waypoint_index is None:
            messagebox.showinfo(
                "Thông báo", "Vui lòng chọn một điểm dừng để chỉnh sửa.")
            return
        waypoint_data = self.waypoints[self.selected_waypoint_index]

        if waypoint_data.get("type", "position") == "delay":
            dialog = DelayEditDialog(self, waypoint_data.get("duration_ms", 0))
            if dialog.result:
                self.waypoints[self.selected_waypoint_index] = dialog.result
                self._redraw_waypoints_list()
        else:
            current_pos_float = {axis: float(
                waypoint_data["pos"][axis]) for axis in waypoint_data["pos"]}
            temp_waypoint_data_for_dialog = waypoint_data.copy()
            temp_waypoint_data_for_dialog["pos"] = current_pos_float

            dialog = EditWaypointDialog(self, temp_waypoint_data_for_dialog)
            if dialog.result:
                self.waypoints[self.selected_waypoint_index] = dialog.result
                self.waypoints[self.selected_waypoint_index]['type'] = 'position'
                self._redraw_waypoints_list()

    def go_to_selected_waypoint(self):
        if self.selected_waypoint_index is None:
            return
        waypoint_data = self.waypoints[self.selected_waypoint_index]
        if waypoint_data.get("type", "position") == "delay":
            return
        self._reset_machine_state()
        target_deg = waypoint_data['pos']

        command_or_queue = self._create_move_command(target_deg)
        if not command_or_queue:
            self.update_status("Không có di chuyển hoặc vượt giới hạn.")
            return

        if isinstance(command_or_queue, str):
            self.last_command_sent = command_or_queue
            self.controller.send_command(
                command_or_queue, callback=lambda s, r: self._handle_move_command_completion(s, r, target_deg))
        else:  # SEQUENTIAL mode
            sequential_commands_queue = []
            axes_order = ["X", "Y", "Z"]
            for axis in axes_order:
                steps = command_or_queue[axis]
                if steps != 0:
                    current_axis_target_pos_deg = self.current_position[axis] + self._pulses_to_degrees(
                        steps)
                    sequential_commands_queue.append(
                        (axis, steps, current_axis_target_pos_deg))

            if sequential_commands_queue:
                self._handle_move_command_completion(
                    True, "Starting sequential move", target_deg, sequential_commands_queue)
            else:
                self.update_status("Không có di chuyển cần thiết.")

    def _redraw_waypoints_list(self):
        for widget in self.waypoint_scroll_frame.winfo_children():
            widget.destroy()
        for i, wp in enumerate(self.waypoints):
            if wp.get("type", "position") == "position":
                pos_str = f"X:{wp['pos']['X']:.2f}° Y:{wp['pos']['Y']:.2f}° Z:{wp['pos']['Z']:.2f}°"
                text = f"{i+1}. {wp['name']} - ({pos_str})"
            else:
                text = f"{i+1}. {wp['name']} ({wp.get('duration_ms', 0):.0f}ms)"

            frame = customtkinter.CTkFrame(self.waypoint_scroll_frame)
            frame.pack(fill="x", padx=5, pady=2)
            label = customtkinter.CTkLabel(frame, text=text)
            label.pack(side="left", padx=5, pady=5)
            label.bind("<Button-1>", lambda e,
                       index=i: self._select_waypoint(index))
            frame.bind("<Button-1>", lambda e,
                       index=i: self._select_waypoint(index))
            if i == self.selected_waypoint_index:
                frame.configure(fg_color=("lightblue", "darkblue"))

    def _select_waypoint(self, index):
        self.selected_waypoint_index = index
        self._redraw_waypoints_list()

    def run_program(self):
        if self.is_running_program:
            self.is_running_program = False
            self.update_program_status_label(
                "Chương trình đã bị người dùng dừng.")
            self.update_ui_state()
            return
        if not self.waypoints:
            messagebox.showinfo("Thông báo", "Danh sách điểm dừng trống.")
            return
        self._reset_machine_state()
        self.is_running_program = True
        self.program_index = 0
        self.update_ui_state()
        self._execute_next_program_step()

    def _execute_next_program_step(self):
        if not self.is_running_program:
            return
        if self.program_index >= len(self.waypoints):
            if self.repeat_program_var.get():
                self.program_index = 0
            else:
                self.is_running_program = False
                self.update_program_status_label("Chương trình hoàn tất.")
                self.update_ui_state()
                return

        target_wp = self.waypoints[self.program_index]

        if target_wp.get("type") == "delay":
            duration_ms = target_wp.get("duration_ms", 1000)
            self.update_program_status_label(
                f"Delaying for {duration_ms / 1000.0:.1f}s ({duration_ms}ms)...")
            self.program_index += 1
            self.after(duration_ms, self._execute_next_program_step)
            return

        self.update_program_status_label(
            f"Di chuyển tới điểm {self.program_index + 1}: {target_wp['name']}")
        command_or_queue = self._create_move_command(target_wp['pos'])
        if not command_or_queue:
            self.program_index += 1
            self.after(10, self._execute_next_program_step)
            return

        if isinstance(command_or_queue, str):
            self.last_command_sent = command_or_queue
            self.controller.send_command(command_or_queue, callback=lambda s,
                                         r: self._program_step_callback_for_move(s, r, target_wp['pos']))
        else:  # SEQUENTIAL mode
            sequential_commands_queue = []
            axes_order = ["X", "Y", "Z"]
            for axis in axes_order:
                steps = command_or_queue[axis]
                if steps != 0:
                    current_axis_target_pos_deg = self.current_position[axis] + self._pulses_to_degrees(
                        steps)
                    sequential_commands_queue.append(
                        (axis, steps, current_axis_target_pos_deg))

            if sequential_commands_queue:
                self._program_step_callback_for_move(
                    True, "Starting sequential move for program", target_wp['pos'], sequential_commands_queue)
            else:
                self.program_index += 1
                self.after(10, self._execute_next_program_step)

    def _program_step_callback_for_move(self, success, response, original_target_pos_deg, sequential_commands_queue=None):
        if not self.is_running_program:
            self.update_program_status_label("Chương trình đã dừng.")
            self.update_ui_state()
            return

        if success:
            if sequential_commands_queue and len(sequential_commands_queue) > 0:
                next_command_tuple = sequential_commands_queue.pop(0)
                axis_to_move = next_command_tuple[0]
                steps_to_move = next_command_tuple[1]
                current_axis_target_pos_deg = next_command_tuple[2]

                self.current_position[axis_to_move] = current_axis_target_pos_deg
                self.update_position_labels()

                self.update_status(f"Di chuyển trục {axis_to_move}...")
                self.last_command_sent = f"{axis_to_move}{steps_to_move}"
                self.controller.send_command(self.last_command_sent,
                                             callback=lambda s, r: self._program_step_callback_for_move(s, r, original_target_pos_deg, sequential_commands_queue))
            elif sequential_commands_queue is not None and len(sequential_commands_queue) == 0:
                self.current_position = original_target_pos_deg.copy()
                self.update_position_labels()
                self.program_index += 1
                self.after(10, self._execute_next_program_step)
            else:
                self.current_position = original_target_pos_deg.copy()
                self.update_position_labels()
                self.program_index += 1
                self.after(10, self._execute_next_program_step)

        else:  # Lệnh di chuyển thất bại
            self.is_running_program = False
            self.update_program_status_label(
                f"Lỗi ở bước {self.program_index + 1}. Chương trình đã dừng.")
            messagebox.showerror(
                "Lỗi chương trình", f"Di chuyển tới điểm {self.program_index + 1} thất bại: {response}")
            self.update_ui_state()

    def _convert_old_program_data(self, program_data):
        if not program_data or "waypoints" not in program_data or not program_data["waypoints"]:
            return program_data, False

        converted = False
        new_waypoints = []
        for wp in program_data["waypoints"]:
            if wp.get("type") == "delay":
                new_waypoints.append(wp)
            elif "pos" in wp:
                is_old_format_waypoint = False
                for axis in ["X", "Y", "Z"]:
                    val = wp["pos"].get(axis)
                    if isinstance(val, int) and abs(val) > 360:
                        is_old_format_waypoint = True
                        break

                if is_old_format_waypoint:
                    converted = True
                    new_pos = {
                        "X": self._pulses_to_degrees(wp["pos"]["X"]),
                        "Y": self._pulses_to_degrees(wp["pos"]["Y"]),
                        "Z": self._pulses_to_degrees(wp["pos"]["Z"]),
                    }
                    new_waypoints.append(
                        {"name": wp["name"], "pos": new_pos, "type": "position"})
                else:
                    if isinstance(wp["pos"].get("X"), (int, float)):
                        wp["pos"] = {axis: float(val)
                                     for axis, val in wp["pos"].items()}
                    if "type" not in wp:
                        wp["type"] = "position"
                    new_waypoints.append(wp)
            else:
                if "type" not in wp:
                    wp["type"] = "position"
                new_waypoints.append(wp)

        program_data["waypoints"] = new_waypoints
        return program_data, converted

    def _load_default_programs(self):
        program_dir = "programs"
        if not os.path.isdir(program_dir):
            return
        converted_any_program_from_files = False
        for filename in os.listdir(program_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(program_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)

                    data, converted = self._convert_old_program_data(data)
                    if converted:
                        messagebox.showinfo(
                            "Chuyển đổi dữ liệu", f"File chương trình cũ '{filename}' đã được tự động chuyển đổi từ 'số bước' sang 'độ'.")
                        converted_any_program_from_files = True

                    program_name = os.path.splitext(filename)[0]
                    self.programs[program_name] = {"waypoints": data.get("waypoints", []), "created": data.get(
                        "created", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}
                except Exception as e:
                    print(
                        f"Lỗi khi tải chương trình mặc định '{filename}': {e}")
        if converted_any_program_from_files:
            self.save_settings()

        self._redraw_programs_list()

    def save_program(self):
        if not self.waypoints:
            messagebox.showinfo("Thông báo", "Không có điểm dừng nào để lưu.")
            return
        program_name = simpledialog.askstring(
            "Lưu chương trình", "Nhập tên chương trình:", parent=self)
        if program_name:
            if program_name in self.programs and not messagebox.askyesno("Ghi đè", f"Chương trình '{program_name}' đã tồn tại. Bạn có muốn ghi đè?"):
                return
            self.programs[program_name] = {"waypoints": [wp.copy(
            ) for wp in self.waypoints], "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            self._redraw_programs_list()
            self.save_settings()

    def load_selected_program(self):
        if self.selected_program_name is None:
            messagebox.showinfo(
                "Thông báo", "Vui lòng chọn một chương trình để tải.")
            return
        if self.waypoints and not messagebox.askyesno("Xác nhận", "Thao tác này sẽ ghi đè danh sách điểm dừng hiện tại. Tiếp tục?"):
            return
        loaded_waypoints = []
        for wp in self.programs[self.selected_program_name]["waypoints"]:
            new_wp = wp.copy()
            if new_wp.get("type", "position") == "position":
                new_wp["pos"] = {axis: float(val)
                                 for axis, val in new_wp["pos"].items()}
            loaded_waypoints.append(new_wp)

        self.waypoints = loaded_waypoints
        self.selected_waypoint_index = None
        self._redraw_waypoints_list()
        self.tab_view.set("Program")
        self.update_status(
            f"Đã tải chương trình '{self.selected_program_name}'.")

    def delete_program(self):
        if self.selected_program_name is not None and messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa chương trình '{self.selected_program_name}'?"):
            del self.programs[self.selected_program_name]
            self.selected_program_name = None
            self._redraw_programs_list()
            self.save_settings()

    def import_program(self):
        filepath = filedialog.askopenfilename(title="Import Program", filetypes=[(
            "JSON files", "*.json"), ("All files", "*.*")], defaultextension=".json")
        if not filepath:
            return
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            data, converted = self._convert_old_program_data(data)
            if converted:
                messagebox.showinfo(
                    "Chuyển đổi dữ liệu", "File chương trình cũ đã được tự động chuyển đổi từ 'số bước' sang 'độ'.")
            if "waypoints" in data and isinstance(data["waypoints"], list):
                for i, wp in enumerate(data["waypoints"]):
                    if wp.get("type", "position") == "position" and isinstance(wp["pos"].get("X"), (int, float)):
                        wp["pos"] = {axis: float(val)
                                     for axis, val in wp["pos"].items()}
                    if "type" not in wp:
                        wp["type"] = "position"

                program_name = os.path.splitext(os.path.basename(filepath))[0]
                if program_name in self.programs and not messagebox.askyesno("Ghi đè", f"Chương trình '{program_name}' đã tồn tại. Bạn có muốn ghi đè?"):
                    return
                self.programs[program_name] = {"waypoints": data["waypoints"], "created": data.get(
                    "created", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}
                self._redraw_programs_list()
                self.save_settings()
                self.update_status(f"Đã nhập chương trình từ {program_name}.")
            else:
                raise ValueError("Định dạng file không hợp lệ.")
        except Exception as e:
            messagebox.showerror(
                "Lỗi Import", f"Không thể nhập chương trình: {e}")

    def _redraw_programs_list(self):
        for widget in self.program_list_frame.winfo_children():
            widget.destroy()
        for name, data in self.programs.items():
            frame = customtkinter.CTkFrame(self.program_list_frame)
            frame.pack(fill="x", padx=5, pady=2)
            label = customtkinter.CTkLabel(
                frame, text=f"{name} (Tạo lúc: {data.get('created', 'N/A')})")
            label.pack(side="left", padx=5, pady=5)
            label.bind("<Button-1>", lambda e,
                       p_name=name: self._select_program(p_name))
            frame.bind("<Button-1>", lambda e,
                       p_name=name: self._select_program(p_name))
            if name == self.selected_program_name:
                frame.configure(fg_color=("lightblue", "darkblue"))

    def _select_program(self, name):
        self.selected_program_name = name
        self._redraw_programs_list()

    def _check_soft_limit(self, axis, target_pos_deg):
        limit_str = self.soft_limits[axis].get()
        if not limit_str:
            return True
        try:
            limit_val_deg = float(limit_str)
            if limit_val_deg > 0:
                return 0 <= target_pos_deg <= limit_val_deg
            else:
                return limit_val_deg <= target_pos_deg <= 0
        except ValueError:
            return True

    # CẬP NHẬT: Thêm lại đối số `axis` vào `toggle_limit_lock`
    def toggle_limit_lock(self, axis):
        is_locked = not self.limit_locked[axis].get()
        self.limit_locked[axis].set(is_locked)
        state = "disabled" if is_locked else "normal"
        self.limit_entries[axis].configure(state=state)
        text = "Unlock" if is_locked else "Lock"
        self.limit_lock_buttons[axis].configure(text=text)

    # CẬP NHẬT: Thêm lại đối số `self` vào `get_settings_path`
    def get_settings_path(self):
        return os.path.join(os.path.expanduser("~"), ".cnc_controller_settings.json")

    # CẬP NHẬT: Thêm lại `filepath=None` vào định nghĩa hàm
    def save_settings(self, filepath=None):
        if filepath is None:
            filepath = self.get_settings_path()
        settings = {
            "last_used_port": self.last_used_port.get(),
            "speed_percentage": self.speed_percentage_var.get(),
            "soft_limits": {axis: var.get() for axis, var in self.soft_limits.items()},
            "programs": self.programs,
        }
        try:
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=4)
            self.update_status("Đã lưu cài đặt thành công.")
        except Exception as e:
            messagebox.showerror("Lỗi lưu cài đặt", str(e))

    def load_settings(self, filepath=None):
        if filepath is None:
            filepath = self.get_settings_path()
        if not os.path.exists(filepath):
            return
        try:
            with open(filepath, 'r') as f:
                settings = json.load(f)
            self.last_used_port.set(settings.get("last_used_port", ""))
            self.speed_percentage_var.set(
                settings.get("speed_percentage", 100))
            loaded_limits = settings.get("soft_limits", {})
            for axis in ["X", "Y", "Z"]:
                val = loaded_limits.get(axis, "0.0")
                if isinstance(val, (int, float)):
                    self.soft_limits[axis].set(str(float(val)))
                else:
                    self.soft_limits[axis].set(val)

            loaded_programs = settings.get("programs", {})
            processed_programs = {}
            any_program_converted_in_settings = False
            for name, data in loaded_programs.items():
                processed_data, converted = self._convert_old_program_data(
                    data)
                if converted:
                    any_program_converted_in_settings = True
                if "waypoints" in processed_data:
                    for i, wp in enumerate(processed_data["waypoints"]):
                        if wp.get("type", "position") == "position" and isinstance(wp["pos"].get("X"), (int, float)):
                            wp["pos"] = {axis: float(val)
                                         for axis, val in wp["pos"].items()}
                        if "type" not in wp:
                            wp["type"] = "position"
                processed_programs[name] = processed_data
            self.programs = processed_programs

            if any_program_converted_in_settings:
                messagebox.showinfo(
                    "Chuyển đổi dữ liệu", "Một hoặc nhiều chương trình cũ từ cài đặt đã được tự động chuyển đổi từ 'số bước' sang 'độ'.")
                self.save_settings()

            self._redraw_programs_list()
            self.update_status("Đã tải cài đặt.")
        except Exception as e:
            print(f"Không thể tải cài đặt: {e}")

    def import_settings(self):  # Sửa lỗi chính tả self
        filepath = filedialog.askopenfilename(title="Import Settings", filetypes=[(
            "JSON files", "*.json"), ("All files", "*.*")], defaultextension=".json")
        if filepath:
            self.load_settings(filepath)
            self.update_ui_state()

    def update_ui_state(self):
        is_connected = self.controller.is_connected
        is_busy = self.is_homing or self.is_running_program or self.is_returning_home
        self.connect_button.configure(
            text="Disconnect" if is_connected else "Connect")
        self.motor_toggle_button.configure(text="Motor Power: ON" if self.motor_power_on else "Motor Power: OFF",
                                           fg_color="green" if self.motor_power_on else "gray50", state="normal" if is_connected else "disabled")
        self.move_mode_button.configure(
            text=f"Move Mode: {self.move_mode.get()}", state="normal" if is_connected and self.is_homed else "disabled")
        self.homing_button.configure(
            state="disabled" if is_busy or not is_connected else "normal")
        enable_manual = is_connected and self.is_homed and not is_busy
        self.return_home_button.configure(
            state="normal" if enable_manual else "disabled")
        self.coord_move_button.configure(
            state="normal" if enable_manual else "disabled")
        for child in self.program_tab.winfo_children():
            if isinstance(child, (customtkinter.CTkButton, customtkinter.CTkCheckBox)):
                child.configure(
                    state="normal" if enable_manual else "disabled")
        self.run_button.configure(text="STOP PROGRAM" if self.is_running_program else "RUN PROGRAM", fg_color=("#D32F2F", "#B71C1C") if self.is_running_program else (
            "#1F6AA5", "#144870"), hover_color=("#B71C1C", "#8B0000") if self.is_running_program else ("#144870", "#103957"))
        if is_connected and self.is_homed:
            self.run_button.configure(state="normal")
        else:
            self.run_button.configure(state="disabled")

    def update_position_labels(self):
        for axis, label in self.pos_labels.items():
            if self.is_homed:
                label.configure(text=f"{self.current_position[axis]:.2f}°")
            else:
                label.configure(text="N/A")

    def update_status(self, message):
        self.status_label.configure(text=message)
        print(message)

    def update_program_status_label(self, message="Program idle."):
        self.program_status_label.configure(text=message)

    def on_closing(self):
        self.save_settings()
        if self.controller.is_connected:
            self.controller.disconnect()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
