import numpy as np
import pandas as pd
from scipy.signal import butter, freqz, filtfilt
import logging
logger = logging.getLogger("__data_processing__")

def butter_filter(signal, order, btype, lowcut=None, highcut=None, cut=None, fs=None ):
    """
    Applies a Butterworth filter to a signal.

    Parameters
    ----------
    signal : np.ndarray
        The input signal to filter.
    order : int
        The order of the filter.
    btype : str
        Type of filter ('lowpass', 'highpass', 'bandpass', or 'bandstop').
    lowcut : float, optional
        Low-frequency cutoff for bandpass and bandstop filters.
    highcut : float, optional
        High-frequency cutoff for bandpass and bandstop filters.
    cut : float, optional
        Cutoff frequency for lowpass or highpass filters.
    fs : int, optional, default=10000
        Sampling frequency of the signal.

    Returns
    -------
    np.ndarray
        The filtered signal.
    """
    signal = np.asarray(pd.to_numeric(signal, errors='coerce'), dtype=np.float64)
    if np.isnan(signal).any():
        raise ValueError(
            f"Signal contains NaN after numeric coercion — "
            f"{np.isnan(signal).sum()} non-numeric value(s) found.")

    fs = int(fs)
    nyq = 0.5 * fs
    if cut:
        midcut = cut / nyq
    if lowcut:
        low = lowcut / nyq
    if highcut:
        high = highcut / nyq
    if btype in ["highpass", "lowpass"]:
        b, a = butter(order, midcut, btype=btype)
        w, h = freqz(b, a)
    elif btype in ["bandstop", "bandpass"]:
        b, a = butter(order, [low, high], btype=btype)
        w, h = freqz(b, a)

    #xanswer = (w / (2 * np.pi)) * freq
    #yanswer = 20 * np.log10(abs(h))

    filtered_signal = filtfilt(b, a, signal)

    return filtered_signal  # , xanswer, yanswer


def fast_fourier_deprecated(signal, freq):
    """
    Computes the Fast Fourier Transform (FFT) of a signal.

    Parameters
    ----------
    signal : np.ndarray
        The input signal.
    freq : int
        The sampling frequency.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        The FFT magnitude spectrum and the corresponding frequencies.
    """
    
    fft_df = np.fft.fft(signal)
    freqs = np.fft.fftfreq(len(signal), d=1 / freq)

    clean_fft_df = abs(fft_df)
    clean_freqs = abs(freqs[0:len(freqs // 2)])
    return clean_fft_df[:int(len(clean_fft_df) / 2)], clean_freqs[:int(len(clean_freqs) / 2)]

def fast_fourier(signal, freq):
    """
    Computes the FFT magnitude of a windowed signal.

    Parameters
    ----------
    signal : np.ndarray
        Input signal.
    freq : int
        Sampling frequency in Hz.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        Magnitude spectrum and corresponding frequencies (positive only).
    """
    N = len(signal)

    # Apply Hann window
    window = np.hanning(N)
    signal_windowed = signal * window

    # Compute FFT
    fft_vals = np.fft.fft(signal_windowed)
    fft_magnitude = np.abs(fft_vals) / N  # normalize

    # Compute frequencies
    freqs = np.fft.fftfreq(N, d=1/freq)

    # Return only positive frequencies
    return fft_magnitude[:N//2], freqs[:N//2]


def merge_all_columns_to_mean(df: pd.DataFrame, except_column=""):
    """
    Computes the mean of all columns in a DataFrame except for one optional column.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    except_column : str, optional, default=""
        The column to exclude from the mean computation.

    Returns
    -------
    pd.DataFrame
        A DataFrame with the mean of the selected columns and the excluded column (if specified).
    """

    excepted_column = pd.DataFrame()
    if except_column:
        for col in df.columns:
            if except_column in col:
                except_column = col
        excepted_column = df[except_column]
        df.drop(except_column, axis=1, inplace=True)

    df_mean = pd.DataFrame(columns=["mean", ])
    df_mean['mean'] = df.mean(axis=1)

    if except_column != "":
        for col in df.columns:
            if except_column in col:
                except_column = col
        df_mean[except_column] = excepted_column

    return df_mean



def top_n_columns(df, n, except_column=""):
    """
    Selects the top N columns with the highest standard deviation.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame containing electrode signals.
    n : int
        The number of columns to retain based on standard deviation.
    except_column : str, optional, default="TimeStamp [µs]"
        The column to exclude from selection but retain in the output.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the top N columns and the `except_column`.

    Notes
    -----
    - Uses standard deviation to rank columns.
    - Can be adapted to other ranking metrics by modifying the relevant section.

    Examples
    --------
    >> data = pd.read_csv("electrodes.csv")
    >> top_channels = top_n_electrodes(data, n=10, except_column="TimeStamp [µs]")
    """
    
    # getting the complete name of the column to exclude, in case of slight fluctuation in name
    dfc = df.copy()
    if except_column:
        for col in df.columns:
            if except_column in col:
                except_column = col
    
    # managing 'except_column'
        dfc = df.drop(except_column, axis=1)
    logger.debug(f"Excepted column from selection: {except_column}")
    df_filtered = pd.DataFrame()
    if except_column:
        df_filtered[except_column] = df[except_column]

    # getting the top channels by metric. Metric changes should be done here.
    all_metric = []
    for c in dfc.columns:
        all_metric.append(np.std(dfc[c]))
    top_indices = sorted(range(len(all_metric)), key=lambda i: all_metric[i], reverse=True)[:n]
    
    # creating resulting data
    for c in dfc.columns:
        index = dfc.columns.get_loc(c)
        if index in top_indices:
            df_filtered[c] = dfc[c]

    return df_filtered
