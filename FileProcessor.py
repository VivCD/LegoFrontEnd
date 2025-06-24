import subprocess
import time
import queue
import threading

stop_event = threading.Event()

def read_pipe_forever(output_queue: queue.Queue):
    ssh_command = [
        "ssh",
        "root@172.16.16.111",
        "cat /root/LegoRobotOutputFile/backend_sending_node_data"
    ]

    while not stop_event.is_set():
        try:
            with subprocess.Popen(ssh_command, stdout=subprocess.PIPE, text=True) as proc:
                for line in proc.stdout:
                    line = line.strip()
                    if stop_event.is_set():
                        proc.terminate()
                        return
                    output_queue.put(line)
                    if line == 'x':
                        stop_event.set()
                        return
        except Exception as e:
            print(f"[PIPE ERROR] {str(e)}")
            if not stop_event.is_set():
                time.sleep(1)



def write_x():
    print("[PIPE DEBUG] Sending termination signal 'x'")
    ssh_command = [
        "ssh",
        "root@172.16.16.111",
        "echo -n x > /root/LegoRobotOutputFile/backend_sending_node_data"
    ]
    subprocess.run(ssh_command)