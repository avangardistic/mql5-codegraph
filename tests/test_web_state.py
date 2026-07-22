from pathlib import Path
from threading import Event
from time import monotonic, sleep
from unittest import TestCase

from mql5_codegraph.graph import CodeGraph
from mql5_codegraph.web.state import DashboardState


FIXTURE = Path(__file__).parent / "fixtures" / "basic_ea"


def wait_for_job(state: DashboardState, job_id: str, timeout: float = 3.0):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        job = state.get_job(job_id)
        if job and job.status in {"completed", "failed"}:
            return job
        sleep(0.01)
    raise AssertionError("analysis job did not finish")


class DashboardStateTests(TestCase):
    def test_analysis_replaces_graph_atomically(self) -> None:
        state = DashboardState()
        job = state.start_analysis(FIXTURE)
        finished = wait_for_job(state, job.id)
        graph, root, version = state.snapshot()
        self.assertEqual("completed", finished.status)
        self.assertIsNotNone(graph)
        self.assertEqual(FIXTURE.resolve(), root)
        self.assertEqual(1, version)
        self.assertTrue(state.status()["ready"])

    def test_only_one_analysis_runs_at_a_time(self) -> None:
        release = Event()

        def slow_analyzer(root, includes):
            release.wait(2)
            return CodeGraph({"file_count": 0})

        state = DashboardState(analyzer=slow_analyzer)
        first = state.start_analysis(FIXTURE)
        with self.assertRaisesRegex(RuntimeError, "already running"):
            state.start_analysis(FIXTURE)
        release.set()
        self.assertEqual("completed", wait_for_job(state, first.id).status)

    def test_failed_reindex_keeps_previous_graph(self) -> None:
        calls = 0

        def analyzer(root, includes):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise ValueError("synthetic failure")
            return CodeGraph({"file_count": 1})

        state = DashboardState(analyzer=analyzer)
        wait_for_job(state, state.start_analysis(FIXTURE).id)
        original, _, version = state.snapshot()
        failed = wait_for_job(state, state.start_analysis(FIXTURE).id)
        current, _, current_version = state.snapshot()
        self.assertEqual("failed", failed.status)
        self.assertIs(original, current)
        self.assertEqual(version, current_version)
        self.assertEqual("synthetic failure", state.status()["last_error"])
