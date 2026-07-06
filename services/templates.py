from __future__ import annotations
import json
import os
import threading
import subprocess

from fabric.utils import monitor_file

from gi.repository import GLib
from loguru import logger

from user_options import user_options

TEMPLATES_DIR        = os.path.expanduser("~/.config/caffyne-shell/templates")
TEMPLATES_REPO       = "https://github.com/caffyne-org/caffyne-templates"
MATUGEN_CONFIG_CACHE = os.path.expanduser("~/.cache/caffyne-shell/matugen-templates.toml")


class TemplateService:
    _instance: "TemplateService | None" = None

    def __init__(self):
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        self._monitor = monitor_file(TEMPLATES_DIR)


    @staticmethod
    def get_instance() -> "TemplateService":
        if TemplateService._instance is None:
            TemplateService._instance = TemplateService()
        return TemplateService._instance
    @property
    def monitor(self):
        return self._monitor

    def list_templates(self) -> list[dict]:
        """
        Scan TEMPLATES_DIR and return a list of template metadata dicts.
        Each dict is the parsed meta.json with two extra keys injected:
          _folder  — absolute path to the template folder
          enabled  — whether this template id is in user_options.templates.enabled
        """
        templates = []
        if not os.path.isdir(TEMPLATES_DIR):
            logger.warning(f"[TemplateService] templates dir not found: {TEMPLATES_DIR}")
            return templates

        for folder_name in sorted(os.listdir(TEMPLATES_DIR)):
            folder_path = os.path.join(TEMPLATES_DIR, folder_name)
            if not os.path.isdir(folder_path):
                continue

            meta_path = os.path.join(folder_path, "meta.json")
            if not os.path.isfile(meta_path):
                logger.warning(f"[TemplateService] no meta.json in {folder_path}, skipping")
                continue

            try:
                with open(meta_path) as f:
                    meta = json.load(f)
            except Exception as e:
                logger.error(f"[TemplateService] failed to read {meta_path}: {e}")
                continue

            # id falls back to folder name if not specified in meta
            template_id = meta.get("id", folder_name)
            meta["id"]      = template_id
            meta["_folder"] = folder_path
            meta["enabled"] = template_id in user_options.templates.enabled
            templates.append(meta)

        return templates

    def set_enabled(self, template_id: str, enabled: bool) -> None:
        """Toggle a template on or off and persist to user_options."""
        current = set(user_options.templates.enabled)
        if enabled:
            current.add(template_id)
        else:
            current.discard(template_id)
        user_options.templates.enabled = list(current)
        user_options.save()
        logger.info(f"[TemplateService] '{template_id}' {'enabled' if enabled else 'disabled'}")

    def build_matugen_config(self) -> str:
        """
        Build a matugen TOML config from the caffyne-shell template (always)
        plus any user-enabled templates. Always returns the config path.
        """
        templates = self.list_templates()
        enabled   = [t for t in templates if t.get("enabled")]

        lines = ["[config]", ""]

        # caffyne-shell colors are always applied
        lines.append("[templates.caffyne]")
        lines.append(f"input_path = '{os.path.expanduser('~/.config/caffyne-shell/style/caffyne-shell-colors.css')}'")
        lines.append(f"output_path = '{os.path.expanduser('~/.config/caffyne-shell/style/colors.css')}'")
        lines.append("")

        for t in enabled:
            folder = t["_folder"]
            template_id = t["id"]

            # multi-template support
            sub_templates = t.get("templates")
            if sub_templates:
                for sub in sub_templates:
                    sub_id      = sub["id"]
                    raw_input   = sub.get("input_path", "")
                    input_path  = os.path.join(folder, raw_input) if not os.path.isabs(raw_input) else raw_input
                    output_path = os.path.expanduser(sub.get("output_path", ""))

                    if not input_path or not output_path:
                        logger.warning(f"[TemplateService] '{sub_id}' missing input/output path, skipping")
                        continue

                    lines.append(f"[templates.{sub_id}]")
                    lines.append(f"input_path = '{input_path}'")
                    lines.append(f"output_path = '{output_path}'")

                    if post_hook_script := sub.get("post_hook_script"):
                        script_path = os.path.join(folder, post_hook_script)
                        lines.append(f'post_hook = "bash {script_path}"')
                    elif post_hook := sub.get("post_hook"):
                        lines.append(f'post_hook = "{post_hook}"')
                    lines.append("")
            else:
                # original single template logic unchanged
                raw_input   = t.get("input_path", "")
                input_path  = os.path.join(folder, raw_input) if not os.path.isabs(raw_input) else raw_input
                output_path = os.path.expanduser(t.get("output_path", ""))

                if not input_path or not output_path:
                    logger.warning(f"[TemplateService] '{template_id}' missing input/output path, skipping")
                    continue

                lines.append(f"[templates.{template_id}]")
                lines.append(f"input_path = '{input_path}'")
                lines.append(f"output_path = '{output_path}'")

                if post_hook_script := t.get("post_hook_script"):
                    script_path = os.path.join(t["_folder"], post_hook_script)
                    lines.append(f'post_hook = "bash {script_path}"')
                elif post_hook := t.get("post_hook"):
                    lines.append(f'post_hook = "{post_hook}"')

                lines.append("")

        try:
            os.makedirs(os.path.dirname(MATUGEN_CONFIG_CACHE), exist_ok=True)
            with open(MATUGEN_CONFIG_CACHE, "w") as f:
                f.write("\n".join(lines))
            logger.info(f"[TemplateService] wrote matugen config → {MATUGEN_CONFIG_CACHE}")
        except Exception as e:
            logger.error(f"[TemplateService] failed to write config: {e}")

        return MATUGEN_CONFIG_CACHE

    def fetch_templates(self, callback: callable | None = None) -> None:
        """
        Clone the templates repo if it doesn't exist, otherwise pull.
        Calls callback(success: bool) on the main thread when done.
        """
        def run():
            try:
                git_dir = os.path.join(TEMPLATES_DIR, ".git")
                if os.path.isdir(git_dir):
                    logger.info("[TemplateService] pulling latest templates")
                    cmd = ["git", "-C", TEMPLATES_DIR, "pull"]
                else:
                    logger.info("[TemplateService] cloning templates repo")
                    os.makedirs(TEMPLATES_DIR, exist_ok=True)
                    cmd = ["git", "clone", TEMPLATES_REPO, TEMPLATES_DIR]

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info("[TemplateService] fetch successful")
                else:
                    logger.error(f"[TemplateService] fetch failed: {result.stderr.strip()}")

                if callback:
                    GLib.idle_add(callback, result.returncode == 0)

            except Exception as e:
                logger.error(f"[TemplateService] fetch exception: {e}")
                if callback:
                    GLib.idle_add(callback, False)

        threading.Thread(target=run, daemon=True).start()

    def run_toggle_script(self, template_id: str, enabled: bool) -> None:
        """Run enable.sh or disable.sh for a template if it exists."""
        templates = self.list_templates()
        template  = next((t for t in templates if t["id"] == template_id), None)
        if template is None:
            return

        script_name = "enable.sh" if enabled else "disable.sh"
        script_path = os.path.join(template["_folder"], script_name)

        if not os.path.isfile(script_path):
            logger.info(f"[TemplateService] no {script_name} for '{template_id}', skipping")
            return

        def run():
            try:
                logger.info(f"[TemplateService] running {script_name} for '{template_id}'")
                subprocess.run(["bash", script_path], capture_output=True, text=True)
            except Exception as e:
                logger.error(f"[TemplateService] toggle script failed for '{template_id}': {e}")

        threading.Thread(target=run, daemon=True).start()
template_service = TemplateService.get_instance()