from trame_image_tools.widgets import *  # noqa: F403


def initialize(server):
    from trame_image_tools import module

    server.enable_module(module)
