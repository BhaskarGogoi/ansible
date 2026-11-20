import os
import time
import boto3


# AWS region where the EC2 instances are created
# AWS_REGION = "ap-south-2"
AWS_REGION = "eu-west-1"

# File name for the dynamically generated Ansible inventory file
INVENTORY_FILE = "dynamic_inventory"

# Path to the private SSH key on the Master Instance
SSH_KEY_PATH = "~/.ssh/id_rsa"


def get_latest_ubuntu_ami():
    # Queries AWS for the latest official Ubuntu AMI
    try:
        ec2_client = boto3.client("ec2", region_name=AWS_REGION)

        response = ec2_client.describe_images(
            Owners=["099720109477"],
            Filters=[
                {
                    "Name": "name",
                    "Values": ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"],
                },
                {"Name": "state", "Values": ["available"]},
                {"Name": "architecture", "Values": ["x86_64"]},
            ],
        )

        images = response.get("Images", [])

        if not images:
            print(f"\nERROR: No suitable Ubuntu AMI found in region '{AWS_REGION}'.")
            return None

        latest_image = max(images, key=lambda img: img.get("CreationDate", ""))
        ami_id = latest_image["ImageId"]
        ami_name = latest_image.get("Name", "Unknown")

        print(f"\nSelected latest Ubuntu AMI: {ami_id} ({ami_name})")
        return ami_id

    except Exception as e:
        print(f"\nERROR: Failed to retrieve latest Ubuntu AMI: {e}")
        return None


def run_playbook(playbook, extra_vars=None, inventory=None):
    # This function takes a YAML 'playbook' filename and executes it using os.system()
    command = f"ansible-playbook {playbook}"

    if inventory:
        command += f" -i {inventory}"

    if extra_vars:
        command += f' -e "{extra_vars}"'

    print(f"\nRunning: {command}")
    exit_code = os.system(command)

    if exit_code != 0:
        print(f"\nERROR: Playbook {playbook} failed to execute properly.")
        return False

    return True


def get_number(prompt):
    # This function repeatedly prompts the user until they enter a valid number
    # between 1 and 2 inclusive, and returns the integer value.
    while True:
        value = input(prompt).strip()
        if value in ("1", "2"):
            return int(value)
        print("Invalid input. Please enter either 1 or 2.")


def get_instances_for_group(group_name):
    # This function uses a boto3 EC2 resource object to filter for running EC2 instances
    instances = []
    try:
        ec2 = boto3.resource("ec2", region_name=AWS_REGION)

        instance_iterator = ec2.instances.filter(
            Filters=[
                {"Name": "tag:AnsibleEC2Group", "Values": [group_name]},
                {"Name": "instance-state-name", "Values": ["running"]},
            ]
        )

        for instance in instance_iterator:
            if instance.public_ip_address:
                instances.append(instance)

    except Exception as e:
        print(f"\nERROR: Failed to retrieve EC2 instances from AWS: {e}")

    return instances


def create_dynamic_inventory(group_name, expected_count):
    # This function waits until the expected number of running instances in
    # 'group_name' have public IP addresses assigned, and writes those IP
    # addresses into the Ansible inventory file.
    print(f"\nWaiting for AWS to assign public IP addresses for {group_name}...")

    instances = []

    # Check every 10 seconds (up to 30 attempts) until public IPs are ready
    for attempt in range(30):
        instances = get_instances_for_group(group_name)

        if len(instances) >= expected_count:
            break

        print(
            f"  Attempt {attempt + 1}/30: Found {len(instances)} of {expected_count} "
            f"running instance(s) with public IPs. Waiting 10s..."
        )
        time.sleep(10)

    if len(instances) < expected_count:
        print(
            f"\nERROR: Expected {expected_count} running instance(s) for "
            f"{group_name}, but found {len(instances)}."
        )
        return None

    try:
        with open(INVENTORY_FILE, "w") as inventory:
            inventory.write("[target_instances]\n")

            for instance in instances:
                inventory.write(
                    f"{instance.public_ip_address} "
                    f"ansible_user=ubuntu "
                    f"ansible_ssh_private_key_file={SSH_KEY_PATH}\n"
                )
    except Exception as e:
        print(f"\nERROR: Could not write inventory file '{INVENTORY_FILE}': {e}")
        return None

    print(f"\nDynamic inventory file '{INVENTORY_FILE}' created with hosts:")
    for instance in instances:
        print(f"  - {instance.public_ip_address} (Instance ID: {instance.id})")

    return INVENTORY_FILE


def main():
    # Main function that asks the user how many EC2 instances to launch for two
    # groups, fetches the latest Ubuntu AMI, runs launch_instances.yaml, asks
    # which group should host Apache2, generates the inventory file for that
    # group and runs install_apache.yaml.
    print("=== AWS EC2 & Apache2 Ansible Automation ===")

    group1_count = get_number("Enter number of instances for Group 1 (1-2): ")
    group2_count = get_number("Enter number of instances for Group 2 (1-2): ")

    print("\n--- Step 1: Fetching Latest Ubuntu AMI & Launching EC2 Instances ---")

    ami_id = get_latest_ubuntu_ami()
    if not ami_id:
        return

    success = run_playbook(
        "launch_instances.yaml",
        extra_vars=f"group1_count={group1_count} group2_count={group2_count} ami_id={ami_id}",
    )
    if not success:
        return

    choice = get_number(
        "\nWhich group should host the Apache2 server? (Enter '1' or '2'): "
    )

    if choice == 1:
        selected_group = "Group1"
        selected_count = group1_count
    else:
        selected_group = "Group2"
        selected_count = group2_count

    print(f"\n--- Step 2: Generating Dynamic Inventory for {selected_group} ---")

    inventory = create_dynamic_inventory(selected_group, selected_count)
    if not inventory:
        return

    # Wait 30 seconds before running the second playbook so the Ubuntu OS
    # inside the newly launched EC2 instances finishes booting and starts
    # the SSH service on port 22.
    print(
        "\nWaiting 30 seconds for Ubuntu OS boot and SSH service "
        f"initialization on {selected_group} instances before connecting..."
    )
    time.sleep(30)

    print(f"\n--- Step 3: Installing Apache2 on {selected_group} ---")

    success = run_playbook("install_apache.yaml", inventory=inventory)

    if not success:
        print("\nApache2 installation failed.")
        return

    print("\n=== Complete ===")


if __name__ == "__main__":
    main()