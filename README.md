# Force Feedback for LeRobot SO-101 teleoperator
![SO-101 robot with sensor installed in gripper](images/gripper_with_sensor-fs8.png)
This project extends the SO-101 Leader (teleoperator) / Follower (robot) by adding haptic feedback at the gripper joint. Without feedback, operators tend to squeeze too hard when manipulating objects. These teleoperator actions then enter the training dataset and are imitated during inference.

Force feeback during teleoperation allows the operator to use appropriate gripping force, thereby avoiding dropping objects (too little force) or damaging delicate objects and causing excess stress and heat in the robot's gripper motor (too much force).

## Method
A force sensor is added to the end effector of the robot, and a 2804 brushless outrunner "gimbal" motor is used as the final joint of the leader to provide force feedback to the operator. The motor is controlled with a SimpleFOC mini v1.0 with an AS5600 Magnetic Encoder communicating with an arduino Uno over I2C.
![force sensor and gimbal motor](images/sensor_and_motor.png)
The force sensor's readings are included in the robot's observation state. The lerobot-teleoperate and lerobot-record loops are (minimally) modified to provide feedback from the robot to the teleoperator (via the leader's send_feedback() method).
![data flow between computer, leader, and follower](images/feedback_teleop_data_flow.png)

## Software Integration
Each arm inherits from the standard so-101 base class for its type, leader and follower, and adds code only for the new functionality.
```python
class FeedbackLeader(SO101Leader):
    ...
    @property
    def action_features(self) -> dict[str, type]:
        return { **super().action_features, "gimbal.pos": float }
    ...
```
Conveniently, LeRobot ecosystem automatically detects new robots and teleoperators installed in your python enviornment, as long as certain naming conventions are followed (https://huggingface.co/docs/lerobot/en/integrate_hardware). This makes it easy to use LeRobot's scripts like lerobot-record to create training datasets, to train a policy, and then to run inference on that policy on the modified hardware. The script lerobot-record requires just one added statement to send the robot's observation back to the leader as feedback:
```python
teleop.send_feedback(obs)
```
I have copied the code from lerobot-record into this project's src/record_with_feedback/\_\_main\_\_.py (and made the one-line modification), and you can run this using the script at examples/record_with_feedback.sh after installing this repo in your lerobot virtual env.


A class is created to handle the sensor (ForceSensor), and another class to handle the feedback motor (FeedbackMotor), and each is managed by its respective arm.

## Hardware / Architecture
The leader and the follower each get a companion microcontroller (I used arduino Uno's). The Uno's are each attached to the computer (that runs lerobot) by a com port over USB. The modified lerobot code sends serial commands to the Uno's to read state (sensor readings and gimbal motor angles), and, for the feedback motor, also to write torques.

## Install
Clone this repo. cd into it. Ensure your lerobot virtual env is activated, and:
```shell
pip install -e .
```
