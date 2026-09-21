import logging
import traceback

import numpy as np
import pandas as pd
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QMessageBox
from matplotlib import transforms
from matplotlib.patches import Ellipse
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from QtScripts import params
from QtScripts.MODEL.PcaModel import PcaModel
from QtScripts.VIEW.PcaView import PcaView

logger = logging.getLogger("__Pca__")


class PcaController:
    def __init__(self, app: QApplication, parent_controller):
        self.app = app
        self.parent_controller = parent_controller
        self.model = PcaModel(self)  # set model
        self.view = PcaView(self.app, parent=self.parent_controller.view.pca_tab, controller=self)
    
    def load_dataset(self):
        dialog = (self.parent_controller.parent_controller.
                  load_path_and_update_edit(self.view.widgets["specific_load_edit"], mode='getOpenFileName',
                                            filter_="Dataset (*.csv)"))
        
        if dialog:
            try:
                df = pd.read_csv(dialog)
            except Exception as e:
                QMessageBox.warning(self.view, "Error", f"Error while loading file. {traceback.format_exc()}")
                return
            
            self.model.dataset = df
            self.view.widgets["specific_pca_tableplot"].clear()
            combo = self.view.widgets["specific_target_col_cbbox"]
            combo.currentIndexChanged.disconnect()
            combo.clear()
            combo.currentIndexChanged.connect(lambda: self.update_combotable_items("specific_pca_tableplot"))
            combo.addItems(self.model.dataset.columns)
    
    def update_combotable_items(self, combotable_name: str):
        if combotable_name in self.view.widgets.keys():
            combotable = self.view.widgets[combotable_name]
            target_col = self.view.widgets["specific_target_col_cbbox"].currentText()
            items = list(set(self.model.dataset[target_col]))
            
            if len(items) > 200:
                reply = QMessageBox.question(self.view, "Warning",
                                             "The number of unique elements in the column exceeds 200. Proceed ?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
                
                if reply == QMessageBox.StandardButton.Cancel:
                    return
            
            combotable.update_combo_items(items)
    
    def check_params(self):
        errors = []
        n_artists = self.view.widgets["specific_pca_tableplot"].table.rowCount()
        if not n_artists:
            errors.append("You need to add Artists to plot.")
        
        for artist in range(n_artists):
            dataplot_keys = [key for key in self.model.widgets_values.keys() if
                             key.startswith('pcaplot_') and key.endswith(f'_{artist}')]
            linewidths = [key for key in dataplot_keys if 'linewidth_edit' in key]
            for l in linewidths:
                if not self.model.widgets_values[l]:
                    errors.append(f"Linewidth {n_artists} is not defined.")
        
        if errors:
            QMessageBox.warning(self.view, "Warning", "\n".join(errors))
            return False
        else:
            return True
    
    def _fit_and_apply_pca(self):
        """
        Fits PCA on selected data and applies transformation.

        Returns
        -------
        tuple
            Transformed PCA dataframe and explained variance ratio.
        """
        df = self.model.dataset
        label_column = self.model.widgets_values["specific_target_col_cbbox"]
        df[label_column] = df[label_column].astype(str)
        n_artists = self.view.widgets["specific_pca_tableplot"].table.rowCount()
        labels_to_fit, labels_to_apply = [], []
        for artist in range(n_artists):
            if self.model.widgets_values[f"pcaplot_fit_ckbox_{artist}"]:
                labels_to_fit.append(self.model.widgets_values[f"pcaplot_target_cbbox_{artist}"])
            if self.model.widgets_values[f"pcaplot_apply_ckbox_{artist}"]:
                labels_to_apply.append(self.model.widgets_values[f"pcaplot_target_cbbox_{artist}"])

        print(f"labels_to_fit: {labels_to_fit}")
        print(f"labels_to_apply: {labels_to_apply}")
        print(f"label_column: {label_column}")
        print(f"unique values in column: {df[label_column].unique()}")

        df_fit = df[df[label_column].isin(labels_to_fit)]
        print(f"df_fit shape: {df_fit.shape}")
        n_components = int(self.model.widgets_values["specific_components_cbbox"])
        pca, pcdf_fit, ratio = self.fit_pca(df_fit, n_components=n_components, label_column=label_column)
        if not labels_to_fit:
            QMessageBox.warning(self.view, "Warning",
                                "No labels selected for fitting. Please check at least one 'Fit' checkbox.")
            return None, None

        if not labels_to_apply:
            QMessageBox.warning(self.view, "Warning",
                                "No labels selected for applying. Please check at least one 'Apply' checkbox.")
            return None, None

        df_apply = df[df[label_column].isin(labels_to_apply)]
        pcdf_applied = self.apply_pca(pca, df_apply, label_column=label_column)
        return pcdf_applied, [round(x * 100, 2) for x in ratio]
    
    @staticmethod
    def fit_pca(dataframe: pd.DataFrame, n_components=3, label_column="label"):
        features = dataframe.loc[:, dataframe.columns != label_column].columns
        x = dataframe.loc[:, features].values
        x = StandardScaler().fit_transform(x)  # normalizing the features
        pca = PCA(n_components=n_components)
        principalComponent = pca.fit_transform(x)
        principal_component_columns = [f"principal component {i + 1}" for i in range(n_components)]
        
        pcdf = pd.DataFrame(data=principalComponent
                            , columns=principal_component_columns, )
        pcdf.reset_index(drop=True, inplace=True)
        dataframe.reset_index(drop=True, inplace=True)
        
        pcdf[label_column] = dataframe[label_column]
        
        return pca, pcdf, pca.explained_variance_ratio_
    
    @staticmethod
    def apply_pca(pca, dataframe, label_column="label"):
        features = dataframe.loc[:, dataframe.columns != label_column].columns
        x = dataframe.loc[:, features].values
        x = StandardScaler().fit_transform(x)  # normalizing the features
        transformed_ds = pca.transform(x)
        transformed_df = pd.DataFrame(data=transformed_ds,
                                      columns=[f"principal component {i + 1}" for i in range(transformed_ds.shape[1])])
        
        transformed_df.reset_index(drop=True, inplace=True)
        dataframe.reset_index(drop=True, inplace=True)
        transformed_df[label_column] = dataframe[label_column]
        return transformed_df
    
    def _plot_data(self, ax, pcdf_applied, ratio):
        label_column = self.model.widgets_values["specific_target_col_cbbox"]
        n_components = int(self.model.widgets_values["specific_components_cbbox"])
        n_artists = self.view.widgets["specific_pca_tableplot"].table.rowCount()

        if n_components == 2:
            for artist in range(n_artists):
                color_btn = self.view.widgets[f"pcaplot_color_btn_{artist}"]
                palette = color_btn.palette()
                bg_color = palette.color(QPalette.ColorRole.Button)
                color = bg_color.name()
                
                current_label = self.model.widgets_values[f"pcaplot_target_cbbox_{artist}"]
                x_data = pcdf_applied.loc[pcdf_applied[label_column] == current_label, pcdf_applied.columns[0]]
                y_data = pcdf_applied.loc[pcdf_applied[label_column] == current_label, pcdf_applied.columns[1]]
                ax.scatter(x_data, y_data,
                           s=int(self.model.widgets_values[f"pcaplot_markersize_edit_{artist}"]),
                           marker=params.MARKERS[self.model.widgets_values[f"pcaplot_markerstyle_cbbox_{artist}"]],
                           color=color,
                           alpha=self.model.widgets_values[f"pcaplot_alpha_slider_{artist}"]/100,
                           label=current_label)
                
            for artist in range(n_artists):
                color_btn = self.view.widgets[f"pcaplot_color_btn_{artist}"]
                palette = color_btn.palette()
                bg_color = palette.color(QPalette.ColorRole.Button)
                color = bg_color.name()
                current_label = self.model.widgets_values[f"pcaplot_target_cbbox_{artist}"]
                x_data = pcdf_applied.loc[pcdf_applied[label_column] == current_label, pcdf_applied.columns[0]]
                y_data = pcdf_applied.loc[pcdf_applied[label_column] == current_label, pcdf_applied.columns[1]]
                if self.model.widgets_values["specific_ellipsis_ckbox"]:
                    ax.scatter(np.mean(x_data), np.mean(y_data), marker="+", color=color,
                               linewidth=2, s=160)
                    self.confidence_ellipse(x_data, y_data, n_std=1.0, alpha=self.model.widgets_values["specific_ellipsis_alpha_slider"]/100,
                                       color=color, fill=False, linewidth=2)
    
    def confidence_ellipse(self, x, y, n_std=3.0, color='none', **kwargs):
        if x.size != y.size:
            raise ValueError("x and y must be the same size")
        
        cov = np.cov(x, y)
        pearson = cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])
        # Using a special case to obtain the eigenvalues of this
        # two-dimensional full_dataset.
        ell_radius_x = np.sqrt(1 + pearson)
        ell_radius_y = np.sqrt(1 - pearson)
        ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2,
                          color=color, **kwargs)
        
        # Calculating the standard deviation of x from
        # the squareroot of the variance and multiplying
        # with the given number of standard deviations.
        scale_x = np.sqrt(cov[0, 0]) * n_std
        mean_x = np.mean(x)
        
        # calculating the standard deviation of y ...
        scale_y = np.sqrt(cov[1, 1]) * n_std
        mean_y = np.mean(y)
        
        transform = transforms.Affine2D() \
            .rotate_deg(45) \
            .scale(scale_x, scale_y) \
            .translate(mean_x, mean_y)
        
        ellipse.set_transform(transform + self.view.ax.transData)
        return self.view.ax.add_patch(ellipse)

    def draw(self):
        self.parent_controller.parent_controller.update_model_from_view(self.model, self.view)
        if self.check_params():
            n_components = int(self.model.widgets_values["specific_components_cbbox"])
            if n_components == 2:
                self.view.ax.clear()
                pcdf_applied, ratio = self._fit_and_apply_pca()
                if pcdf_applied is None:
                    return
                self._plot_data(self.view.ax, pcdf_applied, ratio)
                self.set_labels(self.view.ax, ratio)
                self.set_ticks(self.view.ax)
                self.set_legend(self.view.ax)
                self.view.figure.tight_layout()
                self.view.canvas.draw()
            else:
                QMessageBox.information(self.view, "PCA", "3D PCA is not supported yet.")
            
    
    def set_ticks(self, ax,):
        # x_data = [i for i in range(n_val)]
        # xmin = min(x_data)
        # xmax = max(x_data)
        # xstep = (xmax - xmin) / (int(self.model.widgets_values["plot_x_n_tick_edit"]) - 1)
        # xtick = xmin
        # xticks = []
        # for i in range(int(self.model.widgets_values["plot_x_n_tick_edit"]) - 1):
        #     xticks.append(xtick)
        #     xtick += xstep
        # xticks.append(xmax)
        # xticks_labels = np.array(xticks)
        # xticks_labels = [np.around(x, int(self.model.widgets_values["plot_x_round_edit"])) for x in xticks_labels]
        #
        # if int(self.model.widgets_values["plot_x_round_edit"]) == 0:
        #     xticks_labels = [int(x) for x in xticks_labels]
        #
        # xticks_labels = [str(x) for x in xticks_labels]
        #
        # rounded_xticks = list(np.around(np.array(xticks), int(self.model.widgets_values["plot_x_round_edit"])))
        # ax.set_xticks(rounded_xticks, xticks_labels)
        ax.tick_params(axis='x',
                       labelsize=int(self.model.widgets_values["plot_x_tick_size_slider"]),
                       labelrotation=int(self.model.widgets_values["plot_x_tick_rotation_slider"]))
        
        # ystep = (ymax - ymin) / (int(self.model.widgets_values["plot_y_n_tick_edit"]) - 1)
        # ytick = ymin
        # yticks = []
        # for i in range(int(self.model.widgets_values["plot_y_n_tick_edit"]) - 1):
        #     yticks.append(ytick)
        #     ytick += ystep
        # yticks.append(ymax)
        # yticks_labels = np.array(yticks)
        # yticks_labels = [np.around(y, int(self.model.widgets_values["plot_y_round_edit"])) for y in yticks_labels]
        # rounded_yticks = list(np.around(np.array(yticks), int(self.model.widgets_values["plot_y_round_edit"])))
        # ax.set_yticks(rounded_yticks, yticks_labels)
        ax.tick_params(axis='y',
                       labelsize=int(self.model.widgets_values["plot_y_tick_size_slider"]),
                       labelrotation=int(self.model.widgets_values["plot_y_tick_rotation_slider"]))
    
    def set_labels(self, ax, ratio):
        show_ratiox = f' ({ratio[0]}%)' if self.model.widgets_values["specific_show_ratio_ckbox"] else ''
        show_ratioy = f' ({ratio[1]}%)' if self.model.widgets_values["specific_show_ratio_ckbox"] else ''
        ax.set_xlabel(self.model.widgets_values["plot_x_label_edit"]+show_ratiox,
                      fontdict={"font": self.model.widgets_values["plot_axes_font_cbbox"],
                                "fontsize": self.model.widgets_values["plot_x_label_size_slider"]})
        
        ax.set_ylabel(self.model.widgets_values["plot_y_label_edit"]+show_ratioy,
                      fontdict={"font": self.model.widgets_values["plot_axes_font_cbbox"],
                                "fontsize": self.model.widgets_values["plot_y_label_size_slider"]})
        ax.set_title(self.model.widgets_values["plot_title_edit"],
                     fontdict={"font": self.model.widgets_values["plot_title_font_cbbox"],
                               "fontsize": self.model.widgets_values["plot_title_size_slider"], })
    
    def set_legend(self, ax):
        if self.model.widgets_values["plot_legend_ckbox"]:
            if self.model.widgets_values["plot_anchor_cbbox"] == 'custom':
                ax.legend(loc='upper left',
                          bbox_to_anchor=(self.model.widgets_values["plot_legend_x_pos_slider"],
                                          self.model.widgets_values["plot_legend_y_pos_slider"]),
                          draggable=self.model.widgets_values["plot_draggable_ckbox"],
                          ncols=self.model.widgets_values["plot_legend_col_edit"],
                          fontsize=self.model.widgets_values["plot_legend_size_slider"],
                          framealpha=self.model.widgets_values["plot_alpha_slider"] / 100,
                          )
            else:
                ax.legend(loc=self.model.widgets_values["plot_anchor_cbbox"],
                          draggable=self.model.widgets_values["plot_draggable_ckbox"],
                          ncols=self.model.widgets_values["plot_legend_col_edit"],
                          fontsize=self.model.widgets_values["plot_legend_size_slider"],
                          framealpha=self.model.widgets_values["plot_alpha_slider"] / 100,
                          )
            
            for t, lh in zip(ax.get_legend().texts, ax.get_legend().legend_handles):
                t.set_alpha(self.model.widgets_values["plot_alpha_slider"] / 100)
                lh.set_alpha(self.model.widgets_values["plot_alpha_slider"] / 100)
        
        elif ax.get_legend():
            ax.get_legend().remove()
