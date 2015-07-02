#version 110

varying vec2 texcoord0;

void main() {
	texcoord0 = vec2(gl_TextureMatrix[0] * gl_MultiTexCoord0);
	gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}