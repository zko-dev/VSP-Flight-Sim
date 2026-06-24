# VSP-Flight-Sim
OpenVSP driven aircraft analysis tool &amp; gazebo SITL flight sim.

# Description
Terminal based code package that allows direct control of VSPAero’s solver ranging from scheduled batch sweeps to turn-based geometric modification

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

Integrate a direct topic plugin for Gazebo, building a direct a flight sim directly with openvsp geometry and solver result to simulate flight stability & behavior. 
