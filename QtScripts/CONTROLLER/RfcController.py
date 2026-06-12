import datetime
import logging
import multiprocessing
import os
import pickle
from itertools import product

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from fiiireflyyy import files as ff
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import ParameterGrid

from QtScripts.MODEL.RfcModel import RfcModel
from QtScripts.PROCESSES.RfcLearningProcess import RfcLearningProcess
from QtScripts.VIEW.RfcView import RfcView
from QtScripts.WIDGETS import input_validation as ival

logger = logging.getLogger("__RFC__")

class RfcController:
    def __init__(self, app: QApplication, parent_controller):
        self.app = app
        self.parent_controller = parent_controller
        self.model = RfcModel(self)  # set model
        self.threads_alive = None
        self.cancelled = None
        self.start_learning_time = datetime.datetime.now()
        self.results = {}
        self.params_combinations_queue = None
        self.learning_thread = None
        self.view = RfcView(self.app, parent=self.parent_controller.view.rfc_tab, controller=self)
        
    def load_train_dataset(self, autoload='', withwarning=True):
        if not autoload:
            dialog = self.parent_controller.parent_controller.load_path_and_update_edit(self.view.widgets["learn_load_train_edit"],
                                                                                        mode="getOpenFileName")
        else:
            dialog = autoload
        if dialog:
            df = pd.read_csv(dialog,)
            self.model.train_dataset = df
            self.view.widgets["learn_target_column_cbbox"].addItems(list(df.columns))
            
            if not autoload:
                dataset_basename = os.path.basename(dialog)
                all_files = ff.get_all_files(os.path.dirname(dialog))
                for file in all_files:
                    basename = os.path.basename(file)
                    
                    if basename == dataset_basename.replace("_Xy_train.", "_Xy_test."):
                        logger.info(f"Autoload train {file}")
                        self.load_test_dataset(autoload=file)
                
    
    def load_test_dataset(self, autoload=''):
        if not autoload:
            dialog = self.parent_controller.parent_controller.load_path_and_update_edit(
                self.view.widgets["learn_load_test_edit"],
                mode="getOpenFileName")
        else:
            dialog = autoload
        if dialog:
            df = pd.read_csv(dialog,)
            self.model.test_dataset = df
            self.view.widgets["learn_load_test_edit"].setText(dialog)
            if not autoload:
                
                dataset_basename = os.path.basename(dialog)
                all_files = ff.get_all_files(os.path.dirname(dialog))
                for file in all_files:
                    basename = os.path.basename(file)
                    
                    if basename == dataset_basename.replace("_Xy_test.", "_Xy_train."):
                        logger.info(f"Autoload train {file}")
                        self.load_train_dataset(autoload=file)
    
    def update_combotable_items(self, combotable_name:str):
        if combotable_name in self.view.widgets.keys():
            combotable = self.view.widgets[combotable_name]
            target_col = self.view.widgets["learn_target_column_cbbox"].currentText()
            items = list(set(self.model.train_dataset[target_col]))
            
            if len(items) > 200:
                reply = QMessageBox.question(self.view, "Warning",
                                             "The number of unique elements in the column exceeds 200. Proceed ?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
                
                if reply == QMessageBox.StandardButton.Cancel:
                    return
            
            combotable.update_combo_items(items)
    
    @staticmethod
    def get_fixed_default_rfc_params():
        clf = RandomForestClassifier()
        params = dict(clf.get_params().items())
        fixed_params = {}
        to_fix = {'bootstrap': True, 'class_weight': 'balanced'}
        for k, v in params.items():
            fixed_params[k] = params[k] if k not in to_fix.keys() else to_fix[k]
        
        return fixed_params
    
    def _check_params_validity(self, ):
        """
        Checks the validity of the parameters entered by the user.

        Returns
        -------
        bool
            True if parameters are valid, False otherwise.
        """
        errors = []
        filesorter_errors = False
        signal_errors = False
        filename_errors = False
        
        if self.threads_alive:
            if self.cancelled:
                QMessageBox.warning(self.view, "Warning",
                                    "Threads from previous learnings are still alive and being terminated."
                                    " Please wait a bit before starting a new learning",
                                    QMessageBox.StandardButton.Ok)
                return False
            else:
                QMessageBox.warning(self.view, "Warning", "Threads are currently alive."
                                                          "To start a new learning, please either cancel the current one "
                                                          "or wait for it to finish.", QMessageBox.StandardButton.Ok)
                return False
        
        if self.view.widgets["learn_save_edit"].text() == "":
            proceed = QMessageBox.question(self.view, "Warning", "You will run a training without"
                                                                  " saving the resulting model. Continue ?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
           
            if proceed == QMessageBox.StandardButton.Cancel:
                return False
            
        elif not os.path.exists(os.path.dirname(self.view.widgets["learn_save_edit"].text())):
            QMessageBox.critical(self.view, "Error", "Path to save the classifier does not exist.")
            return False

        if ('cv' in self.view.widgets["learn_scoring_cbbox"].currentText().lower()
        or 'trust' in self.view.widgets["learn_scoring_cbbox"].currentText().lower()) and not self.view.widgets["learn_kfold_ckbox"].isChecked():
            QMessageBox.critical(self.view, "Error",'You can not chose a scoring function involving Cross Validation if'
                                                ' K-Fold option is unchecked.')
            return False
        
        if not self.view.widgets["learn_load_train_edit"].text():
            QMessageBox.critical(self.view, "Error", "No full_dataset loaded.")
            return False
        else:
            if not os.path.isfile(self.view.widgets["learn_load_train_edit"].text()) or not os.path.exists(self.view.widgets["learn_load_train_edit"].text()):
                QMessageBox.critical(self.view, "Error", "Invalid full_dataset path.")
                return False
        
        combotable = self.view.widgets["learn_combotable"]
        targets = combotable.get_current_values()['target']
        targets = list(set(targets))

        if self.view.widgets["learn_kfold_ckbox"].isChecked():
            kfold_val = self.view.widgets["learn_kfold_edit"].text().strip()
            if not kfold_val or not kfold_val.isdigit() or int(kfold_val) < 2:
                QMessageBox.critical(self.view, "Error",
                                     "K-Fold is enabled but the K value is missing or invalid. "
                                     "Please enter an integer ≥ 2.")
                return False
        
        if len(targets) < 1:
            QMessageBox.critical(self.view, "Missing value", "Targets are needed to train a Random Forest Classifier.")
            return False

        return True
    
    def _update_rfc_params(self, rfc_params):
        local_dict = {}
        for key, value in rfc_params.items():
            local_dict[key] = self.parent_controller.parent_controller.extract_widget_value(value)

        self.model.rfc_params.update(local_dict)
    
    def load_model(self):
        model_path = \
            QFileDialog.getOpenFileName(parent=self.view, caption="Loading learning configuration",
                                        filter="*" + self.model.extension)[0]
        if model_path:
            self.model.load_model(path=model_path)
            self.load_train_dataset(autoload=self.model.widgets_values["learn_load_train_edit"])
            self.load_test_dataset(autoload=self.model.widgets_values["learn_load_test_edit"])
            self.parent_controller.parent_controller.update_view_from_model(self.view, self.model)
    
    def save_model(self):
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)
        model_path = \
            QFileDialog.getSaveFileName(parent=self.view, caption="Save learning configuration",
                                        filter="*" + self.model.extension)[0]
        if model_path:
            self.model.save_model(path=model_path)
    
    def export_metrics(self):
        filename_ = self.model.widgets_values["learn_save_edit"]
        if not filename_:
            filename_ = QFileDialog.getSaveFileName(parent=self.view,)[0]
            filename_ = filename_+'.csv' if not os.path.basename(filename_).endswith('.csv') else filename_
        
        if filename_:
            filename_ = filename_.replace(".rfc", "_export.csv")
            with open(filename_, 'w') as f:
                f.write(self.view.widgets["metrics_textedit"].toPlainText())
            
            QMessageBox.information(self.view, "Metrics exported", f"Results saved under {filename_}")
            
    
    def init_learning(self):
        self.start_learning_time = datetime.datetime.now()
        if self._check_params_validity():
            self.cancelled = False
            combotable = self.view.widgets["learn_combotable"]
            targets = combotable.get_current_values()['target']
            targets = list(set(targets))
            self.model.train_targets = targets
            
            self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)
            self._update_rfc_params(self.view.rfc_params)
            self._learning_preparation()
            
    
    @staticmethod
    def _extract_rfc_params(rfc_params_string_var):
        
        rfc_params = {}
        for key, widget in rfc_params_string_var.items():
            if 'class_weight' not in key:
                if ival.isint(widget):
                    rfc_params[key] = int(widget)
                elif ival.isfloat(widget):
                    rfc_params[key] = float(widget)
                elif widget == 'None':
                    rfc_params[key] = None
                else:
                    rfc_params[key] = widget
        return rfc_params
    
    def _get_param_grid_search(self, ):
        rfc_params = self._extract_rfc_params(self.view.rfc_params)
        param_grid = {}
        
        checked_hyperparams = [key for key in self.model.hyperparameters_to_tune.keys() if
                               self.model.widgets_values[f"hyperparam_{key}_ckbox"] == True]
        
        for param, values in [(param, self.model.widgets_values[f"hyperparam_{param}_edit"]) for param in
                              checked_hyperparams]:  # params to be optimized
            indiv_values = [val.strip() for val in values.split(',')]

            # check for 'None' values as string and replace them by actual None
            # indiv_values = self._convert_list_elements(indiv_values)
            converted_indiv_values = [ival.convert_to_type(value) for value in indiv_values]

            param_grid[param] = converted_indiv_values

        for k, v in rfc_params.items():  # params with a single value
            if k not in param_grid.keys():
                param_grid[k] = [v, ]
        return param_grid
    
    def _update_number_of_tasks(self, num_combinations):
        loading = 1
        splitting = 2

        training = 3
        testing = 2
        params_done = 1
        k_fold = 1
        format_metrics = 1
        per_worker = training + testing + k_fold + format_metrics + params_done

        learning = num_combinations  # per_worker*num_combinations

        terminate_workers = 1
        best_perf = 1
        finishing_display = 1
        saving_model = 1 if self.model.widgets_values["learn_save_edit"] else 0
        post_learning = terminate_workers + best_perf + finishing_display + saving_model

        total_tasks = loading + splitting + learning + post_learning

        return total_tasks
    
    def _init_progress_bar(self, num_combinations):
        self.view.progress_bar.set_range(0, self._update_number_of_tasks(num_combinations))
        self.view.progress_bar.set_value(0)
    
    def _learning_preparation(self):
        param_grid = self._get_param_grid_search()
        num_combinations = len(list(product(*param_grid.values())))
        
        reply = QMessageBox.question(
            self.view,
            "Information",
            f"{num_combinations} training iteration will begin.\nProceed ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return
        
        self.view.progress_bar.set_task("Initializing progress bar...")
        self._init_progress_bar(num_combinations)
        
        train_df = pd.read_csv(self.model.widgets_values["learn_load_train_edit"], index_col=False, dtype=str)
        test_df = pd.read_csv(self.model.widgets_values["learn_load_test_edit"], index_col=False, dtype=str)
        
        self.handle_progress(1)
        self.view.progress_bar.set_task("Splitting")
        
        target_column = self.model.widgets_values["learn_target_column_cbbox"]
        
        train_df[target_column] = train_df[target_column].astype(str)
        train_df = train_df[train_df[target_column].isin(self.model.train_targets)]
        train_df.reset_index(inplace=True, drop=True)
        y_train = train_df[target_column]
        y_train = self.parent_controller.label_encoding(y_train)
        X_train = train_df.loc[:, train_df.columns != target_column]
        self.handle_progress(1)
        
        test_df[target_column] = test_df[target_column].astype(str)
        test_df = test_df[test_df[target_column].isin(self.model.train_targets)]
        test_df.reset_index(inplace=True, drop=True)
        y_test = test_df[target_column]
        y_test = self.parent_controller.label_encoding(y_test)
        X_test = test_df.loc[:, test_df.columns != target_column]
        
        self.handle_progress(1)
        self.view.progress_bar.set_task("Training")
        
        all_params_grid = ParameterGrid(param_grid)
        converted_all_params_grid = []
        for p_grid in all_params_grid:
            converted_p_grid = ival.convert_dict_values_from_str(p_grid)
            converted_all_params_grid.append(converted_p_grid)
        
        all_params_grid_list = converted_all_params_grid
        n_cpu = multiprocessing.cpu_count()
        n_workers = 1
        if len(all_params_grid) > int(0.7 * n_cpu):
            n_workers = 1 if int(0.7 * n_cpu) == 0 else int(0.7 * n_cpu)
        elif len(all_params_grid) < int(0.7 * multiprocessing.cpu_count()):
            n_workers = len(all_params_grid)
            
        self.start_learning(converted_all_params_grid, n_workers, X_train, y_train, X_test, y_test)
            
    def start_learning(self, combintaions, n_threads, X_train, y_train, X_test, y_test):
        self.start_learning_time = datetime.datetime.now()
        self.results = {}
        
        self.view.progress_bar.canceled.connect(self.handle_cancel)
        
        self.view.progress_bar.set_task("Learning...")
        
        self.params_combinations_queue = multiprocessing.Queue()
        
        # Populate the queue with files
        for file in combintaions:
            self.params_combinations_queue.put(file)
        
        # Add sentinel values (one per worker)
        for _ in range(n_threads):
            self.params_combinations_queue.put(None)
        
        self.learning_thread = RfcLearningProcess(self.params_combinations_queue,
                                                  X_train, y_train,
                                                  X_test, y_test,
                                                  self.model.widgets_values
                                                  )
        # Connect signals to slots
        self.learning_thread.result_ready.connect(self.handle_result)
        self.learning_thread.progress_made.connect(self.handle_progress)
        self.learning_thread.error_occurred.connect(self.handle_error)
        self.learning_thread.finished.connect(self.handle_finished)
        self.learning_thread.cancelled.connect(self.handle_cancel)
        
        # Start the worker thread
        self.learning_thread.start()
        self.app.add_thread("rfc_1", self.learning_thread)
        
    def _get_best_performing_combination(self, all_params_combination):
        """
        Identifies the key of the best performing model based on the selected scoring method.

        Parameters
        ----------
        all_params_combination : dict
            Contains all the tested combinations in the format
            {random_key: (combination, all_cv_scores, train_score, test_score, clf), ...}

        Returns
        -------
        best_key : str
            The key of the best performing model.
        """
        best_key = ''

        if self.model.widgets_values["learn_scoring_cbbox"] == "Trust score":
            best_trust = 0
            for random_key, metrics in all_params_combination.items():
                all_cv_scores = metrics[1]
                train_score = metrics[2]
                test_score = metrics[3]
                trust = self.parent_controller.compute_normalized_trust(acc_train=train_score,
                                                  acc_test=test_score,
                                                  acc_kfolds=all_cv_scores)

                best_key = random_key if trust > best_trust else best_key
                best_trust = max(trust, best_trust)

                logger.debug(f"{trust} {metrics}")

        if self.model.widgets_values["learn_scoring_cbbox"] == 'Relative K-Fold CV accuracy':
            best_rel_cv = 100
            for random_key, metrics in all_params_combination.items():
                all_cv_scores = metrics[1]
                train_score = metrics[2]

                kcv = np.mean(all_cv_scores)
                kfold_acc_diff = round(train_score - kcv, 3)
                kfold_acc_relative_diff = round(kfold_acc_diff / train_score * 100, 2)
                best_key = random_key if kfold_acc_relative_diff < best_rel_cv else best_key
                best_rel_cv = kfold_acc_relative_diff if kfold_acc_relative_diff < best_rel_cv else best_rel_cv

        if self.model.widgets_values["learn_scoring_cbbox"] == 'K-Fold CV accuracy':
            best_cv = 0
            for random_key, metrics in all_params_combination.items():
                all_cv_scores = metrics[1]
                kcv = np.mean(all_cv_scores)
                best_key = random_key if kcv > best_cv else best_key
                best_cv = kcv if kcv > best_cv else best_cv

        if self.model.widgets_values["learn_scoring_cbbox"] == 'Training accuracy':
            best_acc = 0
            for random_key, metrics in all_params_combination.items():
                train_score = metrics[2]
                best_key = random_key if train_score > best_acc else best_key
                best_acc = train_score if train_score > best_acc else best_acc
        if self.model.widgets_values["learn_scoring_cbbox"] == 'Testing accuracy':
            best_acc = 0
            for random_key, metrics in all_params_combination.items():
                test_score = metrics[3]
                best_key = random_key if test_score > best_acc else best_key
                best_acc = test_score if test_score > best_acc else best_acc

        return best_key

    def handle_result(self, random_key, formatted_metrics):
        self.results[random_key] = formatted_metrics  # Store results dynamically
    
    def handle_cancel(self):
        self.cancelled = True
        self.learning_thread.stop()
        self.learning_thread.wait()
        self.results = {}
        self.view.progress_bar.reset()
        end_learning = datetime.datetime.now()
        logger.info(f"Learning time: {end_learning - self.start_learning_time}")

    
    def handle_progress(self, count):
        logger.info(f"Progress made: {count}")
        self.view.progress_bar.increment_steps(count)
        # Update progress bar, etc.
    
    def handle_error(self, worker_name, error_msg):
        logger.error(f"Error from {worker_name}: {error_msg}")
        # Show error dialog, log, etc.
    
    def handle_finished(self, worker_name,):
        self.handle_progress(1)

        if not self.results:
            QMessageBox.critical(self.view, "Error",
                                 "Learning produced no results. Check the error log for details.")
            self.threads_alive = False
            self.cancelled = False
            return

        for _ in range(1):
            if self.cancelled:
                break
            self.view.progress_bar.set_task("Getting best performing combination...")

            best_key = self._get_best_performing_combination(self.results)
            self.handle_progress(1)
            # MainController.update_textbox(self.model.textboxes)
            if self.cancelled:
                break

            metrics_text_elements = []
            metrics_text_elements = self.learning_display_computed_metrics(best_key,
                                                                            metrics_text_elements,
                                                                            self.results)
            if self.cancelled:
                break

            # self._update_metrics_textbox(metrics_text_elements)
            self.view.widgets["metrics_textedit"].setHtml('<br/>'.join(metrics_text_elements))
            if self.model.widgets_values["learn_save_edit"]:
                self.view.progress_bar.set_task("Saving best performing model...")
                
                file = open(f'{self.model.widgets_values["learn_save_edit"]}', 'wb')
                pickle.dump(self.results[best_key][4], file)
                file.close()
                self.handle_progress(1)
            self.handle_progress(1)
            self.threads_alive = False
            end_learning = datetime.datetime.now()
            self.view.progress_bar.set_task("No task running.")
            self.view.progress_bar.reset()
            logger.info(f"Learning time: {end_learning - self.start_learning_time}")

        if self.cancelled:
            QMessageBox.warning(self.view, "Cancel Learning", "All workers properly cancelled.")
        else:
            QMessageBox.warning(self.view, "Learning finished",
                                "All workers properly terminated.")

        self.threads_alive = False
        self.cancelled = False
        
    def learning_display_computed_metrics(self,
                                           best_key,
                                           metrics_text_elements,
                                           all_param_combinations):
        def display_colored_scores(score, score_type='train_test'):
            train_test_colors = ["#fc1803", "#fc8003", "#fcca03", "#1ab00c"]  # red, orange, yellow, green
            ci = 0
            score = float(score)
            match score_type:
                case "train_test":
                    if score < 0.65:
                        ci = 0
                    elif 0.65 >= score <0.79:
                        ci = 1
                    elif 0.79 >= score < 0.9:
                        ci = 2
                    else:
                        ci = 3
                case "kfold":
                    if score < 3:
                        ci = 3
                    elif 3 >= score < 5:
                        ci = 2
                    elif 5 >= score < 10:
                        ci = 1
                    else:
                        ci = 0
                        
            colored_str = f'<span style="color:{train_test_colors[ci]};">{str(score)}</span>'
            return colored_str
        pm = u"\u00B1"
        metrics_text_elements.append(f"<b>General parameters:</b>")
        metrics_text_elements.append(f"Number of parameters combination : {len(all_param_combinations.keys())}", )

        metrics_text_elements.append(f"Scoring function: {self.model.widgets_values['learn_scoring_cbbox']}")
        metrics_text_elements.append("Best performing model metrics:")
        metrics_text_elements.append(f"Training accuracy: {display_colored_scores(all_param_combinations[best_key][2])}")
        metrics_text_elements.append(f"Testing accuracy: {display_colored_scores(all_param_combinations[best_key][3])}")
        metrics_text_elements.append(f"F1-score: {display_colored_scores(all_param_combinations[best_key][5]['f1-score'])}")
        metrics_text_elements.append(f"Recall: {display_colored_scores(all_param_combinations[best_key][5]['recall'])}")
        metrics_text_elements.append(f"Precision: {display_colored_scores(all_param_combinations[best_key][5]['precision'])}")

        if self.model.widgets_values["learn_kfold_ckbox"]:
            acc = all_param_combinations[best_key][2]
            kcv = round(np.array(all_param_combinations[best_key][1]).mean(), 3)
            kcv_std = round(np.array(all_param_combinations[best_key][1]).std(), 3)

            kcv_acc_diff = round(acc - kcv, 3)
            kcv_acc_relative_diff = round(kcv_acc_diff / acc * 100, 2)
            metrics_text_elements.append(f"{self.model.widgets_values['learn_kfold_edit']}-fold Cross Validation: {kcv}{pm}{kcv_std}")
            metrics_text_elements.append(f"KFold-Accuracy difference = {acc}-{kcv} = {kcv_acc_diff}\n")
            metrics_text_elements.append(f"KFold-Accuracy relative difference: {display_colored_scores(kcv_acc_relative_diff, score_type='kfold')} %\n")

            all_cv_scores = all_param_combinations[best_key][1]
            train_score = all_param_combinations[best_key][2]
            test_score = all_param_combinations[best_key][3]
            trust_score = self.parent_controller.compute_normalized_trust(acc_train=train_score, acc_test=test_score,
                                                                                acc_kfolds=all_cv_scores)
            metrics_text_elements.append(f"Trust score: {display_colored_scores(round(trust_score, 3), score_type='train_test')}")

        metrics_text_elements.append("")
        metrics_text_elements.append("<b>RFC best performing parameters:</b>")
        for param, value in all_param_combinations[best_key][0].items():
            metrics_text_elements.append(f"{param} : {value}")

        metrics_text_elements.append("")
        metrics_text_elements.append("<b>Average metrics across all iterations:</b>")
        all_train_scores = [all_param_combinations[key][2] for key in all_param_combinations.keys()]
        all_test_scores = [all_param_combinations[key][3] for key in all_param_combinations.keys()]
        all_cv_scores = [all_param_combinations[key][1] for key in all_param_combinations.keys()]
        mean_accuracy = np.mean(all_train_scores).round(3)
        metrics_text_elements.append(
            f"Training accuracy: {display_colored_scores(mean_accuracy)} {pm} {str(np.std(all_train_scores).round(3))}", )
        metrics_text_elements.append(
            f"Testing accuracy: {display_colored_scores(np.mean(all_test_scores).round(3))} {pm} {str(np.std(all_test_scores).round(3))}")

        if self.model.widgets_values["learn_kfold_ckbox"]:
            mean_kfold = round(np.array(all_cv_scores).mean(), 3)
            std_kfold = round(np.array(all_cv_scores).std(), 3)
            kfold_acc_diff = round(mean_accuracy - mean_kfold, 3)
            kfold_acc_relative_diff = round(kfold_acc_diff / mean_accuracy * 100, 2)
            metrics_text_elements.append(
                f"{len(all_cv_scores[0])}-fold Cross Validation: {str(mean_kfold)} {pm} {str(std_kfold)}")
            metrics_text_elements.append(
                f"KFold-Accuracy difference = {mean_accuracy}-{mean_kfold} = {kfold_acc_diff}\n")
            metrics_text_elements.append(f"KFold-Accuracy relative difference: {display_colored_scores(kfold_acc_relative_diff, score_type='kfold')} %\n")
        metrics_text_elements.append("")

        return metrics_text_elements
    
    def reload_rfc_params(self,):
        """
        Reloads the parameters of a Random Forest Classifier and sets them to the provided string variables.

        Parameters
        ----------
        rfc_params_string_var : dict
            A dictionary containing string variables to store the parameter values of the Random Forest Classifier.

        Returns
        -------
        dict
            default random forest classifier parameters
        """
        default_params = self.get_fixed_default_rfc_params()
        for name, value in default_params.items():
            value = str(value)
            if value != self.view.widgets[f"params_{name}_edit"]:
                self.view.rfc_params[name] = value
                self.view.widgets[f"params_{name}_edit"].setText(value)
        
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)
