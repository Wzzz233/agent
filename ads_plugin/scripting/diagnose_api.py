"""
Diagnostic: Check if open_design returns the active design
"""
import keysight.ads.de as de
from keysight.ads.de import db_uu

print("="*60)
print("Checking design context...")
print("="*60)

# Check what methods exist to get current/active design
print("\n--- Looking for 'active' or 'current' design methods ---")
for name in dir(db_uu):
    if 'active' in name.lower() or 'current' in name.lower() or 'top' in name.lower():
        print(f"  db_uu.{name}")

for name in dir(de):
    if 'active' in name.lower() or 'current' in name.lower() or 'editor' in name.lower():
        print(f"  de.{name}")

# Try to get the active design
print("\n--- Trying to get active design ---")

# First, let's open the test design
d1 = db_uu.open_design("MyLibrary3_lib:test_circuit:schematic")
print(f"d1 = db_uu.open_design(...): {d1}")
print(f"d1 id: {id(d1)}")
print(f"d1 instances: {len(d1.instances)}")

# Open again
d2 = db_uu.open_design("MyLibrary3_lib:test_circuit:schematic")
print(f"\nd2 = db_uu.open_design(...) again: {d2}")
print(f"d2 id: {id(d2)}")
print(f"d2 instances: {len(d2.instances)}")

# Are they the same object?
print(f"\nd1 is d2: {d1 is d2}")
print(f"d1 == d2: {d1 == d2}")

# Add instance to d1
print("\n--- Adding instance to d1 ---")
inst = d1.add_instance("ads_rflib:R:symbol", (200, 200))
print(f"Added to d1: {inst}")
print(f"d1 instances: {len(d1.instances)}")
print(f"d2 instances: {len(d2.instances)}")

print("\n" + "="*60)
