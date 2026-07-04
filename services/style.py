import os
from fabric.core.service import Service, Property
from fabric.utils import get_relative_path, monitor_file
from gi.repository import GLib
from plugin_loader import apply_plugin_css


class StyleService(Service):

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._style_changed = False

        style_dir = os.environ.get("CAFFYNE_STYLE_DIR", os.path.expanduser("~/.config/caffyne-shell/style"))
        self.style_monitor = monitor_file(style_dir)
        self.style_monitor.connect("changed", lambda *_: self.reload())

    @Property(bool, default_value=False)
    def style_changed(self) -> bool:
        return self._style_changed

    def reload(self, *_):
        try:
            style_file = os.path.join(os.environ.get("CAFFYNE_STYLE_DIR", get_relative_path("../style")), "style.css")
            self.app.set_stylesheet_from_file(
                file_path=style_file,
            )
            
            GLib.timeout_add(100, apply_plugin_css, self.app)

            self._style_changed = not self._style_changed
            
            self.notify("style-changed")
            
        except Exception as e:
            print(f"[StyleService] Error reloading styles: {e}")
