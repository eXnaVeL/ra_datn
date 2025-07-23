# gui/delay_dialogs.py OK

import customtkinter
import tkinter as tk
from tkinter import messagebox


class DelayEditDialog(customtkinter.CTkToplevel):
    def __init__(self, parent, duration_ms):
        super().__init__(parent)
        self.title("Edit Delay Waypoint")
        self.geometry("300x150")
        self._center_window(300, 150)
        self.transient(parent)
        self.grab_set()
        self.result = None

        self.duration_ms_var = tk.StringVar(
            value=str(float(duration_ms)))  # Sử dụng StringVar

        customtkinter.CTkLabel(
            self, text="Duration (milliseconds):").pack(pady=10)
        customtkinter.CTkEntry(
            self, textvariable=self.duration_ms_var).pack(padx=20, fill="x")

        button_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=15)
        customtkinter.CTkButton(button_frame, text="Save", command=self.save).pack(
            side="left", padx=10)
        customtkinter.CTkButton(button_frame, text="Cancel", command=self.cancel,
                                fg_color="gray50").pack(side="left", padx=10)

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.wait_window()

    def _center_window(self, width, height):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    def save(self):
        try:
            # Lấy giá trị từ StringVar và chuyển đổi
            duration_ms_float = float(self.duration_ms_var.get())

            if duration_ms_float < 1:
                messagebox.showerror(
                    "Invalid Input", "Duration must be at least 1 millisecond.", parent=self)
                return

            self.result = {
                "name": f"Delay {duration_ms_float:.0f}ms",
                "type": "delay",
                "duration_ms": int(duration_ms_float)
            }
            self.destroy()
        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Please enter a valid number for duration (milliseconds).", parent=self)

    def cancel(self):
        self.result = None
        self.destroy()
