import paramiko
REMOTE_IP = '192.168.0.100'   
USERNAME = 'Asclepion'        
PASSWORD = 'Asclepion'        
SCRIPT_PATH = '/home/Asclepion/Desktop/git/restore_IV_position.py'

def execute_remote_script():
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(REMOTE_IP, username=USERNAME, password=PASSWORD)
        stdin, stdout, stderr = ssh_client.exec_command(f'python3 {SCRIPT_PATH}')
        output = stdout.read().decode()
        error = stderr.read().decode()
        if output:
            print("Output:\n", output)
        if error:
            print("Error:\n", error)
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        
        ssh_client.close()

if __name__ == '__main__':
    execute_remote_script()