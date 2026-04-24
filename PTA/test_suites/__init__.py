"""
Tek PTA Test Suites Package
===========================

This folder contains test suite plugins that are automatically discovered
and loaded by Tek PTA at startup.

To create a new test suite:
1. Copy example_suites.py as a starting point
2. Define your test suites as TestSuitePlugin objects
3. Implement register_suites() to return your test suites
4. Place the file in this folder

See tek_pta_plugin_api.py for the base classes and utilities available.
See example_suites.py for working examples.
"""

__all__ = ['tek_pta_plugin_api', 'example_suites']
