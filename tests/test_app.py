from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_local_app_calculates_and_invalidates():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=90).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "1 · Load data",
        "2 · Explore triangles",
        "3 · Calculate ultimate",
    ]
    assert any(r.label == "Triangle view" and r.value == "Development factors" for r in app.radio)
    calculate = next(b for b in app.button if b.label == "Calculate analysis")
    calculate.click().run()
    assert not app.exception
    assert any(m.label == "Origins selected" for m in app.metric)
    next(n for n in app.number_input if n.label == "Annual severity trend (%)").set_value(3.0).run()
    assert not app.exception
    assert any("changed" in w.value for w in app.warning)
