import logging

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from sklearn.model_selection import train_test_split
from sklearn.model_selection import StratifiedShuffleSplit

from QtScripts.MODEL.UtilitiesModel import UtilitiesModel
from QtScripts.VIEW.UtilitiesView import UtilitiesView

logger = logging.getLogger("__Processing__")


class UtilitiesController:
    def __init__(self, app: QApplication, parent_controller):
        self.app = app
        self.parent_controller = parent_controller
        self.model = UtilitiesModel(self)  # set model
        
        self.view = UtilitiesView(self.app, parent=self.parent_controller.view.utilities_tab, controller=self)
    
    def save_dataset(self, line_edit_name):
        self.parent_controller.parent_controller.load_path_and_update_edit(self.view.widgets[line_edit_name], mode='getSaveFileName')
        
    def load_dataset(self, line_edit_name, cbbox_name):
        dialog = self.parent_controller.parent_controller.load_path_and_update_edit(self.view.widgets[line_edit_name], mode='getOpenFileName',
                                                                                     filter_="Dataset (*.csv *.xlsx)")
        if dialog:
            df = pd.read_csv(dialog)
            combo = self.view.widgets[cbbox_name]
            combo.clear()
            combo.addItems(df.columns)
            combo.setMaxVisibleItems(20)
            
            combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            del df
            
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)

    def split_dataset(self):
        """
        Splits the full_dataset into training and testing sets based on a specified ratio and saves them to new files.

        Returns
        -------
        None
        """
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)

        ratio = float(self.model.widgets_values["split_ratio_slider"]) / 100
        path = self.model.widgets_values["split_load_edit"]
        method = self.model.widgets_values["split_method_cbbox"]

        if path:
            df = pd.read_csv(path)
            target_col = self.model.widgets_values["split_target_column_cbbox"]
            base_path = path.split(".")
            X = df.loc[:, df.columns != target_col]
            y = df[target_col]

            if method == "StratifiedShuffleSplit":
                sss = StratifiedShuffleSplit(n_splits=1, train_size=ratio, random_state=42)
                train_idx, test_idx = next(sss.split(X, y))
                train_df = df.iloc[train_idx].reset_index(drop=True)
                test_df = df.iloc[test_idx].reset_index(drop=True)
            else:
                X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=ratio, random_state=42)
                train_df = X_train.copy()
                train_df[target_col] = y_train.values
                test_df = X_test.copy()
                test_df[target_col] = y_test.values

            train_df.to_csv(f"{base_path[0]}_Xy_train.{base_path[1]}", index=False)
            test_df.to_csv(f"{base_path[0]}_Xy_test.{base_path[1]}", index=False)
            QMessageBox.information(self.view, "Splitting", f"Splitting done ({method})")

    
    def rename_targets(self):
        path = self.model.widgets_values["rename_load_edit"]
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)
        if path:
            df = pd.read_csv(path)
            target_col = self.model.widgets_values["rename_target_column_cbbox"]
            df[target_col] = df[target_col].replace(self.model.rename_targets)
            
            save_path = self.model.widgets_values["rename_save_edit"]
            if not save_path:
                save_path = self.model.widgets_values["rename_load_edit"].replace(".csv", "_renamed.csv")
            
            df.to_csv(save_path, index=False)
            QMessageBox.information(self.view, "Rename", f"Renaming done. File saved at {save_path}")
        
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)



    def load_and_explore_dataset(self):
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)
        line_edit_name = "explore_load_edit"
        line_edit = self.view.widgets[line_edit_name]
        cbbox_name = "explore_target_column_cbbox"
        dialog = \
        QFileDialog().getOpenFileName(parent=self.view, caption="Open full_dataset", filter="Dataset (*.csv *.xlsx)")[0]
        if dialog:
            line_edit.setText(dialog)
            df = pd.read_csv(dialog)
            combo = self.view.widgets[cbbox_name]
            combo.clear()
            combo.addItems(df.columns)
            combo.setMaxVisibleItems(20)
            
            combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            
            self.view.widgets["explore_n_rows_label"].setText(f"Number of rows: {len(df)}")
            self.view.widgets["explore_n_cols_label"].setText(f"Number of columns: {len(df.columns)}")

            del df
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)

    
    def explore_column(self):
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)

        path = self.model.widgets_values["explore_load_edit"]
        if path:
            df = pd.read_csv(path)
            combo = self.view.widgets["explore_column_cbbox"]
            combo.clear()
            target_col = self.model.widgets_values["explore_target_column_cbbox"]
            unique_values = list(set(df[target_col]))
            if len(unique_values) > 50:
                reply = QMessageBox.question(self.view, "Explore", f"The selected column contains {len(unique_values)} unique values. "
                                                                   f"Proceed to display them ?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                
            combo.addItems([str(x) for x in unique_values])
            combo.setMaxVisibleItems(20)
            
            combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            
            
            del df
            
    def load_merge_datasets(self, line_edit_name, mode, extension=''):
        self.parent_controller.parent_controller.load_path_and_update_edit(self.view.widgets[line_edit_name],
                                                                            mode=mode, extension=extension)
        
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)
    
    def merge_datasets(self):
        path1 = self.model.widgets_values["merge_load_first_edit"]
        path2 = self.model.widgets_values["merge_load_second_edit"]
        save_path = self.model.widgets_values["merge_save_edit"]
        if path1 and path2 and save_path:
            df1 = pd.read_csv(path1)
            df2 = pd.read_csv(path2)
            
            save_path = save_path+".csv" if ".csv" not in save_path else save_path
            if df1.columns.tolist() == df2.columns.tolist():
                df_merge = pd.concat([df1, df2], ignore_index=True, axis=0)
                df_merge.to_csv(save_path, index=False)
                
                QMessageBox.information(self.view, "Merge", "Merge done.")
                
            else:
                QMessageBox.warning(self.view, "Merge", f"The two datasets must have the same columns. ")
        else:
            QMessageBox.information(self.view, "Merge", "You need to load 2 datasets and a save path before merging.")