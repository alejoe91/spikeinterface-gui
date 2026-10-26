import numpy as np

from .vennview import VennView, solve_venn_geometry


class CompareSpikesView(VennView):
    """
    Venn diagram of the spikes of one pair of units (one per sorter): spikes found by both,
    and spikes found by only one of the two. Clicking a region selects its spikes and plots
    their waveforms.
    """
    id = "comparespikes"
    _supported_backend = ['qt', 'panel']
    _depend_on = ['comparison']
    _settings = [
        {'name': 'max_waveforms', 'type': 'int', 'value': 100},
    ]

    def __init__(self, controller=None, parent=None, backend="qt"):
        # the spike venn of the last compared pair, set by the "compare spikes" button
        self._compared_pair = None
        self._spike_venn = None
        VennView.__init__(self, controller=controller, parent=parent, backend=backend)

    def get_visible_pair(self):
        """The (unit_id1, unit_id2) pair when the visible units are one unit of each sorter, else None"""
        visible_unit_ids = list(self.controller.get_visible_unit_ids())
        if len(visible_unit_ids) != 2:
            return None
        visible_unit_ids.sort(key=self.controller.get_analyzer_index)
        if [self.controller.get_analyzer_index(u) for u in visible_unit_ids] != [1, 2]:
            return None
        return tuple(visible_unit_ids)

    def compare_spikes(self):
        pair = self.get_visible_pair()
        if pair is None:
            return
        with self.busy_cursor():
            self._spike_venn = self.controller.get_spike_venn(*pair)
        self._compared_pair = pair
        self._clear_waveforms()
        self.refresh()

    def get_venn_data(self):
        # never show the result of another pair than the visible one
        if self._spike_venn is None or self._compared_pair != self.get_visible_pair():
            venn = dict(matched=[], only1=[], only2=[])
        else:
            venn = dict(
                matched=self._spike_venn['matched1'],
                only1=self._spike_venn['only1'],
                only2=self._spike_venn['only2'],
            )
        geometry = solve_venn_geometry(len(venn['only1']), len(venn['matched']), len(venn['only2']))
        return venn, geometry

    def select_units_on_click(self, x, y, reset=True):
        # here a click selects the spikes of a region, not units
        venn, geometry = self.get_venn_data()
        region = self.get_clicked_region(x, y, geometry)
        if region is None or len(venn[region]) == 0:
            return

        unit_id1, unit_id2 = self._compared_pair
        if region == 'matched':
            spike_inds_by_unit = {
                unit_id1: self._spike_venn['matched1'],
                unit_id2: self._spike_venn['matched2'],
            }
        elif region == 'only1':
            spike_inds_by_unit = {unit_id1: self._spike_venn['only1']}
        else:
            spike_inds_by_unit = {unit_id2: self._spike_venn['only2']}

        self.controller.set_indices_spike_selected(np.sort(np.concatenate(list(spike_inds_by_unit.values()))))
        self.notify_spike_selection_changed()

        self._show_waveforms(region, spike_inds_by_unit)

    def get_waveforms_data(self, spike_inds_by_unit):
        """
        The waveforms to plot, on the extremum channel of the first unit of the region.

        Returns (times_ms, lines, title) where lines is a list of (unit_id, wfs, is_mean),
        or None when there are no waveforms.
        """
        controller = self.controller
        unit_ids = list(spike_inds_by_unit.keys())
        channel_index = controller.get_main_channel(unit_ids[0])
        rng = np.random.default_rng()

        lines = []
        texts = []
        for unit_id, spike_inds in spike_inds_by_unit.items():
            result = controller.get_waveforms_for_spikes(unit_id, spike_inds)
            if result is None:
                return None
            wfs, chan_inds, kept = result
            texts.append(f"{unit_id}: {len(kept)} of {len(spike_inds)} spikes have waveforms (random_spikes)")
            chan_pos = np.flatnonzero(chan_inds == channel_index)
            if len(chan_pos) == 0 or len(kept) == 0:
                # the extremum channel is not in the sparsity of this unit
                continue
            wfs = wfs[:, :, chan_pos[0]]
            if wfs.shape[0] > self.settings['max_waveforms']:
                wfs = wfs[rng.choice(wfs.shape[0], self.settings['max_waveforms'], replace=False)]
            lines.append((unit_id, wfs, False))
            lines.append((unit_id, wfs.mean(axis=0, keepdims=True), True))

        num_samples = controller.nbefore + controller.nafter
        times_ms = (np.arange(num_samples) - controller.nbefore) / controller.sampling_frequency * 1000.
        return times_ms, lines, " | ".join(texts)

    ## Qt ##
    def _qt_make_layout(self):
        from .myqt import QT
        import pyqtgraph as pg

        self.layout = QT.QVBoxLayout()

        header = QT.QHBoxLayout()
        self.compare_button = QT.QPushButton('compare spikes')
        self.compare_button.clicked.connect(self.compare_spikes)
        header.addWidget(self.compare_button)
        self.pair_label = QT.QLabel('')
        header.addWidget(self.pair_label)
        header.addStretch()
        self.layout.addLayout(header)

        self._qt_make_venn_plot()

        self.waveform_plot = pg.PlotWidget()
        self.waveform_plot.setLabel('bottom', 'time (ms)')
        self.layout.addWidget(self.waveform_plot)

    def _qt_refresh(self):
        pair = self.get_visible_pair()
        self.compare_button.setEnabled(pair is not None)
        if pair is None:
            self.pair_label.setText('select a pair of units, one of each sorter')
        else:
            self.pair_label.setText(f'{pair[0]} vs {pair[1]}')
        if self._compared_pair != pair:
            self._clear_waveforms()
        self._qt_draw_venn(*self.get_venn_data())

    def _clear_waveforms(self):
        if self.backend == 'qt':
            self.waveform_plot.clear()
            self.waveform_plot.setTitle('')
        elif self.backend == 'panel':
            self.waveform_source.data.update({"xs": [], "ys": [], "color": [], "alpha": [], "width": []})
            self.waveform_figure.title.text = ''

    def _show_waveforms(self, region, spike_inds_by_unit):
        self._clear_waveforms()
        data = self.get_waveforms_data(spike_inds_by_unit)
        if data is None:
            return
        if self.backend == 'qt':
            self._qt_show_waveforms(*data)
        elif self.backend == 'panel':
            self._panel_show_waveforms(*data)

    def _qt_show_waveforms(self, times_ms, lines, title):
        import pyqtgraph as pg

        for unit_id, wfs, is_mean in lines:
            color = self.get_unit_color(unit_id, alpha=1.0 if is_mean else 0.3)
            # all the waveforms of a unit in one curve, separated by nan
            xs = np.tile(np.append(times_ms, np.nan), wfs.shape[0])
            ys = np.hstack([wfs, np.full((wfs.shape[0], 1), np.nan)]).ravel()
            curve = pg.PlotCurveItem(xs, ys, connect='finite', pen=pg.mkPen(color, width=3 if is_mean else 1))
            self.waveform_plot.addItem(curve)
        self.waveform_plot.setTitle(title)

    ## panel ##
    def _panel_make_layout(self):
        import panel as pn
        import bokeh.plotting as bpl
        from bokeh.models import ColumnDataSource
        from .utils_panel import _bg_color

        self.compare_button = pn.widgets.Button(name="compare spikes", button_type="primary", sizing_mode="stretch_width")
        self.compare_button.on_click(lambda event: self.compare_spikes())

        self._panel_make_venn_figure()

        self.waveform_figure = bpl.figure(
            sizing_mode="stretch_both",
            tools="pan,wheel_zoom,reset",
            background_fill_color=_bg_color,
            border_fill_color=_bg_color,
            outline_line_color="white",
            x_axis_label="time (ms)",
            styles={"flex": "1"},
        )
        self.waveform_figure.toolbar.logo = None
        self.waveform_source = ColumnDataSource({"xs": [], "ys": [], "color": [], "alpha": [], "width": []})
        self.waveform_figure.multi_line(
            xs="xs", ys="ys", source=self.waveform_source,
            line_color="color", line_alpha="alpha", line_width="width",
        )

        self.layout = pn.Column(
            self.compare_button,
            self.figure,
            self.waveform_figure,
            styles={"display": "flex", "flex-direction": "column"},
            sizing_mode="stretch_both",
        )

    def _panel_refresh(self):
        pair = self.get_visible_pair()
        self.compare_button.disabled = pair is None
        self.compare_button.name = "compare spikes" if pair is None else f"compare spikes: {pair[0]} vs {pair[1]}"
        if self._compared_pair != pair:
            self._clear_waveforms()
        self._panel_draw_venn(*self.get_venn_data())

    def _panel_show_waveforms(self, times_ms, lines, title):
        data = {"xs": [], "ys": [], "color": [], "alpha": [], "width": []}
        for unit_id, wfs, is_mean in lines:
            color = self.get_unit_color(unit_id)
            for wf in wfs:
                data["xs"].append(times_ms.tolist())
                data["ys"].append(wf.tolist())
                data["color"].append(color)
                data["alpha"].append(1.0 if is_mean else 0.3)
                data["width"].append(3 if is_mean else 1)
        self.waveform_source.data.update(data)
        self.waveform_figure.title.text = title


CompareSpikesView._gui_help_txt = """
## Compare Spikes View

Spike level comparison of one pair of units, one unit of each sorter. Select a row of the
comparison unit table with two units, then click **compare spikes**.

The Venn diagram shows the spikes found by both units (matched, within the comparison
`delta_time`), and the spikes found by only one of them. The areas are proportional to the
spike counts.

### Controls
- **compare spikes** : compute the spike Venn diagram of the visible pair.
- **left click on a region** : select the spikes of that region (they show up in the spike
  list and trace views) and plot their waveforms on the extremum channel of the first unit.

Waveforms only exist for the `random_spikes` subset, so only those spikes of the region are
plotted. The title tells how many of the region's spikes have waveforms.

### Settings
- **max_waveforms** : the maximum number of waveforms plotted per unit.
"""
