#pragma once

#include <vector>
#include <string>
#include <memory>
#include <cmath>

/**
 * SpatialReverbBridge
 * C++ DSP Bridge for ElevenX – HRTF binaural panning + RIR convolution + Schroeder reverb.
 * Designed for 256-sample buffers (~10.7 ms at 24 kHz).
 */
class SpatialReverbBridge {
public:
    SpatialReverbBridge(int sampleRate = 24000, int bufferSize = 256);
    ~SpatialReverbBridge();

    // Process a mono input buffer → stereo binaural output
    // input:  mono float samples [-1, 1]
    // output: interleaved stereo (L,R,L,R,...) size = input.size() * 2
    void process(const float* input, float* output, size_t numSamples);

    // Set 3D position of the virtual source (degrees)
    void setSourcePosition(float azimuthDeg, float elevationDeg, float distance = 1.0f);

    // Load a Room Impulse Response (mono WAV or raw float)
    bool loadRIR(const std::string& path);

    // Enable / disable late reverb tail
    void setReverbEnabled(bool enabled);
    void setReverbMix(float mix);   // 0.0 – 1.0

private:
    int sampleRate_;
    int bufferSize_;

    // Simple HRTF approximation (can be replaced by SOFA loader)
    float leftGain_ = 1.0f;
    float rightGain_ = 1.0f;
    float itdSamples_ = 0.0f;   // interaural time difference

    // Partitioned convolution state (placeholder)
    std::vector<float> rir_;
    bool rirLoaded_ = false;

    // Schroeder reverberator
    bool reverbEnabled_ = true;
    float reverbMix_ = 0.25f;
    static constexpr int NUM_COMBS = 4;
    static constexpr int NUM_ALLPASS = 2;
    std::vector<float> combBuffers_[NUM_COMBS];
    std::vector<float> allpassBuffers_[NUM_ALLPASS];
    size_t combIdx_[NUM_COMBS] = {};
    size_t allpassIdx_[NUM_ALLPASS] = {};
    float combFeedback_[NUM_COMBS] = {0.84f, 0.88f, 0.86f, 0.90f};
    float allpassFeedback_ = 0.7f;

    void initSchroeder();
    float processSchroeder(float x);
    void updateHRTF(float azimuthDeg, float elevationDeg);
};
