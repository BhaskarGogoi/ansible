## How to run this ansible program on a AWS EC2 instance
### A.	Create and Prepare SSH Key Pair
 *	Log in to the AWS Management Console and go to the EC2 Dashboard.
 *	On the left navigation pane, under Network & Security, click Key Pairs. 
 *	Click the orange Create key pair button in the top right.
 *	Name the key **ansible-key** (so it perfectly matches with the YAML playbook). 
 *	Leave the Key pair type as RSA. For Private key file format, select **.pem**.
 *	Click Create key pair. The .pem file will automatically download to your computer. 
 *	Open PuTTYgen, click Load to import the .pem key, and click Save private key to convert and save it as a .ppk file.

 ### B.	Connect and Configure the EC2 Master Instance
 *	Connect to your Linux EC2 instance using PuTTY and your generated **.ppk** key. 
 *	Open the original **ansible-key.pem** file on your machine using Notepad and copy its entire contents. 
 *	In your EC2 instance terminal, open the SSH identity file: 
```
    nano ~/.ssh/id_rsa
``` 
 *	Paste the copied key contents, save, and exit. Secure the file by running:  
 ```
    chmod 0600 ~/.ssh/id_rsa
```
 *	Next, set up your AWS credentials directory and file:
 ``` 
    mkdir -p ~/.aws 
    nano ~/.aws/credentials 
```
 *	Copy and paste your AWS access keys (IAM user keys) into this file, save, and exit. Follow the below format.
```
    aws_access_key_id = <YOUR ACCESS KEY>
    aws_secret_access_key = <YOUR SECRET KEY>
    region = <YOUR REGION> 
```
### C.	Install Dependencies
Install the required packages by running the following commands on your master EC2 instance:
``` 
    sudo apt update
    sudo apt install ansible
    sudo apt install python3-boto3
```
### D. Run The Program
```
    python3 ansible_runner.py
```