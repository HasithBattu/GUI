import paramiko

def shutdown_raspberry_pi(hostname, port, username, password):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port=port, username=username, password=password)
        stdin, stdout, stderr = ssh.exec_command('sudo shutdown now')
        stdout.channel.recv_exit_status()
        
        print("Shutdown command sent successfully.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        
    finally:
        ssh.close()

if __name__ == "__main__":
    hostname = '192.168.0.100'
    port = 22
    username = 'Asclepion'
    password = 'Asclepion'
    
    shutdown_raspberry_pi(hostname, port, username, password)
