"""
Ethical watermarking using Meta AudioSeal.
"""

import torch
import torchaudio
from audioseal import AudioSeal


class AudioWatermark:
    def __init__(self, device=None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.generator = AudioSeal.load_generator("audioseal_wm_16bits").to(device)
        self.detector = AudioSeal.load_detector("audioseal_detector_16bits").to(device)

    def embed(self, waveform: torch.Tensor, sample_rate: int = 24000,
              message: str = "elevenx") -> torch.Tensor:
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)

        payload = self.generator.encode_message(message)
        watermark = self.generator.get_watermark(
            waveform.unsqueeze(1), sample_rate, message=payload
        )
        watermarked = waveform + watermark.squeeze(1)
        return watermarked.squeeze(0)

    def detect(self, waveform: torch.Tensor, sample_rate: int = 24000) -> dict:
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)

        result = self.detector.detect_watermark(
            waveform.unsqueeze(1), sample_rate
        )
        return {
            "detected": result["detected"].item(),
            "message": result.get("message", "unknown"),
            "confidence": result.get("confidence", 0.0)
        }


if __name__ == "__main__":
    wm = AudioWatermark()
    audio, sr = torchaudio.load("elevenx_output.wav")
    watermarked = wm.embed(audio, sr, message="elevenx-demo")
    torchaudio.save("watermarked_output.wav", watermarked.unsqueeze(0), sr)
    print(wm.detect(watermarked, sr))
