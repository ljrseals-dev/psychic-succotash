# ElevenX Systems Architecture

## Polyglot Pipeline

See root README for the full diagram.

## Component Responsibilities

| Layer              | Language    | Responsibility                          | Latency Target |
|--------------------|-------------|-----------------------------------------|----------------|
| Client             | TypeScript  | WebRTC / WebSocket + HRTF PannerNode    | < 5 ms render  |
| API Gateway        | Rust        | Auth, rate-limit, 100k+ connections     | < 1 ms         |
| Orchestration      | Python      | XTTS-v2, emotion, cloning, Ray          | first chunk ~150-200 ms |
| Spatial Bridge     | C++         | RIR convolution, Schroeder, HRTF        | < 3 ms / buffer |
| Codec & Transport  | C++ / Rust  | HarmoniaCodec + Opus                    | < 5 ms         |

## Critical Path for <10 ms

1. TensorRT / ONNX Runtime for TTS + vocoder
2. Shared-memory ring buffer (no network hop between Python ↔ C++/Rust)
3. 256-sample buffers at 24 kHz
4. Pre-warmed conditioning latents
5. Zero-copy Opus packaging in Rust

## Build Order

1. Python engine + FastAPI (works today)
2. C++ SpatialReverbBridge (compile with CMake)
3. Rust streamer (cargo build)
4. TypeScript client
5. TensorRT export + shared-memory integration
6. Kubernetes + KEDA autoscaling
