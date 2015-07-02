from construct import *

actor_types=('BR_ACTOR_NONE,BR_ACTOR_MODEL,BR_ACTOR_LIGHT,BR_ACTOR_CAMERA,_BR_ACTOR_RESERVED,'+
		'BR_ACTOR_BOUNDS,BR_ACTOR_BOUNDS_CORRECT,BR_ACTOR_CLIP_PLANE,BR_ACTOR_MAX').split(',')
render_methods=('BR_RSTYLE_DEFAULT,BR_RSTYLE_NONE,BR_RSTYLE_POINTS,BR_RSTYLE_EDGES,BR_RSTYLE_FACES,'+
	'BR_RSTYLE_BOUNDING_POINTS,BR_RSTYLE_BOUNDING_EDGES,BR_RSTYLE_BOUNDING_FACES,BR_RSTYLE_MAX').split(',')
transform_types=('BR_TRANSFORM_MATRIX34,BR_TRANSFORM_MATRIX34_LP,BR_TRANSFORM_QUAT,'+
	'BR_TRANSFORM_EULER,BR_TRANSFORM_LOOK_UP,BR_TRANSFORM_TRANSLATION,BR_TRANSFORM_IDENTITY,BR_TRANSFORM_MAX').split(',')
PIXEL_TYPES=('BR_PMT_INDEX_1,BR_PMT_INDEX_2,BR_PMT_INDEX_4,BR_PMT_INDEX_8,'+
	'BR_PMT_RGB_555,BR_PMT_RGB_565,BR_PMT_RGB_888,BR_PMT_RGBX_888,BR_PMT_RGBA_8888,'+
	'BR_PMT_YUYV_8888,BR_PMT_YUV_888,BR_PMT_DEPTH_16,BR_PMT_DEPTH_32,BR_PMT_ALPHA_8,'+
	'BR_PMT_INDEXA_88').split(',')

def makeEnum(seq):
	d={}
	for i,name in enumerate(seq):
		d[name]=i
	return d

def Scalar(name=None):
	return ExprAdapter(SLInt32(name),
    encoder = lambda obj, ctx: int(obj * 65536),
    decoder = lambda obj, ctx: obj / 65536.0,
)
def Angle(name=None):
	return ExprAdapter(ULInt16(name),
    encoder = lambda obj, ctx: int(obj * 65536/360.0),
    decoder = lambda obj, ctx: obj / 65536.0 * 360.0,
)
def Fraction(name=None):
	return ExprAdapter(ULInt16(name),
    encoder = lambda obj, ctx: int(obj * 65536.0),
    decoder = lambda obj, ctx: obj / 65536.0 ,
)
def SignedFraction(name=None):
	return ExprAdapter(SLInt16(name),
    encoder = lambda obj, ctx: int(obj * 65536.0),
    decoder = lambda obj, ctx: obj / 65536.0 ,
)

def Vector3(name=None):
	return Struct(name,
		Scalar('x'),Scalar('y'),Scalar('z'),
	)

def Vector2(name=None):
	return Struct(name,
		Scalar('x'),Scalar('y')
	)

def FVector3(name=None):
	return Struct(name,
		SignedFraction('x'),SignedFraction('y'),SignedFraction('z')
	)


def Matrix23(name):
	return Sequence(name,
		Scalar('s0'),
		Scalar('s1'),
		Value('implied0',lambda ctx:0.0),
		Scalar('s2'),
		Scalar('s3'),
		Value('implied1',lambda ctx:0.0),
		Scalar('s4'),
		Scalar('s5'),
		Value('implied2',lambda ctx:1.0),
	)

transform=Struct('transform',
	Enum(ULInt16('transform_type'),
		**makeEnum(transform_types)
	),
	Padding(2),
	Sequence('matrix',
		Scalar('s0'),
		Scalar('s1'),
		Scalar('s2'),
		Value('implied0',lambda ctx:0.0),
		Scalar('s3'),
		Scalar('s4'),
		Scalar('s5'),
		Value('implied1',lambda ctx:0.0),
		Scalar('s6'),
		Scalar('s7'),
		Scalar('s8'),
		Value('implied2',lambda ctx:0.0),
		Scalar('s9'),
		Scalar('s10'),
		Scalar('s11'),
		Value('implied3',lambda ctx:1.0),
	)
)


Actor = Struct('BRender actor',
	ULInt32("next"),
	ULInt32("prev"),
	ULInt32("children"),
	ULInt32("parent"),
	ULInt16("depth"),
	Enum(ULInt8("actor_type"),
			**makeEnum(actor_types)
	),
	Padding(1),
	ULInt32("name"),
	ULInt32("model"),
	ULInt32("material"),
	Enum(ULInt8("render_type"),
		**makeEnum(render_methods)
	),
	Padding(3),
	transform,
	ULInt32("type_data"),

)

Camera = Struct('BRender camera',
	ULInt32('identifier'),
	Enum(ULInt8('type'),
		BR_CAMERA_PARALLEL=0,
		BR_CAMERA_PERSPECTIVE_FOV=1,
		BR_CAMERA_PERSPECTIVE_WHD=2
	),
	Padding(1),
	Angle('field_of_view'),
	Scalar('hither_z'),
	Scalar('yon_z'),
	Scalar('aspect'),
	Scalar('width'),
	Scalar('height'),
	Scalar('distance')
)

Light = Struct('BRender light',
	ULInt32('identifier'),
	FlagsEnum(ULInt8('type'),
		BR_LIGHT_POINT=0,
		BR_LIGHT_DIRECT=1,
		BR_LIGHT_SPOT=2,
		BR_LIGHT_VIEW=4,
	),
	ULInt32('color'),
	Scalar('attenuation_c'),
	Scalar('attenuation_l'),
	Scalar('attenuation_q'),

	Angle('cone_outer'),
	Angle('cone_inner'),
)


Model = Struct('BRender model',
	ULInt32('identifier'),

	ULInt32('vertices'),
	ULInt32('faces'),
	ULInt16('nvertices'),
	ULInt16('nfaces'),
	Vector3('pivot'),
	ULInt16('flags'),
	Padding(2),
	ULInt32('custom'),
	ULInt32('user'),
	Scalar('radius'),
	Struct('bounds',
		Vector3('min'),
		Vector3('max')
	),

	ULInt16('nprepared_vertices'),
	ULInt16('nprepared_faces'),
	ULInt32('prepared_faces'),
	ULInt32('prepared_vertices'),

	ULInt16('nface_groups'),
	ULInt16('nvertex_groups'),
	ULInt32('face_groups'),
	ULInt32('vertex_groups'),

	ULInt16('nedges'),
	Padding(2),
	ULInt32('face_tags'),
	ULInt32('vertex_tags'),

	ULInt32('prep_flags'),
	ULInt16('smooth_strings'),
	Padding(2),
	ULInt32('rptr')
)

Vertex = Struct('BR Vertex',
	Vector3('p'),
	Vector2('map'),
	
	ULInt8('index'),
	ULInt8('r'),
	ULInt8('g'),
	ULInt8('b'),

	ULInt16('_r'),
	FVector3('_n'),
)
Face = Struct('BR Face',
	Sequence('vertices',
		ULInt16('v1'),
		ULInt16('v2'),
		ULInt16('v3'),
	),
	Sequence('edges',
		ULInt16('e1'),
		ULInt16('e2'),
		ULInt16('e3'),
	),
	ULInt32('material'),
	ULInt16('smoothing'),
	ULInt8('flags'),
	Padding(13),
)

FaceGroup = Struct('BR Face Group',
	ULInt32('material'),
	ULInt32('faces'),
	ULInt16('nfaces'),
	Padding(2),
)
Material = Struct('BR Material',
	ULInt32('identifier'),
	ULInt32('color'),
	ULInt8('opacity'),
	Padding(1),
	Fraction('ka'),
	Fraction('kd'),
	Fraction('ks'),
	Scalar('power'),
	FlagsEnum(ULInt32('flags'),
		BR_MATF_LIGHT			= 0x00000001,
		BR_MATF_PRELIT			= 0x00000002,

		BR_MATF_SMOOTH			= 0x00000004,

		BR_MATF_ENVIRONMENT_I	= 0x00000008,
		BR_MATF_ENVIRONMENT_L	= 0x00000010,
		BR_MATF_PERSPECTIVE		= 0x00000020,
		BR_MATF_DECAL			= 0x00000040,

		BR_MATF_I_FROM_U		= 0x00000080,
		BR_MATF_I_FROM_V		= 0x00000100,
		BR_MATF_U_FROM_I		= 0x00000200,
		BR_MATF_V_FROM_I		= 0x00000400,

		BR_MATF_ALWAYS_VISIBLE	= 0x00000800,
		BR_MATF_TWO_SIDED		= 0x00001000,

		BR_MATF_FORCE_Z_0		= 0x00002000,

		BR_MATF_DITHER			= 0x00004000

	),
	Matrix23('map_transform'),
	ULInt8('index_base'),
	ULInt8('index_range'),
	Padding(2),
	ULInt32('color_map'),
	ULInt32('screendoor'),
	ULInt32('index_shade'),
	ULInt32('index_blend'),
	ULInt8('_prep_flags'),
	Padding(3),
	ULInt32('_rptr'),
)
Pixelmap = Struct('BR Pixelmap',
	ULInt32('identifier'),
	ULInt32('pixels'),
	ULInt32('_reserved'),
	ULInt32('map'),
	ULInt16('row_bytes'),
	
	Enum(ULInt8('type'),
		**makeEnum(PIXEL_TYPES)
	),
	
	FlagsEnum(ULInt8('flags'),
		BR_PMF_NO_ACCESS		= 0x01,

		BR_PMF_LINEAR			= 0x02,
		BR_PMF_ROW_WHOLEPIXELS	= 0x04
	),
	ULInt16('base_x'),
	ULInt16('base_y'),

	ULInt16('width'),
	ULInt16('height'),

	ULInt16('origin_x'),
	ULInt16('origin_y'),

	ULInt32('device')

)

RenderArguments = Struct('Render arguments',
	Padding(4),
	ULInt32('world'),
	ULInt32('camera'),
	ULInt32('pixels'),
	ULInt32('depth'),

)

RGBQUAD = Struct('RGB Quad',
	ULInt8('b'),
	ULInt8('g'),
	ULInt8('r'),
	Padding(1)
)

PALETTE = Array(256,RGBQUAD)
