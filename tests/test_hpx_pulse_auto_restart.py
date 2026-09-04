from app.jobs.hpx_pulse_auto_restart import hpx_pulse_auto_restart_job
from app.models.hpx_pulse import HpxPulseCreate, HpxPulseUpdate


def test_auto_restart_interval_accepts_zero_as_off():
    create = HpxPulseCreate(
        name="pulse_test",
        iran_public_ip="1.1.1.1",
        abroad_public_ip="2.2.2.2",
        auto_restart_interval_minutes=0,
    )
    assert create.auto_restart_interval_minutes == 0

    update = HpxPulseUpdate(auto_restart_interval_minutes=60)
    assert update.auto_restart_interval_minutes == 60


def test_hpx_pulse_auto_restart_job_is_callable():
    assert callable(hpx_pulse_auto_restart_job)
