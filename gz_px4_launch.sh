#!/bin/bash

cd /Users/Shared/workspace/PX4-Autopilot

export PATH=/Users/Shared/workspace/install/bin:$PATH

pkill -f px4
pkill -f gz
pkill -f ruby

echo "Launching QGroundControl..."
open -a /Applications/QGroundControl.app


PX4_GZ_HEADLESS=0 make px4_sitl gz_tiltrotor