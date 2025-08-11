from app.core.job_manager import JobManager


def test_take_top_k_points_bullets():
    jm = JobManager()
    text = "- a\n- b\n- c\n- d"
    top2 = jm._take_top_k_points(text, 2)
    assert top2.strip().splitlines() == ["- a", "- b"]


def test_take_top_k_points_json_array():
    jm = JobManager()
    text = "Here is result: [\"x\", \"y\", \"z\"] end"
    top1 = jm._take_top_k_points(text, 1)
    assert top1.strip() == "- x"


