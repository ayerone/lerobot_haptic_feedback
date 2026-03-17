#!/usr/bin/env bash

# export teleop_port=/your/leader/port
# export feedback_port=/port/for/your/gimbal/motor/arduino

# Error if leader_port or feedback_port environment variables are not set
set -u

lerobot-calibrate \
    --teleop.type=feedback_leader \
    --teleop.port=$teleop_port \
    --teleop.feedback_port=$feedback_port \
    --teleop.id=my_feedback_leader
