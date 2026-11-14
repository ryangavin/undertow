#version 440
// The interference strip, drawn on the GPU: every pixel works out how near it
// is to each of the four waves and adds up their light. Waves.qml feeds it
// the readings; compile with
//   /usr/lib/qt6/bin/qsb --glsl "100 es,120,150" --hlsl 50 --msl 12 -o waves.frag.qsb waves.frag
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 size;      // the strip, in logical pixels
    float phase;    // advances while the strip moves
    float cursor;   // the pointer across the strip, 0 to 1, or below 0 when away
    vec4 levels;    // CPU, GPU, memory, network, each 0 to 1
};

const float PI = 3.14159265;

// Height of wave `layer` at `u` (0 to 1 across), in logical pixels from the top.
float wave(float u, int layer, float energy) {
    float l = float(layer);
    float envelope = pow(max(sin(PI * u), 0.0), 1.3);
    float together = sin(u * 12.0 - phase * 0.65) * energy * 12.0;
    float own = sin(u * (17.0 + l * 3.0) - phase * (0.65 + l * 0.12) + l * 1.4);
    float touch = cursor < 0.0 ? 0.0 : exp(-pow((u - cursor) * 10.0, 2.0)) * sin(u * 45.0 - phase * 2.0) * 16.0;
    return size.y * 0.59 + envelope * (own * (6.0 + levels[layer] * 28.0) + together + touch);
}

void main() {
    vec2 p = qt_TexCoord0 * size;
    float u = qt_TexCoord0.x;
    float du = 1.0 / max(size.x, 1.0);
    // How much one device pixel is in logical pixels, for smooth edges.
    float pixel = max(fwidth(p.y), 0.0001);
    float energy = (levels.x + levels.y + levels.z + levels.w) / 4.0;
    vec3 colours[4] = vec3[4](vec3(0.404, 0.863, 0.925), vec3(0.706, 0.604, 0.980),
                              vec3(0.910, 0.749, 0.502), vec3(0.459, 0.875, 0.706));
    vec3 light = vec3(0.0);
    float alpha = 0.0;
    for (int layer = 0; layer < 4; layer++) {
        float y = wave(u, layer, energy);
        // Distance to the curve, not straight down to it, so steep parts keep their width.
        float slope = (wave(u + du, layer, energy) - y) / max(size.x * du, 0.0001);
        float d = abs(p.y - y) / sqrt(1.0 + slope * slope);
        // A faint 12 px glow and a bright 1.5 px line, as the canvas drew them.
        float halo = 1.0 - smoothstep(6.0 - pixel * 0.5, 6.0 + pixel * 0.5, d);
        float line = 1.0 - smoothstep(0.75 - pixel * 0.5, 0.75 + pixel * 0.5, d);
        float intensity = halo * 0.045 + line * 0.65;
        light += colours[layer] * intensity;
        alpha += intensity;
    }
    // Added up as light, as the canvas's "lighter" did; premultiplied.
    alpha = min(alpha, 1.0);
    fragColor = vec4(min(light, vec3(alpha)), alpha) * qt_Opacity;
}
