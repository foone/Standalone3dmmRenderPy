from ctypes import *
from ctypes.wintypes import HWND

ReadProcessMemory = windll.kernel32.ReadProcessMemory
FindWindowEx = windll.user32.FindWindowExA
GetWindowThreadProcessId = windll.user32.GetWindowThreadProcessId
OpenProcess = windll.kernel32.OpenProcess

PROCESS_VM_READ=16
PROCESS_VM_WRITE=32
PROCESS_VM_OPERATION=8
PROCESS_QUERY_INFORMATION=1024
FALSE=0

from construct import Container
from brender_structures import Actor
import struct

class ProcessMemory(object):
	def __init__(self):
		hnd = FindWindowEx(0,0,'3DMOVIE','Microsoft 3D Movie Maker')
		if hnd == 0:
			raise OSError("Couldn't find 3dmm window!")
		pid = c_uint32()
		thread = GetWindowThreadProcessId(hnd, byref(pid))
		if thread == 0:
			raise OSError("Couldn't get process for window %d" % hnd)

		ret = OpenProcess(PROCESS_VM_READ|PROCESS_VM_WRITE|PROCESS_VM_OPERATION|PROCESS_QUERY_INFORMATION,FALSE,pid)
		if ret == 0:
			raise OSError("Couldn't open 3dmm process!")
		self.pid = ret
	
	def read(self, offset, size):
		buf=create_string_buffer(size)
		ret=ReadProcessMemory(self.pid,offset,buf,size,0)
		if ret == 0:
			err = WinError()
			raise OSError("Failed to read %0X(%0d) bytes at %08X(%0d) in process %s: %s" % (size, size, offset, offset, self.pid, err))
		return buf.raw

	def unpack(self, offset, fmt):
		size=struct.calcsize(fmt)
		return struct.unpack(fmt, self.read(offset,size))

	def getGreyscale(self, w, h, offset):
		return self.getRawImage(w*2,h,offset)

	def getRawImage(self, w, h, offset):
		return self.read(offset,w*h).encode('base64')

	def getStructAt(self,addr,struct):
		out=struct.parse(self.read(addr,struct.sizeof()))
		if isinstance(out,Container):
			out['address']=addr
		return out

	def getActorAt(self, addr):
		return self.getStructAt(addr,Actor)

	def getName(self,addr):
		if addr==0:
			return ''
		data=self.read(addr,256)
		return data.split('\0')[0]

	def collectArray(self, address,n,klass):
		out=[]
		for i in range(n):
			off=address + i*klass.sizeof()
			out.append(self.getStructAt(off,klass))
		return out