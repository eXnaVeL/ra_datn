# gui/widgets.py OK

import customtkinter
import tkinter as tk


def create_connection_widgets(parent, app):
    parent.grid_columnconfigure(6, weight=1)

    customtkinter.CTkLabel(parent, text="Port:").grid(
        row=0, column=0, padx=(10, 5), pady=10
    )
    app.port_combobox = customtkinter.CTkComboBox(
        parent, values=app.controller.get_serial_ports(), variable=app.last_used_port
    )
    app.port_combobox.grid(row=0, column=1, pady=10)

    customtkinter.CTkButton(
        parent, text="Refresh", command=app.refresh_ports, width=80
    ).grid(row=0, column=2, padx=5, pady=10)

    app.connect_button = customtkinter.CTkButton(
        parent, text="Connect", command=app.toggle_connection, width=100
    )
    app.connect_button.grid(row=0, column=3, padx=5, pady=10)

    app.motor_toggle_button = customtkinter.CTkButton(
        parent, text="", command=app.toggle_motor_power, width=140
    )
    app.motor_toggle_button.grid(row=0, column=4, padx=10, pady=10)

    app.move_mode_button = customtkinter.CTkButton(
        parent, text="", command=app.toggle_move_mode, width=160
    )
    app.move_mode_button.grid(row=0, column=5, padx=10, pady=10, sticky="e")

    app.homing_button = customtkinter.CTkButton(
        parent, text="Machine Homing", command=app.start_homing
    )
    app.homing_button.grid(row=0, column=6, padx=10, pady=10, sticky="e")

    app.stop_button = customtkinter.CTkButton(
        parent,
        text="STOP MACHINE",
        command=app.stop_machine,
        fg_color="#D32F2F",
        hover_color="#B71C1C",
    )
    app.stop_button.grid(row=0, column=7, padx=10, pady=10)


def create_manual_control_widgets(parent, app):
    parent.pack_propagate(False)
    customtkinter.CTkLabel(
        parent, text="Manual Control", font=("Segoe UI", 16, "bold")
    ).pack(pady=10)

    pos_frame = customtkinter.CTkFrame(parent)
    pos_frame.pack(fill="x", pady=5, padx=10)
    customtkinter.CTkLabel(
        pos_frame,
        text="Machine Position (degrees from home)",
        font=("Segoe UI", 12, "bold"),
    ).pack(anchor="w")
    app.pos_labels = {}
    for axis in ["X", "Y", "Z"]:
        f = customtkinter.CTkFrame(pos_frame, fg_color="transparent")
        f.pack(fill="x", pady=2)
        customtkinter.CTkLabel(
            f, text=f"{axis}:", font=("Courier", 12, "bold"), width=20
        ).pack(side="left")
        app.pos_labels[axis] = customtkinter.CTkLabel(
            f, text="N/A", font=("Courier", 12), width=100, anchor="w"
        )
        app.pos_labels[axis].pack(side="left", padx=5)
    app.return_home_button = customtkinter.CTkButton(
        pos_frame, text="Return to Home (0,0,0)", command=app.return_to_home
    )
    app.return_home_button.pack(pady=10, fill="x")

    coord_move_frame = customtkinter.CTkFrame(parent)
    coord_move_frame.pack(fill="x", pady=5, padx=10)
    customtkinter.CTkLabel(
        coord_move_frame, text="Go to Absolute Angle (degrees)", font=("Segoe UI", 12, "bold")
    ).pack(anchor="w")
    entry_frame = customtkinter.CTkFrame(
        coord_move_frame, fg_color="transparent")
    entry_frame.pack(fill="x")
    # Gán các widget Entry vào app.target_coord_entry_widgets
    for i, axis in enumerate(["X", "Y", "Z"]):
        customtkinter.CTkLabel(entry_frame, text=f"{axis}:").pack(
            side="left", padx=(10, 2), pady=5
        )
        entry_widget = customtkinter.CTkEntry(
            entry_frame, textvariable=app.target_coord_entry[axis], width=70
        )
        entry_widget.pack(side="left", padx=(0, 10))
        app.target_coord_entry_widgets[axis] = entry_widget  # Gán widget

    app.coord_move_button = customtkinter.CTkButton(
        coord_move_frame, text="MOVE", command=app.coordinate_move
    )
    app.coord_move_button.pack(fill="x", pady=5, padx=5)

    speed_frame = customtkinter.CTkFrame(parent, fg_color="transparent")
    speed_frame.pack(fill="x", pady=10, padx=10)
    customtkinter.CTkLabel(speed_frame, text="Speed Control").pack(anchor="w")

    app.speed_percentage_label = customtkinter.CTkLabel(
        speed_frame, text=f"Current Speed: {app.speed_percentage_var.get()}%"
    )
    app.speed_percentage_label.pack(anchor="w", padx=5, pady=(5, 0))

    speed_buttons_frame = customtkinter.CTkFrame(
        speed_frame, fg_color="transparent")
    speed_buttons_frame.pack(fill="x", padx=5, pady=5)
    speed_buttons_frame.grid_columnconfigure((0, 1, 2), weight=1)

    app.decrease_speed_button = customtkinter.CTkButton(  # Gán nút vào app
        speed_buttons_frame, text="-", command=app.decrease_speed, width=50
    )
    app.decrease_speed_button.grid(row=0, column=0, padx=(0, 5), sticky="w")

    customtkinter.CTkLabel(
        speed_buttons_frame, textvariable=app.speed_percentage_var, font=(
            "Segoe UI", 12, "bold")
    ).grid(row=0, column=1, sticky="ew")

    app.increase_speed_button = customtkinter.CTkButton(  # Gán nút vào app
        speed_buttons_frame, text="+", command=app.increase_speed, width=50
    )
    app.increase_speed_button.grid(row=0, column=2, padx=(5, 0), sticky="e")

    # CẬP NHẬT: Thay đổi layout nút jog để khớp chính xác với hình ảnh
    joystick_buttons_frame = customtkinter.CTkFrame(
        parent, fg_color="transparent")
    joystick_buttons_frame.pack(pady=10, padx=10)
    # 4 cột: 0 (X←), 1 (khoảng cách), 2 (Y↑/Y↓), 3 (Z↑/Z↓), 4 (X→)
    # Đặt weight để các cột giãn ra
    joystick_buttons_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
    joystick_buttons_frame.grid_rowconfigure((0, 1, 2), weight=1)  # 3 hàng

    # Nút Y↑ (Hàng 0, Cột 1)
    btn = customtkinter.CTkButton(
        joystick_buttons_frame, text="Y \u2191", command=lambda: app.jog_axis("Y", 1), width=60, height=40, font=("Segoe UI", 16)
    )
    btn.grid(row=0, column=1, pady=(0, 5), padx=(0, 5), sticky="e")
    app.jog_buttons['Y'][1] = btn  # Gán nút vào app

    # Nút Z↑ (Hàng 0, Cột 2)
    btn = customtkinter.CTkButton(
        joystick_buttons_frame, text="Z \u2191", command=lambda: app.jog_axis("Z", -1), width=60, height=40, font=("Segoe UI", 16)
    )
    btn.grid(row=0, column=2, pady=(0, 5), padx=(5, 0), sticky="w")
    app.jog_buttons['Z'][-1] = btn  # Gán nút vào app

    # Nút X← (Hàng 1, Cột 0)
    btn = customtkinter.CTkButton(
        joystick_buttons_frame, text="\u2190 X", command=lambda: app.jog_axis("X", -1), width=60, height=40, font=("Segoe UI", 16)
    )
    btn.grid(row=1, column=0, padx=(0, 5), sticky="e")
    app.jog_buttons['X'][-1] = btn  # Gán nút vào app

    # Nút X→ (Hàng 1, Cột 4) -- Cột cuối cùng
    btn = customtkinter.CTkButton(
        joystick_buttons_frame, text="X \u2192", command=lambda: app.jog_axis("X", 1), width=60, height=40, font=("Segoe UI", 16)
    )
    btn.grid(row=1, column=4, padx=(5, 0), sticky="w")
    app.jog_buttons['X'][1] = btn  # Gán nút vào app

    # Nút Y↓ (Hàng 2, Cột 1)
    btn = customtkinter.CTkButton(
        joystick_buttons_frame, text="Y \u2193", command=lambda: app.jog_axis("Y", -1), width=60, height=40, font=("Segoe UI", 16)
    )
    btn.grid(row=2, column=1, pady=(5, 0), padx=(0, 5), sticky="e")
    app.jog_buttons['Y'][-1] = btn  # Gán nút vào app

    # Nút Z↓ (Hàng 2, Cột 2)
    btn = customtkinter.CTkButton(
        joystick_buttons_frame, text="Z \u2193", command=lambda: app.jog_axis("Z", 1), width=60, height=40, font=("Segoe UI", 16)
    )
    btn.grid(row=2, column=2, pady=(5, 0), padx=(5, 0), sticky="w")
    app.jog_buttons['Z'][1] = btn  # Gán nút vào app


def create_program_widgets(parent, app):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    customtkinter.CTkLabel(
        parent, text="Position List (Waypoints)", font=("Segoe UI", 16, "bold")
    ).grid(row=0, column=0, pady=10)

    app.waypoint_scroll_frame = customtkinter.CTkScrollableFrame(parent)
    app.waypoint_scroll_frame.grid(
        row=1, column=0, padx=10, pady=5, sticky="nsew")

    wp_action_frame = customtkinter.CTkFrame(parent, fg_color="transparent")
    wp_action_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

    list_ops_frame = customtkinter.CTkFrame(wp_action_frame)
    list_ops_frame.pack(fill="x", pady=2)
    list_ops_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

    # Gán các nút vào app.
    app.save_current_pos_button = customtkinter.CTkButton(
        list_ops_frame, text="Save Current Pos", command=app.add_waypoint
    )
    app.save_current_pos_button.grid(
        row=0, column=0, padx=2, pady=2, sticky="ew")

    app.add_home_waypoint_button = customtkinter.CTkButton(
        list_ops_frame, text="Add Home (0,0,0)", command=app.add_home_waypoint
    )
    app.add_home_waypoint_button.grid(
        row=0, column=1, padx=2, pady=2, sticky="ew")

    app.add_delay_waypoint_button = customtkinter.CTkButton(
        list_ops_frame, text="Add Delay", command=app.add_delay_waypoint
    )
    app.add_delay_waypoint_button.grid(
        row=0, column=2, padx=2, pady=2, sticky="ew")

    app.delete_waypoint_button = customtkinter.CTkButton(
        list_ops_frame, text="Delete", command=app.delete_waypoint
    )
    app.delete_waypoint_button.grid(
        row=0, column=3, padx=2, pady=2, sticky="ew")

    app.clear_waypoints_button = customtkinter.CTkButton(
        list_ops_frame, text="Clear All", command=app.clear_waypoints
    )
    app.clear_waypoints_button.grid(
        row=0, column=4, padx=2, pady=2, sticky="ew")

    edit_ops_frame = customtkinter.CTkFrame(wp_action_frame)
    edit_ops_frame.pack(fill="x", pady=2)
    edit_ops_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

    app.move_waypoint_up_button = customtkinter.CTkButton(
        edit_ops_frame, text="Move Up ↑", command=app.move_waypoint_up
    )
    app.move_waypoint_up_button.grid(
        row=0, column=0, padx=2, pady=2, sticky="ew")

    app.move_waypoint_down_button = customtkinter.CTkButton(
        edit_ops_frame, text="Move Down ↓", command=app.move_waypoint_down
    )
    app.move_waypoint_down_button.grid(
        row=0, column=1, padx=2, pady=2, sticky="ew")

    app.edit_selected_waypoint_button = customtkinter.CTkButton(
        edit_ops_frame, text="Edit Selected", command=app.edit_selected_waypoint
    )
    app.edit_selected_waypoint_button.grid(
        row=0, column=2, padx=2, pady=2, sticky="ew")

    app.duplicate_selected_waypoint_button = customtkinter.CTkButton(
        edit_ops_frame, text="Duplicate Selected", command=app.duplicate_selected_waypoint
    )
    app.duplicate_selected_waypoint_button.grid(
        row=0, column=3, padx=2, pady=2, sticky="ew")

    app.go_to_selected_waypoint_button = customtkinter.CTkButton(
        edit_ops_frame, text="Go to Selected", command=app.go_to_selected_waypoint
    )
    app.go_to_selected_waypoint_button.grid(
        row=0, column=4, padx=2, pady=2, sticky="ew")

    manual_add_frame = customtkinter.CTkFrame(parent)
    manual_add_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
    manual_add_frame.grid_columnconfigure(6, weight=1)

    for i, axis in enumerate(["X", "Y", "Z"]):
        customtkinter.CTkLabel(manual_add_frame, text=f"{axis}:").grid(
            row=0, column=0 + i*2, padx=(10, 2), pady=10
        )
        entry_widget = customtkinter.CTkEntry(  # Tạo widget
            manual_add_frame, textvariable=app.manual_pos_entry[axis], width=70
        )
        entry_widget.grid(row=0, column=1 + i*2)
        app.manual_pos_entry_widgets[axis] = entry_widget  # Gán widget

    app.add_manual_waypoint_button = customtkinter.CTkButton(
        manual_add_frame, text="Add Manual", command=app.add_manual_waypoint
    )
    app.add_manual_waypoint_button.grid(
        row=0, column=6, padx=10, pady=10, sticky="ew")

    program_ctrl_frame = customtkinter.CTkFrame(parent)
    program_ctrl_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
    program_ctrl_frame.grid_columnconfigure(0, weight=2)
    program_ctrl_frame.grid_columnconfigure(1, weight=1)

    app.run_button = customtkinter.CTkButton(
        program_ctrl_frame,
        text="RUN PROGRAM",
        command=app.run_program,
        height=40,
        font=("Segoe UI", 14, "bold"),
    )
    app.run_button.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

    app.repeat_checkbox = customtkinter.CTkCheckBox(
        program_ctrl_frame, text="Lặp lại chương trình", variable=app.repeat_program_var
    )
    app.repeat_checkbox.grid(row=0, column=1, sticky="w", padx=10)

    app.program_status_label = customtkinter.CTkLabel(
        parent,
        text="Program idle.",
        height=40,
        fg_color=("gray81", "gray20"),
        corner_radius=6,
    )
    app.program_status_label.grid(
        row=5, column=0, padx=10, pady=(5, 10), sticky="ew")


def create_programs_tab_widgets(parent, app):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    customtkinter.CTkLabel(
        parent, text="Program Management", font=("Segoe UI", 16, "bold")
    ).grid(row=0, column=0, pady=10)

    app.program_list_frame = customtkinter.CTkScrollableFrame(parent)
    app.program_list_frame.grid(
        row=1, column=0, padx=10, pady=5, sticky="nsew")

    btn_frame = customtkinter.CTkFrame(parent)
    btn_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
    btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

    # Gán các nút vào app.
    app.save_program_button = customtkinter.CTkButton(
        btn_frame, text="Save Current as Program", command=app.save_program
    )
    app.save_program_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

    app.load_selected_program_button = customtkinter.CTkButton(
        btn_frame, text="Load Selected Program", command=app.load_selected_program
    )
    app.load_selected_program_button.grid(
        row=0, column=1, padx=5, pady=5, sticky="ew")

    app.delete_selected_program_button = customtkinter.CTkButton(
        btn_frame, text="Delete Selected Program", command=app.delete_program
    )
    app.delete_selected_program_button.grid(
        row=0, column=2, padx=5, pady=5, sticky="ew")

    app.import_program_button = customtkinter.CTkButton(
        btn_frame, text="Import Program from File...", command=app.import_program
    )
    app.import_program_button.grid(
        row=0, column=3, padx=5, pady=5, sticky="ew")


def create_settings_widgets(parent, app):
    # Dòng này bị lỗi và không cần thiết vì parent (self.settings_tab) đã được cấu hình grid trong App.__init__
    # parent.grid_column(0, weight=1)

    limits_frame = customtkinter.CTkFrame(parent)
    limits_frame.pack(fill="x", padx=10, pady=10)
    customtkinter.CTkLabel(
        limits_frame, text="Soft Limits (Working Area in degrees)", font=("Segoe UI", 16, "bold")
    ).pack(pady=10)

    # app.limit_entries và app.limit_lock_buttons đã được khởi tạo trong __init__ của App
    # và sẽ được điền ở đây
    # (Khởi tạo lại dicts ở đây là thừa nếu đã làm trong __init__, nhưng không gây lỗi)
    # Tuy nhiên, để đảm bảo code sạch hơn, bạn có thể cân nhắc bỏ 2 dòng khởi tạo này nếu chúng đã có trong __init__
    # app.limit_entries = {}
    # app.limit_lock_buttons = {}

    entry_frame = customtkinter.CTkFrame(limits_frame, fg_color="transparent")
    entry_frame.pack(pady=5)
    entry_frame.grid_columnconfigure(1, weight=1)

    for i, axis in enumerate(["X", "Y", "Z"]):
        customtkinter.CTkLabel(entry_frame, text=f"{axis} Limit Angle (°):").grid(
            row=i, column=0, padx=10, pady=5, sticky="w"
        )
        entry = customtkinter.CTkEntry(
            entry_frame, textvariable=app.soft_limits[axis], width=120
        )
        entry.grid(row=i, column=1, padx=5, pady=5)
        app.limit_entries[axis] = entry  # Gán widget Entry vào dictionary

        lock_button = customtkinter.CTkButton(
            entry_frame,
            text="Lock",
            width=60,
            command=lambda a=axis: app.toggle_limit_lock(a),
        )
        lock_button.grid(row=i, column=2, padx=5)
        # Gán nút khóa vào dictionary
        app.limit_lock_buttons[axis] = lock_button

    customtkinter.CTkLabel(
        limits_frame,
        text="Gốc tọa độ (Origin) luôn là 0°. Giới hạn bạn đặt ở đây là góc biên còn lại.\nĐể trống để vô hiệu hóa giới hạn cho trục đó.",
        wraplength=400,
    ).pack(pady=5)

    file_frame = customtkinter.CTkFrame(parent)
    file_frame.pack(fill="x", padx=10, pady=10)
    customtkinter.CTkLabel(
        file_frame, text="Configuration File", font=("Segoe UI", 16, "bold")
    ).pack(pady=10)
    customtkinter.CTkButton(
        file_frame, text="Save Settings", command=app.save_settings
    ).pack(fill="x", padx=20, pady=5)
    customtkinter.CTkButton(
        file_frame, text="Import Settings", command=app.import_settings
    ).pack(fill="x", padx=20, pady=5)
