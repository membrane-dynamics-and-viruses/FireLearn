import logging
import os

import pandas as pd
from PyQt6.QtCore import pyqtSignal, QThread
from matplotlib import pyplot as plt

from QtScripts.CONTROLLER import data_processing as dpr
from fiiireflyyy import process as fp

logger = logging.getLogger("__FileProcessor__")

class FileProcess(QThread):
    result_ready = pyqtSignal(object)
    progress_made = pyqtSignal(int)
    finished = pyqtSignal(str, object)
    error_occurred = pyqtSignal(str, str)
    cancelled = pyqtSignal()

    def __init__(self,name, files_queue, harmonics, processing_basename, model_vars, parent=None):
        super().__init__(parent)
        self.name = name
        self.files_queue = files_queue
        self.harmonics = harmonics
        self.processing_basename = processing_basename
        self.model_vars = model_vars
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        while not self._stop_flag:
            try:
                if self.files_queue.empty():
                    break

                file = self.files_queue.get_nowait()

                if file is None:
                    break
                    
                if self._stop_flag:
                    break
                result = self._process_file(file, self.harmonics, self.processing_basename)
                if self._stop_flag:
                    break

                self.result_ready.emit(result)

                self.progress_made.emit(1)

                logger.info(f"Worker {self.objectName()} processed file: {file}")

            except Exception as e:
                logger.exception(f"Worker {self.objectName()} encountered an error.")
                self.error_occurred.emit(self.objectName(), str(e))
                break
        if self._stop_flag:
            self.cancelled.emit()
        else:
            self.finished.emit(self.objectName(), self.processing_basename)

    # def process_file_for_worker(self, files_queue, harmonics, processing_basename):
    #     """Processes files from the queue and updates the progress queue until a sentinel is received."""
    #     while True:
    #         try:
    #             if self._stop_flag:
    #                 logger.info(f"{self.name} cancelled")
    #                 break
    # 
    #             file = files_queue.get(timeout=1)
    # 
    #             # Check for the sentinel value to trigger shutdown
    #             if file is None:
    #                 logger.info(f"Worker {self.name} received stop signal and is exiting gracefully.")
    #                 break
    # 
    #             logger.debug(f"Worker {self.name} - file queue size: {files_queue.qsize()}, processing file: {file}")
    #             result = self._process_file(file, harmonics, processing_basename)
    #             logger.debug(f"{self.name} Attempting to put result of size {sys.getsizeof(result)} in queue"
    #                          f" with size {self.result_queue.qsize()}")
    # 
    #             if self._stop_flag:
    #                 logger.info(f"{self.name} cancelled")
    #                 break
    # 
    #             if self.result_queue.full():
    #                 logger.info(f"Worker {self.name} encountered an error adding results of {file}:")
    # 
    #             self.result_queue.put((file, result), timeout=10)
    #             with self.lock:
    #                 self.progress_queue.put(1)
    #             logger.info(f"Worker {self.name} DONE - file queue size: {files_queue.qsize()}, file: {file}")
    #         except Exception as e:
    #             logger.info(f"Worker {self.name} encountered an error. Terminating. {e}")
    #             break
    # 
    #     logger.info(f"Worker {self.name} exiting. Final file queue size: {files_queue.qsize()}")

    def _process_file(self, file, harmonics, processing_basename):
        """
        Processes a single file by performing several operations such as filtering,
        downsampling, Fourier transforms, and averaging. The processed data is
        either saved to a file or added to a list for further processing.

        Parameters
        ----------
        file : str
            The path to the CSV file to be processed.
        Returns
        -------
        tuple
            A tuple containing:
            - processing_basename : list of str
                The base names used in the processed file's name.
            - processed_files_to_make_dataset : list of tuple
                The updated list of tuples with processed dataframes and their filenames.

        Notes
        -----
        This function applies several transformations to the raw data in the input file:
        - Beheading: Skips rows from the file if the corresponding setting is enabled.
        - Column Selection: Selects specific columns if requested.
        - Down Sampling: Samples the data at a specific rate if enabled.
        - Filtering: Applies filters (e.g., highpass, lowpass, bandstop, or bandpass) on the signals.
        - Fast Fourier Transform (FFT): Applies FFT to the signal if enabled.
        - Averaging: Averages the signal across selected columns if requested.
        - Interpolation: Interpolates the signal if the setting is enabled.

        After processing, the data is either saved as a CSV file or added to the
        `processed_files_to_make_dataset` list depending on the user's settings.

        """
        df = self._behead(file)
        df = self._column_selection(df)
        samples = self._down_sampling(df)
        processed_files_to_make_dataset = []
        for df_s in samples:
            if self._stop_flag:
                break
            if self.model_vars['filter_ckbox']:
                df_s = self._filter(df_s, harmonics=harmonics)

            if self._stop_flag:
                break
            if self.model_vars['fft_ckbox']:
                df_s = self._fast_fourier_transform(df_s)

            if self._stop_flag:
                break
            if self.model_vars['average_ckbox']:
                df_s = self._average_columns(df_s)

            if self._stop_flag:
                break
            # interpolation signal
            df_s_processed = self._linear_interpolation(df_s)

            if self._stop_flag:
                break
            # saving file
            if self.model_vars['make_dataset_ckbox']:
                processed_files_to_make_dataset.append((df_s_processed, file))
            else:
                self._save_individual_processed_file(file, df_s_processed, processing_basename)
                processed_files_to_make_dataset.append((df_s_processed, file))
        return processed_files_to_make_dataset

    def _behead(self, file):
        """
        Behead a csv file using the skiprows argument if enabled in the UI.
        Parameters
        ----------
        file : str
            The original file path that will be read and processed

        Returns
        -------
        df : pd.Dataframe
            Beheaded (or not) dataframe depending on the UI values.
        """

        if self.model_vars['behead_ckbox']:
            df = pd.read_csv(file, index_col=False, skiprows=self._get_skiprows())
            self.progress_made.emit(1)
        else:
            df = pd.read_csv(file, index_col=False)
        return df

    def _get_skiprows(self):
        """
        get the skiprow entry value in the UI

        Returns
        -------
        skiprow: int
            the number (int) of rows to skip based on UI values

        """
        skiprow = 0
        if self.model_vars['behead_ckbox']:
            skiprow = int(self.model_vars['behead_edit'])
        return skiprow

    def _column_selection(self, df):
        """
        Select the top n columns based on UI values.

        Parameters
        ----------
        df : pd.Dataframe
            data to process
        Returns
        -------
        df : pd.Dataframe
            returns a dataframe whith only selected columns, or untouched dataframe depending on UI values.
        """
        if self.model_vars['select_column_ckbox']:
            df = dpr.top_n_columns(df, int(self.model_vars['select_column_edit']),
                                   except_column=self.model_vars["exception_column_edit"])
            self.progress_made.emit(1)

        return df

    def _down_sampling(self, df):
        """
        Performs downsampling on the given dataframe based on the specified sampling rate.

        Parameters
        ----------
        df : pandas.DataFrame
            The dataframe containing the signal data to be downsampled.

        Returns
        -------
        list of pandas.DataFrame
            A list containing the downsampled dataframe(s). If downsampling is not
            performed, the original dataframe is returned in the list.

        Notes
        -----
        If downsampling is enabled (based on the `signal sampling ckbox` flag in
        `self.model_vars`), the function applies downsampling to the dataframe using
        the specified sampling rate. If downsampling is not enabled, the original
        dataframe is returned without modification.

        """
        samples = []
        if self.model_vars['subsample_ckbox']:
            samples = fp.equal_samples(df, int(self.model_vars['subsample_edit']),)
            self.progress_made.emit(1)

        else:
            self.progress_made.emit(1)
            samples.append(df)

        return samples

    def _filter(self, df_s, harmonics):
        """
        Applies a series of filters to the signal data in the given dataframe.

        Parameters
        ----------
        df_s : pandas.DataFrame
            The dataframe containing signal data to be filtered.

        Returns
        -------
        pandas.DataFrame
            The filtered dataframe with the updated signal data after applying the
            specified filters.

        Notes
        -----
        This function applies a specified filter (highpass, lowpass, bandstop, or bandpass)
        to each signal channel in the dataframe, based on the settings in `self.model_vars`.
        If the harmonics checkbox is enabled, additional bandstop filters are applied around
        each harmonic frequency. The dataframe is updated with the filtered signal data.

        The filtering operations are performed using a Butterworth filter with configurable
        filter order and cutoff frequencies. The filter type and parameters (e.g., first and
        second cutoff frequencies) are dynamically selected based on the model's settings.

        """

        for ch in [col for col in df_s.columns if self.model_vars["exception_column_edit"] not in col]:
            df_s_ch = df_s[ch]
            if self.model_vars['filter_type_cbbox'] == 'Highpass' and self.model_vars['filter_first_cut_edit']:
                df_s_ch = dpr.butter_filter(df_s_ch, order=int(self.model_vars['filter_order_edit']),
                                            btype='highpass',
                                            cut=float(self.model_vars['filter_first_cut_edit']),
                                            fs=float(self.model_vars["filter_sampling_frequency_edit"]))
            elif self.model_vars['filter_type_cbbox'] == 'Lowpass' and self.model_vars['filter_first_cut_edit']:
                df_s_ch = dpr.butter_filter(df_s_ch, order=int(self.model_vars['filter_order_edit']),
                                            btype='lowpass',
                                            cut=float(self.model_vars['filter_first_cut_edit']),
                                            fs=float(self.model_vars["filter_sampling_frequency_edit"]))
            elif self.model_vars['filter_type_cbbox'] == 'Bandstop' and self.model_vars['filter_first_cut_edit'] and \
                    self.model_vars['filter_second_cut_edit']:
                df_s_ch = dpr.butter_filter(df_s_ch, order=int(self.model_vars['filter_order_edit']),
                                            btype='bandstop',
                                            lowcut=float(self.model_vars['filter_first_cut_edit']),
                                            highcut=float(self.model_vars['filter_second_cut_edit']),
                                            fs=float(self.model_vars["filter_sampling_frequency_edit"]))
            elif self.model_vars['filter_type_cbbox'] == 'Bandpass' and self.model_vars['filter_first_cut_edit'] and \
                    self.model_vars['filter_second_cut_edit']:
                df_s_ch = dpr.butter_filter(df_s_ch, order=int(self.model_vars['filter_order_edit']),
                                            btype='bandpass',
                                            lowcut=float(self.model_vars['filter_first_cut_edit']),
                                            highcut=float(self.model_vars['filter_second_cut_edit']),
                                            fs=float(self.model_vars["filter_sampling_frequency_edit"]))
            if self.model_vars['harmonics_ckbox']:
                for h in harmonics:
                    df_s_ch = dpr.butter_filter(df_s_ch,
                                                order=int(self.model_vars['filter_order_edit']),
                                                btype='bandstop', lowcut=h - 2,
                                                highcut=h + 2,
                                                fs=float(self.model_vars["filter_sampling_frequency_edit"]))

            df_s.loc[:, ch] = df_s_ch
            self.progress_made.emit(1)
        return df_s

    def _fast_fourier_transform(self, df_s):
        """
        Applies Fast Fourier Transform (FFT) to each signal channel in the given dataframe.

        Parameters
        ----------
        df_s : pandas.DataFrame
            The dataframe containing signal data to be transformed using FFT.

        Returns
        -------
        pandas.DataFrame
            A dataframe containing the FFT results for each signal channel. The "Frequency [Hz]"
            column is added to the dataframe along with the transformed signal data for each channel.

        Notes
        -----
        This function applies FFT to each signal channel in the dataframe, excluding columns that match
        the "except column" filter. The resulting FFT values are stored in a new dataframe (`df_s_fft`),
        with the corresponding frequency values in the "Frequency [Hz]" column.

        The FFT operation is performed using the `dpr.fast_fourier` function, with the sampling frequency
        provided by the model's configuration (`signal fft sf`).
        """
        df_s_fft = pd.DataFrame()
        for ch in [col for col in df_s.columns if self.model_vars["exception_column_edit"] not in col]:
            df_s_ch = df_s[ch]
            # fast fourier
            clean_fft, clean_freqs = dpr.fast_fourier(df_s_ch, int(self.model_vars['fft_edit']))
            if "Frequency [Hz]" not in df_s_fft.columns:
                df_s_fft['Frequency [Hz]'] = clean_freqs
            df_s_fft[ch] = clean_fft
            
            self.progress_made.emit(1)
        df_s = df_s_fft

        return df_s

    def _average_columns(self, df_s):
        """
        Average columns except the frequency column or teh 'exception column' provided in the UI.

        Parameters
        ----------
        df_s : pandas.DataFrame
            The dataframe containing signal data to be transformed using FFT.

        Returns
        -------

        """

        if self.model_vars['fft_ckbox']:
            df_s = dpr.merge_all_columns_to_mean(df_s, "Frequency [Hz]").round(3)
        else:
            df_s = dpr.merge_all_columns_to_mean(df_s, self.model_vars["exception_column_edit"]).round(3)

        self.progress_made.emit(1)

        return df_s

    def _linear_interpolation(self, df_s):
        df_s_processed = pd.DataFrame()
        if self.model_vars['lin_interp_ckbox']:
            for ch in df_s.columns:
                df_s_processed[ch] = fp.smoothing(df_s[ch], int(self.model_vars['lin_interp_edit']),
                                                  'mean')
            self.progress_made.emit(1)
        else:
            df_s_processed = df_s

        return df_s_processed

    def _save_individual_processed_file(self, file, df_s_processed, processing_basename):
        """
        Saves an individual processed dataframe to a CSV file with a constructed filename.

        Parameters
        ----------
        file : str
            The path to the original input file that was processed.

        df_s_processed : pandas.DataFrame
            The processed dataframe that will be saved to a CSV file.

        Returns
        -------
        None
            This function does not return any value. It saves the processed dataframe
            to a CSV file at the location specified in the model's variables.

        Notes
        -----
        The function constructs the output file's name by combining the original file's name
        (without extension), the `processing_basename` list, and the `.csv` extension. The
        resulting filename is used to save the processed dataframe to the specified directory
        (from `self.model_vars['filename save under']`).

        """
        filename_constructor = []
        filename = os.path.basename(file).split(".")[0]

        filename_constructor.append(filename)
        filename_constructor.append("_".join(processing_basename))
        filename_constructor.append(".csv")
        df_s_processed.to_csv(
            os.path.join(self.model_vars['save_edit'], '_'.join(filename_constructor)),
            index=False)
