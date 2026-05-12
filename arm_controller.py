"""
arm_controller.py  –  Servo / Robotic Arm control via RPi.GPIO
─────────────────────────────────────────────────────────────────
Hardware assumed:
  • 2 servo motors
      – Servo A (base rotation)  → GPIO pin 17  (PWM)
      – Servo B (vertical lift)  → GPIO pin 27  (PWM)
  • Standard 50 Hz hobby servo (0°–180°)

Usage (import in main.py or screens.py):
    from arm_controller import ArmController
    arm = ArmController()
    arm.move_to_scan()        # raises arm over user's head
    arm.move_to_home()        # returns to rest position
    arm.cleanup()             # call on app exit
"""

import time
import threading

# ── Safe import (won't crash on non-Pi machines) ───────────────────────────────
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("[ArmController] RPi.GPIO not found – running in simulation mode.")


class ArmController:
    # GPIO BCM pin numbers
    PIN_BASE  = 17
    PIN_LIFT  = 27
    PWM_FREQ  = 50          # Hz – standard for servos

    # Pulse widths → angle mapping
    # duty = (angle / 18) + 2  for most SG90-style servos
    HOME_BASE  = 90          # degrees
    HOME_LIFT  = 30          # degrees – resting (arm down)
    SCAN_BASE  = 90          # degrees – centred over user
    SCAN_LIFT  = 130         # degrees – raised above head

    MOVE_STEP_DELAY = 0.015  # seconds between each degree step (smooth motion)

    def __init__(self):
        self._lock = threading.Lock()
        self._current_base = self.HOME_BASE
        self._current_lift = self.HOME_LIFT

        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.PIN_BASE, GPIO.OUT)
            GPIO.setup(self.PIN_LIFT, GPIO.OUT)
            self._pwm_base = GPIO.PWM(self.PIN_BASE, self.PWM_FREQ)
            self._pwm_lift = GPIO.PWM(self.PIN_LIFT, self.PWM_FREQ)
            self._pwm_base.start(self._angle_to_duty(self.HOME_BASE))
            self._pwm_lift.start(self._angle_to_duty(self.HOME_LIFT))
            time.sleep(0.5)
        else:
            self._pwm_base = None
            self._pwm_lift = None

    # ── Public API ─────────────────────────────────────────────────────────────
    def move_to_scan(self, callback=None):
        """
        Non-blocking: smoothly move arm to scanning position.
        Optional callback() called when movement is done.
        """
        t = threading.Thread(target=self._move_sequence,
                             args=(self.SCAN_BASE, self.SCAN_LIFT, callback),
                             daemon=True)
        t.start()

    def move_to_home(self, callback=None):
        """Non-blocking: return arm to resting position."""
        t = threading.Thread(target=self._move_sequence,
                             args=(self.HOME_BASE, self.HOME_LIFT, callback),
                             daemon=True)
        t.start()

    def cleanup(self):
        if GPIO_AVAILABLE:
            self._pwm_base.stop()
            self._pwm_lift.stop()
            GPIO.cleanup()

    # ── Internal helpers ───────────────────────────────────────────────────────
    def _angle_to_duty(self, angle: float) -> float:
        """Convert 0–180° to PWM duty cycle (2–12%)."""
        return (angle / 18.0) + 2.0

    def _set_angle(self, pwm, angle: float):
        if pwm:
            pwm.ChangeDutyCycle(self._angle_to_duty(angle))

    def _smooth_move(self, pwm, current: float, target: float) -> float:
        """Step servo from current → target angle smoothly."""
        step = 1 if target > current else -1
        for angle in range(int(current), int(target) + step, step):
            self._set_angle(pwm, angle)
            time.sleep(self.MOVE_STEP_DELAY)
        return float(target)

    def _move_sequence(self, base_target, lift_target, callback):
        with self._lock:
            # Move lift first (safety), then base
            self._current_lift = self._smooth_move(
                self._pwm_lift, self._current_lift, lift_target)
            self._current_base = self._smooth_move(
                self._pwm_base, self._current_base, base_target)
        if callback:
            callback()


# ── Quick manual test (run directly on Pi) ────────────────────────────────────
if __name__ == "__main__":
    arm = ArmController()
    print("Moving to SCAN position...")
    arm.move_to_scan(callback=lambda: print("  → At scan position!"))
    time.sleep(4)
    print("Returning HOME...")
    arm.move_to_home(callback=lambda: print("  → At home!"))
    time.sleep(4)
    arm.cleanup()
    print("Done.")
