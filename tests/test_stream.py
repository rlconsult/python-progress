import io
import sys
import pytest
import progressbar


def test_nowrap():
    # Make sure we definitely unwrap
    for i in range(5):
        progressbar.streams.unwrap(stderr=True, stdout=True)

    stdout = sys.stdout
    stderr = sys.stderr

    progressbar.streams.wrap()

    assert stdout == sys.stdout
    assert stderr == sys.stderr

    progressbar.streams.unwrap()

    assert stdout == sys.stdout
    assert stderr == sys.stderr

    # Make sure we definitely unwrap
    for i in range(5):
        progressbar.streams.unwrap(stderr=True, stdout=True)


def test_wrap():
    # Make sure we definitely unwrap
    for i in range(5):
        progressbar.streams.unwrap(stderr=True, stdout=True)

    stdout = sys.stdout
    stderr = sys.stderr

    progressbar.streams.wrap(stderr=True, stdout=True)

    assert stdout != sys.stdout
    assert stderr != sys.stderr

    # Wrap again
    stdout = sys.stdout
    stderr = sys.stderr

    progressbar.streams.wrap(stderr=True, stdout=True)

    assert stdout == sys.stdout
    assert stderr == sys.stderr

    # Make sure we definitely unwrap
    for i in range(5):
        progressbar.streams.unwrap(stderr=True, stdout=True)


def test_excepthook():
    progressbar.streams.wrap(stderr=True, stdout=True)

    try:
        raise RuntimeError()
    except:
        progressbar.streams.excepthook(sys.exc_type, sys.exc_value,
                                       sys.exc_traceback)

    progressbar.streams.unwrap_excepthook()
    progressbar.streams.unwrap_excepthook()


def test_fd_as_io_stream():
    stream = io.StringIO()
    with progressbar.ProgressBar(fd=stream) as pb:
        for i in range(101):
            pb.update(i)
    stream.close()


@pytest.mark.parametrize('stream', [sys.__stdout__, sys.__stderr__])
def test_fd_as_standard_streams(stream):
    with progressbar.ProgressBar(fd=stream) as pb:
        for i in range(101):
            pb.update(i)