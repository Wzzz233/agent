import skrf as rf
from skrf.media.mline import MLine
import matplotlib.pyplot as plt
import scipy.constants as const
from scipy.optimize import newton

# 1. Define Substrate (FR4)
freq_val = 6 # GHz
frequency = rf.Frequency(freq_val, freq_val, 1, 'ghz')

er = 4.4
h = 1.6e-3  # m
t = 35e-6   # m
tand = 0.02

# 2. Synthesis Function for Width
# MLine takes w (width) and returns Z0. We need to inverse this.
def z0_error(w_guess):
    # Create MLine with guessed width
    # Note: MLine uses 'ep_r' for relative permittivity
    ms = MLine(frequency=frequency, z0_port=50, w=w_guess, h=h, t=t, ep_r=er, tand=tand)
    # Return difference from 50 Ohm
    return ms.z0[0].real - 50.0

# Initial guess: h is a good order of magnitude
print("Synthesizing Width for 50 Ohm...")
width_m = newton(z0_error, x0=h)

print(f"--- Calculation Results ---")
print(f"Frequency: {freq_val} GHz")
print(f"Substrate: FR4 (Er={er}, H={h*1000}mm)")
print(f"Target Impedance: 50.0 Ohm")
print(f"Calculated Width: {width_m*1000:.4f} mm")

# 3. Create Final Media Object
ms_actual = MLine(frequency=frequency, z0_port=50, w=width_m, h=h, t=t, ep_r=er, tand=tand)

# 4. Calculate Length for 90 degrees (Quarter Wave)
# electrical_length (radians) = beta * length
gamma = ms_actual.gamma
beta = gamma.imag[0] # propagation constant (imaginary part)

# Target: 90 degrees = pi/2 radians
target_theta = const.pi / 2
length_m = target_theta / beta

print(f"Target Electrical Length: 90 degrees (Quarter Wave)")
print(f"Calculated Physical Length: {length_m*1000:.4f} mm")

# 5. Draw Layout
plt.figure(figsize=(10, 4))
w_mm = width_m * 1000
l_mm = length_m * 1000

# Substrate
margin = 5
plt.gca().add_patch(plt.Rectangle((-margin, -w_mm/2 - margin), l_mm + 2*margin, w_mm + 2*margin, color='#e0e0e0', label='FR4 Substrate'))

# Trace
plt.gca().add_patch(plt.Rectangle((0, -w_mm/2), l_mm, w_mm, color='orange', alpha=0.9, label='Microstrip (Cu)'))

# Dimensions Annotations
plt.arrow(0, w_mm/2 + 2, l_mm, 0, length_includes_head=True, head_width=0.5, color='black')
plt.text(l_mm/2, w_mm/2 + 2.5, f'L = {l_mm:.2f} mm', ha='center', va='bottom')

plt.arrow(-2, -w_mm/2, 0, w_mm, length_includes_head=True, head_width=0.5, color='black')
plt.text(-2.5, 0, f'W = {w_mm:.2f} mm', ha='right', va='center', rotation=90)

# Ports
plt.scatter([0], [0], color='red', marker='>', s=100, label='Port 1', zorder=10)
plt.scatter([l_mm], [0], color='red', marker='<', s=100, label='Port 2', zorder=10)

plt.xlim(-margin-2, l_mm + margin + 2)
plt.ylim(-w_mm - margin - 2, w_mm + margin + 5)
plt.xlabel('x (mm)')
plt.ylabel('y (mm)')
plt.title(f'Level 1 Task: 6GHz Quarter-Wave Line Layout\\nWidth={w_mm:.3f}mm, Length={l_mm:.3f}mm')
plt.grid(True, linestyle=':', alpha=0.6)
plt.legend(loc='lower right')
plt.axis('equal')

output_file = '/home/wzzz/clawd/ads_agent_dev/level1_result.png'
plt.savefig(output_file)
print(f"Visualization saved to {output_file}")
