import time

from myproject.health_check import start_pulse_server

if __name__ == "__main__":
    # Enable healthcheck
    start_pulse_server()
    print("Hello world!")
    time.sleep(60)
