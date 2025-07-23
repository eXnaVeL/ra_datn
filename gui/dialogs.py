# gui/dialogs.py OK

import customtkinter
import tkinter as tk
from tkinter import messagebox


class EditWaypointDialog(customtkinter.CTkToplevel):
    def __init__(self, parent, waypoint_data):
        super().__init__(parent)
        self.title("Edit Waypoint")
        self.geometry("350x250")
        self._center_window(350, 250)
        self.transient(parent)
        self.grab_set()
        self.result = None
        self.grid_columnconfigure(1, weight=1)

        self.name_var = tk.StringVar(value=waypoint_data["name"])
        self.x_var = tk.StringVar(value=str(float(waypoint_data["pos"]["X"])))
        self.y_var = tk.StringVar(value=str(float(waypoint_data["pos"]["Y"])))
        self.z_var = tk.StringVar(value=str(float(waypoint_data["pos"]["Z"])))

        customtkinter.CTkLabel(self, text="Name:").grid(
            row=0, column=0, padx=10, pady=10, sticky="w")
        customtkinter.CTkEntry(self, textvariable=self.name_var).grid(
            row=0, column=1, padx=10, pady=10, sticky="ew")

        customtkinter.CTkLabel(self, text="X (deg):").grid(
            row=1, column=0, padx=10, pady=5, sticky="w")
        customtkinter.CTkEntry(self, textvariable=self.x_var).grid(
            row=1, column=1, padx=10, pady=5, sticky="ew")

        customtkinter.CTkLabel(self, text="Y (deg):").grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        customtkinter.CTkEntry(self, textvariable=self.y_var).grid(
            row=2, column=1, padx=10, pady=5, sticky="ew")

        customtkinter.CTkLabel(self, text="Z (deg):").grid(
            row=3, column=0, padx=10, pady=5, sticky="w")
        customtkinter.CTkEntry(self, textvariable=self.z_var).grid(
            row=3, column=1, padx=10, pady=5, sticky="ew")

        button_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
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
            self.result = {
                "name": self.name_var.get(),
                "pos": {
                    "X": float(self.x_var.get()),
                    "Y": float(self.y_var.get()),
                    "Z": float(self.z_var.get()),
                },
            }
            self.destroy()
        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Please enter valid numeric values for degrees.", parent=self)

    def cancel(self):
        self.result = None
        self.destroy()
