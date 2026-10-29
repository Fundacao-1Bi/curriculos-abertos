#!/usr/bin/env python3
"""Repeat full original-label/position/heading proof for final V3 sidecars."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];B=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('metadata',B/'verify_metadata.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
s=importlib.util.spec_from_file_location('adapter_v3',ROOT/'data/manifests/uncoded/es-complement-coded-v3-extract.py');v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
if __name__=='__main__':m.a=v.b;m.OUT=v.OUT;v.b.dest=v.dest;v.b.OUT=v.OUT;m.main()
