import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import threading
import time
import random
import numpy as np
from screens import HomeScreen, ScanScreen, ResultScreen

# ─── App Config ───────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SCREEN_W, SCREEN_H = 800, 480   # 7-inch typical resolution

# ─── Main App Controller ──────────────────────────────────────────────────────
class KioskApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("H&S Smart Scalp Analyzer")
        self.geometry(f"{SCREEN_W}x{SCREEN_H}")
        self.resizable(False, False)
        self.configure(fg_color="#0A0A14")

        # Remove window borders for kiosk feel (uncomment on Pi)
        # self.overrideredirect(True)

        self.camera = None
        self.captured_frame = None
        self.current_screen = None

        self.show_home()

    # ── Screen Navigation ──────────────────────────────────────────────────────
    def show_home(self):
        self._switch_screen(HomeScreen(self, on_start=self.show_scan))

    def show_scan(self):
        self._switch_screen(ScanScreen(self, on_capture=self.handle_capture))

    def show_result(self, image_path):
        self._switch_screen(ResultScreen(self, image_path=image_path, on_restart=self.show_home))

    def _switch_screen(self, new_screen):
        if self.current_screen:
            self.current_screen.destroy()
        self.current_screen = new_screen
        new_screen.place(x=0, y=0, relwidth=1, relheight=1)

    # ── Camera Helpers ─────────────────────────────────────────────────────────
    def open_camera(self):
        if self.camera is None or not self.camera.isOpened():
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return self.camera

    def release_camera(self):
        if self.camera and self.camera.isOpened():
            self.camera.release()
            self.camera = None

    def handle_capture(self, frame):
        """Called from ScanScreen when photo is taken."""
        self.captured_frame = frame
        # Save raw capture
        path = "/tmp/scalp_capture.jpg"
        cv2.imwrite(path, frame)
        self.release_camera()
        # Move to result screen
        self.after(0, lambda: self.show_result(path))

    def on_closing(self):
        self.release_camera()
        self.destroy()


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = KioskApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
