import sys
import numpy as np
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QComboBox, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from rosbags.highlevel import AnyReader

class MultiBagGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Flexible Multi-Bag Analyzer")
        self.setGeometry(100, 100, 1200, 900) 
        
        self.bag_paths = []
        self.plot_data = [] 

        # --- Layout Setup ---
        main_layout = QVBoxLayout()

        self.label = QLabel("1. Load up to 3 ROS1 .bag files to begin.")
        font = self.label.font()
        font.setPointSize(11)
        self.label.setFont(font)
        main_layout.addWidget(self.label)

        # Controls Layout
        control_layout = QHBoxLayout()
        
        self.btn = QPushButton("Open .bag Files")
        self.btn.clicked.connect(self.load_bags)
        control_layout.addWidget(self.btn)

        self.topic_combo = QComboBox()
        self.topic_combo.addItem("Select Topic...")
        self.topic_combo.currentTextChanged.connect(self.on_topic_selected)
        self.topic_combo.setEnabled(False)
        control_layout.addWidget(self.topic_combo)

        self.field_combo = QComboBox()
        self.field_combo.addItem("Select Variable...")
        self.field_combo.currentTextChanged.connect(self.on_field_selected)
        self.field_combo.setEnabled(False)
        control_layout.addWidget(self.field_combo)

        main_layout.addLayout(control_layout)

        # --- Matplotlib Integration ---
        self.fig = Figure(figsize=(12, 8), dpi=100) 
        self.canvas = FigureCanvas(self.fig)
        
        self.toolbar = NavigationToolbar(self.canvas, self)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

        self.canvas.mpl_connect('scroll_event', self.on_mouse_scroll)

        self.axes = [self.fig.add_subplot(111)]
        self.axes[0].set_title("Waiting for data...")
        self.axes[0].set_xlabel("Time (s)")
        self.apply_grid(self.axes[0])

        self.setLayout(main_layout)

    def apply_grid(self, ax):
        ax.minorticks_on()
        ax.grid(which='major', linestyle='-', linewidth='0.8', color='gray')
        ax.grid(which='minor', linestyle=':', linewidth='0.5', color='lightgray')

    # --- Interaction Events ---
    def on_mouse_scroll(self, event):
        if not event.inaxes:
            return
            
        ax = event.inaxes 
        
        base_scale = 1.15
        scale_factor = 1 / base_scale if event.button == 'up' else base_scale

        xdata, ydata = event.xdata, event.ydata
        xlim, ylim = ax.get_xlim(), ax.get_ylim()

        new_xlim = [xdata - (xdata - xlim[0]) * scale_factor, xdata + (xlim[1] - xdata) * scale_factor]
        
        # Only zoom the X-axis with the scroll wheel, let the auto-scaler handle the Y-axis
        ax.set_xlim(new_xlim)
        self.canvas.draw_idle()

    def on_xlim_changed(self, ax):
        if not self.plot_data:
            return

        try:
            idx = list(self.axes).index(ax)
            data = self.plot_data[idx]
            
            t = data['times']
            v = data['values']
            
            xlim = ax.get_xlim()
            mask = (t >= xlim[0]) & (t <= xlim[1])
            
            if np.any(mask):
                v_view = v[mask]
                v_min, v_max = np.min(v_view), np.max(v_view)
                
                # Move the lines
                data['min_line'].set_ydata([v_min, v_min])
                data['min_line'].set_label(f"Min ({v_min:.3f})")
                
                data['max_line'].set_ydata([v_max, v_max])
                data['max_line'].set_label(f"Max ({v_max:.3f})")
                
                # Auto-Scale the Y-axis so the Min and Max are ALWAYS visible
                y_margin = (v_max - v_min) * 0.1 
                if y_margin == 0: y_margin = 0.5 
                
                ax.set_ylim(v_min - y_margin, v_max + y_margin)
                
                ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5))
                self.canvas.draw_idle()

        except ValueError:
            pass

    # --- Dynamic Data Discovery ---
    def get_numeric_fields(self, obj, prefix=""):
        fields = []
        for attr in dir(obj):
            if attr.startswith('_') or callable(getattr(obj, attr)):
                continue
            val = getattr(obj, attr)
            full_name = f"{prefix}.{attr}" if prefix else attr
            if type(val) in (int, float):
                fields.append(full_name)
            elif hasattr(val, '__dataclass_fields__') or (hasattr(val, '__module__') and 'rosbags' in val.__module__):
                fields.extend(self.get_numeric_fields(val, full_name))
        return fields

    def extract_value(self, msg, path):
        val = msg
        try:
            for p in path.split('.'):
                val = getattr(val, p)
            return val
        except AttributeError:
            return None

    # --- UI Interactions ---
    def load_bags(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select ROS Bag Files", "", "ROS Bag Files (*.bag)")
        if not file_paths: return

        if len(file_paths) > 3:
            QMessageBox.warning(self, "Too Many Files", "You selected more than 3 files. Only the first 3 will be loaded.")
            self.bag_paths = file_paths[:3]
        else:
            self.bag_paths = file_paths

        # --- NEW: Remember the user's previous topic selection ---
        old_topic = self.topic_combo.currentText()

        self.label.setText(f"Loaded {len(self.bag_paths)} bags. Scanning structure of the first bag...")
        QApplication.processEvents()

        with AnyReader([Path(self.bag_paths[0])]) as reader:
            topics = sorted(list(set([conn.topic for conn in reader.connections])))
            
            self.topic_combo.blockSignals(True)
            self.topic_combo.clear()
            self.topic_combo.addItem("Select Topic...")
            self.topic_combo.addItems(topics)
            
            # Check if the previously selected topic exists in the new bag file
            topic_retained = False
            if old_topic != "Select Topic..." and old_topic in topics:
                self.topic_combo.setCurrentText(old_topic)
                topic_retained = True
                
            self.topic_combo.setEnabled(True)
            self.topic_combo.blockSignals(False)
            
        # If the topic exists, pass control down to check the variables
        if topic_retained:
            self.on_topic_selected(old_topic)
        else:
            self.field_combo.clear()
            self.field_combo.setEnabled(False)
            self.label.setText("2. Select a Topic from the dropdown menu.")

    def on_topic_selected(self, topic):
        if not self.bag_paths or topic == "Select Topic...": return

        self.label.setText(f"Analyzing structure of {topic}...")
        QApplication.processEvents()

        # --- NEW: Remember the user's previous variable selection ---
        old_field = self.field_combo.currentText()

        with AnyReader([Path(self.bag_paths[0])]) as reader:
            connections = [x for x in reader.connections if x.topic == topic]
            for connection, _, rawdata in reader.messages(connections=connections):
                msg = reader.deserialize(rawdata, connection.msgtype)
                available_fields = self.get_numeric_fields(msg)
                break  

        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItem("Select Variable...")
        self.field_combo.addItems(available_fields)
        
        # Check if the previously selected variable exists within this topic's new structure
        field_retained = False
        if old_field != "Select Variable..." and old_field in available_fields:
            self.field_combo.setCurrentText(old_field)
            field_retained = True
            
        self.field_combo.setEnabled(True)
        self.field_combo.blockSignals(False)

        # If both matches are valid, execute the automatic plot generation immediately
        if field_retained:
            self.label.setText(f"Automatically extracting {old_field} from all bags...")
            QApplication.processEvents()
            self.plot_all_bags(topic, old_field)
        else:
            self.label.setText("3. Select a specific Variable to plot across all bags.")

    def on_field_selected(self, field):
        if field == "Select Variable...": return
        topic = self.topic_combo.currentText()
        
        self.label.setText(f"Extracting {field} from all bags...")
        QApplication.processEvents()
        
        self.plot_all_bags(topic, field)

    # --- Plotting Logic ---
    def plot_all_bags(self, topic, field):
        self.fig.clear() 
        self.plot_data = [] 
        
        num_bags = len(self.bag_paths)
        self.axes = self.fig.subplots(num_bags, 1)
        
        if num_bags == 1:
            self.axes = [self.axes]

        for i, bag_path in enumerate(self.bag_paths):
            ax = self.axes[i]
            bag_name = Path(bag_path).name
            values, times = [], []

            try:
                with AnyReader([Path(bag_path)]) as reader:
                    connections = [x for x in reader.connections if x.topic == topic]
                    for connection, timestamp, rawdata in reader.messages(connections=connections):
                        msg = reader.deserialize(rawdata, connection.msgtype)
                        
                        val = self.extract_value(msg, field)
                        if val is not None:
                            values.append(val)
                            times.append(timestamp * 1e-9)
            except Exception as e:
                ax.set_title(f"Error reading {bag_name}")
                continue

            if not times:
                ax.set_title(f"No {topic} data in {bag_name}")
                self.apply_grid(ax)
                continue

            times = np.array(times)
            times = times - times[0] 
            values = np.array(values)

            v_min, v_max = np.min(values), np.max(values)

            self.apply_grid(ax)
            
            ax.plot(times, values, label=field, color='blue')
            
            min_line = ax.axhline(v_min, linestyle="--", color='green', linewidth=1.5, label=f"Min ({v_min:.3f})")
            max_line = ax.axhline(v_max, linestyle="--", color='red', linewidth=1.5, label=f"Max ({v_max:.3f})")
            
            self.plot_data.append({
                'times': times,
                'values': values,
                'min_line': min_line,
                'max_line': max_line
            })

            ax.callbacks.connect('xlim_changed', self.on_xlim_changed)

            ax.set_ylabel("Value")
            ax.set_title(f"{bag_name}") 
            
            if i == num_bags - 1:
                ax.set_xlabel("Time (s)")
            
            ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5))

        self.label.setText(f">>> Status: SUCCESS | Plotted {num_bags} files. <<<")
        
        self.fig.tight_layout()
        self.canvas.draw()
        
        if self.toolbar.mode == '': 
            self.toolbar.zoom()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MultiBagGUI()
    window.show()
    sys.exit(app.exec_())
