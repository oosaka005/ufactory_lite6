from xarm.wrapper import XArmAPI
import time

ROBOT_IP = "192.168.1.169"

# ==================== POSITIONS (in mm and degrees) ====================
# Format: [x, y, z, roll, pitch, yaw]
# All movements maintain these roll/pitch/yaw values (this is the "align" behavior)

INITIAL_POSITION = [203.3, 0, 167.3, 179.2, 1, 0]  # Safe home position

# Checkpoint 1: Above microplate location (high up for obstacle avoidance)
CHECKPOINT_1_PICKUP = [119.3, -360, 167.3, 179.2, 1, 90.1]

# Microplate pickup position (approach point, before going down)
MICROPLATE_PICKUP_APPROACH = [119.3, -360, 100, 179.2, 1, 90.1]

# Microplate actual pickup (on the plate)
MICROPLATE_PICKUP = [119.3, -360, 74.6, 179.2, 1, 90.1]

# Checkpoint 2: After pickup (lift up, stay over plate area)
CHECKPOINT_2_AFTER_PICKUP = [119.3, -360, 167.3, 179.2, 1, 90.1]
# Checkpoint 3: Moving toward middle (mid-way point for safe pathing)
CHECKPOINT_3_TO_MIDDLE = [232.9, -196.7, 167.3, 179.2, 1, 90.1]
# Checkpoint 4: Moving toward reader (mid-way point for safe pathing)
CHECKPOINT_4_TO_READER = [174, 194, 226, 179.2, 1, -90.1]

# Reader position (approach point)
READER_APPROACH = [68.5, 340.6, 226, 179.2, 1, -90.1]

# Reader placement position (where to place the plate)
READER_PLACEMENT = [68.5, 340.6, 168.6, 179.2, 1, -90.1]

# Checkpoint 5: After placement (lift and move away)
CHECKPOINT_5_AFTER_PLACEMENT = [68.5, 340.6, 226, 179.2, 1, -90.1]

# ==================== MOTION PARAMETERS ====================
APPROACH_SPEED = 30  # mm/s for normal movements
SLOW_SPEED = 20      # mm/s for fine positioning (pickup/placement)
RETREAT_SPEED = 30   # mm/s for moving away

# ==================== HELPER FUNCTIONS ====================

def safe_move(arm, position, speed=50, label="Move"):
    """
    Safely move to a position with constant orientation.
    Returns True if successful, False if failed.
    """
    print(f"\n[{label}] Moving to {position[:3]} (x,y,z)...")
    
    code = arm.set_position(
        x=position[0],
        y=position[1],
        z=position[2],
        roll=position[3],
        pitch=position[4],
        yaw=position[5],
        speed=speed,
        wait=True,
        timeout=30
    )
    
    if code != 0:
        print(f"[{label}] FAILED! Error code: {code}")
        return False
    
    # Wait until motion is complete (might be redundant with wait=True, but added for safety)
    timeout = 30
    start_time = time.time()
    while arm.get_is_moving() and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if time.time() - start_time >= timeout:
        print(f"[{label}] WARNING: Motion timeout")
        return False
    
    print(f"[{label}] Complete")
    return True

def connect_arm(ip):
    """Initialize and ready the arm."""
    print("Connecting to xArm...")
    arm = XArmAPI(ip, enable_heartbeat=True)
    time.sleep(0.5)
    
    # Clear any errors/warnings
    arm.clean_error()
    time.sleep(0.3)
    arm.clean_warn()
    time.sleep(0.3)
    
    # Set mode to position control
    arm.set_mode(0)
    time.sleep(0.3)
    
    # Enable motion
    arm.motion_enable(True)
    time.sleep(0.3)
    
    # Set state to ready
    arm.set_state(0)
    time.sleep(0.5)
    
    print("xArm is ready")
    return arm

def check_arm_ready(arm):
    """Check if arm is in a safe state to operate."""
    # State 2 is "sleeping" on this controller, and it does not block motion.
    # Treat actual error conditions as the readiness gate instead.
    state_result = arm.get_state()
    if isinstance(state_result, tuple) and len(state_result) == 2:
        state_code, state_value = state_result
    else:
        state_code, state_value = 0, state_result
    
    print(f"Arm state: code={state_code}, state={state_value}")
    if arm.has_error:
        print("ERROR: Arm has error code(s)")
        arm.get_err_warn_code(show=True)
        return False
    
    if state_value in (3, 4):
        print(f"ERROR: Arm is not in a usable state ({state_value}).")
        return False
    
    if state_value == 2:
        print("Arm is in sleeping state (2), which is acceptable for this controller.")
    else:
        print("Arm safety checks passed")
    return True

def close_gripper(arm):
    """Close the Lite6 gripper."""
    print("Closing gripper...")
    code = arm.close_lite6_gripper()
    if code == 0:
        time.sleep(0.5)  # Wait for gripper to settle
        print("Gripper closed")
        return True
    else:
        print(f"ERROR: Failed to close gripper (code: {code})")
        return False

def open_gripper(arm):
    """Open the Lite6 gripper."""
    print("Opening gripper...")
    code = arm.open_lite6_gripper()
    if code == 0:
        time.sleep(0.5)  # Wait for gripper to settle
        print("Gripper opened")
        return True
    else:
        print(f"ERROR: Failed to open gripper (code: {code})")
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

# ==================== MAIN WORKFLOW ====================

def pick_and_place_workflow(arm):
    """
    Complete pick-and-place workflow:
    1. Go to initial position
    2. Move to checkpoint 3 (middle)
    3. Move to checkpoint 1 (above microplate)
    4. Approach microplate
    5. Move to microplate location
    6. Pick up microplate (close gripper)
    7. Retract after pickup (checkpoint 2)
    8. Move to checkpoint 3 (middle)
    9. Return to initial position
    10. Move to checkpoint 4 (toward reader)
    11. Approach reader location
    12. Place microplate at reader
    13. Release microplate (open gripper)
    14. Retract from reader (checkpoint 5)
    15. Return to initial position
    """
    
    print("\n" + "="*60)
    print("PICK AND PLACE WORKFLOW")
    print("="*60)
    
    # Step 1: Go to initial position
    if not safe_move(arm, INITIAL_POSITION, APPROACH_SPEED, "Step 1: Initial Position"):
        return False
    
    # Step 2: Move to checkpoint 3 (middle waypoint)
    if not safe_move(arm, CHECKPOINT_3_TO_MIDDLE, APPROACH_SPEED, "Step 2: Checkpoint 3 (Middle)"):
        return False
    
    # Step 3: Move to checkpoint 1 (above microplate)
    if not safe_move(arm, CHECKPOINT_1_PICKUP, APPROACH_SPEED, "Step 3: Checkpoint 1 (Above Microplate)"):
        return False
    
    # Step 4: Approach microplate
    if not safe_move(arm, MICROPLATE_PICKUP_APPROACH, SLOW_SPEED, "Step 4: Microplate Approach"):
        return False
    
    # Step 5: Move to microplate location
    if not safe_move(arm, MICROPLATE_PICKUP, SLOW_SPEED, "Step 5: Microplate Location"):
        return False
    
    # Step 6: Close gripper to pick up
    if not close_gripper(arm):
        print("ERROR: Could not close gripper!")
        return False
    
    # Step 7: Retract after pickup (checkpoint 2)
    if not safe_move(arm, CHECKPOINT_2_AFTER_PICKUP, APPROACH_SPEED, "Step 7: Checkpoint 2 (Retract After Pickup)"):
        return False
    
    # Step 8: Move to checkpoint 3 (middle)
    if not safe_move(arm, CHECKPOINT_3_TO_MIDDLE, APPROACH_SPEED, "Step 8: Checkpoint 3 (Middle)"):
        return False
    
    # Step 9: Return to initial position
    if not safe_move(arm, INITIAL_POSITION, RETREAT_SPEED, "Step 9: Initial Position"):
        return False
    
    # Step 10: Move to checkpoint 4 (toward reader)
    if not safe_move(arm, CHECKPOINT_4_TO_READER, APPROACH_SPEED, "Step 10: Checkpoint 4 (Toward Reader)"):
        return False
    
    # Step 11: Approach reader location
    if not safe_move(arm, READER_APPROACH, SLOW_SPEED, "Step 11: Reader Approach"):
        return False
    
    # Step 12: Move down to reader placement position
    if not safe_move(arm, READER_PLACEMENT, SLOW_SPEED, "Step 12: Reader Placement"):
        return False
    
    time.sleep(1.5)  # Brief pause before releasing
    
    # Step 13: Open gripper to release microplate
    if not open_gripper(arm):
        print("ERROR: Could not open gripper!")
        return False
    
    # Step 14: Retract from reader (checkpoint 5)
    if not safe_move(arm, CHECKPOINT_5_AFTER_PLACEMENT, APPROACH_SPEED, "Step 14: Checkpoint 5 (Retract After Placement)"):
        return False
    
    # Step 15: Return to initial position
    if not safe_move(arm, INITIAL_POSITION, RETREAT_SPEED, "Step 15: Initial Position"):
        return False
    
    print("\n" + "="*60)
    print("WORKFLOW COMPLETE")
    print("="*60)
    return True

def main():
    """Main entry point."""
    try:
        # Connect and initialize
        arm = connect_arm(ROBOT_IP)
        
        # Check arm is ready
        if not check_arm_ready(arm):
            arm.disconnect()
            return
        
        # Run workflow
        success = pick_and_place_workflow(arm)
        
        if success:
            print("\nPick and place completed successfully!")
        else:
            print("\nPick and place workflow encountered an error.")
        
        # Stop and disconnect
        print("\nStopping arm...")
        arm.set_state(4)  # Stop state
        time.sleep(0.5)
        
        stop_gripper(arm)  # Ensure gripper is stopped as well
        arm.disconnect()
        print("Disconnected from robot arm.")
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        try:
            arm.set_state(4)
            stop_gripper(arm)
            arm.disconnect()
        except:
            pass

if __name__ == "__main__":
    main()
