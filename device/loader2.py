from optparse import OptionParser
import serial
import sys
import time
import os

def between(d,a,b):
	y=d.find(a)
	if y == -1: return -1
	c=d[y+len(a):]
	z=c.find(b)
	if z == -1: return -1
	return c[:z]

def inlines(inf=[],lines=[]):
	for a in lines: 
		m=0 #marker
		for i in inf:
			if i in a:return m 
			m+=1
	return -1
	
def die(*strings):
	#print strings
	for s in strings: print s
	sys.exit(1)

class __config:
	def __init__(self,args={}):
		self.port=args.port
		self.baud=args.baud
		f=args.filename 
		print f
		self.fileFull=os.path.abspath(f)
		try:
			self.filename=f[len(f)-f[::-1].index("\\"):]
		except: 
			try:self.filename=f[len(f)-f[::-1].index("/"):]
			except: self.filename=f
	def configfile(self): pass

class _loader__file:
	def __init__(self,config):
		self.binary=False
		if config.filename is None: 
			isfile=False
			return
		self.isfile=True
		if not ( config.fileFull[-3:] in [ "pyc","pyo" ] ) :
			try:
				if config.fileFull == "": raise 0
				self.file = open(config.fileFull,'r')	#the full path of the file
				self.fileInput = self.file.readlines()
			except: print "[ERROR] While opening file"
		else: 
			self.binary = True
		self.fileLength = os.path.getsize(config.fileFull)
	def compile(self):
		pass

class  _loader__serialPort:
	def __init__(self,config):
		if config.port is None or config.baud is None:
			die("[ERROR] baud or port not selected.")  
		try:
			self.conn = serial.Serial(config.port,config.baud,timeout=1,bytesize=8,\
			stopbits=1,parity='N',writeTimeout=1,rtscts=True)
			self.conn.close()
			self.conn.open()
		except serial.SerialException,e: die("[ERROR] Serial failure: ",e)
		self.moduleTest()
	def __enter__(self): # On entering...
		return(self) # Return object created in __init__ part
	def __exit__(self,exc_type, exc_val, exc_tb): # On exiting...
		pass # Use close method of zipfile.ZipFile
		
	def reply(self):
		tooLong=time.time()+10
		t=0
		while True:
			time.sleep(0.25)
			try: 
				if time.time() > tooLong: break
				if self.conn.inWaiting() < 3: continue
				break
			except:	
				if t>=3: return "ERROR" # 3tries
				t+=1
				tooLong=time.time()+10
		time.sleep(1)
		return self.conn.readlines()
			
	def moduleTest(self):
		self.conn.flushInput() #clear buffer of junk
		self.conn.write("AT\r") #send a AT<CR>
		if "OK\r\n" in self.reply():
			print "[OK] Telit replied, communications OK....."
			return True
		else: die(\
		"[WARNING] Failed to talk to Telit, is it on? Is the port free?\n"\
		"Try to figure it out and try again\n")		
class loader:
	def __init__(self,config=None,fileObject=None,serial=None):
		if config == None: 
			die("[ERROR] You must pass \"__config object\"")
		self.config=config
		self.file=fileObject
		if serial is None: self.serial=__serialPort(config)
		
	def fileInit(self):
		if self.file is None: self.file=_loader__file(self.config)
		
	def writeFile(self):
		self.fileInit()
		print "[INFO] Writing to module: file:"+self.config.filename+" SIZE:"+str(self.file.fileLength)
		if int(self.file.fileLength)>204800: die ("ERROR file is too big  byte max")
		writeCommand= "AT#WSCRIPT=%s,%i\r\n" % (self.config.filename,self.file.fileLength)
		with self.serial.conn as com: 
			print "[INFO] Sending:" + writeCommand
#			self.serial.check()		
			com.flushInput()
			com.write(writeCommand)
			input = self.serial.reply()	
			if ">>>" not in input: die("didn't get >>>??",input)		
			print"[OK] File transfer started"
			lineMarker=0
			bitssended=0
			com.flush()
			line = ""
			if self.file.binary:
				try:
					f = open(self.config.fileFull,"rb")
				except: return
				while True:
					line=f.read(256)
					if (line == "") : break
					try: 
						com.write(line)
						lineMarker+=1
						print lineMarker
					except serial.serialutil.SerialTimeoutException:
						die ("ERROR: serial timed out on line :"+LineMarker)
			else:
				for line in self.file.fileInput:
					if( not ( self.file.binary ) and line[-1:] != "\r\n" ) : 
						line=line[:-1]+ "\r\n"
					try: com.write(line)
					except serial.serialutil.SerialTimeoutException:
						die ("ERROR: serial timed out on line :"+LineMarker)
					lineMarker+=1
			print lineMarker
			com.write("\r")
			#time.sleep(2)
			input=self.serial.reply()
			if inlines(["OK\r\n"],input)>=0:
				print "[OK] Scipt loaded correctly."
			else: print input
			com.flush()
			
	def deleteFile(self,fileName=None):
		fileName=self.config.filename
		deleteCommand= "AT#DSCRIPT=%s\r\n" % (fileName)
		with self.serial.conn as port: 
			if ".py" in fileName:
				print "[INFO] Deleting "+self.config.filename+" .\n"\
				"[INFO] Sending: " + deleteCommand
				port.flushInput()
				port.write(deleteCommand) 
				if 0==inlines(["OK","ERROR"],self.serial.reply()): 
					print "[info] FOUND AND DELETED:" +fileName

				else: print "[ERROR] Module doesn't find "+fileName+" file:"
				#delete .pyo
				print "\nDELETING .pyo file:"
				deleteCommand= "AT#DSCRIPT=%so\r\n" % (fileName) #add 'o' for pyo
				print "[INFO] Sending: " + deleteCommand
				port.flushInput()
				port.write(deleteCommand)
			else:
				print "\nDELETING file:"
				#delete file
				print "Sending: " + deleteCommand
				port.flush()
				port.write(deleteCommand)
		lines=self.serial.reply()
		r=inlines(["OK","ERROR"],lines)
		if r==0: print "FOUND AND DELETED:" +fileName+"o"
		elif r==1:
			print "[ERROR] didn't find .pyo file: " +fileName
			print lines
	
	def listFiles(self,find=None):
		#self.serial.check()
		fileList=[]
		listCommand= "AT#LSCRIPT\r\n" 
		print "[INFO] Listing current files:"
		print "[INFO] Sending: " + listCommand
		with self.serial as com:
			com.conn.flush()
			com.conn.write(listCommand)
			foundfile=False
			for line in com.reply(): 
				l=between(line,'"','"')
				if l != -1:	
					print l
					if l == find: return l
					fileList.append(l)
			self.currentFileList=fileList
		return None
			
	def deleteAll(self):
		if len(self.fileList) <=0: listFiles()
		for f in self.fileList: self.delete(f)
			
	def enable(self):
		fileName=self.config.filename
		#setPort.serialOpenCheck()			#open serial connection send AT to check
		readCommand = "AT#ESCRIPT=\"%s\"\r\n" % (fileName)
		print "[INFO] Setting main() script as:"+fileName
		print "[INFO] Sending: " + readCommand
		with self.serial.conn as com:
			com.flush()
			com.write(readCommand)
			print "[STATUS]"
			for line in self.serial.reply(): print line
			
	def readFile(self):
		fileName=self.config.filename
		#self.serial.check()			#open serial connection send AT to check
		readCommand = "AT#RSCRIPT=\"%s\"\r\n" % (fileName)
		print "[INFO] Reading file: " + fileName
		print "[INFO]Sending: " + readCommand
		with self.serial.conn as com:
			com.flush()
			com.write(readCommand)
		logFile= open("./telit_"+fileName+".txt", 'w')	#overwrite eachtime
		lineMarker=0
		for line in self.serial.reply():
			logFile.write(line)
			time.sleep(0.1)
			print "%i: %s"%(lineMarker,line)
			lineMarker+=1
		print "[OK] Reading done."
		logFile.close()

def parseArgs():
	parser = OptionParser()
	parser.add_option("-f", "--file", dest="filename",help="A script destination.", metavar="FILE")
	parser.add_option("-p","--PORT", type="string", dest="port", default=2, help="Select port with script will talk.")
	parser.add_option("-b","--baud",type="int", dest="baud", default=115200, help="Baud of port.")
	parser.add_option("-l","--list",action="store_true", dest="list")
	parser.add_option("--dA","--deleteAll",action="store_true", dest="deleteAll")
	parser.add_option("-r","--read",action="store_true", dest="readfile")
	parser.add_option("-s","--find",action="store_true", dest="findfile")
	parser.add_option("-d","--delete",action="store_true", dest="deletefile")
	parser.add_option("-u","--upload",action="store_true", dest="uploadfile")
	parser.add_option("--uA","--uploadALL",action="store_true", dest="uploadAll")
	parser.add_option("--uC","--uploadCheck",action="store_true", dest="uploadCheck")
	parser.add_option("-e","--enable",action="store_true", dest="enable")
	parser.add_option("--eC","--enableCheck",action="store_true", dest="enableCheck")
	return parser.parse_args()[0]
	
if __name__ == "__main__":
	args=parseArgs()
	#args.filename="p1\\main.py"
	#args.uploadfile=True
	settings=__config(args)
	Loader = loader(settings);
	if args.list or args.deleteAll or args.uploadCheck: Loader.listFiles()
	if args.findfile: Loader.listFiles(settings.filename)
	if args.enableCheck:pass
	if not args.filename is None:
		if args.readfile: Loader.readFile()
		if args.deletefile: Loader.deleteFile()
		if args.deleteAll: Loader.deleteAll()
		if args.uploadfile: Loader.writeFile()
	if args.enable: Loader.enable()
		
