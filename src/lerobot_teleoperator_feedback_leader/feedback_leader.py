from .config_feedback_leader import FeedbackLeaderConfig
from .feedback_motor import FeedbackMotor, GimbalCalibration

import logging
logger = logging.getLogger(__name__)

import draccus

from lerobot.teleoperators.so_leader import SO101Leader
from lerobot.motors import Motor, MotorCalibration

from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected

from lerobot.utils.constants import HF_LEROBOT_CALIBRATION, TELEOPERATORS

class FeedbackLeader(SO101Leader):
    config_class = FeedbackLeaderConfig
    name = "feedback_leader"

    SENSOR_DEADBAND_THRESHOLD = 0
    GRIP_FEEDBACK_SCALAR = 1 / 200
    TELEOP_EFFECTOR_TOO_OPEN_THRESHOLD = 15
    JAW_OPEN_SCALAR = 0.01

    def __init__(self, config: FeedbackLeaderConfig):
        super().__init__(config)

        self._gimbal_position = 0
        self.gimbal_calibration: GimbalCalibration | None = None
        self.gimbal_calibration_fpath = HF_LEROBOT_CALIBRATION / TELEOPERATORS / self.name / f"{self.id}.gimbal.json"
        self._load_gimbal_calibration()
        self.feedback_motor = FeedbackMotor(
            port=config.feedback_port,
            calibration=self.gimbal_calibration
        )
        return
    
    @property
    def action_features(self) -> dict[str, type]:
        return { **super().action_features, "gimbal.pos": float }
    
    @property
    def feedback_features(self) -> dict[str, type]:
        return { "gimbal.pos": float }

    @property
    def is_connected(self) -> bool:
        return super().is_connected and self.feedback_motor.is_connected
    
    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        self.feedback_motor.connect()

        if not self.feedback_motor.is_calibrated:
            self.calibrate_gimbal()

        super().connect(calibrate=calibrate)

        logger.info(f"{self.name} Connected")
        return
    
    def calibrate_gimbal(self) -> None:
        self.feedback_motor.disable_torque()
        input(f"Move {self.feedback_motor} to the middle of its range of motion and press ENTER....")
        gimbal_half_turn = self.feedback_motor.get_half_turn()
        
        range_min, range_max = self.feedback_motor.record_range_of_motion()

        # self.gimbal_calibration = MotorCalibration(
        #     id="gimbal",
        #     drive_mode=0,
        #     homing_offset=gimbal_half_turn,
        #     range_min=range_min,
        #     range_max=range_max,
        # )

        self.gimbal_calibration = GimbalCalibration(
            homing_offset=gimbal_half_turn,
            range_min=range_min,
            range_max=range_max,
        )

        self._save_gimbal_calibration()
        self.feedback_motor.write_calibration(self.gimbal_calibration)
        self.feedback_motor.enable_torque()
        return

    def calibrate(self) -> None:
        logger.info("Calibrating the BASE ARM")
        super().calibrate()

        logger.info(f"\nCalibrating the GIMBAL MOTOR: {self.feedback_motor}")
        self.calibrate_gimbal()
        logger.info("Finished gimbal calibration")


    def _load_gimbal_calibration(self) -> None:
        fpath = self.gimbal_calibration_fpath
        if not fpath.is_file():
            return
        with open(fpath) as f, draccus.config_type("json"):
            self.gimbal_calibration = draccus.load(GimbalCalibration, f)
        return
    
    def _save_gimbal_calibration(self) -> None:
        fpath = self.gimbal_calibration_fpath
        with open(fpath, "w") as f, draccus.config_type("json"):
            draccus.dump(self.gimbal_calibration, f, indent=4)

    @check_if_not_connected
    def get_action(self) -> dict[str: float]:
        so_action = super().get_action()

        # Re: sending angle commands to robot's gripper,
        # we will clip at a max value, set in FeedbackMotor.
        # I did this to get more resolution out of the feedback motor,
        # since super wide jaw opening is typically not used. This way,
        # a full turn of the feedback motor is mapped to a smaller range
        # in robot actions.
        self._gimbal_position = self.feedback_motor.read()
        max_angle = self.feedback_motor.robot_jaw_max_angle
        to_send = min(self._gimbal_position, max_angle)
        so_action["gripper.pos"] = to_send

        return so_action
        # return { 
        #     **super().get_action(),
        #     "gimbal.pos": self.feedback_motor.read()
        # }

    @check_if_not_connected
    def send_feedback(self, feedback: dict[str, float]):
        '''
        When gripping an object, force reported by the robot is scaled by
        GRIP_FEEDBACK_SCALAR (a property of this class, FeedbackLeader) to
        determine torque exerted by the feedback motor on the teleop.

        The gimbal motor has continuous rotation. To indicate the "fully open"
        position to the operator:
        when the teleop gripper control is significantly more open than the
        robot's gripper, a simulated spring (with displacement "error") acts
        to push the feedback motor toward the gripper "closed" position.
        '''
        # position feedback:
        # return self.feedback_motor.write(feedback["gimbal.pos"]);
        #
        # realtime error feedback:
        # error = feedback["gimbal.pos"] - feedback["gripper.pos"]
        # return self.feedback_motor.write(error/10);
        #
        # sensor to torque feedback

        # TODO:
        # try adding a derivative term to damp quick motion

        # During gripping
        if feedback["sensor.force"] > self.SENSOR_DEADBAND_THRESHOLD:
            return self.feedback_motor.write(- self.GRIP_FEEDBACK_SCALAR * feedback["sensor.force"])
        # During jaw wide open
        error = self._gimbal_position - feedback["gripper.pos"]
        if error > self.TELEOP_EFFECTOR_TOO_OPEN_THRESHOLD:
            return self.feedback_motor.write(self.JAW_OPEN_SCALAR * error)
        # Gripper in normal range & not touching anything
        return self.feedback_motor.write(0)
    
    @check_if_not_connected
    def disconnect(self) -> None:
        super().disconnect();
        self.feedback_motor.disconnect();
        pass