"""Connectors — pluggable data sources.

Each connector implements the Connector protocol from `base.py` and
publishes typed events to the bus. Adding a new source (Linear, Notion,
PagerDuty, GCal) is one new file in this package + registration.
"""
