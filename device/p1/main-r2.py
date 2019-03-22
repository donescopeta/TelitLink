import MOD
import SER
import MDM
import sys
import GPIO
import binascii
import marshal

def isError(s):
	if s.find("ERROR") >= 0:
		print "Error: \r\n", s
		sys.exit()

reboot = lambda x =MDM.send: x("AT#REBOOT",0)

def forward(i=1, o=1,pack=[],of = 0):
	end,isnsep,offset,c = pack[1:]
	offset = offset + i
	if o:
		while offset < end:
			if isnsep(offset):
				pack[3] = offset
				return of,c(offset)
			offset = offset + 1
			of = of + 1
		else:
			pack[3] = offset
			return of,""
	else:
		pack[3] = offset
		if offset < end: return 0,c(offset)
		return 0,""
		
## Utilities
def GPIO_handlePin((pin,dir,value)):
	GPIO.setIOdir(pin,value,dir)
	return lambda value=None, pin=pin:\
		not (value is None) and \
			GPIO.setIOvalue(pin,value) \
		or	GPIO.getIOvalue(pin)
## ________________

def sendATlist(l,s=MDM.send,r=MDM.receive, counter=MOD.secCounter, sleep=MOD.sleep):
	timer = 0
	for x in l:
		timer = counter() + 10
		if x:
			try:
				s(x)
				while not r() and ( timer >= counter() ): sleep(10)
			except: pass

class settingsDB:
	def __init__(self):
		self.Keys = None
		self.byId = []
		self.byKey = {}
		self.lenght = 0

	def def_values(self,mfile=None,\
		template = (\
			("atstart",()),\
			("id",("0",)),\
			("sms_limit", (8,)),\
#			("watchdog_time", (3600,)),\
			("maxlate", (300,)),\
			("name",("telit1",)),\
			("desc",("test device",)),\
			("sms_checktime", (3600,)),\
			("timecheck",(3600,)),\
			("maxoptime",(46,)),\
			("serverAddr",("193,253,56,3","43234")),\
			("gsmuser",('',)),\
			("gsmpass",(''),),\
			("gpio_watchdog",('1','1','1')),\
			("gpio_optics",('1','1','1')),\
			("charm",())
	)):
		t = None
		self.lenght = l = len(template)
		#bd = self.byId
		bh = self.byKey
		if mfile:
			bh.update(marshal.load(mfile))
		else:
			for i in xrange(l):
				t = list(template[i][1])
				#bd.append(t)
				bh[template[i][0]] = t

	def def_values_form(self,file="config.bin"):
		f = open(file,'r')
		try:
			self.def_values(f)
			f.close()
		except:
			f.close()
			unlink(file)
			reboot()

	def dump(self,file="config.bin"):
		f = open(file,'w')
		marshal.dump(self.byKey,f)
		#l = lambda y,x, f = f, d = marshal.dump: d(x,f)
		#reduce(l,self.byId)
		f.close()

	def load(self,data="config.bin"):
		i = 0
		f = open(data,'r')
		l = marshal.load
		b = self.byId
		for i in xrange(self.lenght):
			b[i][0] = l(f)
		f.close()

	def loads(self,data):
		b = self.byId
		l = marshal.loads
		for i in xrange(self.lenght):
			b[i][0] = l(data)

	def dump2MDM(self,m=MDM.send,crc=binascii.crc_hqx):
		d = marshal.dumps(self.byKey)
		m("@dump2MDM" +" "+ str(len(d)) + " " + str(crc(d,0)) + " " + d,2)


class config:
	def __init__(self, module):
		self.module = module
		self.rt = 1  # return
		self.log = []
		self.settings = self.module.settings
		self.forward = None
		#self.commands =


	def marshal(self,l):
		"""Decodes marshal configuration"""
		p = self.pack
		c = p[2]
		p[3] = d = c + l
		self.module.settings.loads(p[0][c:d])
		
	def encode(self,f="config"):
		o = open(f, 'w')
		m = self.module
		charm = reduce(lambda x,y: x+'/'+y,m.charm,"")+'/;'
		#config = ""+\
		#	'~'+m.serverip+':'+m.serverport+';'+\
		#	'#'+m.i+\
		#	"%"+m.name+\
		#	'%'+charm+\
		#	"@sms_limit="+m.maxSMSinMEM+';'
		c = '~'+m.serverip+':'+m.serverport+';'
		c = c + '#'+m.i
		c = c +" %"+m.name
		c = c + '%'+charm
		c = c + "@sms_limit="+m.maxSMSinMEM
		o.write(c)
		o.close()

	def packVars(self,data,end,f = " \n\t\015".find):
		b = []
		b.extend([\
			data ,\
			end ,\
				lambda x = 0, d = b, f = f:\
					f(d[0][x]) < 0,
			0,
			lambda x, p=b: p[0][x]
		])
		self.data = lambda x = 0, f = b: f[0][x]
		self.end = lambda f = b: f[1]
		e = forward
		e.func_defaults = ( 1, 1, b ,0 )
		self.pack = b
		self.forward = e
		return e
		
	def parse(self, data, end,fchr = "@!~&#'".find):
		oprs = parserOprs
		self.rt = 1
		forward = self.packVars(data,end)
		c_now = forward(0)[1]
		while c_now:
			#if c_now == '\n' forward(0)
			oprs[fchr(c_now) + 1](self)
			c_now = forward()[1]
		return self.rt

	def parseExec(self):
		# - Lista  funkcji które maja być wykonane po znalezieniu
		# - odpowiedniego kodu poprzedzonego znakiem "!".
		MOD.watchdogEnable(600)
		mopers = self.module.operations.get
		a = ""
		t = ""
		b = 0
		c_now = ""
		forward = self.forward
		c_now = forward(1)[1]
		while not b and c_now and ( c_now != ';' ):
			a = a + c_now
			b,c_now = forward()
		if b < 1: self.rt = mopers(a)(self.module)
		MOD.watchdogDisable()
		return 1

	def parseServerAddress(self):
		# Konfiguracja pakietu oraz portu w formacie ~<adres>:<port>;.
		forward = self.forward
		c_now = forward()[1]
		print "Parsing server settings."
		address = ["", ""]
		p = 0
		while ( c_now and c_now != ';' ):
			if c_now == ":":
				p = p + 1
			else:
				address[p] = address[p] + c_now
			c_now = forward()[1]
		m = self.module
		del m.serverAddr[:]
		m.serverAddr.extend(address)
		print address[0],address[1]
		return 1

	def parseConfigLine(self):
		# - Znak "#" powoduje do wprowadznie konfiguracji nastepujacej po nim
		# - Za wyjątkiem sytuacji w której pd znaku "#" występuje znak "?",
		#	w tej sytuacji moduł wysyła na interfejs konfiguracje w formacie:
		#	<Id>%<Nazwa modułu>%<Opis>%<Harmonogram>
		argsLine = [""]
		charm = []
		argsIn = 0
		isnEnd = 1
		a = ""
		c_now = ""
		forward = self.forward
		m = self.module
		c_now = forward()[1]
		if c_now == "?":
			MDM.send(self.module.getDeviceInfoLine(), 1)
			return
		else:
			print "Parsing properties."
			while ( c_now and c_now != ';' ):
				a = argsLine[argsIn]
				if c_now == '/' and a:
					charm.append(argsLine[argsIn])
					argsLine[argsIn] = ""
				elif c_now == "%":
					print "Argument: ", a
					argsIn = argsIn + 1
					argsLine.append("")
				else:
					argsLine[argsIn] = a + c_now
				c_now = forward()[1]
			if argsIn:
				m.i[0] = argsLine[0]
				m.name[0] = argsLine[1]
				m.desc[0] = argsLine[2]
			if len(charm) and m.mainLoop:
				m.mainLoop.parseCharmSequence(charm)
			print \
				"id: ", m.i[0],'\r\n',\
				"name: ", m.name[0],'\r\n',\
				"desc: ", m.desc[0],'\r\n',\
				"charm: ", charm,'\r\n',\
				"parsing charm...",'\r\n'
			print "OK"
		return 1

	def parseCommand(self):
		forward=self.forward
		c_now = ""
		isnEnd = 1
		f,c_now = forward()
		valname = ""
		value = ""
		arguments = []
		is_assign = 0
		is_keyworld = 0
		buf = ""
		while 1:
			while c_now and ( c_now != ';' ):
				if not is_keyworld and ( c_now == '=' ):
					if not is_assign:
						is_assign = 1
						c_now = forward()[1]
						break
				elif not is_assign and f:
					if not is_keyworld:
						is_keyworld = 1
						break
					if buf:
						arguments.append(buf)
						buf = ""
				if c_now == '"':
					c_now = forward(1,0)[1]
					while c_now and ( c_now != '"' ):
						buf = buf + c_now
						c_now = forward(1,0)[1]
					f,c_now = forward()
					continue
				buf = buf + c_now
				f,c_now = forward()
			else:
				if is_assign:
					if not value: value = buf
				elif is_keyworld and buf: arguments.append(buf)
				break
			valname = buf
			buf = ""

		if valname:
			if valname == "set_charm" and len(arguments):
				self.module.charm.extend(arguments)
				m.mainLoop.parseCharmSequence(arguments)
			elif valname == "at" and len(arguments): sendATlist(arguments)
			else:
				try:
					key = self.settings.byKey[valname]
					del key[:]
					if len(arguments): key.extend(arguments)
					elif value: key.append(value)
					else: key.append("")
				except: print "Parser: invalid value: " + valname

	def onstr(self):
		isstring = lambda d, o: d.find("'''", o, o + 3) >= 0
		string = ""
		p = self.pack
		end = p[1]
		if not isstring(p[0], p[3]): return 0
		forward(3,0)
		endifstring = p[0].find("'''", p[3], end)
		if endifstring > -1:
			string = p[0][p[3]:endifstring]
			p[3] = endifstring + 3
			forward(0)
		else:
			print "string not suspended"
		filename = ""
		stream = 0
		ex = 0  # exeit loop
		c_now = forward(0,0)[1]
		while c_now:
			if stream:
				if not (c_now in " ;"):
					f = 0
					while not f:
						if c_now == ';' or not c_now:
							ex = 1
							break
						else:
							filename = filename + c_now
						f,c_now = forward()
					if ex or ( f <= 1 and c_now == ";" ):
						# success writing to file
						o = open(filename, 'w')
						o.write(string)
						o.close()
						break
					else:
						break
			if c_now == '>':
				stream = 1
				c_now = forward()[1];
		return 1


parserOprs = [
	lambda x: 0,
	config.parseCommand, # react to "@"
	config.parseExec, # react to "!"
	config.parseServerAddress, # react to "~"
	config.parseServerAddress, # react to "&"
	config.parseConfigLine, # react to "#"
	config.onstr #react to "'"
]

parse_cclk = lambda t: int(t[17:19]) * 3600 + (int(t[20:22]) * 60)


def parse_cclk_T(t):
	i = 0
	for x in t:
		print str(i) + " -> " + x
		i = i + 1
	print t[17:19]
	print t[20:22]
	try:
		return parse_cclk(t)
	except:
		print '"' + t + '"'


class mInit:
	"Obiekt obsługi modułu."
	# -- Wakunki dla kolejnych znaków dla zmiany prędkości. -->
	operations = {
		"config": lambda module: module.getConfigurationFromFile(),
		"dump2MDM": lambda module: module.settings.dump2MDM(),
		"SAVE": lambda module:\
			module.settings.dump() or 1 and \
			module.mainLoop.dump(),
		"REBOOT": lambda module: MDM.send("AT#REBOOT\r",5),
		"NONE": lambda module: 0
	}
	def add_operation(self,name,func):
		self.operations[name]=func

	m_net = (("" \
				  'AT+CGDCONT = 1,"IP","internet","0.0.0.0"\r',),(
				  'AT+FCLASS=0\r',
				  'AT#SGACT=1,1\r',
				  'AT#SCFG=1,1,0,0,600,1',
				  'AT#SCFGEXT=1,0,0,30,0,1\r')\
			)
	m_init = "" \
				  "AT&f\r" \
				  "ATE0\r" \
				  "ATZ\r" \
				  "AT#SIMDET=1\r" \
				  "AT#selint=2\r" \
				  'AT#SGACT=1,0\r'

	# -- zmiana prędkości RS, rozmiaru fakietu, bufora w zależności od kodu > 0 , <6 .
	bauds = {
		"0": ['300', {
			'serial': {"maxPS": 128, "limit": 512},
			'tcp': {"maxPS": 128, "limit": 512},
		}],
		"1": ['600', {
			'serial': {"maxPS": 128, "limit": 512},
			'tcp': {"maxPS": 128, "limit": 512},
		}],
		"2": ['1200', {
			'serial': {"maxPS": 128, "limit": 512},
			'tcp': {"maxPS": 128, "limit": 512},
		}],
		"3": ['2400', {
			'serial': {"maxPS": 128, "limit": 512},
			'tcp': {"maxPS": 128, "limit": 512},
		}],
		"4": ['4800', {
			'serial': {"maxPS": 128, "limit": 512},
			'tcp': {"maxPS": 128, "limit": 512},

		}],
		"5": ['9600', {
			'serial': {"maxPS": 512, "limit": 2048},
			'tcp': {"maxPS": 512, "limit": 2048},

		}],
		"6": ['19200', {
			'serial': {"maxPS": 512, "limit": 2048},
			'tcp': {"maxPS": 512, "limit": 2048},
		}]
	}

	def getTime(self):
		# MDM.send("ATE\r",1)
		# MDM.receive(0)
		# MDM.send("AT+CCLK?\r",10)
		# cclk=MDM.read()
		# print cclk
		# self.time = parse_cclk_T(cclk)
		t = MOD.secCounter() % 86400
		self.time = t
		return t

	def getConfigurationFromFile(self):
		"""Funkcja pobiera konfiguracje z pliku o nazwie
			"config". """
		f = open("config", 'r')
		c = f.read()
		# print c,"length: ",len(c)
		a = config(self)
		a.parse(c, len(c))

	def getDeviceInfoLine(self):
		"""	Funkcja przygotowuje konfiguracje do wysłania
			przez TCP do serwera."""
		s = ""
		for x in self.charm:
			s = s + x + "/"
		return "#" + self.i[0] + '%' \
			   + self.name[0] + '%' \
			   + "CONNECTED" + '%' \
			   + self.desc[0] + "%" \
			   + s + ';'

	def getCSGN(self):
		MDM.receive(0)
		MDM.send('AT+CGSN\r', 10)
		MOD.sleep(10)
		a = MDM.receive(10)
		self.CSGN = a[2:17]

	def net(self):
		"""	Funkcja Wprowadza komendy AT odpowiedzialne
			za komunikacje internetnetową"""
		b = ""
		i = 0
		a1,a2 = self.m_net
		list = map(\
			(lambda x,y,s=(self.settingsByKey): x + s[y][0] +'"\r'),\
			('AT#USERID="','AT#PASSW="'),\
			('gsmuser',"gsmpass")\
		)
		for a in a1,list,a2:
			for c in a:
				MDM.send(str(c), 10)
				i = 0
				while i < 20:
					b = MDM.receive(10)
					if not b:
						i = i + 1
						MOD.sleep(5)
						continue
					print "Network Initializer: ", c
					isError(b)
					break
				# self.ipAddr=b[:b.find("\r")]
				else:
					print "ERROR to receive command responce."

	def __init__(self,settings):
		self.timer = MOD.secCounter()
		self.settings=settings
		self.settingsByKey = settingsByKey = self.settings.byKey
		SER.set_speed('300')
		#self.charmParsed = settingsByKey['charm']
		self.name = settingsByKey['name']
		self.i = settingsByKey['id']
		self.serverAddr = settingsByKey['serverAddr']
		self.maxLate = settingsByKey['maxlate']
		self.desc = settingsByKey['desc']
		self.charm = settingsByKey['charm']
		self.mainLoop = None
		print self.timer
		# Komendy odpowiedzialne za komunikacje internetową
		SER.setDSR(0)
		SER.setCTS(0)
		SER.setDCD(0)
		self.time = 0
		self.SMS = SMS(self)
		self.ipAddr = ""
		self.getTime()
		atstart = settingsByKey["atstart"]
		if len(atstart): sendATlist(atstart)
		self.maxSMSinMEM = settingsByKey["sms_limit"]
		MDM.send(self.m_init, 10)
		MDM.receive(20)


class conTmp:
	""" Wrapper dla interfejsów MDM oraz SER w funkcji "ser2mdm" """

	def __init__(self, api=None, maxPS=512):
		self.api = api
		if api is MDM:
			self.isMDM = 1
			self.isSER = 0
			self.name = "MDM"
			self.send = lambda b: MDM.send(b, 1)
			self.alive = self.MDM_connection_alive
		else:
			self.isSER = 1
			self.isMDM = 0
			self.name = "SER"
			self.limit = 256
			self.alive = lambda: 1
			self.send = lambda b: SER.send(b)
		self.maxPS = maxPS
		self.baudSec = 0
		self.baud = None
		self.isMDM = 0
		self.baudId = "-1"
		self.b = ""
		self.ex = 0
		self.p = 0
		self.c = 0
		self.name = ""
		self.limit = 1024
		self.l = 0
		self.reset = 0
		self.nextInterface = None

	def MDM_connection_alive(self):
		return self.b.find("NO CARRIER", self.l - 12) < 0

class TelitLink_GPIO_handling:
	def __init__(self,module):
		sets = lambda k, x = module.settings.byKey: map(int,x["gpio_"+k])
		self.OpticalModule =  GPIO_handlePin(sets("optics"))
		self.watchdog =  GPIO_handlePin(sets("watchdog"))
		self.module = module
		module.add_operation("WATCHDOG", lambda module,w=self.watchdog: w(1))

class TelitLink_Client_Connection:

	baudSwitch = (
		lambda x: x == "\x06",
		lambda x: x == "\xB2",
		lambda x: ord(x) >= 47 and (ord(x) <= 57) and 2,
		lambda x: x == "\xB2",
		lambda x: x == "\x8D" and 3,
	)
	def __init__(self,module):
		self.module = module
		c = config(self.module)
		self.GPIO = TelitLink_GPIO_handling(module)
		module.add_operation("START", lambda module,TelitLink = self: \
			TelitLink.ser2mdm_bridge() \
		)
		module.add_operation("CONNECT", lambda module,TelitLink = self: 
			TelitLink.connectToServer(module)
		)
		
	def connectToServer(self,module):
		"""Funkcja rozpoczyna komunikacje z serwerem"""
		i = 0;
		module.getCSGN()
		MDM.send("AT#SH=1\r", 1)
		MDM.receive(0)
		print module.serverAddr
		ip,port = module.serverAddr[0:2]
		command = "AT#SD=1,0," + port + "," + ip + "\r"
		if sendAndCheck(command, "CONNECT", 5, 5, 5):
			print "--SOCKET OPENED--"
			MDM.send(str("$" + module.CSGN), 1)
			self.serverCommunication()
		else:
			print "Cannot connect to socket"
			print "--SOCKET FAILURE--"
			MDM.send("AT#SH=1", 1)
			MDM.receive(0)
			#module = mInit()
			#m.net()
			

	def serverCommunication(self,\
			counter = MOD.secCounter,
			read = MDM.read,
			sleep = MOD.sleep
		):
		"""	Funkcja przekazuje komunikacje do funkcji
			parseConfiguration odpowiedzialnej za
			interpretacje konfiguracji."""
		x = "";
		loD = 0
		timeout = counter() + 60
		p = config(self.module)
		while timeout > counter():
			x = read()
			if x == "":
				sleep(10)
				continue
			loD = len(x)
			e = p.parse(x, loD)
			if e == 0: return
			timeout = counter() + 60
		del p
		MDM.send("+++", 10)
		MDM.receive(50)
		MDM.send("AT#SH=1",10)
		MDM.receive(10)
		
	def ser2mdm_bridge(self):
		"""
		Funkcja wymienia dane międzi interfejsami SER i MDM
		Jednocześnie kontrolując rozmiar wysyłanych pakietów oraz
		ilość danych oczekujących na wysłanie Interfejsy SER i
		MDM są umieszczone w instanciach(md,sr)  klasy "conTmp".
		Atrybut con.nextInterfeace zawiera następny interfejs
		na który ma za zadanie operować funkcja .Jednocześnie
		prawdzając czy w komunikacji nie występuje sekwencja
		zmiany prędkośći interfejsu SER.
		"""

		baudSwitching = 0
		md = conTmp(MDM)
		sr = conTmp(SER)
		sr.nextInterface = md
		md.nextInterface = sr
		empty = 0
		ackpos = -1
		lBS = len(self.baudSwitch) - 1
		con = md
		c = ""
		rB = ""
		findSequences = self.ser2mdm_findSequences
		MDM.send("OK", 1)
		timeout = 0
		isBaudDeafult = 1
		
		def LoopExit(con,optics=self.GPIO.OpticalModule):
			print "[MDM] connection not alive"
			con.send("AT#SH=1\r")
			optics(0)
			return 0

		self.GPIO.OpticalModule(1)
		print "SER2MDM Started."
		equal = lambda a, b, c: (a == b) and (c == a)  # lambda a,b,c: reduce(lambda x,y: x == y and x,[a,b],c)
		while 1:
			if equal(md.l, md.p, md.c) and (sr.l == sr.p):
				if baudSwitching > 0:
					baud = mInit.bauds[md.baudId]
					SER.set_speed(baud[0])
					print "SER2MDM Changing baud to: ", baud[0]
					sr.maxPS = baud[1]["serial"]["maxPS"]
					sr.limit = baud[1]["serial"]["limit"]
					md.maxPS = baud[1]["tcp"]["maxPS"]
					md.limit = baud[1]["tcp"]["limit"]
					sr.reset = 1
					isBaudDeafult = 0
					md.baud = None
					baudSwitching = 0
				if con.ex >= 3:
					return
				for i in [md, sr]:
					if i.reset:
						print "Buffer cleaning."
						i.c = 0
						i.p = 0
						i.b = ""
						i.l = 0
						i.reset = 0

			MOD.watchdogReset()
			while 1:
				con = con.nextInterface
				if not con.reset:
					rB = con.api.receive(1)
					lrB = len(rB)
					if lrB > 0:
						con.b = con.b[:con.l] + rB
						con.l = con.l + lrB
						if con.l >= con.limit: con.reset = 1
						rB = ""
				empty = con.l - con.p
				if empty > 0:
					if empty >= con.maxPS:
						a = con.b[con.p:con.l]
						con.nextInterface.send(a)
						con.p = con.p + con.maxPS
						break
					else:
						a = con.b[con.p:con.l]
						con.nextInterface.send(a)
						con.p = con.l
					break
				elif isBaudDeafult:
					if con.alive():
						continue
					else: return LoopExit(con)
				elif not timeout:
					timeout = MOD.secCounter() + 10
					continue
				elif timeout <= MOD.secCounter():
					print "Return to 300 bps."
					SER.set_speed('300')
					timeout = 0
					isBaudDeafult = 1
			# print "Packages sended."
			timeout = 0
			MOD.watchdogReset()
			if baudSwitching or con.isSER: continue
			# Finding baud change sequence.
			baudSwitching = findSequences(con, lBS)
	
	def ser2mdm_findSequences(self, con, lBS):
		ackpos = 0
		b = con.baudSec
		bfind = con.b.find
		while 1:
			while not b:
				# print "finding ACK"
				ackpos = bfind("\x06", con.c)
				if ackpos < 0:
					con.c = con.l
					return 0
				print "<ACK> character found"
				con.c = ackpos + 1
				b = 1
			else:
				bs = self.baudSwitch
				a = 0

			while con.c < con.p:
				c = con.b[con.c]
				con.c = con.c + 1
				a = bs[b](c)
				if a:
					b = b + 1
					if a == 1: continue
					if a == 2:
						con.baudId = c
						continue
					if a == 3:
						baudSwitching = 1
						con.baudSec = 0
						con.reset = 1
						con.nextInterface.reset = 1
						con.c = con.l
						return 1
				else:
					b = 0
					con.baudId = 0
					break
			else:
				con.baudSec = b
				return 0
			# if c == '+':
			#	con.ex = con.ex + 1
			#	continue
			# else: con.ex=0
		# con.c = con.l


def sendAndCheck(command="AT\r", commit="OK", s=10, retryR=3, retryS=1, timeout=5):
	"""
		Funkcja wysyła komendy AT oraz sprawdza ich
		wartość zwrotną. Wrazie nietrzymania wartości
		zwrotnej funkcja ponawia próbe jej odebrania.
		Wrazie przekroczenie limitu prób odebrania
		wartości zwrotnej ("retryR" razy). Funkcja
		ponawia próbe wywołania komendy AT (retryS razy)
	"""
	i = 0
	c = e = None
	while i < retryS:
		MDM.receive(1)
		# if a[:-1]!="\r": a+="\r"
		e = MDM.send(command, s)
		for a in range(0, retryR):
			c = MDM.receive(10)
			if c.find(commit) > -1: return 1
			MOD.sleep(timeout)
		i = i + 1
	return 0


class SMS:
	def __init__(self,module):
		self.allowedNumbers = [
			"+48796752703",
			"+48601593746"
		]

		MDM.send('ATE0\r', 2)
		self.prepare()
		self.messageFlag = 0
		self.messages = {}
		self.messagePos = ""
		module.add_operation("SMSCHECK", lambda module,SMS = self: \
			SMS.smsCheck(module) \
		)

	def smsCheck(self,module):
		print "Checking messages"
		if self.isMessage():
			number, message = self.receiveMessage()
			print "SMS from", number
			config(module).parse(message, len(message))
			if int(self.messagePos) >= module.maxSMSinMEM[0]:
				self.del_all_SMS()


	def prepare(self):
		MDM.send('AT+CMGF=1\r', 2)
		MDM.send('AT+CNMI=2,1,0,0,0\r', 2)

	def getMessage(self, msgid):
		msg = self.messages.get(msgid)
		if msg: return msg
		MDM.receive(10)
		MDM.send('AT+CMGR=' + str(msgid) + '\r', 2)
		SMScontent = ""
		t = 0
		while not SMScontent:
			SMScontent = MDM.receive(15)
			if t >= 5:
				print "[SMS] Cannot get message number", msgid, "\r"
				return ""
			t = t + 1
		self.messages[msgid] = SMScontent
		return SMScontent

	def getSMSnumber(self):
		if not self.messageFlag:
			return 0

		SMScontent = self.getMessage(self.messagePos)  # send the read message command
		b = SMScontent.find('"+')  # Identify the start of the number
		return SMScontent[b + 1:b + 13]  # Extract the number

	def getSMSmessage(self):
		if not self.messageFlag:
			return 0
		SMScontent = self.getMessage(self.messagePos)
		# extract message from response
		return SMScontent[SMScontent.find('\n', 4): len(SMScontent)]

	def isMessage(self):
		res = MDM.receive(5)
		a = res.find('+CMTI: "SM",')
		if (a != -1):
			firstdigit_pos = a + 12
			self.messagePos = res[firstdigit_pos:-2]
			print "Message id is", self.messagePos
			self.messageFlag = 1
			return 1
		else:
			self.messageFlag = 0
			return 0

	def receiveMessage(self):
		SMSnumber = self.getSMSnumber()
		SMSmessage = self.getSMSmessage()
		return SMSnumber, SMSmessage

	def sendSMS(self, number, smstext):
		# Send command for sending message
		a = MDM.send('AT+CMGS="' + number + '"\r', 2)
		# clear receive buffer
		res = MDM.receive(10)
		a = MDM.send(smstext, 2)  # Send body of message
		# this terminates the message and sends it
		a = MDM.sendbyte(0x1A, 2)  # terminating the message require ctrl-z
		return ()

	def del_all_SMS(self,SMSpos=1):
		delSMS_command = 'AT+CMGD=' + str(SMSpos) + ',4\r'
		if sendAndCheck("AT+CMGL\r","OK",10,5,3) \
		and sendAndCheck(delSMS_command, "OK",10,5,3):
				print "All messages deleted."
		else: print "cannot delete messages"
		self.prepare()
		return ()


time = 0

def fileExists(name):
	try:
		open(name,'r').close()
		return 1
	except: return 0


toSecondsSince2000 = lambda ( year, month, day ),\
	sum = lambda x,y: x+y,\
	Mdays = (31,28,31,30,31,31,30,31,30,31): \
	(\
		reduce( sum  ,Mdays[:month - 1] ,( month > 2 and not (year%4) ) ) + \
		( ( year - 1 ) / 4 ) + \
		( year * 365 ) + \
		day \
	) * 86400

class mainLoop2:
	def __init__(self,module,filename=""):
		self.module = module
		module.mainLoop = self
		self.maxLate = maxlate = int(module.maxLate[0])
		self.charm = ch = []
		if filename:
			try:
				d = marshal.load
				f = open(filename,'r')
				self.charmMatrix = matrix = map(int,d(f))
				self.charmMatrixOp = matrixop = d(f)
				self.daily = daily = d(f)
				self.intervals = intervs = d(f)
				#print matrix,matrixop,daily,intervs
				f.close()
			except:
				f.close()
				unlink(filename)
				reboot()
		else:
			self.charmMatrix = matrix = []
			self.charmMatrixOp = matrixop = []
			self.intervals = intervs = []
			self.daily = daily = []
			
		self.charmOp = op = {}
		self.charmLenght = 0
		ins = self.insertInOrder
		self.operations = opers = module.operations.get
		self.f_args=(\
			(intervs.append, daily.append, matrixop.insert, ins, matrix.extend, ch, maxlate),\
			(opers,module,ch,op,ins,ch.pop,matrix,matrixop,maxlate),\
			(opers, ins, op),\
			(ch.insert, ch, 0)\
		)

	def insertInOrder(self,time, l):
		ins,a,r = self.f_args[3]
		while r < l and (time > a[r]): r = r + 1
		ins(r,time)
		return r

	def dump(self,filename="charm.bin", d=marshal.dump):
		f = open(filename,'w')
		d(self.charmMatrix,f)
		d(self.charmMatrixOp,f)
		d(self.daily,f)
		d(self.intervals,f)
		f.close()

	def parseCharmSequence(self,seqs, mode=(["daily","inter"].index)):
#		a = list(self.f_args[0][0:4])
#		print a
		interval, daily, matrix, inserttime, mat, c, maxLate = self.f_args[0]
		modeI = None
		t = m = h = y = m = d = i = 0
		secends = 0
		for seq in seqs:
			if not seq : continue
			try: aDate, aTime, aOper = seq.split('-')
			except:
				print "Parsing Charm: Splitting error"
				continue
			h, m = map(int,aTime.split(':'))
			time = h * 3600 + ( m * 60 )
			try :
				(mode(aDate) and interval or daily)( \
					(aOper,time >= maxLate and time or maxLate)\
				)
			except: # date
				try: secends = toSecondsSince2000(map(int,aDate.split('/'))) + time
				except:
					print "Parsing Charm: invalid date format."
					continue
				matrix(inserttime(secends,i),aOper)
				i = i + 1
		mat(c)
		self.charmLenght = i

	def setIntervals(self, intervs, l, time, daily = 0, newtime=0):
		ot , ins, charmOp = self.f_args[2]
		for x,y in intervs:
			z = ot(x)
			if z:
				newtime = int( time + y )
				charmOp[newtime] = ( z, daily and 86400 or y )
				ins(newtime,l)
				l = l + 1
		return l

	def main_charm_while(self,\
			defri = lambda defr: ( defr >> 31 & 0x1, abs(defr) )\
		):
		opers, module, charm, charmOp, ins, line, matrix, matrixop, maxLate = self.f_args[1]
		lenght = self.charmLenght
		counter = MOD.secCounter
		powerSaving = MOD.powerSaving
		lineD = ()
		op,interv = ( 0, 0 )
		defaultInterv = (\
			opers("SMSCHECK") or \
			opers("CONNECT") or \
			( lambda m : sys.exit() ),\
		86400 )
		newtime = 0
		r = i = 0
		timeW = 0
		timeD = 0
		sign = 0
		## __set_dates__
		#print charm,charmOp,matrix,matrixop
		while r < lenght:
			i = opers(matrixop[r])
			if i: charmOp[matrix[r]] = ( i, 0 )
			r = r + 1

		## __set_intervals__
		setIntervs = self.setIntervals
		time = counter()
		lenght = setIntervs(self.intervals,lenght,time) #intervals
		today = time - (time % 86400)
		lenght = setIntervs(self.daily,lenght,today,1) #today
		## __main_loop__
		while 1:
			timeW = line(0)
			sign, timeD = defri(timeW - counter())
			#print sign,timeD,timeW,maxLate
			op, interv = lineD = charmOp[timeW]
			while 1:
				if timeD >= maxLate:
					if sign: break
					print "Waiting: " + str(timeD)
					powerSaving(timeD)
					timeD = timeW - counter()
					continue
				op(module)
				break

			if interv: # for daylt and intervals
				newtime = timeW + interv
				charmOp[newtime] = lineD
				ins(newtime, lenght - 1)
			else: lenght = lenght - 1
			del charmOp[timeW]

			if lenght: continue
			#if charm is empty
			length = 1
			newtime = counter()
			charmOp[newtime] = defaultInterv
			self.charm.append(newtime)

if __name__ == "__main__":
	settings = None
	configbin = 0
	m = None
	if fileExists("config!"):
		fileExists("config") and \
			unlink("config")
		rename("config!","config")
		configbin = 0
	else: configbin = fileExists("config.bin")

	while 1:
		settings = settingsDB()
		if configbin:
			settings.def_values_form("config.bin")
			m = mInit(settings)
			if fileExists("charm.bin"): ml = mainLoop2(m,"charm.bin")
			else:
				del settings,m
				configbin = 0
				continue
			break
		settings.def_values()
		m = mInit(settings)
		ml = mainLoop2(m)
		m.getConfigurationFromFile()
		ml.dump("charm.bin")
		settings.dump("config.bin")
		break

	m.net()
	t = TelitLink_Client_Connection(m)
	#t.connectToServer()
	ml.main_charm_while()

