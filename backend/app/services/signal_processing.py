from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np

FEATURE_EXTRACTOR_VERSION = "signal-features-v1"


@dataclass(frozen=True)
class SignalFeatureResult:
    features: dict[str, float]
    configuration: dict[str, float | int | str]


def _moments(values: np.ndarray) -> tuple[float, float]:
    centered = values - float(np.mean(values))
    standard_deviation = float(np.std(values))
    if standard_deviation == 0:
        return 0.0, 0.0
    normalized = centered / standard_deviation
    return float(np.mean(normalized**3)), float(np.mean(normalized**4))


def extract_signal_features(
    samples: list[float],
    sample_rate_hz: float,
    *,
    smoothing_window: int = 1,
) -> SignalFeatureResult:
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    if len(samples) < 8:
        raise ValueError("At least 8 samples are required")
    if smoothing_window < 1 or smoothing_window > len(samples):
        raise ValueError("smoothing_window must be between 1 and the sample count")

    raw = np.asarray(samples, dtype=np.float64)
    if not np.all(np.isfinite(raw)):
        raise ValueError("Samples must contain only finite values")

    if smoothing_window > 1:
        kernel = np.ones(smoothing_window, dtype=np.float64) / smoothing_window
        signal = np.convolve(raw, kernel, mode="valid")
    else:
        signal = raw

    mean = float(np.mean(signal))
    rms = float(sqrt(float(np.mean(signal**2))))
    variance = float(np.var(signal))
    peak = float(np.max(np.abs(signal)))
    skewness, kurtosis = _moments(signal)
    crest_factor = peak / rms if rms > 0 else 0.0

    centered = signal - mean
    spectrum = np.fft.rfft(centered)
    frequencies = np.fft.rfftfreq(len(centered), d=1.0 / sample_rate_hz)
    power = (np.abs(spectrum) ** 2) / len(centered)
    if len(power) > 1:
        dominant_index = int(np.argmax(power[1:]) + 1)
        dominant_frequency = float(frequencies[dominant_index])
    else:
        dominant_frequency = 0.0

    total_energy = float(np.sum(power))
    nyquist = sample_rate_hz / 2

    def band_fraction(lower: float, upper: float) -> float:
        mask = (frequencies >= lower) & (frequencies < upper)
        return float(np.sum(power[mask]) / total_energy) if total_energy > 0 else 0.0

    second_harmonic_frequency = dominant_frequency * 2
    if dominant_frequency > 0 and second_harmonic_frequency <= nyquist:
        second_harmonic_index = int(np.argmin(np.abs(frequencies - second_harmonic_frequency)))
        fundamental_power = float(power[dominant_index])
        second_harmonic_ratio = float(power[second_harmonic_index] / fundamental_power) if fundamental_power > 0 else 0.0
    else:
        second_harmonic_ratio = 0.0

    features = {
        "mean": mean,
        "rms": rms,
        "variance": variance,
        "peak": peak,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "crest_factor": float(crest_factor),
        "dominant_frequency_hz": dominant_frequency,
        "spectral_energy": total_energy,
        "low_band_energy_fraction": band_fraction(0, nyquist * 0.1),
        "mid_band_energy_fraction": band_fraction(nyquist * 0.1, nyquist * 0.3),
        "high_band_energy_fraction": band_fraction(nyquist * 0.3, float(np.nextafter(nyquist, np.inf))),
        "second_harmonic_ratio": second_harmonic_ratio,
    }
    return SignalFeatureResult(
        features=features,
        configuration={
            "extractor_version": FEATURE_EXTRACTOR_VERSION,
            "smoothing": "moving_average",
            "smoothing_window": smoothing_window,
            "sample_rate_hz": sample_rate_hz,
            "input_sample_count": len(samples),
            "processed_sample_count": len(signal),
            "frequency_bands": "low=[0,0.1*nyquist), mid=[0.1,0.3*nyquist), high=[0.3,nyquist]",
        },
    )
