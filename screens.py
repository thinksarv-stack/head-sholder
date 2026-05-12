"""
screens.py  –  All three kiosk screens
HomeScreen  → ScanScreen  → ResultScreen  → HomeScreen
"""

import customtkinter as ctk
import cv2
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageEnhance
import threading
import time
import random
import math
import numpy as np

# ── Palette ────────────────────────────────────────────────────────────────────
BG        = "#0A0A14"
BLUE      = "#00AAFF"
BLUE_DIM  = "#005588"
WHITE     = "#FFFFFF"
GRAY      = "#8899AA"
RED_MARK  = "#FF3355"
GREEN_OK  = "#00FF99"
HS_BLUE   = "#003DA5"   # official H&S brand blue


# ══════════════════════════════════════════════════════════════════════════════
# HOME SCREEN
# ══════════════════════════════════════════════════════════════════════════════
class HomeScreen(ctk.CTkFrame):
    def __init__(self, master, on_start):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.on_start = on_start
        self._pulse_job = None
        self._build_ui()
        self._start_pulse()

    def _build_ui(self):
        # Background gradient canvas
        self.canvas = ctk.CTkCanvas(self, bg=BG, highlightthickness=0)
        self.canvas.place(relwidth=1, relheight=1)
        self._draw_bg_lines()

        # Brand badge
        badge = ctk.CTkFrame(self, fg_color=HS_BLUE, corner_radius=8, width=220, height=36)
        badge.place(relx=0.5, y=60, anchor="center")
        ctk.CTkLabel(badge, text="HEAD & SHOULDERS",
                     font=("Helvetica", 13, "bold"), text_color=WHITE).place(relx=0.5, rely=0.5, anchor="center")

        # Title
        ctk.CTkLabel(self,
                     text="Smart Scalp\nAnalyzer",
                     font=("Helvetica", 52, "bold"),
                     text_color=WHITE,
                     justify="center").place(relx=0.5, y=190, anchor="center")

        ctk.CTkLabel(self,
                     text="AI-Powered Dandruff Detection",
                     font=("Helvetica", 16),
                     text_color=BLUE).place(relx=0.5, y=270, anchor="center")

        # Animated start button
        self.start_btn = ctk.CTkButton(
            self,
            text="▶  START SCAN",
            font=("Helvetica", 20, "bold"),
            fg_color=BLUE,
            hover_color="#0088DD",
            text_color=WHITE,
            corner_radius=40,
            width=260, height=60,
            command=self.on_start
        )
        self.start_btn.place(relx=0.5, y=370, anchor="center")

        ctk.CTkLabel(self,
                     text="Position your head in front of the camera",
                     font=("Helvetica", 12),
                     text_color=GRAY).place(relx=0.5, y=440, anchor="center")

    def _draw_bg_lines(self):
        """Subtle grid lines for futuristic look."""
        w, h = 800, 480
        for x in range(0, w, 60):
            self.canvas.create_line(x, 0, x, h, fill="#111122", width=1)
        for y in range(0, h, 60):
            self.canvas.create_line(0, y, w, y, fill="#111122", width=1)
        # Glowing circle (Tkinter only supports 6-digit hex, no alpha)
        cx, cy, r = 400, 240, 180
        glow_colors = ["#001830", "#002244", "#003366", "#004488", "#0055AA"]
        for i, color in enumerate(glow_colors):
            offset = (5 - i) * 8
            self.canvas.create_oval(cx-r-offset, cy-r-offset,
                                    cx+r+offset, cy+r+offset,
                                    outline=color, width=1)

    def _start_pulse(self):
        """Make the button subtly pulse."""
        self._pulse_state = 0
        self._pulse()

    def _pulse(self):
        if not self.winfo_exists():
            return
        self._pulse_state = (self._pulse_state + 1) % 40
        t = math.sin(self._pulse_state * math.pi / 20)
        r = max(0, min(255, int(0 + t * 30)))
        g = max(0, min(255, int(170 + t * 40)))
        b = 255
        color = f"#{r:02x}{g:02x}{b:02x}"
        try:
            self.start_btn.configure(fg_color=color)
        except Exception:
            return
        self._pulse_job = self.after(50, self._pulse)

    def destroy(self):
        if self._pulse_job:
            self.after_cancel(self._pulse_job)
        super().destroy()


# ══════════════════════════════════════════════════════════════════════════════
# SCAN SCREEN
# ══════════════════════════════════════════════════════════════════════════════
class ScanScreen(ctk.CTkFrame):
    SCAN_DURATION = 3.0   # seconds of "scanning" animation

    def __init__(self, master, on_capture):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.on_capture = on_capture
        self.app = master
        self._camera_job = None
        self._anim_job   = None
        self._scanning   = False
        self._scan_start = 0
        self._scan_angle = 0
        self._captured_frame = None
        self._build_ui()
        self._start_feed()

    def _build_ui(self):
        # ── Left: camera feed ──────────────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="#0D0D1E", corner_radius=0, width=480, height=480)
        left.place(x=0, y=0)

        ctk.CTkLabel(left, text="LIVE FEED",
                     font=("Helvetica", 11, "bold"), text_color=BLUE_DIM).place(x=16, y=10)

        # Camera canvas (360×360 circle clip done via oval overlay)
        self.cam_canvas = ctk.CTkCanvas(left, width=360, height=360,
                                        bg="#0D0D1E", highlightthickness=0)
        self.cam_canvas.place(x=60, y=55)

        # Overlay ring (drawn on top in _update_feed)
        self.scan_canvas = ctk.CTkCanvas(left, width=380, height=380,
                                         bg="#0D0D1E", highlightthickness=0)
        self.scan_canvas.place(x=50, y=45)

        # ── Right: controls & info ─────────────────────────────────────────
        right = ctk.CTkFrame(self, fg_color=BG, corner_radius=0, width=320, height=480)
        right.place(x=480, y=0)

        ctk.CTkLabel(right, text="HEAD & SHOULDERS",
                     font=("Helvetica", 10, "bold"), text_color=BLUE_DIM).place(x=20, y=20)

        ctk.CTkLabel(right, text="Scalp\nAnalysis",
                     font=("Helvetica", 30, "bold"), text_color=WHITE,
                     justify="left").place(x=20, y=45)

        # Status label
        self.status_label = ctk.CTkLabel(right, text="Align your head\nwith the circle",
                                         font=("Helvetica", 14), text_color=GRAY,
                                         justify="left")
        self.status_label.place(x=20, y=145)

        # Progress bar (hidden until scan)
        self.progress = ctk.CTkProgressBar(right, width=260, height=10,
                                            fg_color="#1A1A2E", progress_color=BLUE)
        self.progress.set(0)
        self.progress.place(x=20, y=240)
        self.progress.place_forget()

        self.progress_label = ctk.CTkLabel(right, text="",
                                           font=("Helvetica", 11), text_color=BLUE)
        self.progress_label.place(x=20, y=258)

        # Scan button
        self.scan_btn = ctk.CTkButton(
            right,
            text="📷  SCAN MY SCALP",
            font=("Helvetica", 16, "bold"),
            fg_color=BLUE, hover_color="#0088DD",
            text_color=WHITE,
            corner_radius=30,
            width=260, height=54,
            command=self._trigger_scan
        )
        self.scan_btn.place(x=20, y=310)

        # Stats strip
        for i, (val, label) in enumerate([("100%", "Dandruff\nRemoval"), ("3s", "Scan\nTime"), ("Free", "No\nCharge")]):
            f = ctk.CTkFrame(right, fg_color="#111126", corner_radius=8, width=74, height=64)
            f.place(x=20 + i*90, y=390)
            ctk.CTkLabel(f, text=val, font=("Helvetica", 16, "bold"), text_color=BLUE).place(relx=0.5, y=18, anchor="center")
            ctk.CTkLabel(f, text=label, font=("Helvetica", 8), text_color=GRAY, justify="center").place(relx=0.5, y=44, anchor="center")

    # ── Camera Feed ────────────────────────────────────────────────────────────
    def _start_feed(self):
        self.cam = self.app.open_camera()
        self._update_feed()

    def _update_feed(self):
        if not self.winfo_exists():
            return
        ret, frame = self.cam.read()
        if ret:
            self._captured_frame = frame.copy()
            # Convert BGR→RGB, resize, draw on canvas
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (360, 360))
            # Circular mask
            mask = np.zeros((360, 360), dtype=np.uint8)
            cv2.circle(mask, (180, 180), 176, 255, -1)
            img_masked = cv2.bitwise_and(img, img, mask=mask)
            pil = Image.fromarray(img_masked)
            self._tk_img = ImageTk.PhotoImage(pil)
            self.cam_canvas.delete("all")
            self.cam_canvas.create_image(0, 0, anchor="nw", image=self._tk_img)

        # Draw scan ring
        self._draw_ring()

        if self._scanning:
            elapsed = time.time() - self._scan_start
            pct = min(elapsed / self.SCAN_DURATION, 1.0)
            self.progress.set(pct)
            tips = ["Detecting follicle density...", "Mapping sebum zones...",
                    "Analysing dandruff markers...", "Computing H&S score..."]
            idx = int(pct * (len(tips) - 1))
            self.progress_label.configure(text=tips[idx])
            if pct >= 1.0:
                self._finish_scan()

        self._camera_job = self.after(33, self._update_feed)   # ~30 fps

    def _draw_ring(self):
        self.scan_canvas.delete("all")
        cx, cy, r = 190, 190, 178
        # Base circle
        self.scan_canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                     outline=BLUE_DIM, width=2)
        if self._scanning:
            self._scan_angle = (self._scan_angle + 6) % 360
            # Spinning arc (approximate with lines)
            for deg in range(0, 120, 5):
                a = math.radians(self._scan_angle + deg)
                x1 = cx + r * math.cos(a)
                y1 = cy + r * math.sin(a)
                a2 = math.radians(self._scan_angle + deg + 5)
                x2 = cx + r * math.cos(a2)
                y2 = cy + r * math.sin(a2)
                alpha = int(255 * deg / 120)
                col = f"#{0:02x}{int(170 + 85*deg/120):02x}{255:02x}"
                self.scan_canvas.create_line(x1, y1, x2, y2, fill=col, width=3)
        else:
            # Cross-hair lines
            self.scan_canvas.create_line(cx, cy-20, cx, cy+20, fill=BLUE_DIM, width=1)
            self.scan_canvas.create_line(cx-20, cy, cx+20, cy, fill=BLUE_DIM, width=1)
            # Corner ticks
            for ax, ay, dx, dy in [(-r+5,-r+5,-1,-1),(r-5,-r+5,1,-1),
                                    (-r+5,r-5,-1,1),(r-5,r-5,1,1)]:
                self.scan_canvas.create_line(cx+ax, cy+ay,
                                             cx+ax+dx*18, cy+ay, fill=BLUE, width=2)
                self.scan_canvas.create_line(cx+ax, cy+ay,
                                             cx+ax, cy+ay+dy*18, fill=BLUE, width=2)

    # ── Scan Logic ─────────────────────────────────────────────────────────────
    def _trigger_scan(self):
        if self._scanning:
            return
        self._scanning  = True
        self._scan_start = time.time()
        self.scan_btn.configure(state="disabled", text="⏳  Scanning...")
        self.status_label.configure(text="Hold still!\nScanning in progress...", text_color=BLUE)
        self.progress.place(x=20, y=240)
        self.progress_label.place(x=20, y=258)

    def _finish_scan(self):
        self._scanning = False
        frame = self._captured_frame
        self.after(200, lambda: self.on_capture(frame))

    def destroy(self):
        if self._camera_job:
            self.after_cancel(self._camera_job)
        super().destroy()


# ══════════════════════════════════════════════════════════════════════════════
# RESULT SCREEN
# ══════════════════════════════════════════════════════════════════════════════
class ResultScreen(ctk.CTkFrame):
    PRODUCTS = [
        ("Cool Menthol", "Intense Freshness"),
        ("Anti-Dandruff", "Classic Clean"),
        ("Smooth & Silky", "Moisturising Care"),
    ]

    def __init__(self, master, image_path, on_restart):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.image_path  = image_path
        self.on_restart  = on_restart
        self._reveal_job = None
        self._build_ui()
        self._animate_reveal()

    def _build_ui(self):
        # ── Left panel: analysed image ─────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="#0D0D1E", corner_radius=0, width=390, height=480)
        left.place(x=0, y=0)

        ctk.CTkLabel(left, text="SCALP ANALYSIS RESULT",
                     font=("Helvetica", 10, "bold"), text_color=BLUE_DIM).place(x=16, y=10)

        # Load + annotate captured image
        self.img_canvas = ctk.CTkCanvas(left, width=340, height=280,
                                        bg="#0D0D1E", highlightthickness=0)
        self.img_canvas.place(x=25, y=35)
        self._draw_analysed_image()

        # Score bar
        score = random.randint(62, 91)
        self.score_val = score
        ctk.CTkLabel(left, text=f"Dandruff Score: {score}%",
                     font=("Helvetica", 14, "bold"), text_color=RED_MARK).place(x=25, y=328)
        bar = ctk.CTkProgressBar(left, width=340, height=14,
                                  fg_color="#1A1A2E", progress_color=RED_MARK)
        bar.set(score / 100)
        bar.place(x=25, y=350)

        # Verdict tags
        tags = ["Dry Scalp Detected", "Flaking Zones Found", "Treatment Needed"]
        for i, t in enumerate(tags):
            f = ctk.CTkFrame(left, fg_color="#2A0A14", corner_radius=12, width=100, height=26)
            f.place(x=25 + i*116, y=380)
            ctk.CTkLabel(f, text=t, font=("Helvetica", 8, "bold"),
                         text_color=RED_MARK).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(left, text="⚠  Clinical-grade scan complete",
                     font=("Helvetica", 10), text_color=GRAY).place(x=25, y=418)
        ctk.CTkLabel(left, text="*For demonstration purposes only",
                     font=("Helvetica", 8), text_color="#444455").place(x=25, y=450)

        # ── Right panel: recommendation + ANIMATED BOTTLE ──────────────────
        right = ctk.CTkFrame(self, fg_color=BG, corner_radius=0, width=410, height=480)
        right.place(x=390, y=0)

        # Top info strip
        ctk.CTkLabel(right, text="✓  SOLUTION FOUND",
                     font=("Helvetica", 11, "bold"), text_color=GREEN_OK).place(x=12, y=8)

        prod_name, prod_sub = random.choice(self.PRODUCTS)
        ctk.CTkLabel(right, text="Head & Shoulders",
                     font=("Helvetica", 20, "bold"), text_color=WHITE).place(x=12, y=30)
        ctk.CTkLabel(right, text=prod_name,
                     font=("Helvetica", 14, "bold"), text_color=BLUE).place(x=12, y=58)

        # ── Animated bottle canvas (main attraction) ──────────────────────
        self.bottle_canvas = ctk.CTkCanvas(right, width=390, height=240,
                                           bg=BG, highlightthickness=0)
        self.bottle_canvas.place(x=10, y=82)
        self._load_bottle_image()

        # Animation state
        self._anim_tick   = 0
        self._float_y     = 0.0
        self._glow_phase  = 0.0
        self._ray_angle   = 0.0
        self._bottle_job  = None
        self._start_bottle_anim()

        # Benefit mini-strips (compact, 2 per row)
        benefits = [
            "💧 100% dandruff removal",
            "❄️  ZPT formula",
            "✨ Dermatologist tested",
            "🌿 pH balanced",
        ]
        for i, txt in enumerate(benefits):
            col = i % 2
            row = i // 2
            f = ctk.CTkFrame(right, fg_color="#0E0E22", corner_radius=6, width=178, height=28)
            f.place(x=10 + col*196, y=330 + row*36)
            ctk.CTkLabel(f, text=txt, font=("Helvetica", 10), text_color=WHITE).place(
                relx=0.5, rely=0.5, anchor="center")

        # Tagline
        ctk.CTkLabel(right, text='"Scalp confidence starts here."',
                     font=("Helvetica", 11, "italic"), text_color=BLUE).place(x=12, y=408)

        # Restart button
        ctk.CTkButton(
            right,
            text="🔄  Scan Again",
            font=("Helvetica", 13, "bold"),
            fg_color="#111126", hover_color=BLUE_DIM,
            text_color=BLUE, border_color=BLUE, border_width=2,
            corner_radius=30, width=180, height=40,
            command=self.on_restart
        ).place(x=12, y=430)

    def _load_bottle_image(self):
        """Load the H&S bottle PNG and prepare base + glow versions."""
        import os
        bottle_path = os.path.join(os.path.dirname(__file__), "hs_bottle.png")
        try:
            raw = Image.open(bottle_path).convert("RGBA")
        except Exception:
            raw = Image.new("RGBA", (160, 220), (0, 80, 180, 255))

        # Resize to fit nicely in canvas (height = 200px)
        ratio = 200 / raw.height
        new_w = int(raw.width * ratio)
        self._bottle_base = raw.resize((new_w, 200), Image.LANCZOS)
        self._bottle_w = new_w
        self._bottle_h = 200

    def _start_bottle_anim(self):
        """Kick off the continuous bottle animation."""
        self._anim_tick = 0
        self._animate_bottle()

    def _animate_bottle(self):
        if not self.winfo_exists():
            return

        tick = self._anim_tick
        self._anim_tick += 1

        # ── Parameters driven by tick ──────────────────────────────────────
        float_y   = math.sin(tick * 0.06) * 10          # gentle float ±10px
        glow_r    = max(0, min(255, int(0   + math.sin(tick * 0.05) * 30)))
        glow_g    = max(0, min(255, int(120 + math.sin(tick * 0.04) * 60)))
        glow_b    = 255
        glow_col  = f"#{glow_r:02x}{glow_g:02x}{glow_b:02x}"
        ray_angle = (tick * 2) % 360                     # spinning rays

        cw, ch = 390, 240
        cx, cy = cw // 2, ch // 2

        self.bottle_canvas.delete("all")

        # ── 1. Dark radial background ─────────────────────────────────────
        for i in range(6, 0, -1):
            r = 30 + i * 18
            shade = 10 + i * 4
            col = f"#{shade:02x}{shade:02x}{shade+10:02x}"
            self.bottle_canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                           fill=col, outline="")

        # ── 2. Spinning light rays ─────────────────────────────────────────
        num_rays = 12
        for n in range(num_rays):
            angle = math.radians(ray_angle + n * (360 / num_rays))
            x2 = cx + math.cos(angle) * 180
            y2 = cy + math.sin(angle) * 180
            # Alternating brightness
            intensity = 30 if n % 2 == 0 else 18
            col = f"#{0:02x}{intensity:02x}{intensity+10:02x}"
            self.bottle_canvas.create_line(cx, cy, x2, y2,
                                           fill=col, width=2)

        # ── 3. Glow rings (pulsing) ────────────────────────────────────────
        glow_sizes = [85, 70, 55, 40]
        for i, gr in enumerate(glow_sizes):
            alpha_shade = max(0, min(255, int(20 + i * 14 + math.sin(tick * 0.07 + i) * 10)))
            col = f"#{0:02x}{min(255, alpha_shade+40):02x}{min(255, alpha_shade+80):02x}"
            self.bottle_canvas.create_oval(cx-gr, cy-gr+int(float_y),
                                           cx+gr, cy+gr+int(float_y),
                                           outline=col, width=2)

        # ── 4. Bottle image (floating) ─────────────────────────────────────
        bx = cx - self._bottle_w // 2
        by = int(cy - self._bottle_h // 2 + float_y)

        # Composite onto dark bg for display
        bg_patch = Image.new("RGBA", (self._bottle_w, self._bottle_h), (10, 10, 20, 255))
        bg_patch.paste(self._bottle_base, (0, 0), self._bottle_base)
        self._tk_bottle = ImageTk.PhotoImage(bg_patch)
        self.bottle_canvas.create_image(bx, by, anchor="nw", image=self._tk_bottle)

        # ── 5. Shimmer highlight on bottle ────────────────────────────────
        shimmer_x = bx + int((math.sin(tick * 0.08) * 0.5 + 0.5) * self._bottle_w)
        self.bottle_canvas.create_line(shimmer_x, by, shimmer_x, by + self._bottle_h,
                                       fill="#AADDFF", width=2)

        # ── 6. "100% Dandruff Free" badge ─────────────────────────────────
        badge_alpha = max(0, min(255, int(200 + math.sin(tick * 0.1) * 55)))
        badge_col = f"#{0:02x}{min(255, badge_alpha//2):02x}{badge_alpha:02x}"
        self.bottle_canvas.create_oval(cx+55, cy-80+int(float_y),
                                       cx+110, cy-30+int(float_y),
                                       fill=badge_col, outline=glow_col, width=2)
        self.bottle_canvas.create_text(cx+82, cy-55+int(float_y),
                                       text="100%\nFree!",
                                       fill="white", font=("Helvetica", 8, "bold"),
                                       justify="center")

        self._bottle_job = self.after(33, self._animate_bottle)   # ~30 fps

    def _draw_analysed_image(self):
        """Load captured image and overlay fake dandruff markers."""
        try:
            img = Image.open(self.image_path).resize((340, 280))
        except Exception:
            img = Image.new("RGB", (340, 280), "#111122")

        # Darken + slight warm tint
        img = ImageEnhance.Brightness(img).enhance(0.75)

        draw = ImageDraw.Draw(img)

        # Random dandruff spot circles
        random.seed(42)
        for _ in range(18):
            x, y = random.randint(40, 300), random.randint(40, 240)
            r = random.randint(6, 16)
            draw.ellipse([x-r, y-r, x+r, y+r], outline="#FF3355", width=2)
            draw.ellipse([x-2, y-2, x+2, y+2], fill="#FF3355")

        # Scan lines overlay
        for y in range(0, 280, 8):
            draw.line([(0, y), (340, y)], fill=(0, 170, 255, 18), width=1)

        self._result_img = ImageTk.PhotoImage(img)
        self.img_canvas.create_image(0, 0, anchor="nw", image=self._result_img)

        # "DANDRUFF DETECTED" stamp
        self.img_canvas.create_rectangle(10, 248, 210, 272, fill="#FF3355", outline="")
        self.img_canvas.create_text(110, 260, text="⚠  DANDRUFF DETECTED",
                                    fill="white", font=("Helvetica", 10, "bold"))

    def _animate_reveal(self):
        """Flash the result screen in."""
        self._flash = 0
        self._do_flash()

    def _do_flash(self):
        if not self.winfo_exists():
            return
        if self._flash < 3:
            color = WHITE if self._flash % 2 == 0 else BG
            self.configure(fg_color=color)
            self._flash += 1
            self._reveal_job = self.after(80, self._do_flash)
        else:
            self.configure(fg_color=BG)

    def destroy(self):
        if self._reveal_job:
            self.after_cancel(self._reveal_job)
        if self._bottle_job:
            self.after_cancel(self._bottle_job)
        super().destroy()
