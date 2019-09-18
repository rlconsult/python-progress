import time
import pytest

import examples
import progressbar
import original_examples


def test_examples(monkeypatch):
    for example in examples.examples:
        try:
            example()
        except ValueError:
            pass


@pytest.mark.parametrize('example', original_examples.examples)
def test_original_examples(example, monkeypatch):
    monkeypatch.setattr(progressbar.ProgressBar,
                        '_MINIMUM_UPDATE_INTERVAL', 1)
    monkeypatch.setattr(time, 'sleep', lambda t: None)
    example()


def test_examples_nullbar(monkeypatch):
    # Patch progressbar to use null bar instead of regular progress bar
    monkeypatch.setattr(progressbar, 'ProgressBar', progressbar.NullBar)

    assert progressbar.ProgressBar._MINIMUM_UPDATE_INTERVAL < 0.0001
    for example in examples.examples:
        example()


def test_reuse():
    import progressbar

    bar = progressbar.ProgressBar()
    bar.start()
    for i in range(10):
        bar.update(i)
    bar.finish()

    bar.start(init=True)
    for i in range(10):
        bar.update(i)
    bar.finish()

    bar.start(init=False)
    for i in range(10):
        bar.update(i)
    bar.finish()


def test_dirty():
    import progressbar

    bar = progressbar.ProgressBar()
    bar.start()
    for i in range(10):
        bar.update(i)
    bar.finish(dirty=True)
