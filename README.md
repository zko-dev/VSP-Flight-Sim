# VSP-Flight-Sim (Pre-beta)
OpenVSP driven aircraft analysis tool &amp; gazebo SITL flight sim.

# Description
This is a scripting based VSPAero wrapper that allows extended/direct control of the solver bypassing the GUI. Allows you to schedule batch sweeps according to different geometric modifications including airfoil comparison studies, parametric wing modifications and ability to simulate stability given varying CG locations.
![cfd](/Media/cfd.png)

Broken into 3 major components: 
1. OpenVSP itself <- takes user defined wing geom, control surface definitions.
2. run_sim.sh <- main executive for VLM batch config, solver .csv generation, and parser for custom results visualization.
3. gz_px4_launch.sh <- gazebo-px4 launcher for SITL flight sim, remote controlled flight inside the simulated space.

# Why? 
Standalone OpenVSP can be confusing if you don't know what you're looking for. Each run is limited to one geometric configuration at once. 
By moving from the GUI to script, we can significantly speeds up computation labor by concatenating control surface sweeps, airfoil comparison, and unlock customizable workflow for your experiment. Prints out a .csv which can be analyzed flexibly either using this code or your method of analysis.

For research:
CFD Result still viewable in VSPAero GUI
Custom plotting tool using plotly python, we can automate a full aircraft analysis if scripted correctly to collect an aircraft’s stability via alpha, elevator sweep -> interpolate trimmed condition at CMy=0 -> identifying CL_req and its associated CD at different flying velocities and therefore infer it’s flight range.

![Batch_summary](/Media/Batch_summary.png)
![3D_Plot_example](/Media/3D_Plot_example.png)
![Trimmed_elevator](/Media/Trimmed_elevator.png)
![Drag_polar](/Media/Drag_polar_cases.png)
![Trimmed_range](/Media/Trimmed_range.png)

For aircraft prototyping:
Creates a KSP-like environment for rapid iterative design, allows designer to grasp a tangible feel of the aircraft stability behavior before diving into optimization.

![px4-gazebo](/Media/px4-gazebo.png)
https://youtu.be/vLZKRHpSPtk
^Idea is to allow you, the user, to plug in a remote and fly in the sim!

# To Do:
At the moment, only run_sim.sh is fully setup. Slowly working on the gazebo topics and degenGeom model import. Currently just running PX4_GZ_HEADLESS=0 make px4_sitl gz_tiltrotor

Integrate a direct topic plugin for Gazebo, building a direct a flight sim directly with openvsp geometry and solver result to simulate flight stability & behavior. 

# Installation: 
1. Create a local folder, git pull from this repo
2. Download OpenVSP 3.50
3. Install python 3.13 (currently only 3.13 as gazebo-jetty does not support newer)
4. git pull https://github.com/zko-dev/VSP-Flight-Sim.git
5. source venv, activate it
6. chmod +x setup.sh
7. run ./setup.sh to install all required dependencies
8. Setup complete!

# How to use? 
1. Get your openvsp geometry ready
2. Run "Prep-solver" to parse its geometry
3. Setup solver config in vspaero_run.py
4. chmod +x run_sim.sh
5. Run ./run_sim.sh
6. After solver is complete, run Flight_Calc.ipynb to reveal the simulation result
7. chmod +x gz_px4_launch.sh
8. Run ./gz_px4_launch.sh, it should open up the simulation environment (I will include the installation steps in the future)
[![Watch the video](https://img.youtube.com/vi/VIDEO_ID/0.jpg)](https://youtu.be/k7GOzeA1epw)

# Disclaimer:

This project relies on [OpenVSP](http://openvsp.org) for parametric aircraft geometry and conceptual design.
