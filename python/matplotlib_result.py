import numpy as np
import matplotlib.pyplot as plt

W  = np.array([1.8,2.0,2.2,2.4]) #kg
V = np.array([15,20,25,30,35,40]) #km/h

A = 0.15*1 #m^2
rho = 1.225 #kg/m^3
mew = 1.81e-5 #kg/m/s

V_m = V*1000/3600 #m/s

W_grid, V_m_grid = np.meshgrid(W, V_m)

#equations
CL_matrix = 2*W_grid / (V_m_grid**2*A*rho)


fig = plt.figure(figsize=(10,7))
ax = fig.add_subplot(111, projection='3d')
surf = ax.plot_surface(W_grid, V_m_grid, CL_matrix, cmap='viridis')

ax.set_title("CL vs W and V")
ax.set_xlabel("Weight (kg)")
ax.set_ylabel("Velocity (m/s)")
ax.set_zlabel("CL")

fig.colorbar(surf,ax=ax, shrink=0.5, aspect=5, label='$C_L$ Scale')
plt.show()

print("V_m = ", W)
print("CL = ", CL_matrix)