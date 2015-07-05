import sys,os,shutil
from cx_Freeze import setup, Executable

def relpath(path):
	return (os.path.join('..',path),path)

build_exe_options = {
	"packages": ["OpenGL"],
	"excludes": ["tkinter","numpy.core._dotblas",'curses', 'email', 'tcl', 'ttk','win32ui','win32api','win32pdh','win32pipe','tcl85','tk85',"win32com"],
	"include_files":[
		relpath('textures/8x16 font ASCII DOS 437.png'),
		relpath('shaders/pass.vert'),
		relpath('shaders/red_to_z.frag'),
	]
}

base='Win32GUI'
base=None

setup(  name = "RenderPy",
        version = "0.1",
        description = "Renders 3dmm scenes out of memory",
        options = {"build_exe": build_exe_options},
        executables = [Executable("renderer.py", base=base)])


data_dir = 'build/exe.win32-2.7'
for badpath in ('tcl','tk','libfreetype-6.dll','libtiff.dll','libvorbis-0.dll','SDL_mixer.dll','smpeg.dll','tcl85.dll','tk85.dll','_ssl.pyd'):
	path=os.path.join(data_dir, badpath)
	if os.path.exists(path):
		if os.path.isdir(path):
			shutil.rmtree(path)
		else:
			os.unlink(path)
