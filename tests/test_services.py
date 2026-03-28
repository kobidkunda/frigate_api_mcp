from factory_analytics.database import Database
from factory_analytics.services import AnalyticsService


def test_group_scheduler_settings(tmp_path):
    db = Database(tmp_path / "test.db")
    service = AnalyticsService(db)

    # Default settings should include group scheduler enabled
    settings = service.settings()
    assert "group_scheduler_enabled" in settings
    assert settings["group_scheduler_enabled"] is True
    assert "group_analysis_interval_seconds" in settings
    assert settings["group_analysis_interval_seconds"] == 300

    # Update settings
    updated = service.update_settings(
        {"group_scheduler_enabled": False, "group_analysis_interval_seconds": 600}
    )

    assert updated["group_scheduler_enabled"] is False
    assert updated["group_analysis_interval_seconds"] == 600
