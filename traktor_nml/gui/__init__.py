"""The reconnect wizard package: nicegui-based review UI over the printless
reconnect core.

Empty of imports on purpose: tests/test_cli_without_nicegui.py blocks
nicegui at sys.meta_path and any import here would run for anything
touching the package name at all - importing the package itself must
stay free even before a submodule is chosen.
"""
