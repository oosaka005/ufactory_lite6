from xarm.wrapper import XArmAPI
import time

ROBOT_IP = "192.168.1.169"  
# XYZ position: [x, y, z, roll, pitch, yaw] in mm and degrees
TARGET_POSITION = [203.3, 60, 167.3, 180, 0, -92]  # Change these values as needed
MOVE_SPEED = 50  # Speed for cartesian movement in mm/s

# Connect to the xArm robot and initialize it
def connect_arm(ip):
	arm = XArmAPI(ip, enable_heartbeat=True)
	time.sleep(0.5)
	
	# Clear errors and warnings first
	arm.clean_error()
	time.sleep(0.3)
	arm.clean_warn()
	time.sleep(0.3)
	
	# Set mode to position control before enabling motion
	arm.set_mode(0)      # 0: position mode
	time.sleep(0.3)
	
	# Enable motion
	arm.motion_enable(True)
	time.sleep(0.3)
	
	# Set state to ready
	arm.set_state(0)     # 0: ready
	time.sleep(0.5)
	
	return arm

def move_arm(arm, position, speed):
	print(f"Current position: {arm.get_position()}")
	print(f"Moving to XYZ {position[:3]} with speed {speed} mm/s...")
	
	# position = [x, y, z, roll, pitch, yaw]
	code = arm.set_position(x=position[0], y=position[1], z=position[2], 
	                         roll=position[3], pitch=position[4], yaw=position[5],
	                         speed=speed, wait=True)
	print(f"Move command return code: {code}")
	
	# Wait until motion is actually complete
	timeout = 30  # 30 second timeout
	start_time = time.time()
	while arm.get_is_moving() and (time.time() - start_time) < timeout:
		time.sleep(0.1)
	
	if time.time() - start_time >= timeout:
		print("Warning: Motion timeout reached")
	else:
		print("Motion complete")
	
	print(f"New position: {arm.get_position()}")

def close_gripper(arm):
	"""Close the Lite6 gripper."""
	print("\n[GRIPPER] Closing gripper...")
	code = arm.close_lite6_gripper()
	if code == 0:
		print("[GRIPPER] Gripper closed successfully")
		time.sleep(0.5)  # Wait for gripper to settle
		return True
	else:
		print(f"[GRIPPER] ERROR: Failed to close gripper (code: {code})")
		return False

def open_gripper(arm):
	"""Open the Lite6 gripper."""
	print("\n[GRIPPER] Opening gripper...")
	code = arm.open_lite6_gripper()
	if code == 0:
		print("[GRIPPER] Gripper opened successfully")
		time.sleep(0.5)  # Wait for gripper to settle
		return True
	else:
		print(f"[GRIPPER] ERROR: Failed to open gripper (code: {code})")
		return False

def stop_gripper(arm):
	"""Stop the Lite6 gripper."""
	print("\n[GRIPPER] Stopping gripper...")
	code = arm.stop_lite6_gripper()
	if code == 0:
		print("[GRIPPER] Gripper stopped successfully")
		time.sleep(0.5)  # Wait for gripper to settle
		return True
	else:
		print(f"[GRIPPER] ERROR: Failed to stop gripper (code: {code})")
		return False


def main():
	arm = connect_arm(ROBOT_IP)
	
	# State 2 is "sleeping" on this controller, and it does not block motion.
	# Treat actual error conditions as the readiness gate instead.
	state_result = arm.get_state()
	if isinstance(state_result, tuple) and len(state_result) == 2:
		state_code, state_value = state_result
	else:
		state_code, state_value = 0, state_result

	print(f"Arm state: code={state_code}, state={state_value}")
	if arm.has_error:
		print("Error: Arm has error code(s)")
		arm.get_err_warn_code(show=True)
		arm.disconnect()
		return

	if state_value in (3, 4):
		print(f"Error: Arm is not in a usable state ({state_value}).")
		arm.disconnect()
		return

	if state_value == 2:
		print("Arm is in sleeping state (2), which is acceptable for this controller.")
	else:
		print("Arm is ready. Proceeding with movement.")
	
	# Test sequence: move -> close gripper -> move -> open gripper
	print("\n" + "="*60)
	print("GRIPPER TEST SEQUENCE")
	print("="*60)
	
	# Move to target position
	print("\n[STEP 1] Moving to target position...")
	move_arm(arm, TARGET_POSITION, MOVE_SPEED)
	
	# Close gripper at target position
	print("\n[STEP 2] Testing gripper close...")
	if not close_gripper(arm):
		print("ERROR: Gripper close failed! Attempting recovery...")
		arm.set_state(4)
		arm.disconnect()
		return
	
	# Wait a moment with gripper closed
	print("\n[STEP 3] Holding for 2 seconds...")
	time.sleep(2)
	
	# Open gripper
	print("\n[STEP 4] Testing gripper open...")
	if not open_gripper(arm):
		print("ERROR: Gripper open failed! Attempting recovery...")
		arm.set_state(4)
		arm.disconnect()
		return
	
	print("\n" + "="*60)
	print("GRIPPER TEST COMPLETE")
	print("="*60)
	
	# Stop the arm before disconnecting (state 4 = stop, no auto-recovery)
	print("\nStopping arm...")
	arm.set_state(4)
	time.sleep(0.5)
	
	stop_gripper(arm)  # Ensure gripper is stopped as well
	arm.disconnect()
	print("Disconnected from robot arm.")

if __name__ == "__main__":
	main()

##.\.venv\Scripts\Activate