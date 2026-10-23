#include "SpatialReverbBridge.h"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <cstring>

SpatialReverbBridge::SpatialReverbBridge(int sampleRate, int bufferSize)
    : sampleRate_(sampleRate), bufferSize_(bufferSize)
{
    initSchroeder();
    setSourcePosition(0.0f, 0.0f);
}

SpatialReverbBridge::~SpatialReverbBridge() = default;

void SpatialReverbBridge::initSchroeder()
{
    // Classic Schroeder delays (in samples) tuned for 24 kHz
    const int combDelays[NUM_COMBS] = {1557, 1617, 1491, 1422};
    const int allpassDelays[NUM_ALLPASS] = {225, 556};

    for (int i = 0; i < NUM_COMBS; ++i) {
        combBuffers_[i].assign(combDelays[i], 0.0f);
        combIdx_[i] = 0;
    }
    for (int i = 0; i < NUM_ALLPASS; ++i) {
        allpassBuffers_[i].assign(allpassDelays[i], 0.0f);
        allpassIdx_[i] = 0;
    }
}

float SpatialReverbBridge::processSchroeder(float x)
{
    float sum = 0.0f;
    for (int i = 0; i < NUM_COMBS; ++i) {
        float delayed = combBuffers_[i][combIdx_[i]];
        float y = x + delayed * combFeedback_[i];
        combBuffers_[i][combIdx_[i]] = y;
        combIdx_[i] = (combIdx_[i] + 1) % combBuffers_[i].size();
        sum += delayed;
    }
    sum *= 0.25f;

    for (int i = 0; i < NUM_ALLPASS; ++i) {
        float delayed = allpassBuffers_[i][allpassIdx_[i]];
        float y = sum + delayed * allpassFeedback_;
        allpassBuffers_[i][allpassIdx_[i]] = y;
        allpassIdx_[i] = (allpassIdx_[i] + 1) % allpassBuffers_[i].size();
        sum = delayed - sum * allpassFeedback_;
    }
    return sum;
}

void SpatialReverbBridge::updateHRTF(float azimuthDeg, float elevationDeg)
{
    // Very simple amplitude panning + ITD approximation
    // Real production code would load a SOFA HRTF set
    float az = azimuthDeg * 3.14159265f / 180.0f;
    leftGain_  = 0.5f * (1.0f + std::cos(az));
    rightGain_ = 0.5f * (1.0f - std::cos(az));
    // ITD ≈ 0.6 ms * sin(az) at 24 kHz ≈ 14.4 samples * sin(az)
    itdSamples_ = 14.4f * std::sin(az);
}

void SpatialReverbBridge::setSourcePosition(float azimuthDeg, float elevationDeg, float /*distance*/)
{
    updateHRTF(azimuthDeg, elevationDeg);
}

bool SpatialReverbBridge::loadRIR(const std::string& path)
{
    // Placeholder – production version would parse WAV or raw float32
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        std::cerr << "[SpatialReverbBridge] Failed to open RIR: " << path << std::endl;
        return false;
    }
    // For demo we just mark as loaded
    rirLoaded_ = true;
    std::cerr << "[SpatialReverbBridge] RIR load stub – replace with real convolution" << std::endl;
    return true;
}

void SpatialReverbBridge::setReverbEnabled(bool enabled) { reverbEnabled_ = enabled; }
void SpatialReverbBridge::setReverbMix(float mix) { reverbMix_ = std::clamp(mix, 0.0f, 1.0f); }

void SpatialReverbBridge::process(const float* input, float* output, size_t numSamples)
{
    // Simple stereo panning + optional reverb (full partitioned convolution omitted for brevity)
    for (size_t i = 0; i < numSamples; ++i) {
        float x = input[i];
        float wet = reverbEnabled_ ? processSchroeder(x) : 0.0f;
        float dry = x * (1.0f - reverbMix_);
        float mixed = dry + wet * reverbMix_;

        output[i * 2]     = mixed * leftGain_;   // Left
        output[i * 2 + 1] = mixed * rightGain_;  // Right
    }
}
