#!/usr/bin/env python3
"""Utility script to run the two-steps β analysis more easily."""
import argparse
import glob
import os
import re
import shlex
from subprocess import run

SCRIPT_DIR = os.path.dirname(os.path.abspath(__name__))
BATRA = os.path.join(SCRIPT_DIR, 'analyseInPY3.py')
PLOTTER = os.path.join(SCRIPT_DIR, 'BEQAG_plotter.py')
EDITOR = os.environ.get("EDITOR", "gedit")


def settings_sort_key(k):
    if not isinstance(k, str):
        k = k[0]  # Assume key-value pair
    if k == 'files': return 0
    if k.startswith('CH_'): return 1
    if k in {'tmax', 'pmax', 'negpmax', 'amplitude', 'risetime', 'charge', 'rms', 'timeres'}:
        return 2
    if k.endswith('_nB_xL_xU'): return 3
    if k.startswith('CH') and k.endswith('_cut'): return 4
    return 5


def fmt_comment(x):
    return f"# {str(x).replace('\n', '\n# ')}\n"


def modify_card(input_fp, output_fp, overrides, defaults, comment_begin=None, comment_before_cuts=None):
    overrides, defaults = dict(overrides), dict(defaults)
    # Read input file and overwrite defaults
    with open(input_fp) as ifs:
        for ln in ifs:
            # This re does NOT match comments and empty lines
            m = re.fullmatch(r"^(\w+)\s*=\s*(.+)$", ln.strip())
            if m:
                defaults[m[1]] = m[2]
    # Override with overrides
    for k, v in overrides.items():
        defaults[k] = v
    # Write what we collected
    with open(output_fp, "w") as ofs:
        if comment_begin:
            ofs.write(fmt_comment(comment_begin))
        for k, v in sorted(defaults.items(), key=settings_sort_key):
            if k.startswith('CH') and k.endswith('_cut') and comment_before_cuts:
                ofs.write(fmt_comment(comment_before_cuts))
                comment_before_cuts = None
            ofs.write(f"{k}={v}\n")
    return defaults


def print_and_run(cmd_line, *args, **kwargs):
    print(f"\x1b[1m+ {shlex.join(cmd_line)}\x1b[0m")
    run(cmd_line, *args, **kwargs)


def list_t_dir(td):
    for name in sorted({x.GetName() for x in td.GetListOfKeys()}):
        yield name, td[name]


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("card_file", help="Card file used as template")
parser.add_argument("input_files", nargs="+",
                    help="Input stats_*.root files (glob supported)")
parser.add_argument("--subtitle", default=None,
                    help="Subtitle for the BEQAG plots of the CSV")
parser.add_argument("--no-gui", action="store_true",
                    help="Disable displaying histograms in canvas windows"
                         " while editing the cuts in the card file")
args = parser.parse_args()

# List input files expanding glob patterns
input_files = []
for pattern in args.input_files:
    matches = glob.glob(pattern)
    matches.sort()
    if not matches:
        print(f"WARNING No file matches {pattern!r}")
    input_files.extend(os.path.abspath(x) for x in matches)

print("Input files:")
for f in input_files:
    print(f" - {f!r}")
print()

# Choose output directory
output_dir = os.path.dirname(input_files[0])
print(f"Output dir: {output_dir!r}")

# Prepare modified card file (into output directory)
card_copy_fp = os.path.join(output_dir, os.path.basename(args.card_file))
if os.path.exists(card_copy_fp) and os.path.samefile(args.card_file, card_copy_fp):
    n, e = os.path.splitext(card_copy_fp)
    card_copy_fp = f"{n}_mod{e}"
print(f"Creating modified card file {args.card_file!r} -> {card_copy_fp!r}")

file_list_cs = ",\n        ".join(input_files)
overrides = {
    'files': f'"{file_list_cs}"',
    'CH1_cut': '0,0,0,0,0', 'CH2_cut': '0,0,0,0,0',
    'CH3_cut': '0,0,0,0,0', 'CH4_cut': '0,0,0,0,0',
    'CH5_cut': '0,0,0,0,0', 'CH6_cut': '0,0,0,0,0',
    'CH7_cut': '0,0,0,0,0', 'CH8_cut': '0,0,0,0,0',
    'tmax': 'True',
    'pmax': 'True',
    'negpmax': 'True',
    'amplitude': 'False',
    'risetime': 'False',
    'charge': 'False',
    'rms': 'False',
    'timeres': 'False',
}
defaults = {
    'run_safe_mode': 'True',
    'CH_1': '0', 'CH_2': '0', 'CH_3': '0', 'CH_4': '0',
    'CH_5': '0', 'CH_6': '0', 'CH_7': '0', 'CH_8': '0',
    'tmax_nB_xL_xU': '1000,-6,2',
    'pmax_nB_xL_xU': '1000,0,200',
    'negpmax_nB_xL_xU': '50,-40,10',
    'risetime_nB_xL_xU': '120,0.0,1.2',
    'charge_nB_xL_xU': '100,0,20',
    'rms_nB_xL_xU': '40,0,4',
    'timeres_nB_xL_xU': '200,-2.0,0.0',
}
settings = modify_card(args.card_file, card_copy_fp, overrides, defaults)

# Run step 1
print_and_run(['python3', BATRA, card_copy_fp], check=True)

if not args.no_gui:
    import ROOT  # To save time & memory, only import if actually used
    ROOT.gStyle.SetPalette(ROOT.kDeepSea)
    ROOT.gStyle.SetOptStat(0)
    tf = ROOT.TFile(f"{os.path.splitext(card_copy_fp)[0]}.root")
    canvases = {}  # {ch_index: TCanvas}
    legends = {}  # {(ch_index, var_name): TLegend}
    for vi, vn in enumerate(["pmax", "negpmax", "tmax"]):
        for subdir_name, subdir in list_t_dir(tf[vn]):
            for hist_name, hist in list_t_dir(subdir):
                if m := re.match(r"CH(\d+)_(.+)", hist_name):
                    ch = int(m[1])
                    if ch in canvases:
                        c = canvases[ch]
                    else:
                        c = ROOT.TCanvas(f"CH{ch}", f"CH{ch}", 400*3, 300)
                        c.Divide(3)
                        canvases[ch] = c
                    c.cd(vi+1)
                    if (ch, vn) in legends:  # Not 1st histogram in this pad
                        hist.Draw("HIST SAME PLC")
                    else:
                        hist.SetTitle(f"CH{ch} - {hist.GetTitle()}")
                        hist.Draw("HIST PLC")
                        ROOT.gPad.SetLogy()
                        ROOT.gPad.SetGridx()
                        leg = ROOT.TLegend(0.8, 0.8, 0.9, 0.9)
                        legends[(ch, vn)] = leg
                    legends[(ch, vn)].AddEntry(hist, m[2], "L")
        for ch, c in canvases.items():
            c.cd(vi+1)
            leg = legends[(ch, vn)]
            leg.SetY1NDC(leg.GetY2NDC() - 0.04 * leg.GetNRows())
            leg.Draw()
    for c in canvases.values():
        c.Update()

# Prepare modified card file to be edited for step 2
cut_pmax_lower_template = ','.join('0' * len(input_files))
cut_template = f'[{cut_pmax_lower_template}],0,0,0,0'
overrides = {
    'files': f'"{file_list_cs}"',
    'CH1_cut': cut_template if settings['CH_1'] != '0' else '0,0,0,0,0',
    'CH2_cut': cut_template if settings['CH_2'] != '0' else '0,0,0,0,0',
    'CH3_cut': cut_template if settings['CH_3'] != '0' else '0,0,0,0,0',
    'CH4_cut': cut_template if settings['CH_4'] != '0' else '0,0,0,0,0',
    'CH5_cut': cut_template if settings['CH_5'] != '0' else '0,0,0,0,0',
    'CH6_cut': cut_template if settings['CH_6'] != '0' else '0,0,0,0,0',
    'CH7_cut': cut_template if settings['CH_7'] != '0' else '0,0,0,0,0',
    'CH8_cut': cut_template if settings['CH_8'] != '0' else '0,0,0,0,0',
    'tmax': 'True',
    'pmax': 'True',
    'negpmax': 'True',
    'amplitude': 'True',
    'risetime': 'True',
    'charge': 'True',
    'rms': 'True',
    'timeres': 'True',
}
modify_card(
    args.card_file, card_copy_fp, overrides, defaults,
    "Please EDIT the CHx_cuts below (CHECK the file order!!!)",
    "CHx_cut = PMAX_LOWER,PMAX_UPPER,NEGPMAX_LOWER,TMAX_LOWER,TMAX_UPPER (mV and ns)"
)

# Let the user edit the card file
print("--> Please edit card file for step 2 (set cuts) <--")
print(card_copy_fp)
print_and_run([EDITOR, card_copy_fp], check=True)

# Close the canvases and the root file
if not args.no_gui:
    for c in canvases.values():
        c.Close()
    tf.Close()

# Run step 2
print_and_run(['python3', BATRA, card_copy_fp], check=True)

# Check for csv and run the plotter
csv_file = f"{os.path.splitext(card_copy_fp)[0]}.csv"
if os.path.isfile(csv_file):
    subtitle = args.subtitle or os.path.basename(output_dir)
    print_and_run(['python3', PLOTTER, csv_file, subtitle], check=True)
else:
    print("CSV file not found, skipping BEQAG plots")
