import com2ip as com2ip
import atexit
import json
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.twisted.websocket import WebSocketServerFactory
from serial.tools import list_ports
import socket
import time
deviceActive = None
deviceList = [
	{
		"csgn":"fsgdfgdgs",
		"settings":{},
		"status":"CONNECTED",
		"ip":"127.0.0.1",
		"port": "1005",
		"instance":None,
		"toupload":[]
	}
]

webSocketsOpened=[]
hostAddr=""

class WS_webCommunication(WebSocketServerProtocol):
	def __init__(self):
		self.is_closed = False
		#self.bridge = None

	def onConnect(self, request):
		pass
		print("Client connecting: {0}".format(request.peer))

	def deviceInfoSend(self,x):
		self.sendMessage("#*"+json.dumps([self.deviceInfo(x)]),False)

	def deviceUpdate(self,id,upd={}):
		msg = "@update "+id+" "+json.dumps(upd)
		self.sendMessage(msg)

	def deviceInfo(self,x,start=""):
		g = {}
		for y in "ip","port","csgn","settings","status": g[y] = x[y]
		return g

	def onOpen(self):
		global hostAddr
		webSocketsOpened.append(self);
		global deviceList
		string = "#"
		h=[]
		for  x in deviceList:
			h.append(self.deviceInfo(x))
		self.sendMessage("#"+json.dumps(h))
		ports="$"
		for p in list_ports.comports():
			ports+=p[0]+"%"
		self.sendMessage(ports[:-1]+';',False)
		self.sendMessage('@hostaddr '+hostAddr)

	def unplugDevice(self,id):
		for device in deviceList:
			if device["csgn"] == id:
				x = device.get("instance")
				if x: x.terminate = True
				break

	def onMessage(self, payload, isBinary):
		global deviceActive
		global deviceList
		def communication_type(x): self.bridge.communication_type = x
		print "received: ",payload
		dId=""
		if payload[0] == '+':
			{
				"TCP" : lambda: communication_type(com2ip.communication_style.tcp_proxy),
				"SERIAL": lambda: communication_type(com2ip.communication_style.serial_proxy)
			}[payload[1:]]()

		if payload[0] == "$":
			self.bridge.port = payload[1:]
		if payload[0] == "@":
			slc=payload[1:].split(" ")
			{
				'unplug': lambda s,d: s.unplugDevice(d[1])
			}[slc[0]](self,slc)
		if payload[0] == "!":
			dId=payload[1:len(payload)]
			f=0
			id=0
			if dId != '0':
				for h in dId:
					if h == '0': f+=1
					else: break
			id = dId[f:]
			if not ( deviceActive is None ):
				deviceActive["active"].clear()
			while True:
				try:
					for x in deviceList:
						if x["csgn"] == id and "active" in x: raise x
					self.sendMessage("!ERROR",False)
					break
				except: deviceActive=x
				if deviceActive["status"] == "connected":
					deviceActive["active"].set()
					deviceActive["instance"].conn.send('!START;')
					#self.bridge.deviceLock.set()
				else:
					self.sendMessage("!ERROR",False)
					break
				self.sendMessage("!OK",False)
				return
		if payload[0] == ">":
			js = json.loads(payload[1:])
			for x in deviceList:
				if x["csgn"] == js[0]:
					x["settings"].update(js[1])
					x["tosend"].extend(js[1].keys())
					if \
						not x["active"].isSet() and \
						x["status"] == "connected":
						x["instance"].sendVars()
					break


	def onClose(self, wasClean, code, reason):
		print("WebSocket connection closed: {0}".format(reason))

def getMyIp():
	#return "127.0.0.1"
	return socket.gethostbyname(socket.gethostname())

if __name__ == "__main__":
	WSfactory = WebSocketServerFactory("ws://localhost:1007", debug=False)
	WSfactory.protocol = WS_webCommunication
	# SERIAL TO COM INITIALIZATION
	hostAddr = getMyIp()
	c = com2ip.bridge(getMyIp(), 1005, "COM4", "300")
	c.WS = WSfactory.protocol
	c.WSinstances=webSocketsOpened
	c.deviceList=deviceList
	#c.setSerial()
	c.tcpServer()
	c.start()
	#WEBSOCKET INITIALIZATION
	WSfactory.protocol.bridge=c
	reactor.listenTCP(1007, WSfactory)
	reactor.run()


