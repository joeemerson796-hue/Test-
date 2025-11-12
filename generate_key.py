"""
License Key Generator
Use this script to generate license keys for other devices

HOW TO USE:
1. Your friend runs mcafee_automation.py on their device
2. They get their Hardware ID from the error message
3. You run this script and enter their Hardware ID
4. Give them the generated license key
5. They enter the key to activate the script
"""
from license_system import generate_license_key, get_hardware_id

def main():
    print("=" * 60)
    print("McAfee Automation - License Key Generator")
    print("=" * 60)
    print()

    print("Choose an option:")
    print("1. Generate key for THIS device")
    print("2. Generate key for ANOTHER device (need Hardware ID)")
    print()

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        # Generate for current device
        hardware_id = get_hardware_id()
        print()
        print("=" * 60)
        print(f"Hardware ID: {hardware_id}")
        print("=" * 60)
        print()

        license_key = generate_license_key(hardware_id)
        print("Generated License Key:")
        print("-" * 60)
        print(license_key)
        print("-" * 60)
        print()
        print("Copy this key and use it to activate the script!")

    elif choice == "2":
        # Generate for another device
        print()
        print("Enter the Hardware ID from the other device:")
        hardware_id = input("Hardware ID: ").strip()

        if len(hardware_id) != 64:
            print()
            print("❌ Error: Invalid Hardware ID format!")
            print("Hardware ID should be 64 characters long.")
            return

        license_key = generate_license_key(hardware_id)
        print()
        print("=" * 60)
        print("Generated License Key for that device:")
        print("-" * 60)
        print(license_key)
        print("-" * 60)
        print()
        print("Send this key to your friend!")

    else:
        print("❌ Invalid choice!")

    print()
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
