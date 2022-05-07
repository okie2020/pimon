import sys

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

enable_storage = input(f"{bcolors.HEADER}Do you want to monitor external hard drives? (y/N)\n:y{bcolors.ENDC}")
if enable_storage in ['Y', 'y', 'Yes', 'yes', 'YES']:
    storage_path = input("Enter the path to where your disks are mounted. example: /mnt/disk1\n:").lower().strip()
else:
    print(f"{bcolors.WARNING}Not Enabled{bcolors.ENDC}")
