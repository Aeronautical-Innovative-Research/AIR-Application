import telnetlib
import time
import numpy as np

# ============================
#
# Commands:
#   calz: CALZ [period] [average] [delay] || CALZ 500 32
#   list cal vars: LIST C
#   
#   scan: SCAN
#   set var: SET <name> <value> || SET FPS 5
#   list scan vars: LIST S
#   
#   stop: STOP   
#   status: STATUS || returns READY|CALZ|SAVE
#   
# SCAN Variables
#   AVG (1-240|16) - int : average
#   FPS (0-2147483648|100) - long int : frames per scan
#   PERIOD (125-65535|500) - int : period == Data Rate = 1/(PERIOD * 16 * AVG)

class DSA:
    
    def __init__(self, host, port=23, timeout=5):
        
        self.host = host
        self.port = port
        self.timeout = timeout  # scan timeout
        self.tn = None          # telnet object
        
        self.data = []
    
    # Connect to DSA Pressure Scanner
    def connect(self):
        print(f'Connecting to {self.host}:{self.port}')
        
        self.tn = telnetlib.Telnet(self.host, self.port, self.timeout)
        
        print('Connected.')
        
    # Close connection
    def close(self):
        if self.tn:
            self.tn.close()
            print('Connection closed.')
            
    # Send DSA commands
    def send_command(self, command, end_marker = None, returnBit=False):
        
        if not self.tn:
            print(f'Command <{command}> sent. No connection found')
            return 'Not connected.'
        
        self.tn.read_very_eager()
        
        full_command = f'{command}\r\n'
        self.tn.write(full_command.encode('ascii'))
        
        start = time.time()
        response = b''
        
        try:
            if end_marker is None:
                while time.time() - start < self.timeout:
                    
                    chunk = self.tn.read_very_eager()
                    
                    if chunk:
                        response += chunk
                        
                    else:
                        time.sleep(0.01)
                        
                response_full = response.decode('ascii', errors='ignore')
            
            else:
                response = self.tn.read_until(end_marker, timeout=self.timeout)
                time.sleep(0.01)
                response += self.tn.read_very_eager()
                
                print(response)
                
                response_full = response.decode('ascii', errors='ignore')
        
        except EOFError:
            print('Connection dropped while scanning')
            raise EOFError('DSA disconnected')
        
        return response_full.strip()
    
    # Modify DSA variables    
    def set_variable(self, name, value):
        return self.send_command(f'SET {name} {value}')
    
     
    @property
    def status(self):
        return self.send_command('STATUS')
    
    # Calibrate DSA Scanner
    def calz(self):
        print('Starting CalZ')
        return self.send_command('CALZ')
    
    # Execute DSA Scan
    def scan(self, fps = 1000, avg = 10, freq = 125, filename = 'OUTPUT'):
        
        self.data = []
        
        period = int(max(125, round(1e6 / 16 / avg / freq)))
        
        self.set_variable('BIN', 0)
        self.set_variable('FORMAT', 0)
        self.set_variable('EU', 1)
        self.set_variable('UNITSCAN', 'PA')
        
        self.set_variable('FPS', fps)
        self.set_variable('AVG', avg)
        self.set_variable('PERIOD', period)
        
        print(f'Starting scan for {fps} frames...')
        
        # send SCAN command
        self.tn.write(b'SCAN\r\n')
        
        start = time.time()
            
        while time.time() - start < 10:
            
            try:
                raw_bytes = self.tn.read_very_eager()
                
            except EOFError:
                self.clsoe()
                raise
            
            if raw_bytes:
                data = raw_bytes.decode("ascii", errors="replace")
                self.data.append(data)

            time.sleep(0.01)
        
        print("Scan complete. Parsing data...")
        
    
    def parse(self, *lines):
        
        data = self.data
        
        linebyline = [x.rstrip('\r').split(' ') for x in ''.join(data).split('\n') if x != '']
        
        formated_data = {}
        
        k = 0
        for line in linebyline:
            if line[0] == 'Frame': # if line is frame header
                k = line[2]
                formated_data[k] = {}
                
            else:
                formated_data[k].update({
                    int(line[0]): float(line[1])
                })
        
        # Pressure
        
        pressure_data = {}
        ports = []
        
        for frame_num, frame_data in formated_data.items():
            
            if not ports: 
                ports = list(frame_data.keys())
            
            pressure_data[frame_num] = [
                {
                    port: val for port, val in frame_data.items()
                    if len(lines) == 0 or port in lines
                },
                np.mean([val for port, val in frame_data.items()
                    if len(lines) != 0 and port not in lines])
            ]
            
        velocity_data = {}
        
        for frame_num, (dyna_pressure, static_pressure) in pressure_data.items():
            
            vel_data = {}
            
            for port, pres in dyna_pressure.items():
                
                Q = abs(pres - static_pressure)
                vel = np.sqrt(2 / 1.225 * Q)
                
                vel_data[port] = vel
                
            velocity_data[frame_num] = vel_data
        
        
        return pressure_data, velocity_data