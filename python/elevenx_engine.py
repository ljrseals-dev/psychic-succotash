"""
ElevenX Engine – Core TTS + Cloning + Streaming
Python Brain of the polyglot pipeline.
"""

import torch
import numpy as np
import soundfile as sf
import time
import yaml
from pathlib import Path
from typing import Generator, Optional
from TTS.api import TTS
from speechbrain.pretrained import EncoderClassifier

try:
    from spatial_audio import SpatialAudioRenderer
except ImportError:
    SpatialAudioRenderer = None


class ElevenXEngine:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.device = self.config["system"]["device"]
        if self.device == "cuda" and not torch.cuda.is_available():
            print("[!] CUDA not available – falling back to CPU")
            self.device = "cpu"

        self.sample_rate = self.config["system"]["sample_rate"]

        print(f"[*] Loading XTTS-v2 on {self.device}...")
        self.tts = TTS(self.config["tts"]["model_name"]).to(self.device)

        print("[*] Loading SpeechBrain ECAPA-TDNN speaker encoder...")
        self.speaker_encoder = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            run_opts={"device": self.device}
        )

        self._gpt_cond_latent = None
        self._speaker_embedding = None
        self._ref_path = None

        self.spatial = None
        if SpatialAudioRenderer is not None:
            self.spatial = SpatialAudioRenderer(self.config)

        self.use_codec = self.config["system"].get("use_codec", False)
        if self.use_codec:
            try:
                from harmonia import HarmoniaCodec
                self.codec = HarmoniaCodec()
            except ImportError:
                print("[!] HarmoniaCodec not found – disabling codec")
                self.use_codec = False

        print("[*] ElevenX Engine Ready.")

    def extract_voice_embedding(self, reference_audio_path: str) -> torch.Tensor:
        signal, fs = sf.read(reference_audio_path)
        signal = torch.tensor(signal, dtype=torch.float32).unsqueeze(0).to(self.device)
        embeddings = self.speaker_encoder.encode_batch(signal)
        return embeddings.squeeze()

    def _prepare_conditioning(self, reference_audio_path: str):
        if (self._gpt_cond_latent is None or
            self._speaker_embedding is None or
            self._ref_path != reference_audio_path):
            print("[*] Computing conditioning (one-time)...")
            gpt_cond_latent, speaker_embedding = self.tts.synthesizer.tts_model.get_conditioning_latents(
                audio_path=[reference_audio_path]
            )
            self._gpt_cond_latent = gpt_cond_latent
            self._speaker_embedding = speaker_embedding
            self._ref_path = reference_audio_path
            print("[*] Conditioning cached.")

    def synthesize_stream(
        self,
        text: str,
        reference_audio_path: str,
        emotion: str = "neutral"
    ) -> Generator[np.ndarray, None, None]:
        self._prepare_conditioning(reference_audio_path)

        emotion_prefix = self.config["tts"]["emotion_prompts"].get(emotion, "")
        conditioned_text = f"{emotion_prefix} {text}".strip()

        chunks = self.tts.synthesizer.tts_model.inference_stream(
            text=conditioned_text,
            language=self.config["tts"]["language"],
            gpt_cond_latent=self._gpt_cond_latent,
            speaker_embedding=self._speaker_embedding,
            stream_chunk_size=self.config["system"]["streaming_chunk_size"],
            enable_text_splitting=True,
            temperature=0.75 if emotion == "neutral" else 0.9,
            repetition_penalty=7.0,
        )

        for chunk in chunks:
            audio_np = chunk.squeeze().cpu().numpy()

            if self.use_codec:
                audio_tensor = torch.tensor(audio_np).unsqueeze(0).to(self.device)
                encoded = self.codec.encode(audio_tensor)
                decoded = self.codec.decode(encoded)
                audio_np = decoded.squeeze().cpu().numpy()

            yield audio_np

    def synthesize_full(
        self,
        text: str,
        reference_audio_path: str,
        emotion: str = "neutral",
        spatial: bool = False
    ) -> np.ndarray:
        chunks = list(self.synthesize_stream(text, reference_audio_path, emotion))
        audio = np.concatenate(chunks, axis=-1)

        if spatial and self.spatial is not None:
            audio = self.spatial.render(audio)

        return audio


if __name__ == "__main__":
    engine = ElevenXEngine()
    text = "I don't compete. I replace."
    ref_audio = "my_voice_sample.wav"

    if not Path(ref_audio).exists():
        print(f"[!] Reference file '{ref_audio}' not found. Create a short WAV first.")
    else:
        print("[*] Generating audio...")
        chunks = []
        start = time.time()
        for i, chunk in enumerate(engine.synthesize_stream(text, ref_audio, emotion="confidence")):
            if i == 0:
                print(f"[*] First chunk latency: {(time.time()-start)*1000:.1f}ms")
            chunks.append(chunk)

        full_audio = np.concatenate(chunks)
        sf.write("elevenx_output.wav", full_audio, engine.sample_rate)
        print(f"[*] Generated {len(full_audio)/engine.sample_rate:.2f}s of audio")
