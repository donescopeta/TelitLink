import socket
import serial
from twisted.internet import reactor
import binascii
import marshal
import time
import threading
connectionCount=0
def splitByIndex(string,ind):
	try:
		a=string[:ind]
		b=string[ind:]
		return a,b
	except:
		return string,""

class connection(threading.Thread):
	def __init__(self,conn,ip,server):
		self.baudSwitching = False
		self.clientAddr = ip
		self.close = False
		self.baudID=''
		self.id = 0
		self.conn = conn
		self.client = None
		self.terminate = False
		self.isModuleInitialized = False
		self.server = server
		self.fire = None
		self.device = None
		self.serial = server.serial
		self.sequences = {
			"b": [ 0 , 0 , False , self.baudChangeSequence ],
			"c": [ 0, 0, False, self.closeConnectionSequence ]
		}
		threading.Thread.__init__(self)

	def acceptConnection(self):
		#print "[TCP] Waiting for connection."
		global connectionCount
		print '[TCP] Connected by:' + self.clientAddr[0]
		csgn=""
		st = ""
		while True:
			try:
				b=self.conn.recv(2048).split(';')
				time.sleep(0.01)
			except: continue
			for c in b:
				if len(c) <= 1 : break
				if c[0] == "$":
					csgn = c[1:]
					print "[TCP] Received device CSGN: ",csgn
					for x in self.server.deviceList:
						if x["csgn"] == csgn:
							self.device=x
					if self.device is None:
						conf = None
						self.conn.send("!dump2MDM;")
						while True:
							try:
								a = self.conn.recv(2048).split(" ",3)
								if a[0] == "@dump2MDM":
									l = int(a[1])
									while  len(a[3]) < l:
										try: a[3] += self.conn.recv(2048)
										except: time.sleep(0.1)
									else:
										st = a[3][:l]
										crc =  binascii.crc_hqx(st,0)
										if crc ^ int(a[2]): st=''
								else: raise
								break
							except:
								time.sleep(0.1)
								continue;
						self.settings = conf = marshal.loads(st)
						self.device = {
							"status": "CONNECTED",
							"csgn": csgn,
							"ip": self.clientAddr[0],
							"port": str(self.server.port),
							"settings" : conf,
							"instance": self,
							"tosend": []
						}
						self.device["active"] = threading.Event()
						self.device["active"].clear()
						self.server.deviceList.append(self.device)
						for ws in self.server.WSinstances:
							reactor.callFromThread(self.server.WS.deviceInfoSend,ws,self.device)
					else:
						up = {"class":"connected"}
						for ws in self.server.WSinstances:
							reactor.callFromThread(self.server.WS.deviceUpdate,ws,str(self.settings["i"][0]),up)
						self.sendVars()
					self.device["status"]="connected"
					self.device["instance"]=self
					self.isModuleInitialized = True
					connectionCount += 1
					self.id = connectionCount
					return True

	def sendVars(self):
		tosend = self.device["tosend"]
		if len(tosend):
			for x,y in self.device["settings"]:
				if x not in tosend: continue
				self.conn.send('@'+x+" "+" ".join(y)+';')
			self.conn.send('!SAVE;')
			del tosend[:]

	def baudChangeSequence(self):
		self.baudSwitching=False
		print "[SERIAL] Changing baud rate to:",bridge.bauds[self.baudID][0]
		self.server.maxSerialPackageSize = bridge.bauds[self.baudID][1]["serial"]["maxPS"]
		self.server.maxTCPPackageSize = bridge.bauds[self.baudID][1]["tcp"]["maxPS"]
		self.server.serial.setBaudrate(int(bridge.bauds[self.baudID][0]))
		return True

	def closeConnectionSequence(self):
		self.serial.write("OK")
		self.conn.close()
		print "[TCP] Connection closed %s." % self.id
		return False

	def findSequence(mode,buf):
		f=None
		i = 0
		lob=len(buf)
		sequence = lambda x,y=mode: [self.sequences[x][y]]
		for x in buf:
			if ( bridge.baudSwitch[sequence('b')[mode]](x) ):
				if ( sequence('b')[mode] == 2 ): self.baudID = x
				if ( sequence('b')[mode] == 4 ):
					sequence('b')[2]=True
					sequence("b")[mode] = 0
					print "Changing baud",self.baudID
				self.sequences["b"][mode] += 1
			else: self.sequences["b"][mode] = 0
			if x == '+':  self.sequences["c"][mode]+=1
			else: self.sequences["c"][mode]=0

	def bridge(self):
		b = ""
		rIp =  ""
		rSr = ""
		tb = 0
		lrIp = 0
		iW = 0
		wC = 0
		oneCharTime = 1/int(self.server.baud)
		while True:
			self.device["active"].wait()
			try:
				b=""
				b=self.conn.recv(256)
				if not b: raise
				rIp+=b
				rIp,b=splitByIndex(rIp,self.server.maxTCPPackageSize)
				if b: raise
			except:
				while rIp != "":
					lrIp = len(rIp)
					try:
					#	if ( lrIp%2 ) > 0:
					#		if lrIp < 2: break
					#		b=rIp[-1:]+b
					#		tb = rIp[:-1].upper().decode("hex")
					#	else: tb=rIp.upper().decode("hex")
					##### ___insted of:
						tb=rIp
					except:
						print "[TCP] Non hexadecimal digits: skipping"
						rIp=""
						b=""
						break
					print "[TCP] " + tb
					try: self.server.serial.write(tb)
					except Exception as e: print e
					#self.findSequence(0,tb)
					rIp=b
					break
			iW = self.server.serial.inWaiting()
			while iW > 0:
				if iW > wC:
					if ( iW < self.server.maxSerialPackageSize ):
						wC = iW
						break
					else: iW = iW-(iW%self.server.maxSerialPackageSize)
				rSr = self.server.serial.read(iW)
				print "[SERIAL] "+rSr,rSr.encode('hex')
				#self.conn.send(rSr.encode("hex"))
				self.conn.send(rSr)
				self.findSequence(1,rSr)
				wC=iW=0
				break
			else:
				if False and ( not rIp ):
					for key,value in self.sequences.items():
						if (value[2]):
							if not ( value[3]() ): break
							value[2] = False

	def run(self):
		print "[TCP] Trying to initialize module"
		moduleInit=threading.Thread(target=self.acceptConnection)
		moduleInit.start()
		moduleInit.join(60)
		if not self.isModuleInitialized:
			self.conn.close()
			print "[TCP] Initialization interruped. Too long response time."
			return
		else:
			print "[TCP] Module initialization successful."
			print "[TCP] Connection id: %s" % self.id
		if self.server.communication_type == communication_style.serial_proxy:
			self.server.setSerial()
			self.serial = self.server.serial
			self.bridge()
		else:
			#self.server.client.connect()
			self.client = self.server.client
			self.bridge_tcp()

	def bridge_tcp(self):
		b = ''
		b2 = ''
		connectionLock = self.client.connectionTrigger
		deviceLock =  self.device["active"]
		t1 = None
		t2 = None
		def if_device_disconnected(self,t1,t2):
			print "[TCP] Device "+self.device["csgn"]+" disconnected"
			self.device["active"].clear()
			self.device["status"] = "disconnected"
			self.device["instance"] = None
			up = {"class":"disconnected"}
			self.conn.close()
			for ws in self.server.WSinstances:
				reactor.callFromThread(self.server.WS.deviceUpdate,ws,self.device["csgn"],up)
			self.join()
			del self
			threading.Thread(target=map,args=[lambda x: x.join(),[t1,t2]]).start()

		def stop():
			while not ( deviceLock.isSet() and connectionLock.isSet() ):
				connectionLock.wait()
				deviceLock.wait()

		def receive_server():
			b=''
			while True:
				#stop()
				try:
					b = self.conn.recv(256)
					if b == '':
						if_device_disconnected(self,t1,t2)
						raise
					try:
						self.server.client.conn.send(b)
						print "[TCP] device -> ",b
					except: self.client.closeConnection()
					b = ''
				except:
					if self.terminate:
						if_device_disconnected(self,t1,t2)
						return
					if not connectionLock.isSet(): time.sleep(1)
					time.sleep(0.005)


		def receive_client():
			while True:
				stop()
				try:
					b2 = self.server.client.conn.recv(256)
					if b2 == '': raise
					print "[TCP] client -> ",b2
					while True:
						try:
							self.conn.send(b2)
							break
						except: time.sleep(0.005)
				except: self.client.closeConnecton()

		t1 = threading.Thread(target=receive_client)
		t2 = threading.Thread(target=receive_server)
		t1.start()
		t2.start()
	#	while True:
	#		deviceLock = self.device["active"]
	#		if not ( deviceLock.isSet() and connectionLock.isSet() ):
	#			stop.clear()
	#			deviceLock.wait()
	#			connectionLock.wait()
	#		elif not stop.isSet():
	#			stop.set()
	#			time.sleep(5)
	#		time.sleep(0.250)

class bridgeClinet:
	modes = { "client" : 1 , "server" : 0 }
	def __init__(self,ip='127.0.0.1',port=1006):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.clientIP = ip
		self.host=ip
		self.port=port
		self.clientPort = port
		self.connectionTrigger = threading.Event()
		self.connectionTrigger.clear()
		self.connector=None
		self.socketBound = False
		self.conn = None

	def closeConnecton(self):
		if not self.connectionTrigger.is_set(): return
		self.connectionTrigger.clear()
		self.conn.close();
		self.connect()

	def connect(self, mode = "server"):
		fmode = lambda x: (bridgeClinet.modes[mode] == bridgeClinet.modes[x])
		if self.connectionTrigger.is_set(): return
		def client_connector():
			while True:
				try:
					self.socket.connect((self.host,self.port))
					#self.socket.settimeout(self.socketTimeout)
					self.conn = self.socket
					self.connectionTrigger.set()
					print "[TCP] Client connection successful."
					return
				except:
					print "[TCP] Cannot connect to a client."
					time.sleep(10)

		def server_listener():
			if not self.socketBound:
				self.socket.bind((self.host,self.port))
				self.socket.listen(1)
				print "[TCP] Client listener started"
				self.socketBound = True
			while True:
				try:
					conn, addr = self.socket.accept()
					print "[TCP] Client connection from:"+addr[0]
					self.conn = conn
					self.connectionTrigger.set()
					return
				except: time.sleep(0.05)
		if fmode("server"):
			self.connector = threading.Thread(target=server_listener)
		elif fmode("client"):
			self.connector = threading.Thread(target=client_connector)
		self.connector.start()

class communication_style:
	threaded = 0
	looped = 1
	tcp_proxy = 0
	serial_proxy = 1


class bridge(threading.Thread):
	states = {"CLIENT":0,"SERVER":1}
	baudSwitch = "\x06252\x13\x10"
	closeSequence = "+++"
	baudSwitch = [
		lambda x : x == "\x06",
		lambda x : x == "\xB2", # ord(x) >= 47  and ( ord(x) <= 57 ),
		lambda x : ord(x) >= 47  and ( ord(x) <= 57 ),
		lambda x : x == "\xB2",  # ord(x) >= 47  and ( ord(x) <= 57 ),
		lambda x : x == "\x8D"#,
		#lambda x:  x == "\x10"
	]

	bauds= {
		"0" : [ '300' , {
			'serial': { "maxPS": 64 ,"limit": 512 },
			'tcp': { "maxPS": 64 ,"limit": 512 },
		}],
		"1" : [ '600', {
			'serial': { "maxPS": 128 ,"limit": 512 },
			'tcp': { "maxPS": 128 ,"limit": 512 },
		}],
		"2" : [ '1200', {
			'serial': { "maxPS": 128 ,"limit": 512 },
			'tcp': { "maxPS": 128 ,"limit": 512 },
		}],
		"3" : [ '2400',{
			'serial': { "maxPS": 128 ,"limit": 512 },
			'tcp': { "maxPS": 128 ,"limit": 512 },
		}],
		"4" : [ '4800', {
			'serial': { "maxPS": 128 ,"limit": 512 },
			'tcp': { "maxPS": 128 ,"limit": 512 },

		}],
		"5" : [ '9600', {
			'serial': { "maxPS": 512 ,"limit": 2048 },
			'tcp': { "maxPS": 512 ,"limit": 2048 },

		}],
		"6" : [ '19200',{
			'serial': { "maxPS": 512 ,"limit": 2048 },
			'tcp': { "maxPS": 512 ,"limit": 2048 },
		}]
	}

	socketTimeout=0.005

	def __init__(self,host,port,com,baud):
		threading.Thread.__init__(self)
		self.host=host
		self.port=port
		self.client = bridgeClinet('127.0.0.1',1006)
		self.com = com
		self.baud = baud
		self.socket = None
		self.serial = None
		self.state = None
		self.WSinstances = None
		self.connections = []
		self.maxSerialPackageSize = 64
		self.maxTCPPackageSize = 64
		self.conn=None
		self.setDefaults()

	def setDefaults(self):
		self.communication_style = communication_style.looped
		self.communication_type = communication_style.tcp_proxy

	def setSerial(self):
		if not ( self.serial is None ) : return
		self.serial = serial.Serial(self.com,self.baud,timeout=1,bytesize=8,\
		stopbits=1,parity='N')
		self.serial.close()
		self.serial.open()
		
	def tcpServer(self):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.bind((self.host,self.port))
		self.socket.listen(1)
		if communication_style.looped == self.communication_style:
			self.socket.setblocking(0)
		elif communication_style.threaded == self.communication_style:
			pass
		self.socket.settimeout(self.socketTimeout)
		return True;

	def run(self):
		conn=None
		addr=None
		a=None
		if self.communication_type == communication_style.tcp_proxy:
			self.client.connect()
		while True:
			try:
				conn, addr = self.socket.accept()
				print "[TCP] Connection from:"+addr[0]
				a = connection(conn,addr,self)
				a.start()
				self.connections.append(a)
			except:
				time.sleep(0.05)
				continue
