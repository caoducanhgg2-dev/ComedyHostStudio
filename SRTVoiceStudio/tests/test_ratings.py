import pytest
from studio.ratings import WEIGHTS, read_csv, score


def test_scores_require_listening_and_finite_complete_values():
    assert score(None) is None and score({}) is None
    record = dict(scores=dict.fromkeys(WEIGHTS, 8), reviewer='Listener', method='user_listening')
    assert score(record) == 8
    record['scores']['naturalness'] = 10
    assert score(record) == 8.7
    record['scores']['pronunciation'] = float('nan')
    assert score(record) is None


def test_csv_blank_unknown_duplicate_and_partial(tmp_path):
    path = tmp_path/'ratings.csv'
    header = 'voice,' + ','.join(WEIGHTS) + ',reviewer,notes\n'
    path.write_text(header + 'af_heart,,,,,,,,\nam_michael,8,9,8,9,8,7,Listener,Heard both clips\n')
    records = read_csv(path, {'af_heart', 'am_michael'})
    assert set(records) == {'am_michael'}
    assert score(records['am_michael']) == 8.3
    for body in ('unknown,8,8,8,8,8,8,Listener,\n',
                 'af_heart,8,,,,,,Listener,\n',
                 'af_heart,,,,,,,,\naf_heart,,,,,,,,\n'):
        path.write_text(header + body)
        with pytest.raises(ValueError): read_csv(path, {'af_heart'})
