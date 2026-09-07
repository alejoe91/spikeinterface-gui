from argparse import ArgumentParser
from pathlib import Path

import numpy as np

from spikeinterface import load_sorting_analyzer
from spikeinterface_gui import run_mainwindow, run_launcher
from spikeinterface_gui.tests.testingtools import (
    clean_all,
    make_analyzer_folder,
    make_curation_dict,
    make_events_dict,
    make_extra_unit_properties,
    prepare_analyzer,
)


test_folder = Path(__file__).parent


def setup_module():
    global test_folder
    case = test_folder.stem.split('_')[-1]
    make_analyzer_folder(test_folder, case=case, unit_dtype="int")


def teardown_module():
    clean_all(test_folder)


def test_mainwindow(
    mode="desktop",
    start_app=False,
    verbose=True,
    curation=False,
    only_some_extensions=False,
    events=False,
    layout="default",
    port=0,
):
    analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
    print(analyzer)

    curation_dict = make_curation_dict(analyzer) if curation else None
    analyzer = prepare_analyzer(analyzer, only_some_extensions=only_some_extensions)
    extra_unit_properties = make_extra_unit_properties(analyzer)
    events_dict = make_events_dict(analyzer) if events else None

    kwargs = dict(
        mode=mode,
        start_app=start_app,
        verbose=verbose,
        curation=curation,
        curation_dict=curation_dict,
        displayed_unit_properties=None,
        extra_unit_properties=extra_unit_properties,
        layout_preset=layout,
        events=events_dict,
    )
    print(layout)
    if mode == "web":
        kwargs["port"] = port

    return run_mainwindow(analyzer, **kwargs)


def test_launcher(mode="desktop", verbose=True):
    analyzer_folders = None
    root_folder = Path(__file__).parent
    win = run_launcher(mode=mode, analyzer_folders=analyzer_folders, root_folder=root_folder, verbose=verbose)


parser = ArgumentParser()
parser.add_argument('--mode', default="desktop", choices=["desktop", "web"], help='GUI mode: desktop (Qt) or web (Panel)')
parser.add_argument('--dataset', default="small", help='Dataset type: small, medium-split, big, multiprobe')
parser.add_argument('--curation', action="store_true", help='Enable curation')
parser.add_argument('--events', action="store_true", help='Simulate and add events')
parser.add_argument('--layout', default="default", help='Layout preset name')
parser.add_argument('--port', type=int, default=0, help='Port for web mode (0 = auto)')

if __name__ == '__main__':
    args = parser.parse_args()
    test_folder = Path(__file__).parents[2] / f"my_dataset_{args.dataset}"

    if not test_folder.is_dir():
        setup_module()

    win = test_mainwindow(
        mode=args.mode,
        start_app=True,
        verbose=True,
        curation=args.curation,
        events=args.events,
        port=args.port,
        layout=args.layout,
    )
