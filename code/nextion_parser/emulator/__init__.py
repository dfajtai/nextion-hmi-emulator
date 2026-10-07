"""Emulator layer: turns a parsed project into the standalone browser emulator (and its packaging)."""
from .builder import EmulatorBuilder, REPORTS, assets, build_data, generate, parse_size
from .launcher import write_launcher
from .model import EmulatorData, ReportLink, Screen
from .portable import add_updater, write_scripts

__all__ = ["EmulatorBuilder", "EmulatorData", "ReportLink", "Screen", "REPORTS", "assets", "build_data", "generate",
           "parse_size", "write_launcher", "add_updater", "write_scripts"]
