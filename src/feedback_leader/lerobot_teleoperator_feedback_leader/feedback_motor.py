import logging
import serial
from time import time, sleep
from enum import Enum, auto
from numpy import interp, clip
from dataclasses import dataclass

from lerobot.motors import Motor, MotorCalibration
from lerobot.utils.utils import enter_pressed, move_cursor_up

logger = logging.getLogger(__name__)

class SerialCommand(Enum):
    READ    = auto()
    # WRITE = auto() # there is no "WRITE" command, you just send a float in a string
    DISABLE = auto()
    ENABLE  = auto()

@dataclass
class GimbalCalibration:
    homing_offset: float
    range_min: float
    range_max: float

class FeedbackMotor():
    name = "feedback_motor"

    def __init__(self, port: str, calibration: GimbalCalibration|None=None):
        self.port = port
        if calibration:
            self.calibration = calibration
        return

    def __repr__(self):
        return self.name

    @property
    def is_connected(self):
        return hasattr(self, 'serial') and self.serial.is_open

    def connect(self):
        if self.is_connected:
            raise ValueError(f"{self.name} ALREADY CONNECTED")
        
        logger.info(f"Connecting to {self.name}")
        self.serial = serial.Serial(self.port, 9600, timeout=1)
        wakeup = self.receive()
        logger.info(f"{self.name} says {wakeup} on {self.port}")
        return
    
    def send(self, command_or_float):
        # print(f"COM SEND: {command_or_float}")
        to_write = ""
        if isinstance(command_or_float, Enum):
            to_write = command_or_float.name
        if isinstance(command_or_float, float):
            to_write = str(command_or_float)
        to_write += "\n"
        self.serial.write(to_write.encode('utf-8'))
        return
    
    def receive(self) -> str:
        # TODO: add a timeout, raise on timeout
        while self.serial.in_waiting <= 0:
            sleep(0.0005)
        received = self.serial.readline().decode('utf-8').rstrip()
        # print(f"COMM RECV: {received}")
        return received

    def send_receive(self, command_or_float) -> str:
        # print(f"COM S/R: {command_or_float}")
        self.send(command_or_float)
        return self.receive()

    def is_calibrated(self):
        # logger.info("dummy is_calibrated() returning True")
        if not hasattr(self, calibration):
            return False
        if not self.calibration:
            return False
        position = self.read(normalize=False)
        if (position < self.calibration.range_min) or (position > self.calibration.range_max):
            return False
        return True

    def disable_torque(self) -> None:
        self.send_receive(SerialCommand.DISABLE)
        return
    
    def enable_torque(self) -> None:
        self.send_receive(SerialCommand.ENABLE)

    def get_half_turn(self):
        return self.read(normalize=False)

    def record_range_of_motion(self) -> tuple[float]:
        start_position = self.read(normalize=False)
        min_position = max_position = start_position

        user_pressed_enter = False
        while not user_pressed_enter:
            position = self.read(normalize=False)
            min_position = min(position, min_position)
            max_position = max(position, max_position)
            print("\n-------------------------------------------")
            print(f"{'NAME':<15} | {'MIN':>6} | {'POS':>6} | {'MAX':>6}")
            print(f"{'gimbal':<15} | {min_position:>6} | {position:>6} | {max_position:>6}")
            if enter_pressed():
                user_pressed_enter = True
            if not user_pressed_enter:
                move_cursor_up(1 + 3)

        if min_position == max_position:
            raise ValueError("Gimbal has the same min and max values")

        return min_position, max_position

    def write_calibration(self, calibration: GimbalCalibration) -> None:
        self.calibration = calibration
        return

    def scale_number(self, unscaled_value, from_min, from_max, to_min, to_max):
        """
        Scales a number from one range to another.

        Args:
            unscaled_value: The value to scale.
            from_min: The minimum of the source range.
            from_max: The maximum of the source range.
            to_min: The minimum of the target range.
            to_max: The maximum of the target range.

        Returns:
            The scaled value in the target range.
        """
        # Calculate the ratio of the value within the source range (0 to 1)
        old_range = from_max - from_min
        if old_range == 0:
            return to_min # Avoid division by zero, return the minimum of the new range
        
        normalized_value = (unscaled_value - from_min) / old_range
        
        # Scale the normalized value to the target range
        new_range = to_max - to_min
        scaled_value = normalized_value * new_range + to_min
        
        return scaled_value

    def convert_encoder_to_100(self, encoder_value):
        # scaled = interp(
        #     encoder_value,
        #     (self.calibration.range_min, self.calibration.range_max),
        #     (0, 42),
        # ).item()
        scaled = self.scale_number(
            encoder_value,
            self.calibration.range_max, self.calibration.range_min,
            0, 42
        )
        # return clip(scaled, 0, 42).item()
        return scaled

    def convert_100_to_encoder(self, percent_value):
        return self.scale_number(
            percent_value,
            0, 42,
            self.calibration.range_max, self.calibration.range_min
        )
        # return interp(
        #     percent_value,
        #     (0, 42),
        #     (self.calibration.range_min, self.calibration.range_max),
        # ).item()

    def read(self, normalize=True) -> float:
        reading = float( self.send_receive(SerialCommand.READ) )
        if(normalize):
            return self.convert_encoder_to_100(reading)
        return reading

    def write(self, gimbal_pos) -> None:
        # to_send = self.convert_100_to_encoder(gimbal_pos)
        to_send = gimbal_pos
        if abs(to_send) < 0.0000001:
            to_send = 0.0
        return self.send_receive( float(to_send) )
        
    def disconnect(self) -> None:
        self.disable_torque()
        self.serial.close()
        return
