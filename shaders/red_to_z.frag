#version 110
#extension GL_ARB_texture_rectangle : require

varying vec2 texcoord0;

uniform sampler2DRect tex;

void main() {
	vec4 color = texture2DRect(tex,texcoord0.st);
	float v = clamp(color.r+0.5,0.0,1.0);;
	gl_FragDepth = v;
	gl_FragColor = vec4(v,v,v,1.0);
}