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
    print("[PIPE DEBUG] Starting pipe reader thread")
    while not stop_event.is_set():
        with subprocess.Popen(ssh_command, stdout=subprocess.PIPE, text=True) as proc:
            print("[PIPE DEBUG] SSH subprocess started")
            try:
                for line in proc.stdout:
                    if stop_event.is_set():
                        break
                    line = line.strip()
                    if line:
                        print(f"[PIPE DEBUG] Received line: {line}")
                        output_queue.put(line)
                        if line == 'x':
                            print("[PIPE DEBUG] Received termination signal 'x'")
                            stop_event.set()
                            return
                    else:
                        print("[PIPE DEBUG] Received empty line")
            except Exception as e:
                print(f"[PIPE ERROR] Error reading from SSH pipe: {e}")
            print("[PIPE DEBUG] SSH subprocess ended, will restart in 1 second")
        time.sleep(1)
    print("[PIPE DEBUG] Pipe reader thread exiting due to stop_event")


def write_x():
    print("[PIPE DEBUG] Sending termination signal 'x'")
    ssh_command = [
        "ssh",
        "root@172.16.16.111",
        "echo -n x > /root/LegoRobotOutputFile/backend_sending_node_data"
    ]
    subprocess.run(ssh_command)