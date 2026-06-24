# VSP-Flight-Sim (Pre-beta)
OpenVSP driven aircraft analysis tool &amp; gazebo SITL flight sim.

# Description
Terminal based code package that allows direct control of VSPAero’s solver ranging from scheduled batch sweeps to turn-based geometric modification

![Plot_example](/vsp_flight_sim/output/Plot_example.png)

Broken into 3 major components: 
1. OpenVSP itself <- allows user defined wing geom, control surface definitions
2. run_sim.sh <- main executive for VLM batch config, solver .csv generation, and parser for results visualization
3. gz_px4_launch.sh <- gazebo-px4 launcher for SITL flight sim

# What this package does: 
Significantly speeds up aircraft design validation, and prints out a .csv which can be analyzed quickly instead of looking at the GUI for manual interpolation.

For research:
CFD Result still viewable in VSPAero GUI
Custom plotting tool using plotly python, we can automate a full aircraft analysis if scripted correctly to collect an aircraft’s stability via alpha, beta sweep -> Trim model through 3D plot -> CL,CD at different flying conditions and therefore infer it’s flight range.

For aircraft prototyping:
Creates a Kerbal-Space-Program alike environment for rapid iterative design, allows designer to grasp a tangible feel of the aircraft stability behavior before ever touching the hardcore flight physics often only taught in B.S. level aerospace engineering.

# To Do:
Right now run_sim.sh is running. Slowly working on the gazebo topics and degenGeom model import.
Verified sweeping variables:
- CG
- Alpha
- Beta
- Elevator
- Aileron
- Mach sweep
Need to verify:
- Re
**Only VLM is necessary

Integrate a direct topic plugin for Gazebo, building a direct a flight sim directly with openvsp geometry and solver result to simulate flight stability & behavior. 

# Setup: 
1. Create a local folder, git pull from this repo
2. Download OpenVSP 3.50
3. install python 3.13 (currently only 3.13 as gazebo-jetty does not support newer)
4. source venv, activate it
5. chmod +x setup.sh
6. run ./setup.sh to install all required dependencies
7. Setup complete!

# How to use? 
1. Get your openvsp geometry ready
2. Run "Prep-solver" to parse its geometry
3. Setup solver config in vspaero_run.py
4. chmod +x run_sim.sh
5. Run ./run_sim.sh
6. After solver is complete, run Flight_Calc.ipynb to reveal the simulation result
7. chmod +x gz_px4_launch.sh
8. Run ./gz_px4_launch.sh, it should open up the simulation environment (I will include the installation steps in the future)

# Disclaimer:

This project relies on [OpenVSP](http://openvsp.org) for parametric aircraft geometry and conceptual design.
