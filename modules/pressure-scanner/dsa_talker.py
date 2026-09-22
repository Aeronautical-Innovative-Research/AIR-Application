import telnetlib
import time

class DSA:
    
    def __init__(self, host, port=23, timeout=5):
        
        self.host = host
        self.port = port
        self.timeout = timeout  # scan timeout
        self.tn = None          # telnet object
    
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
    def send_command(self, command, end_marker, returnBit=False):
        
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
    def scan(self, filename = 'OUTPUT'):
        
        FPS = 1000 # frames per scan
        freq = 125 # [Hz]
        AVG = 10   # frames to average per outputted frame
        
        PERIOD = max(50, 1e6/16/AVG/freq)
        
        self.set_variable('BIN', 0)
        self.set_variable('FORMAT', 0)
        self.set_variable('EU', 1)
        self.set_variable('UNITSCAN', 'PA')
        
        self.set_variable('FPS', FPS)
        self.set_variable('AVG', AVG)
        self.set_variable('PERIOD', PERIOD)
        
        print(f'Starting scan for {FPS} frames...')
        
        start_time = time.time()
        duration = 60
        
        end_marker = f'Frame # {FPS}'.encode('ascii')
        
        # send SCAN command
        self.tn.write(b'SCAN\r\n')
        
        while (time.time() - start_time) <= duration:
            
            try:
                raw_bytes = self.tn.read_until(end_marker, timeout=10)
                time.sleep(0.01)
                raw_bytes += self.tn.read_very_eager()
                
            except EOFError:
                self.close()
                raise EOFError('Connection dropped while scanning.')
            
            raw_data = raw_bytes.decode('ascii', errors='ignore')
            
            with open(rf'DSA-custom talker/{filename}.csv', 'a') as file:
                file.write(raw_data)
                
        print("Scan complete. Parsing data...")