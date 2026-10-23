"""
Training template for HarmoniaCodec.
Adapt encode/decode signatures to the actual repository API.
"""

import torch
import torch.nn as nn
import torchaudio
from torch.utils.data import Dataset, DataLoader
import os


class AudioDataset(Dataset):
    def __init__(self, root_dir: str, sample_rate: int = 24000, segment_length: float = 2.0):
        self.sample_rate = sample_rate
        self.segment_samples = int(segment_length * sample_rate)
        self.file_paths = []

        for root, _, files in os.walk(root_dir):
            for f in files:
                if f.endswith((".wav", ".flac")):
                    self.file_paths.append(os.path.join(root, f))

        print(f"[*] Found {len(self.file_paths)} audio files.")
        self.resampler = torchaudio.transforms.Resample(orig_freq=16000, new_freq=sample_rate)

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        path = self.file_paths[idx]
        wav, sr = torchaudio.load(path)

        if sr != self.sample_rate:
            wav = self.resampler(wav)

        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)

        if wav.shape[1] < self.segment_samples:
            pad = self.segment_samples - wav.shape[1]
            wav = nn.functional.pad(wav, (0, pad))
        else:
            wav = wav[:, :self.segment_samples]

        return wav.squeeze(0)


def train():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[*] Training on {device}")

    lr = 3e-4
    batch_size = 8
    epochs = 50

    # Point this to your LibriSpeech or VCTK path
    dataset = AudioDataset("/path/to/librispeech/train-clean-100", sample_rate=24000)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=4)

    # from harmonia import HarmoniaCodec
    # codec = HarmoniaCodec().to(device)
    # For now we leave a placeholder
    print("[!] Replace with actual HarmoniaCodec instantiation")
    return

    optimizer = torch.optim.Adam(codec.parameters(), lr=lr)
    criterion = nn.L1Loss()

    codec.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for batch_idx, wav in enumerate(dataloader):
            wav = wav.to(device)
            encoded = codec.encode(wav.unsqueeze(1))
            reconstructed = codec.decode(encoded).squeeze(1)
            loss = criterion(reconstructed, wav)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            if batch_idx % 100 == 0:
                print(f"Epoch [{epoch}/{epochs}], Batch [{batch_idx}], Loss: {loss.item():.4f}")

        avg = total_loss / len(dataloader)
        print(f"=== Epoch {epoch} complete. Avg Loss: {avg:.4f} ===")
        torch.save(codec.state_dict(), f"harmonia_checkpoint_epoch_{epoch}.pt")

    print("[*] Training complete.")


if __name__ == "__main__":
    train()
