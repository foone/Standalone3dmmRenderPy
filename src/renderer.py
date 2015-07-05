from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GLU import *
import pygame
from pygame.locals import *
import json,urllib2,random,sys,os,glob
import requests
import numpy as np
from PIL import Image
from StringIO import StringIO
from OpenGL.GL.ARB.texture_rectangle import GL_TEXTURE_RECTANGLE_ARB
import itertools,hashlib,argparse



options={
	'normals':False,
	'lighting':False,
	'textures':False,
	'background':False,
	'depth':False,
	'info':False,
	'debug':False,
	'logo':False,
	'wireframe':False,
	'skeleton':False,
}
comparison_options={
	'normals':False,
	'lighting':True,
	'textures':True,
	'background':True,
	'depth':True,
	'info':False,
	'debug':False,
	'logo':True,
	'wireframe':False,
	'skeleton':False,
}
TOGGLES={
	K_n:'normals',
	K_l:'lighting',
	K_t:'textures',
	K_b:'background',
	K_z:'depth',
	K_BACKQUOTE:'info',
	K_d:'debug',
	K_w:'wireframe',
	K_s:'skeleton',
}

REVESE_TOGGLES=dict((value,key) for (key,value) in TOGGLES.items())

current_texture=[None,1,1,np.identity(3)]


class Font(object):
	def __init__(self,texture):
		self.texture_id=texture

	def clear(self):
		self.pos=[0,0]

	def write(self,s):
		self.begin()
		for c in s:
			if c=='\n':
				self.pos[0]=0
				self.pos[1]+=16
			else:
				self.char(c)
		self.end()

	def begin(self):
		glPushAttrib(GL_ENABLE_BIT|GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT|GL_LIGHTING_BIT|GL_TEXTURE_BIT)
		glMatrixMode(GL_MODELVIEW)
		glPushMatrix()
		glLoadIdentity()
		glMatrixMode(GL_PROJECTION)
		glPushMatrix()
		glLoadIdentity()
		w,h=SIZE
		gluOrtho2D(0,w-1,h-1,0)
		glEnable(GL_TEXTURE_RECTANGLE_ARB)
		glEnable(GL_ALPHA_TEST)
		glDisable(GL_DEPTH_TEST)
		glAlphaFunc(GL_GREATER,0.5)
		glBindTexture(GL_TEXTURE_RECTANGLE_ARB,self.texture_id)
		glDisable(GL_LIGHTING)
		glDepthMask(GL_FALSE)
		glColor3ub(255,255,255)
		glBegin(GL_QUADS)

	def end(self):
		glEnd()
		glMatrixMode(GL_PROJECTION)
		glPopMatrix()
		glMatrixMode(GL_MODELVIEW)
		glPopMatrix()
		glPopAttrib()

	def char(self,c):
		x,y=self.pos
		v=ord(c)
		tx,ty=8*(v%16), 16*(v//16)

		for mx,my in ((0,0),(1,0),(1,1),(0,1)):
			glTexCoord2f(tx + mx*8,256 - (ty + my*16))
			glVertex2i(x+mx*8,y+my*16)
		self.pos[0]=x+8

from memory_access import ProcessMemory
from memory_walker import SceneBuilder

def compose_pil_palette(palette):
	out=[]
	for entry in palette:
		out.extend([entry.r,entry.g,entry.b])
	return out 

def loadScene(args):
	global render_tree,scene
	
	memory = ProcessMemory()
	sceneb = SceneBuilder(memory)
	sceneb.findRenderArguments()
	sceneb.buildScene()
	scene = sceneb.scene
	scene['pil_palette'] = compose_pil_palette(scene['palette'])

	render_tree = scene['world']
	scene['args'] = args

def resize((width, height)):
	if height==0:
		height=1
	cam=scene['camera']['camera']
	glViewport(0, 0, width, height)
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	gluPerspective(cam['field_of_view'], 1.0*width/height, cam['hither_z'], cam['yon_z'])
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()

def init():
	glShadeModel(GL_FLAT)
	glClearColor(0.6, 0.6, 0.6, 0.0)
	glClearDepth(1.0)
	glEnable(GL_DEPTH_TEST)
	glDepthFunc(GL_LEQUAL)
	glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
	glEnable(GL_NORMALIZE)
	glShadeModel (GL_SMOOTH);
	glEnable(GL_LIGHT0)
	glEnable(GL_COLOR_MATERIAL)


	glLoadIdentity()
	
	walkTree(render_tree,setupInverseCamera)
	walkTree(render_tree,setupLighting)
	#walkTree(render_tree,positionCamera)
	walkTree(render_tree,loadTextures)
	calculatePolygons()
	buildSkeleton()
	loadZBuffer()


def calculatePolygons():
	scene['polygon_count']=0
	scene['vertex_count']=0
	walkTree(render_tree,countPolygons)
 	

def countPolygons(node):
	if 'model' in node and node['model']!=0 and node['render_type']=='BR_RSTYLE_FACES':
		model = node['model']
		scene['polygon_count']+=len(model['faces'])
		scene['vertex_count']+=len(model['vertices'])

def buildSkeleton():
	skeleton_builder = SkeletonBuilder()
	walkTree(render_tree, skeleton_builder)

	scene['skeleton']=skeleton_builder.lines

class TreeWalker(object):
	def enter(self, node):
		pass
	def exit(self, node):
		pass
	def handle(self, node):
		pass

class ModelWalker(TreeWalker):
	def handle(self, node):
		if 'model' in node and node['model']!=0 and node['render_type']=='BR_RSTYLE_FACES':
			self.handleModel(node, node['model'])

	def handleModel(self, node, model):
		pass



class FunctionWalker(TreeWalker):
	def __init__(self,func):
		self.func=func
	def handle(self,node):
		self.func(node)


class SkeletonBuilder(ModelWalker):
	def __init__(self):
		self.stack=[]
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		self.lines=[]

	def handle(self, node):
		stack = self.stack

		if stack:
			parent=stack[-1]
		else:
			parent=None

		mv = modelviewMatrix()
		r=np.matrix([[0,0,0,1]])*mv
		loc=tuple(r.flat)[:3]

		stack.append(loc)

		if parent:
			self.lines.append((parent,loc))
		print parent,loc


	def exit(self, node):
		self.stack.pop()
		print 'POP'



def compileShader(path):
	TYPEMAP={'frag':GL_FRAGMENT_SHADER,'vert':GL_VERTEX_SHADER}
	ext=os.path.splitext(os.path.basename(path))[1].lstrip('.')
	with open(os.path.join('shaders',path),'rb') as f:
		return shaders.compileShader(f.read(),TYPEMAP[ext])


def loadTexture(im,type='RGB',intent='texture'):
	w,h,data=im.size[0], im.size[1], im.tostring("raw", type, 0, -1)
	return pixelsToTexture(w,h,data,type=(GL_RGB if type=='RGB' else GL_RGBA),filter=(GL_NEAREST if intent == 'pixels' else GL_LINEAR))

def loadPixelMapToTexture(pixelmap):
	return loadTexture(loadPixelMapToImage(pixelmap))

def loadPixelMapToImage(pixelmap):
	pixels = pixelmap['pixels']

	im=Image.frombytes('P',(pixelmap['width'],pixelmap['height']),pixels.decode('base64'))
	im.putpalette(scene['pil_palette'])
	return im.convert('RGBA')



def pixelsToTexture(w,h,data,type=GL_RGB, filter=GL_LINEAR):
	id = glGenTextures(1)
	glBindTexture(GL_TEXTURE_RECTANGLE_ARB, id)
	glPixelStorei(GL_UNPACK_ALIGNMENT,1)
	glTexImage2D(GL_TEXTURE_RECTANGLE_ARB,0,type,w,h,0, type,GL_UNSIGNED_BYTE,data)
	glTexParameter(GL_TEXTURE_RECTANGLE_ARB,GL_TEXTURE_MIN_FILTER,filter)
	glTexParameter(GL_TEXTURE_RECTANGLE_ARB,GL_TEXTURE_MAG_FILTER,filter)
	return id

def flipData(w,data):
	out=[]
	for i in range(0,len(data),w):
		out.append(data[i:i+w])
	out.reverse()
	return ''.join(out)


def depthDataToTexture(w,h,data):
	id = glGenTextures(1)
	glBindTexture(GL_TEXTURE_RECTANGLE_ARB, id)
	glPixelStorei(GL_UNPACK_ALIGNMENT,1)
	glTexImage2D(GL_TEXTURE_RECTANGLE_ARB,0,GL_DEPTH_COMPONENT16,w,h,0, GL_DEPTH_COMPONENT,GL_UNSIGNED_SHORT,flipData(w*2,data))
	glTexParameter(GL_TEXTURE_RECTANGLE_ARB,GL_TEXTURE_MIN_FILTER,GL_NEAREST)
	glTexParameter(GL_TEXTURE_RECTANGLE_ARB,GL_TEXTURE_MAG_FILTER,GL_NEAREST)
	return id


def loadTextures(node):
	if node['actor_type']=='BR_ACTOR_MODEL':
		if node['material']!=0:
			m=node['material']
			if m['color_map']!=0 and m['color_map']['pixels']!=0:
				m['texture_id']=loadPixelMapToTexture(m['color_map'])

	scene['background']=loadPixelMapToTexture(scene['pixels'])

	scene['font'] = Font(loadTexture(Image.open('textures/8x16 font ASCII DOS 437.png'),'RGBA','pixels'))

def loadZBuffer():
	vertex=compileShader('pass.vert')
	fragment=compileShader('red_to_z.frag')
	db=scene['depth']
 	db['program'] = shaders.compileProgram(vertex,fragment)
 	tex=db['texture']=depthDataToTexture(db['width'],db['height'],db['depth_pixels'].decode('base64'))


def modelviewMatrix():
	m=np.reshape(glGetFloatv(GL_MODELVIEW_MATRIX),(4,4))
	return np.matrix(m)


def setupInverseCamera(node):
	if node['actor_type']=='BR_ACTOR_CAMERA':
		scene['inverse_camera']=modelviewMatrix().I


def setupLighting(node):
	if node['actor_type']=='BR_ACTOR_LIGHT':
		m=modelviewMatrix() * scene['inverse_camera']
		pos=list((-m[3]).flat)
		pos[3]=1 # renormalize w component
		glLightfv(GL_LIGHT0, GL_POSITION, pos);
		glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0,1.0,1.0,1.0])
		glLightfv(GL_LIGHT0, GL_AMBIENT, [0.5,0.5,0.5,1.0])

		
		scene['light_position']=tuple(pos[:3])

def positionCamera(node):
	global position
	if node['actor_type']=='BR_ACTOR_CAMERA':
		m=glGetFloatv(GL_MODELVIEW_MATRIX)
		x,y,z,w=m[3]
		position=[-x,-y,-z]
		

def walkTree(tree,func_or_object):
	if not hasattr(func_or_object,'enter'):
		return walkTreeWithClass(tree,FunctionWalker(func_or_object))
	else:
		return walkTreeWithClass(tree,func_or_object)


def walkTreeWithClass(node,walker):
	glPushMatrix()
	matrix=(node['transform']['matrix'])
	glMultMatrixd(matrix)
	walker.enter(node)
	walker.handle(node)
	

	if 'children' in node and node['children']!=0:
		for child in node['children']:
			walkTreeWithClass(child,walker)
			
	glPopMatrix()
	walker.exit(node)


def drawBackground(texture_id,depth=False):
	glMatrixMode(GL_PROJECTION)
	glPushMatrix()
	glLoadIdentity()
	w,h=SIZE
	gluOrtho2D(0,w-1,0,h-1)
	glEnable(GL_TEXTURE_RECTANGLE_ARB)
	glBindTexture(GL_TEXTURE_RECTANGLE_ARB,texture_id)
	glDisable(GL_LIGHTING)
	if not depth:
		glDepthMask(GL_FALSE)
		glDisable(GL_DEPTH_TEST)
	glColor3ub(255,255,255)
	glBegin(GL_QUADS)

	tw,th=scene['pixels']['width'],scene['pixels']['height']

	for x,y in ((0,0),(1,0),(1,1),(0,1)):
		glTexCoord2f(x*tw,y*th)
		glVertex2i(min(x*w,w-1),min(y*h,h-1))
	glEnd()


	if not depth:
		glDepthMask(GL_TRUE)
		glEnable(GL_DEPTH_TEST)
	glDisable(GL_TEXTURE_RECTANGLE_ARB)
	glPopMatrix()
	glMatrixMode(GL_MODELVIEW)

def drawDepthBuffer():
	db=scene['depth']
	prog = db['program']
	tex=db['texture']


	glUseProgram(prog)
	loc = glGetUniformLocation(prog,"tex")
	glUniform1i(loc, 0)
	if not options['debug']:
		glColorMask(GL_FALSE,GL_FALSE,GL_FALSE,GL_FALSE)
	drawBackground(tex,True)
	glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE)

	glUseProgram(0)

def drawInfo():
	font=scene['font']
	descriptions=[
		('Texturing','textures'),
		('Background','background'),
		('Lighting','lighting'),
		('Depth buffer','depth'),
		('Debug','debug'),
		('Skeleton','skeleton'),
	]
	lines=[]

	for pretty,key in descriptions:
		keyb=REVESE_TOGGLES[key]
		lines.append('%s: %s (%s)' % (pretty, 'on ' if options[key] else 'off', pygame.key.name(keyb)))
	lines.append('')


	lines.append("Position: (%0.2f,%0.2f,%0.2f)" % tuple(position))
	lines.append("Rotation: (%0.2f,%0.2f,0.0)" % tuple(rotation))
	lines.append("Light: (%0.2f,%0.2f,%0.2f)" % scene['light_position'])
	lines.append("FOV: %0.2f" % scene['camera']['camera']['field_of_view'])
	lines.append('Viewport: %dx%d' % SIZE)

	lines.append('Verts: %d Polys: %d' % (scene['vertex_count'],scene['polygon_count']))

	lines.append("FPS: %d" % scene['fps'])


	font.clear()
	font.write('\n'.join(lines))

def drawLogo():
	font=scene['font']
	font.clear()
	font.write('NewRender')

def drawSkeleton():
	skeleton=scene['skeleton']
	glPushAttrib(GL_ENABLE_BIT|GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT|GL_LIGHTING_BIT|GL_TEXTURE_BIT)
	glDisable(GL_ALPHA_TEST)
	glDisable(GL_DEPTH_TEST)
	glDisable(GL_LIGHTING)
	glDisable(GL_TEXTURE_RECTANGLE_ARB)

	glColor3ub(255,255,255)
	glBegin(GL_LINES)

	for p1,p2 in skeleton:
		glVertex3fv(p1)
		glVertex3fv(p2)

	glEnd()
	glPopAttrib()

def draw():
	glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
	glLoadIdentity()

	if options['depth']:
		drawDepthBuffer()
	if options['background']:
		drawBackground(scene['background'])


	glMultMatrixd(scene['inverse_camera'])
	glRotated(rotation[0],1,0,0)
	glRotated(rotation[1],0,1,0)
	glTranslated(*position)
	
	glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if options['wireframe'] else GL_FILL)

	current_texture[0]=None

	walkTree(render_tree,renderNode)

	glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

	if options['info']:
		drawInfo()
	if options['logo']:
		drawLogo()
	if options['skeleton']:
		drawSkeleton()

	glDisable(GL_TEXTURE_RECTANGLE_ARB)

def renderNode(node):
	if 'model' in node and node['model']!=0 and node['render_type']=='BR_RSTYLE_FACES':
		renderModel(node['model'],node.get('material',0))

def boolGL(v):
	if v:
		return glEnable
	else:
		return glDisable


def renderModel(model, material):
	tex=False

	wireframe = options['wireframe']
	
	color=(128,255,128)
	if material != 0:
		i=len(material['colors'])//2
		color=material['colors'][i]
		if options['textures'] and 'texture_id' in material and (not options['wireframe']):
			current_texture[0]=material['texture_id']
			glBindTexture(GL_TEXTURE_RECTANGLE_ARB,current_texture[0])
			glEnable(GL_TEXTURE_RECTANGLE_ARB)
			cm=material['color_map']
			mt=material['map_transform']
			matrix=np.matrix([mt[0:3],mt[3:6],mt[6:9]])
			current_texture[1:]=[material['color_map']['width'],material['color_map']['height'],matrix]
			tex=True
		else:
			glDisable(GL_TEXTURE_RECTANGLE_ARB)

	tw,th,mapmatrix=current_texture[1:]

	verts=[]
	for vert in model['vertices']:
		n,p=vert['_n'],vert['p']
		m=vert['map']
		mx,my,mz=(mapmatrix*np.matrix([[m['x']],[m['y']],[1]])).flat
		verts.append((p['x'],p['y'],p['z'],n['x'],n['y'],n['z'],mx,my))

			
	boolGL(options['lighting'])(GL_LIGHTING)
	glBegin(GL_TRIANGLES)
	for face in model['faces']:
		if wireframe:
			glColor3ub(240,199,4)
		elif tex:
			glColor3ub(255,255,255)
		else:
			glColor3ub(*color)
		fv=face['vertices']
		for i in fv:
			v=verts[i]
			glNormal3f(v[3],v[4],v[5])
			glTexCoord2f(v[6]*tw,(1.0-v[7])*th)
			glVertex3f(v[0],v[1],v[2])

	glEnd()
	glDisable(GL_LIGHTING)

	if options['normals']:
		glDisable(GL_TEXTURE_RECTANGLE_ARB)
		glColor3ub(255,255,0)
		glBegin(GL_LINES)
		for x,y,z,nx,ny,nz,_,_ in verts:
			glVertex3f(x,y,z)
			glVertex3f(x+nx*5,y+ny*5,z+nz*5)
		glEnd()



def renderModelForFigurine(model, material, node):
	obj=scene['obj-file']

	
	#print >>obj,'g node%d' % node['address']

	tex=False
	
	color=(128,255,128)
	if material != 0:
		name=material.get('material-alias',('tex%d' % material['address']))


		print >>obj,'usemtl %s' % name

		if material['color_map']!=0 and 'width' in material['color_map']:
			cm=material['color_map']
			mt=material['map_transform']
			matrix=np.matrix([mt[0:3],mt[3:6],mt[6:9]])
			current_texture[1:]=[material['color_map']['width'],material['color_map']['height'],matrix]
			height=material['color_map']['height']
			tex=True
		else:
			current_texture[1:]=[1,1,np.matrix([[1,0,0],[0,1,0],[0,0,1]])]
			height=0
	else:
		print 'NO MATERIAL'

	tw,th,mapmatrix=current_texture[1:]

	mv = modelviewMatrix()
	verts=[]
	normals=[]
	texcoords=[]
	for vert in model['vertices']:
		n,p=vert['_n'],vert['p']
		m=vert['map']
		mx,my,mz=(mapmatrix*np.matrix([[m['x']],[1.0-m['y']],[1]])).flat

		before=np.matrix([[p['x'],p['y'],p['z'],1]])
		r=before*mv
		px,py,pz,pw=tuple(r.flat)
		

		print >>obj,'v %f %f %f ' % (px,py,pz)
		print >>obj,'vt %f %f' % (mx,my)
	
	offset=scene['obj-vertex-offset']

	scene['obj-vertex-offset']+=len(model['vertices'])

	for face in model['faces']:
		fv=face['vertices']
		s=' '.join(('%d/%d' % (offset+i,offset+i)) for i in fv)
		for i in fv:
			print >>obj,'f '+s




def renderNodeForFigurine(node):
	if 'model' in node and node['model']!=0 and node['render_type']=='BR_RSTYLE_FACES':
		renderModelForFigurine(node['model'],node.get('material',0),node)

def renderSceneForFigurine():
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
	#glMultMatrixd(scene['inverse_camera'])

	current_texture[0]=None

	walkTree(render_tree,renderNodeForFigurine)


def buildMaterialsMap(node):
	mtl=scene['obj-mtl']
	if 'model' in node and node['model']!=0 and node['render_type']=='BR_RSTYLE_FACES':
		m = node.get('material',0)
		name='tex%d' % m['address']
		if m['color_map']!=0 and m['color_map']['pixels']!=0:
			pixhash=hashlib.md5(m['color_map']['pixels']).hexdigest()
			if pixhash in scene['obj-materials']:
				m['material-alias']=scene['obj-materials'][pixhash]
				return
			else:
				scene['obj-materials'][pixhash]=name
			
			path=name+'.png'
			im=loadPixelMapToImage(m['color_map'])
			im.save('figurine/'+path)
			print >>mtl,'newmtl %s' % name
			print >>mtl,'map_Kd %s ' % path
		elif m['colors']:
			print >>mtl,'newmtl %s' % name
			rgb=tuple(x/255.0 for x in m['colors'][-1])
			print >>mtl,'Kd %0.4f %0.4f %0.4f ' % rgb

def clearFigurineDirectory():
	try:
		os.mkdir('figurine')
	except OSError:
		pass
	for path in glob.glob('figurine/*'):
		os.unlink(path)

def save3DFigurine():
	clearFigurineDirectory()
	scene['obj-vertex-offset']=1

	name = scene['args'].name

	scene['obj-materials']={}
	with open(('figurine/%s.mtl' % name),'w') as mtlfile:
		scene['obj-mtl']=mtlfile
		walkTree(render_tree, buildMaterialsMap)


	f=scene['obj-file']=open(('figurine/%s.obj' % name),'w')
	print >>f,'mtllib %s.mtl' % name
	print >>f,'o %s' % name
	old_options=dict(options)
	options.update(comparison_options)
	renderSceneForFigurine()
	options.update(old_options)
	f.close()	


def saveScreenshot(filename, comparison):
	w,h=SIZE

	if comparison:
		old_options=dict(options)
		options.update(comparison_options)
		draw()
		options.update(old_options)


	data = glReadPixels( 0,0, w, h, GL_RGBA, GL_UNSIGNED_BYTE)
	im = Image.frombuffer("RGBA", (w,h), data, "raw", "RGBA", 0, 0)
	im.save(filename)

def resetPositionAndRotation():
	global rotation,position

	rotation=[0,0]
	position=[0,0,0]

def main(args):
	global SIZE


	SIZE=(int(544*args.scale),int(306*args.scale))


	video_flags = OPENGL|DOUBLEBUF
	
	pygame.init()
	pygame.display.set_caption('Standalone RenderPy')
	pygame.display.set_mode(SIZE, video_flags)

	loadScene(args)

	resetPositionAndRotation()

	resize(SIZE)
	init()



	frames = 0
	ticks = pygame.time.get_ticks()
	while 1:
		event = pygame.event.poll()
		if event.type == QUIT:
			break
		elif event.type == KEYDOWN:
			if event.key == K_ESCAPE:
				break
			elif event.key in TOGGLES:
				key=TOGGLES[event.key]
				options[key] = not options[key]
			elif event.key in (K_F2,K_F3):
				saveScreenshot('screenshot.png',event.key == K_F3)
			elif event.key == K_F4:
				save3DFigurine()
			elif event.key == K_r:
				resetPositionAndRotation()
		elif event.type == MOUSEMOTION:
			if event.buttons[2]:
				rotation[0]+=event.rel[1]
				rotation[1]+=event.rel[0]
			if event.buttons[0]:
				position[2]+=event.rel[1]*5.0
				position[1]+=event.rel[0]*5.0
			if event.buttons[1]:
				position[0]+=event.rel[0]*5.0

		draw()
		pygame.display.flip()
		frames = frames+1

		scene['fps']=(frames*1000)/(pygame.time.get_ticks()-ticks)


if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Display 3dmm models')

	parser.add_argument('--name', help='name for exported model',default='figurine')

	parser.add_argument('--scale', help='Scale of 3D window, in multiples of 544x306', default=1.0, type=float)

	args = parser.parse_args()
	main(args)
