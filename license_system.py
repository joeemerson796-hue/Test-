"""
License System for McAfee Automation Script
Ties license keys to specific devices using hardware fingerprinting
"""
import hashlib
import uuid
import platform
import os
import subprocess

# SECRET KEY - Change this to your own secret (keep it private!)
SECRET_KEY = "McAfee_Automation_2025_Secret_Key_Change_This"

def get_hardware_id():
    """
    Generate a unique hardware ID for this device
    Uses: MAC address, hostname, and system UUID
    """
    # Get MAC address
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                    for elements in range(0,2*6,2)][::-1])

    # Get hostname
    hostname = platform.node()

    # Get system info
    system = platform.system()

    # Try to get disk serial (Windows)
    disk_serial = ""
    try:
        if system == "Windows":
            result = subprocess.check_output("wmic diskdrive get serialnumber", shell=True)
            disk_serial = result.decode().split('\n')[1].strip()
        elif system == "Linux":
            # Try to get disk UUID on Linux
            result = subprocess.check_output("lsblk -no UUID | head -1", shell=True)
            disk_serial = result.decode().strip()
    except:
        disk_serial = "NO_DISK_SERIAL"

    # Combine all hardware info
    hardware_string = f"{mac}:{hostname}:{system}:{disk_serial}"

    # Hash it to create a unique hardware ID
    hardware_id = hashlib.sha256(hardware_string.encode()).hexdigest()

    return hardware_id

def generate_license_key(hardware_id):
    """
    Generate a license key for a specific hardware ID
    Key = HASH(hardware_id + SECRET_KEY)
    """
    combined = f"{hardware_id}:{SECRET_KEY}"
    license_key = hashlib.sha256(combined.encode()).hexdigest()
    return license_key

def validate_license_key(license_key):
    """
    Validate if the license key is correct for this device
    Returns True if valid, False otherwise
    """
    hardware_id = get_hardware_id()
    expected_key = generate_license_key(hardware_id)
    return license_key == expected_key

def save_license_key(license_key):
    """Save license key to file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    license_file = os.path.join(script_dir, "license.key")

    with open(license_file, 'w') as f:
        f.write(license_key)

def load_license_key():
    """Load license key from file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    license_file = os.path.join(script_dir, "license.key")

    if not os.path.exists(license_file):
        return None

    with open(license_file, 'r') as f:
        return f.read().strip()

def check_license():
    """
    Check if the script is licensed for this device
    Returns True if licensed, False otherwise
    """
    license_key = load_license_key()

    if not license_key:
        return False

    return validate_license_key(license_key)

def activate_license(license_key):
    """
    Activate the script with a license key
    Returns True if activation successful, False otherwise
    """
    if validate_license_key(license_key):
        save_license_key(license_key)
        return True
    return False
