from app import default_data, get_day_activity, sync_device_activity


def test_default_data_includes_activity_tracking():
    data = default_data()
    assert "activity" in data
    assert isinstance(data["activity"], dict)


def test_sync_device_activity_updates_shared_day_data():
    data = default_data()
    synced = sync_device_activity(data, {
        "date": "2026-10-08",
        "steps": 8500,
        "calories_burned": 420,
    })

    day = get_day_activity(synced, "2026-10-08")
    assert day["steps"] == 8500
    assert day["calories_burned"] == 420


def test_sync_device_activity_uses_latest_snapshot_per_day():
    data = default_data()
    sync_device_activity(data, {"date": "2026-10-08", "steps": 6000, "calories_burned": 300})
    synced = sync_device_activity(data, {"date": "2026-10-08", "steps": 9200, "calories_burned": 540})

    day = get_day_activity(synced, "2026-10-08")
    assert day["steps"] == 9200
    assert day["calories_burned"] == 540
