import shutil
from gi.repository import GioUnix, Gtk, GdkPixbuf, GLib, Gio
from PIL import Image as PILImage, ImageEnhance, ImageFilter
import io
from snippets import enable_blur, set_blur_regions_from_widget

import threading

_icon_cache: dict[str, str] = {}
_cache_lock = threading.Lock()
_cache_built = False

def _build_cache() -> None:
    global _cache_built
    cache = {}
    for app in Gio.AppInfo.get_all():
        gio_icon = app.get_icon()
        if not gio_icon:
            continue
        icon_str = gio_icon.to_string()
        
        desktop_id = (app.get_id() or "").lower().removesuffix(".desktop")
        app_name = (app.get_name() or "").lower()
        executable = (app.get_executable() or "").split("/")[-1].lower()

        for key in [desktop_id, app_name, executable]:
            if key and key not in cache:
                cache[key] = icon_str
        
        # Also index the last segment of reverse-DNS IDs (org.gnome.Nautilus -> nautilus)
        if "." in desktop_id:
            short = desktop_id.split(".")[-1]
            if short and short not in cache:
                cache[short] = icon_str

    with _cache_lock:
        _icon_cache.update(cache)
        _cache_built = True

# Build cache once in a background thread at import time
threading.Thread(target=_build_cache, daemon=True).start()

def get_app_icon_name(app_id: str) -> str | None:
    if not app_id:
        return None
    
    app_id_lower = app_id.lower()
    short = app_id.split(".")[-1].lower()

    with _cache_lock:
        return (
            _icon_cache.get(app_id_lower)
            or _icon_cache.get(short)
            or _icon_cache.get("-".join(app_id.split(".")).lower())
        )

def popup_with_blur(menu: Gtk.Menu, event, accuracy: int = 1):
    blur_ctx = None

    def do_blur():
        nonlocal blur_ctx
        blur_ctx = enable_blur(menu)
        def do_set_regions():
            if blur_ctx:
                set_blur_regions_from_widget(blur_ctx, menu, accuracy, erode=0)
            return False
        GLib.timeout_add(50, do_set_regions)

    menu.show_all()
    menu.popup_at_pointer(event)
    GLib.idle_add(do_blur)

def executable_exists(executable_name):
    executable_path = shutil.which(executable_name)
    return bool(executable_path)


def load_blurred_pixbuf(
    path: str,
    width: int,
    height: int,
    blur_radius=10,
    darken_factor=1.0,
):
    try:
        img = PILImage.open(path).convert("RGBA")
        img = img.resize((width, height))
        img = img.filter(ImageFilter.GaussianBlur(blur_radius))

        if darken_factor < 1.0:
            img = ImageEnhance.Brightness(img).enhance(darken_factor)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        loader = GdkPixbuf.PixbufLoader.new_with_type("png")
        loader.write(buf.read())
        loader.close()

        return loader.get_pixbuf()
    except Exception:
        return None
    
def load_scaled_pixbuf(path: str, width: int, height: int):
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(
            path, width, height, False
        )
    except Exception:
        return None
    
def load_cover_pixbuf(path: str, width: int, height: int):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)

    src_w = pixbuf.get_width()
    src_h = pixbuf.get_height()

    scale = max(width / src_w, height / src_h)

    scaled_w = int(src_w * scale)
    scaled_h = int(src_h * scale)

    scaled = pixbuf.scale_simple(
        scaled_w,
        scaled_h,
        GdkPixbuf.InterpType.BILINEAR,
    )

    x = (scaled_w - width) // 2
    y = (scaled_h - height) // 2

    return scaled.new_subpixbuf(x, y, width, height)