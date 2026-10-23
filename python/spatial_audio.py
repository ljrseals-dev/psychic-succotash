"""
Fallback pure-Python spatial renderer using pyroomacoustics.
For production, the C++ SpatialReverbBridge is preferred.
"""

import numpy as np
import pyroomacoustics as pra
from pyroomacoustics.directivities import DirectionVector, Cardioid


class SpatialAudioRenderer:
    """Renders mono audio into binaural 3D audio."""

    def __init__(self, config: dict):
        self.config = config["spatial"]
        self.fs = config["system"]["sample_rate"]

        self.room = pra.ShoeBox(
            p=self.config["room_dim"],
            materials=pra.Material(0.2),
            fs=self.fs,
            max_order=10,
        )

        dir_ = Cardioid(DirectionVector(azimuth=0, colatitude=90), gain=1.0)
        self.room.add_source(self.config["source_position"], directivity=dir_)

        mic_pos = np.array(self.config["mic_position"])
        self.room.add_microphone_array(
            pra.MicrophoneArray(
                np.array([mic_pos, mic_pos + [0, 0, 0.15]]).T,
                self.fs
            )
        )

    def render(self, audio: np.ndarray) -> np.ndarray:
        self.room.sources[0].signal = audio
        self.room.simulate()
        binaural = self.room.mic_array.signals
        return binaural.T  # (n_samples, 2)
