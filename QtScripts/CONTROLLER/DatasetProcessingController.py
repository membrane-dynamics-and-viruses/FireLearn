import datetime
import logging
import multiprocessing
import os
import pathlib
import random
import string
import time

import pandas as pd
from PyQt6.QtCore import Qt, QMutex
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from fiiireflyyy import files as ff

from QtScripts.MODEL.DatasetProcessingModel import DatasetProcessingModel
from QtScripts.PROCESSES.FileProcessor import FileProcess
from QtScripts.VIEW.DatasetProcessingView import DatasetProcessingView

logger = logging.getLogger("__DatasetProcessing__")


class DatasetProcessingController:
    def __init__(self, app: QApplication, parent_controller):
        self.app = app
        self.parent_controller = parent_controller
        self.model = DatasetProcessingModel(self)  # set model
        
        self.files_to_process = []
        self.files_queue = None
        
        self.lock = QMutex()
        self.progress_dialog = None
        
        self.processing_thread = None
        
        self.view = DatasetProcessingView(self.app, parent=self.parent_controller.view.dataset_tab, controller=self)
        self.threads_alive = False
        self.cancelled = False
        self.results = {}
        
        self.processing_time_start = datetime.datetime.now()

    def select_parent_directory(self):
        directory = QFileDialog.getExistingDirectory(parent=self.view.parent, caption="Select Parent Directory")
        if directory:
            self.model.parent_directory = directory
            self.view.widgets["path_to_parent_edit"].setText(directory)
            
    def select_single_file_processing(self):
        file = QFileDialog.getOpenFileName(parent=self.view.parent, caption="Select Processing File")[0]
        if file:
            self.model.single_file_processing = file
            self.view.widgets["path_to_file_edit"].setText(file)
    
    def select_save_processed_files_under(self):
        directory = QFileDialog.getExistingDirectory(parent=self.view.parent, caption="Select save directory")
        if directory:
            self.model.parent_directory = directory
            self.view.widgets["save_edit"].setText(directory)
            
    
    def check_params_validity(self):
        errors = []
        filesorter_errors = False
        signal_errors = False
        filename_errors = False
        
        if self.threads_alive:
            if self.cancelled:
                QMessageBox.warning(self.view, "Warning", "Threads from previous processing are still alive and being terminated."
                                     " Please wait a bit before starting a new processing", QMessageBox.StandardButton.Ok)
                return False
            else:
                QMessageBox.warning(self.view, "Warning", "Threads are currently alive."
                                                      "To start a new processing, please either cancel the current one "
                                                      "or wait for it to finish.", QMessageBox.StandardButton.Ok)
                return False
        
        
        # ------- PROCESSING
        if self.view.widgets["behead_ckbox"].checkState() == Qt.CheckState.Checked \
            and not self.view.widgets["behead_edit"].text():
            errors.append("You have to indicate a number of rows to behead the file(s).")
            signal_errors = True
            
        if self.view.widgets["select_column_ckbox"].checkState() == Qt.CheckState.Checked:
            if not self.view.widgets["select_column_edit"].text():
                errors.append("You have to indicate a number of columns to be selected.")
                signal_errors = True
            if self.view.widgets["select_column_mode_cbbox"].currentText() == "None":
                errors.append("You have to select a mode for column selection.")
                signal_errors = True
            if self.view.widgets["select_column_metric_cbbox"].currentText() == "None":
                errors.append("You have to select a metric for column selection.")
                signal_errors = True
        
        if self.view.widgets["subsample_ckbox"].checkState() == Qt.CheckState.Checked \
            and not self.view.widgets["subsample_edit"].text():
            errors.append("You have to indicate a number of sample to subsample the file(s).")
            signal_errors = True
            
        if self.view.widgets["harmonics_ckbox"].checkState() == Qt.CheckState.Checked:
            if self.view.widgets["harmonics_type_cbbox"].currentText() == "None":
                errors.append("You need to select a type for the harmonics.")
                signal_errors = True
            if not self.view.widgets["harmonics_nth_edit"].text():
                errors.append("You have to indicate the index of the last harmonic to be filtered.")
                signal_errors = True
            if not self.view.widgets["harmonics_frequency_edit"].text():
                errors.append("You have to indicate the frequency of the base harmonic to be filtered.")
                signal_errors = True
                
        if self.view.widgets["filter_ckbox"].checkState() == Qt.CheckState.Checked:
            if not all([self.view.widgets["filter_order_edit"].text(),
                        self.view.widgets["filter_type_cbbox"].currentText() != "None",
                        self.view.widgets["filter_sampling_frequency_edit"].text(),
                        self.view.widgets["filter_first_cut_edit"].text() ]):
                errors.append("You need to indicate the order, type, sampling frequency, and first cut at least to use "
                              "the filtering function.")
                signal_errors = True
            if self.view.widgets["filter_type_cbbox"].currentText() in ["Bandpass", "Bandstop"] and not self.view.widgets["filter_second_cut_edit"].text():
                errors.append("For filters of type bandpass and bandstop, you need to indicate the second frequency cut.")
                signal_errors = True

        if self.view.widgets["filter_first_cut_edit"].text() and self.view.widgets["filter_second_cut_edit"].text():
            if float(self.view.widgets["filter_first_cut_edit"].text()) > float(
                    self.view.widgets["filter_second_cut_edit"].text()):
                errors.append("The first cut must be smaller than the second cut frequency.")
                signal_errors = True

        if self.view.widgets["fft_ckbox"].checkState() == Qt.CheckState.Checked \
                and not self.view.widgets["fft_edit"].text():
            errors.append("You have to indicate a sampling frequency to use FFT.")
            signal_errors = True

        if self.view.widgets["fft_ckbox"].checkState() == Qt.CheckState.Checked:
            if self.view.widgets["filter_type_cbbox"].currentText() in ["Bandpass", "Bandstop"]:
                if float(self.view.widgets["filter_second_cut_edit"].text()) >= float(
                        self.view.widgets["filter_sampling_frequency_edit"].text()) / 2:
                    errors.append("Digital filter second cut frequency must be < 1/2 * sampling frequency.")
                    signal_errors = True
            if self.view.widgets["filter_type_cbbox"].currentText() in ["Lowpass", "Highpass"]:
                if float(self.view.widgets["filter_first_cut_edit"].text()) >= float(
                        self.view.widgets["filter_sampling_frequency_edit"].text()) / 2:
                    errors.append("Digital filter first cut frequency must be < 1/2 * sampling frequency.")
                    signal_errors = True
                    
        if self.view.widgets["lin_interp_ckbox"].checkState() == Qt.CheckState.Checked \
            and not self.view.widgets["lin_interp_edit"].text():
            errors.append("You have to indicate a number of values to interpolate.")
            signal_errors = True
            
        if not self.view.widgets["save_edit"].text():
            errors.append("You have to indicate a directory to save you file(s).")
            filename_errors = True
            
        if self.view.widgets["keyword_ckbox"].checkState() == Qt.CheckState.Checked \
            and not self.view.widgets["keyword_edit"].text():
            errors.append("You have to indicate a keyword to put in the file name.")
            filename_errors = True
        
        # ------- FORBIDDEN CHARACTERS
        forbidden_characters = "/\\#."
        frequency_fields = ["filter_first_cut_edit", "filter_second_cut_edit",
                            "filter_sampling_frequency_edit", "harmonics_frequency_edit", "fft_edit"]

        for name, widget in self.view.widgets.items():
            if "_edit" in name:
                if widget.isEnabled():
                    chars_to_check = "/\\#" if name in frequency_fields else forbidden_characters
                    if any(f in widget.text() for f in chars_to_check):
                        errors.append(f"%s contains forbidden characters ({chars_to_check})" % name)
                        filesorter_errors = True
                        signal_errors = True
                        filename_errors = True
                        
        
        
        # ------- INTERDEPENDENCIES
        if all([self.view.widgets["multiple_files_ckbox"].checkState() == Qt.CheckState.Checked,
                self.view.widgets["single_file_ckbox"].checkState() == Qt.CheckState.Checked]):
            errors.append("You can only chose one between Single file analysis or Multiple files analysis.")
            filesorter_errors = True
            
        if not any([self.view.widgets["multiple_files_ckbox"].checkState() == Qt.CheckState.Checked,
                self.view.widgets["single_file_ckbox"].checkState() == Qt.CheckState.Checked]):
            errors.append("You must chose one between Single file analysis or Multiple files analysis.")
            filesorter_errors = True

        if self.view.widgets["multiple_files_ckbox"].checkState() == Qt.CheckState.Checked and not self.view.widgets["path_to_parent_edit"].text():
            errors.append("You have to select a parent directory to run multi-file processing.")
            filesorter_errors = True

        if self.view.widgets["multiple_files_ckbox"].checkState() == Qt.CheckState.Checked:
            path = pathlib.Path(self.view.widgets["path_to_parent_edit"].text())
            if not path.exists():
                errors.append("The selected parent directory is not valid.")
                filesorter_errors = True
        
        if self.view.widgets["single_file_ckbox"].checkState() == Qt.CheckState.Checked and not self.view.widgets["path_to_file_edit"].text():
            errors.append("You have to select a file to run single-file processing.")
            filesorter_errors = True
            
        if self.view.widgets["make_dataset_ckbox"].checkState() == Qt.CheckState.Checked and not \
            (self.view.widgets["average_ckbox"].checkState() == Qt.CheckState.Checked and
            (self.view.widgets["multiple_files_ckbox"].checkState() == Qt.CheckState.Checked or
             self.view.widgets["single_file_ckbox"].checkState() == Qt.CheckState.Checked)):
            errors.append("The 'make full_dataset' option is available only if 'Average' and 'Multiple files analysis' are both enabled.")
            filename_errors = True
        
        if errors:
            
            self.view.tab_states[0] = 0 if not filesorter_errors else 1
            self.view.tab_states[1] = 0 if not signal_errors else 1
            self.view.tab_states[2] = 0 if not filename_errors else 1
            
            self.view.on_tab_changed(2)
            QMessageBox.critical(self.view, "Input Errors", "\n".join(errors))
            return False
        else:
            return True
    
    def init_processing(self):
        if self.check_params_validity():
            self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)
            self.model.update_tableEditors()
            
            if not self._select_files():
                return
            
            reply = QMessageBox.question(
                self.view,
                "Files found",
                f"{len(self.files_to_process)} files have been found.\nProceed with the processing ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            i= 0
            self.view.progress_bar.set_task("Initializing progress bar...")
            
            
            self._init_progress_bar()
            
            processing_basename = self._basename_preparation()
            
            harmonics = self.parent_controller.parent_controller.generate_harmonics(int(self.model.widgets_values['harmonics_frequency_edit']),
                                                          int(self.model.widgets_values['harmonics_nth_edit']),
                                                          self.model.widgets_values['harmonics_type_cbbox']) \
                if self.model.widgets_values['harmonics_ckbox'] else []
            
            self.view.progress_bar.set_task("Distributed processing...")
            
            n_cpu = multiprocessing.cpu_count()
            # n_threads = 1
            if len(self.files_to_process) > int(0.7 * n_cpu):
                n_threads = 1 if int(0.7 * n_cpu) == 0 else int(0.7 * n_cpu)
            elif len(self.files_to_process) < int(0.7 * n_cpu):
                
                n_threads = len(self.files_to_process)
            else:
                n_threads = 1
            logger.debug(f"Using n threads for processing: {n_threads}")
            self.start_processing(n_threads, harmonics, processing_basename)
            
    def start_processing(self, n_threads, harmonics, processing_basename):
        self.processing_time_start = datetime.datetime.now()
        self.results = {}
        
        self.view.progress_bar.canceled.connect(self.handle_cancel)
        
        self.view.progress_bar.set_task("Threaded processing...")
        
        self.files_queue = multiprocessing.Queue()
        
        # Populate the queue with files
        for file in self.files_to_process:
            self.files_queue.put(file)
        
        # Add sentinel values (one per worker)
        for _ in range(n_threads):
            self.files_queue.put(None)
        
        self.processing_thread = FileProcess(name="worker_1",
                                             files_queue=self.files_queue,
                                             harmonics=harmonics,
                                             processing_basename=processing_basename,
                                             model_vars=self.model.widgets_values,
                                             parent=self.view)
        
        # Connect signals to slots
        self.processing_thread.result_ready.connect(self.handle_result)
        self.processing_thread.progress_made.connect(self.handle_progress)
        self.processing_thread.error_occurred.connect(self.handle_error)
        self.processing_thread.finished.connect(self.handle_finished)
        self.processing_thread.cancelled.connect(self.handle_cancel)
        
        # Start the worker thread
        self.processing_thread.start()
        self.app.add_thread("worker_1", self.processing_thread)
        
    def handle_result(self, result):
        filename = result[0][1]
        logger.info(f"Result ready for file: {filename}, result type: {type(result)}")
        self.results[filename] = result
        
    def handle_cancel(self):
        """Handle cancel button click."""
        self.processing_thread.stop()
        self.processing_thread.wait()
        self.results = {}
        self.view.progress_bar.reset()
    
    def handle_progress(self, count):
        logger.debug(f"Progress made: {count}")
        self.view.progress_bar.increment_steps(count)
        # Update progress bar, etc.

    def handle_error(self, worker_name, error_msg):
        logger.error(f"Error from {worker_name}: {error_msg}")
        # Show error dialog, log, etc.

    def handle_finished(self, worker_name, processing_basename):
        logger.info(f"Worker {worker_name} finished processing.")
        if self.model.widgets_values["make_dataset_ckbox"]:
            self.view.progress_bar.set_task("Making full_dataset...")
            self._make_dataset(processing_basename)
        
        processing_time_end = datetime.datetime.now()
        # self.view.progress_bar.setValue()
        self.view.progress_bar.set_task("Processing finished.")
        logger.info(f"Processing time: {processing_time_end - self.processing_time_start}")
        self.view.progress_bar.reset()
        # Cleanup or start other tasks
        
    def _make_dataset(self, processing_basename):
        """
        Creates a full_dataset from the processed files by extracting signal data and
        corresponding labels, then saves the full_dataset to a CSV file.

        Parameters
        ----------
        results : dict
            A dict of with base names used to construct the processed full_dataset file's name.

        processed_files_to_make_dataset : list[tuple]
            A list of tuples containing processed dataframes and their corresponding file paths.
            Each tuple represents one processed file and is used to extract signal data and labels.

        Returns
        -------
        None
            This function does not return any value. It saves the created full_dataset to a CSV file.

        Notes
        -----
        This function iterates over the processed files, extracts the signal data from each
        file's dataframe, and appends it to the `full_dataset`. It also checks if a corresponding
        label exists in the file name (from `self.model.targets`), and associates the label
        with the corresponding signal data. The resulting full_dataset and labels are saved to a
        CSV file whose name is constructed using the provided `processing_basename`.

        """
        # Get a sample dataframe to determine number of columns
        first_df = next(iter(self.results.values()))[0][0]
        num_cols = len(first_df.values)

        # Prepare lists to accumulate full_dataset rows and target labels
        dataset_rows = []
        target_rows = []
        for k, processed_files in self.results.items():
            for data in processed_files:
                dataframe, file = data[0], data[1]
                # Filter the columns once for each dataframe iteration
                valid_columns = [
                    col for col in dataframe.columns
                    if self.model.widgets_values["exception_column_edit"] not in col and "Frequency [Hz]" not in col
                ]
                for col in valid_columns:
                    signal = dataframe[col].values
                    dataset_rows.append(signal)
                    # Iterate through targets and append a label if the key is found in file.
                    # If only one target should be matched, consider breaking after a match.
                    for key_target, value_target in self.model.targets.items():
                        if key_target in file:
                            target_rows.append(value_target)
                            break  # Uncomment this line if only one match is expected per signal

        self.view.progress_bar.increment_steps(1)
        self.view.progress_bar.set_task("Saving full_dataset...")
        # Create DataFrames from the accumulated lists
        dataset = pd.DataFrame(dataset_rows, columns=[str(x) for x in range(num_cols)])
        # Assuming each row in full_dataset has a corresponding target
        targets = pd.DataFrame(target_rows, columns=['label'])
        dataset['label'] = targets['label']

        dataset.to_csv(
            os.path.join(self.model.widgets_values['save_edit'], '_'.join(processing_basename) + '.csv'),
            index=False)

        self.view.progress_bar.increment_steps(1)
        QMessageBox.information(self.view, "Processing Finished", "Processing finished successfully.")
        
    
    def _basename_preparation(self):
        """
        Prepare the base name of the final file depending on UI values.

        Returns
        -------
        list of str that are element for teh future file name.
        """
        processing_basename = []
        characters = string.ascii_letters + string.digits
        if self.model.widgets_values['filename_ckbox']:
            processing_basename.append(self.model.widgets_values['filename_edit'])
        else:
            if self.model.widgets_values['select_column_ckbox']:
                processing_basename.append(f"Sel{self.model.widgets_values['select_column_mode_cbbox'].capitalize()}"
                                           f"{self.model.widgets_values['select_column_metric_cbbox'].capitalize()}"
                                           f"{self.model.widgets_values['select_column_edit']}")
            if self.model.widgets_values['subsample_ckbox']:
                processing_basename.append(f"Ds{self.model.widgets_values['subsample_edit']}")
            if self.model.widgets_values['filter_ckbox']:
                processing_basename.append(
                    f"O{self.model.widgets_values['filter_order_edit']}{self.model.widgets_values['filter_type_cbbox']}"
                    f"{self.model.widgets_values['filter_first_cut_edit']}-{self.model.widgets_values['filter_second_cut_edit']}"
                    f"H{self.model.widgets_values['harmonics_type_cbbox']}{self.model.widgets_values['harmonics_frequency_edit']}-"
                    f"{self.model.widgets_values['harmonics_nth_edit']}")
            if self.model.widgets_values['fft_ckbox']:
                processing_basename.append("signal fft")
            if self.model.widgets_values['average_ckbox']:
                processing_basename.append("avg")
            if self.model.widgets_values['lin_interp_ckbox']:
                processing_basename.append(f"Sm{self.model.widgets_values['lin_interp_edit']}")
        if self.model.widgets_values['random_key_ckbox']:
            processing_basename.append(''.join(random.choice(characters) for _ in range(5)))
        if self.model.widgets_values['keyword_ckbox']:
            processing_basename.append(self.model.widgets_values['keyword_edit'])
        if self.model.widgets_values['timestamp_ckbox']:
            processing_basename.append(time.strftime("%Y-%m-%d-%H-%M"))
        if (not self.model.widgets_values['random_key_ckbox'] 
                and not self.model.widgets_values['keyword_ckbox']  and not
                self.model.widgets_values['timestamp_ckbox']
                and not self.model.widgets_values['filename_ckbox']):
            processing_basename.append("FL_processed")
        
        return processing_basename
    
    def _init_progress_bar(self,):

        skiprow = 0
        if self.model.widgets_values['behead_ckbox']:
            skiprow = int(self.model.widgets_values['behead_edit'])

        example_dataframe = pd.read_csv(self.files_to_process[0], index_col=False, skiprows=skiprow)
        if self.model.widgets_values['select_column_ckbox']:
            n_columns = int(self.model.widgets_values['select_column_edit'])
        else:
            n_columns = int(
                len([col for col in example_dataframe.columns if self.model.widgets_values["exception_column_edit"] not in col]))

        self.view.progress_bar.set_range(0, self._update_number_of_tasks(len(self.files_to_process), n_columns))
        self.view.progress_bar.set_value(0)
        
        
    def _select_files(self):
        all_files = []
        untargeted_files = []
        if self.model.widgets_values['multiple_files_ckbox']:
            files = ff.get_all_files(self.model.widgets_values['path_to_parent_edit'], to_include=self.model.to_include,
                                     to_exclude=self.model.to_exclude)
            # files = [str(p) for p in Path(self.model.widgets_values['path_to_parent_edit']).rglob("*") if p.is_file()]
            for file in files:
                
                if any(value in file for value in self.model.targets.keys()):
                    all_files.append(file)
                else:
                    untargeted_files.append(file)
                        
        if self.model.widgets_values['single_file_ckbox']:
            
            if any(value in self.model.widgets_values["path_to_file_edit"] for value in self.model.targets.keys()):
                all_files.append(self.model.widgets_values["path_to_file_edit"])
            else:
                untargeted_files.append(self.model.widgets_values["path_to_file_edit"])
        if all_files:
            if untargeted_files:
                reply = QMessageBox.question(
                    self.view,
                    "Targets not found",
                    f"{len(untargeted_files)} file(s) contain(s) none of the targets indicated."
                    "They will be ignored. Proceed?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
                )
                if reply == QMessageBox.StandardButton.Yes:
                    all_files += untargeted_files
                    self.files_to_process = all_files
                    return True
                else:
                    return False
            else:
                self.files_to_process = all_files
                return True
        elif not all_files and untargeted_files:
            reply = QMessageBox.question(
                self.view,
                "Targets not found",
                f"{len(untargeted_files)} file(s) contain(s) none of the targets indicated."
                "They will be ignored. Proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                all_files += untargeted_files
                self.files_to_process = all_files
                return True
            else:
                return False
        else:
            QMessageBox.critical(self.view, "No files found",
                                 "No files have been found using your exclusion and inclusion parameters.")
            return False
    
    def _update_number_of_tasks(self, n_file, n_col, ):
        """
        Calculates the total number of tasks to be processed based on the configuration and input parameters.

        This method calculates the total number of tasks that need to be completed, taking into account
        various flags and parameters set in the model. The total task count is used to drive the progress
        bar, indicating how many tasks remain to be processed.

        Parameters
        ----------
        n_file : int
            The number of files to process.

        n_col : int
            The number of columns to process per file.

        Returns
        -------
        int
            The total number of tasks to be completed.
        """
        
        mea = 1 if self.model.widgets_values['behead_ckbox'] else 0
        electrodes = 1 if self.model.widgets_values["select_column_ckbox"] else 0
        sampling = 1 if self.model.widgets_values["select_column_edit"] else 0
        n_sample = int(self.model.widgets_values["subsample_edit"]) if self.model.widgets_values["subsample_ckbox"] else 1
        
        merge = 1 if self.model.widgets_values["average_ckbox"] else 0
        interpolation = 1 if self.model.widgets_values["lin_interp_ckbox"] else 0
        make_dataset = 1 if self.model.widgets_values["make_dataset_ckbox"] else 0
        filtering = 1 if self.model.widgets_values["filter_ckbox"] else 0
        fft = 1 if self.model.widgets_values["fft_ckbox"] else 0
        
        concat_result = 1  # n_file #* n_sample
        
        sending_result = 1
        
        saving_dataset = 1
        
        file_level_tasks = mea + electrodes + sampling + sending_result # performed only once per file
        sample_level_tasks = merge + interpolation  # performed only once per sample (multiple times per file)
        column_level_tasks = filtering + fft   # performed once per column (multiple times per sample)
        
        total_tasks = 0
        total_tasks += (n_file * file_level_tasks
                        + n_file * n_sample * sample_level_tasks
                        + n_file * n_sample * n_col * column_level_tasks)
        # total_tasks = n_file
        
        if make_dataset:
            total_tasks += concat_result + saving_dataset  # * n_sample  + concat_result
        print("total tasks:", file_level_tasks, sample_level_tasks, column_level_tasks, total_tasks)
        # total_tasks = n_file if not make_dataset else n_file + 1
        return total_tasks
    
    def export_summary(self):
        print('exporting summary (doing nothing)')
        
    def load_model(self):
        model_path = \
        QFileDialog.getOpenFileName(parent=self.view, caption="Loading processing configuration",
                                    filter="*"+self.model.extension)[0]
        if model_path:
            self.model.load_model(path=model_path)
            self.parent_controller.parent_controller.update_view_from_model(self.view, self.model)
    
    def save_model(self):
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)
        model_path = \
        QFileDialog.getSaveFileName(parent=self.view, caption="Save processing configuration",
                                    filter="*"+self.model.extension)[0]
        if model_path:
            self.model.save_model(path=model_path)
    