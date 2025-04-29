#!/usr/bin/env python3
"""
EmuNinja Runner Script

This script provides a convenient way to run the EmuNinja emulator with
common configurations.
"""

import os
import sys
from pathlib import Path

# Ensure the script can be run from any directory
script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(script_dir))

# Import the main function from the main module
from src.main import main

if __name__ == "__main__":
    # If no arguments are provided, use default settings
    if len(sys.argv) == 1:
        print("EmuNinja - Device Terminal Equipment Emulator")
        print("=============================================")
        print("No arguments provided. Choose a mode to run:")
        print("1. Serial Mode (requires a serial port)")
        print("2. TCP Server Mode (listens on localhost:6000)")
        print("3. Custom (pass your own arguments)")

        choice = input("Enter your choice (1-3): ")

        if choice == "1":
            # Prompt for serial port
            port = input("Enter serial port (e.g., COM3 or /dev/ttyUSB0): ")
            args = [
                "--transport",
                "serial",
                "--port",
                port,
                "--baud",
                "9600",
                "--rules",
                str(script_dir / "examples" / "rules.yml"),
                "--rx-end",
                "\r\n",
                "--tx-end",
                "\r\n",
                "--debug",
            ]
        elif choice == "2":
            args = [
                "--transport",
                "tcp",
                "--host",
                "0.0.0.0",
                "--tcp-port",
                "6000",
                "--rules",
                str(script_dir / "examples" / "rules.yml"),
                "--rx-end",
                "\n",
                "--tx-end",
                "\n",
                "--debug",
            ]
        elif choice == "3":
            print("Run with your own arguments, e.g.:")
            print(
                f"python {sys.argv[0]} --transport tcp --host 0.0.0.0 --tcp-port 5000 --rules examples/rules.yml"
            )
            sys.exit(0)
        else:
            print("Invalid choice. Exiting.")
            sys.exit(1)
    else:
        # Use the provided arguments
        args = sys.argv[1:]

    # Run the emulator with the selected arguments
    sys.exit(main(args))
