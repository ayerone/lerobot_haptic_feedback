#!/usr/bin/env bash

# export teleop_port=/your/leader/port
# export feedback_port=/port/for/your/gimbal/motor/arduino
# export robot_port=...
# export sensor_port=...
# export HF_USER=...

# Error if environment variables aren't set
set -u

python ./reference/record_with_feedback.py \
    --robot.type=so_sensor_arm \
    --robot.port=$robot_port \
    --robot.sensor_port=$sensor_port \
    --robot.id=my_so_sensor_arm \
    --robot.cameras="{ wrist: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30} }" \
    --teleop.type=feedback_leader \
    --teleop.port=$teleop_port \
    --teleop.feedback_port=$feedback_port \
    --teleop.id=my_feedback_leader \
    --display_data=true \
    --dataset.repo_id="${HF_USER}/haptic_test" \
    --dataset.num_episodes=1 \
    --dataset.single_task="Haptic Hello World"
