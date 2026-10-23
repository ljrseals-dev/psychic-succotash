import { ElevenXAudioRenderer, createPositionSliders } from "./AudioRenderer";

async function main() {
  const renderer = new ElevenXAudioRenderer();
  await renderer.connect("ws://localhost:8080/ws/audio");

  // Optional: attach UI sliders if running in browser
  const container = document.getElementById("controls");
  if (container) {
    createPositionSliders(renderer, container);
  }

  console.log("ElevenX 3D Audio Renderer ready");
}

main().catch(console.error);
