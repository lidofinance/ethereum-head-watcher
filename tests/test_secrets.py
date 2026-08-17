import json
import os

import pytest

from src.secrets import SecretsWatcher, read_secrets_file


@pytest.fixture
def secrets_path(tmp_path):
    return str(tmp_path / 'config')


def write(path: str, values: dict, mtime_ns: int | None = None):
    """
    Writes the way the OpenBao agent does — a temp file renamed over the path, which is what makes
    the inode change on every rotation.
    """
    temp = f'{path}.tmp'
    with open(temp, 'w') as file:
        json.dump(values, file)
    os.replace(temp, path)
    if mtime_ns is not None:
        os.utime(path, ns=(mtime_ns, mtime_ns))


def test_absent_file_reads_as_empty(secrets_path):
    # The VM deployment has no agent and no file; every setting comes from the environment there.
    assert read_secrets_file(secrets_path) == {}


def test_unparseable_file_reads_as_empty(secrets_path):
    with open(secrets_path, 'w') as file:
        file.write('{not json')

    # Not an exception: refusing to start would turn a bad render of one key into an outage.
    assert read_secrets_file(secrets_path) == {}


def test_values_are_read_as_strings(secrets_path):
    write(secrets_path, {'CONSENSUS_CLIENT_URI': 'https://cl', 'CL_REQUEST_TIMEOUT': 180})

    assert read_secrets_file(secrets_path) == {
        'CONSENSUS_CLIENT_URI': 'https://cl',
        'CL_REQUEST_TIMEOUT': '180',
    }


def test_no_change_is_not_reported(secrets_path):
    write(secrets_path, {'CONSENSUS_CLIENT_URI': 'https://cl'})
    seen = []
    watcher = SecretsWatcher(secrets_path, on_change=seen.append)

    assert watcher.check_once() is False
    assert not seen


def test_rotation_is_picked_up_across_the_rename(secrets_path):
    # The rename creates a new inode, which is why the watcher polls the path. A watcher holding
    # the file itself would go silent here — this is the regression that matters.
    write(secrets_path, {'CONSENSUS_CLIENT_URI': 'https://old'}, mtime_ns=1_000_000_000)
    seen = []
    watcher = SecretsWatcher(secrets_path, on_change=seen.append)

    write(secrets_path, {'CONSENSUS_CLIENT_URI': 'https://new'}, mtime_ns=2_000_000_000)

    assert watcher.check_once() is True
    assert seen == [{'CONSENSUS_CLIENT_URI': 'https://new'}]


def test_a_rotation_that_renders_to_nothing_is_not_applied(secrets_path):
    write(secrets_path, {'CONSENSUS_CLIENT_URI': 'https://old'}, mtime_ns=1_000_000_000)
    seen, errors = [], []
    watcher = SecretsWatcher(secrets_path, on_change=seen.append, on_error=lambda: errors.append(1))

    with open(secrets_path, 'w') as file:
        file.write('')
    os.utime(secrets_path, ns=(2_000_000_000, 2_000_000_000))

    assert watcher.check_once() is False
    assert not seen
    assert errors == [1]


def test_a_failing_callback_leaves_the_previous_values_in_place(secrets_path):
    write(secrets_path, {'CONSENSUS_CLIENT_URI': 'https://old'}, mtime_ns=1_000_000_000)
    errors = []

    def explode(_values):
        raise RuntimeError('nope')

    watcher = SecretsWatcher(secrets_path, on_change=explode, on_error=lambda: errors.append(1))

    write(secrets_path, {'CONSENSUS_CLIENT_URI': 'https://new'}, mtime_ns=2_000_000_000)

    # The exception does not escape the poll loop: a broken callback must not kill the thread.
    assert watcher.check_once() is False
    assert errors == [1]


def test_a_bad_rotation_is_not_retried_forever(secrets_path):
    write(secrets_path, {'CONSENSUS_CLIENT_URI': 'https://old'}, mtime_ns=1_000_000_000)
    errors = []

    def explode(_values):
        raise RuntimeError('nope')

    watcher = SecretsWatcher(secrets_path, on_change=explode, on_error=lambda: errors.append(1))
    write(secrets_path, {'CONSENSUS_CLIENT_URI': 'https://new'}, mtime_ns=2_000_000_000)

    watcher.check_once()
    watcher.check_once()

    # One error per rotation, not one per poll: the mtime is recorded even when applying failed,
    # so a file that cannot be applied does not produce a line every interval forever.
    assert errors == [1]
