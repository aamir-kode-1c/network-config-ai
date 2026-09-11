from app.core.observability import increment, metric_value, start_trace


def test_metrics_are_labeled_and_trace_ids_are_available():
    trace_id = start_trace("trace-test")
    increment("deployment_test_total", {"status": "success"})
    assert trace_id == "trace-test"
    assert metric_value("deployment_test_total", {"status": "success"}) == 1
