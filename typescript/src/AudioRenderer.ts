/**
 * ElevenX TypeScript 3D Audio Renderer
 * Receives Opus / PCM over WebSocket and renders binaural audio
 * with dynamic PannerNode positioning.
 */

export class ElevenXAudioRenderer {
  private ctx: AudioContext;
  private panner: PannerNode;
  private gain: GainNode;
  private ws: WebSocket | null = null;
  private workletNode: AudioWorkletNode | null = null;

  constructor() {
    this.ctx = new AudioContext({ sampleRate: 24000 });
    this.panner = this.ctx.createPanner();
    this.panner.panningModel = "HRTF";
    this.panner.distanceModel = "inverse";
    this.panner.refDistance = 1;
    this.panner.maxDistance = 10;
    this.panner.rolloffFactor = 1;

    this.gain = this.ctx.createGain();
    this.gain.gain.value = 0.8;

    this.panner.connect(this.gain);
    this.gain.connect(this.ctx.destination);

    // Default position in front of listener
    this.setPosition(0, 0, -1);
  }

  /** Move the virtual voice in 3D space (meters relative to listener) */
  setPosition(x: number, y: number, z: number) {
    this.panner.positionX.value = x;
    this.panner.positionY.value = y;
    this.panner.positionZ.value = z;
  }

  /** Connect to the ElevenX Rust / Python WebSocket stream */
  async connect(url: string = "ws://localhost:8080/ws/audio") {
    if (this.ctx.state === "suspended") {
      await this.ctx.resume();
    }

    this.ws = new WebSocket(url);
    this.ws.binaryType = "arraybuffer";

    this.ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        this.playPcmChunk(ev.data);
      }
    };

    this.ws.onopen = () => console.log("[ElevenX] WebSocket connected");
    this.ws.onclose = () => console.log("[ElevenX] WebSocket closed");
    this.ws.onerror = (e) => console.error("[ElevenX] WS error", e);
  }

  private playPcmChunk(buffer: ArrayBuffer) {
    const int16 = new Int16Array(buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768.0;
    }

    const audioBuffer = this.ctx.createBuffer(1, float32.length, this.ctx.sampleRate);
    audioBuffer.copyToChannel(float32, 0);

    const source = this.ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.panner);
    source.start();
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }
}

// Simple demo UI helper
export function createPositionSliders(renderer: ElevenXAudioRenderer, container: HTMLElement) {
  const axes = ["X", "Y", "Z"];
  const values = [0, 0, -1];

  axes.forEach((axis, i) => {
    const label = document.createElement("label");
    label.textContent = `${axis}: `;
    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = "-5";
    slider.max = "5";
    slider.step = "0.1";
    slider.value = String(values[i]);
    slider.oninput = () => {
      values[i] = parseFloat(slider.value);
      renderer.setPosition(values[0], values[1], values[2]);
    };
    label.appendChild(slider);
    container.appendChild(label);
    container.appendChild(document.createElement("br"));
  });
}
