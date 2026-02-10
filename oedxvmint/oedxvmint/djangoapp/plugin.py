"""Open edX plugin entrypoint."""

from openedx.core.djangoapps.plugins.constants import ProjectType, SettingsType

plugin_app = {
    ProjectType.LMS: {
        SettingsType.COMMON: {"relative_path": "settings.common"},
        SettingsType.PRODUCTION: {"relative_path": "settings.production"},
        SettingsType.DEVSTACK: {"relative_path": "settings.devstack"},
    }
}
