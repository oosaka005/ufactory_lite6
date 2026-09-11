from xarm.wrapper import XArmAPI
import time

ROBOT_IP = "192.168.1.169"  
JOINT_ANGLES = [0, 0, 36.4, 0, 36.4, 91.9]  # Change these values as needed
MOVE_SPEED = 15  # Speed for joint movement in degrees per second

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

def move_arm(arm, angles, speed):
	print(f"Current position: {arm.get_position()}")
	print(f"Moving to {angles} with speed {speed}...")
	
	code = arm.set_servo_angle(angle=angles, speed=speed, wait=True)
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


def main():
	arm = connect_arm(ROBOT_IP)
	
	# Check if arm is ready (better than checking motor_enable_states[0])
	if arm.state != 0:
		print(f"Error: Arm not in ready state. Current state: {arm.state}")
		print("Check if physical E-switch is enabled.")
		arm.disconnect()
		return
	
	if arm.has_error:
		print("Error: Arm has error code(s)")
		arm.get_err_warn_code(show=True)
		arm.disconnect()
		return
	
	print("Arm is ready. Proceeding with movement.")
	move_arm(arm, JOINT_ANGLES, MOVE_SPEED)
	
	# Stop the arm before disconnecting
	print("Stopping arm...")
	arm.set_state(4)
	time.sleep(0.5)
	
	arm.disconnect()
	print("Disconnected from robot arm.")

if __name__ == "__main__":
	main()

##.\.venv\Scripts\Activate