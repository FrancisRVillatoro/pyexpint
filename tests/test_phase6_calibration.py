from pyexpint import SelectorCalibration, fit_threshold_selector


def test_threshold_calibration_finds_size_crossover():
    cases=[]
    for n in [128,256,1024]:
        for w in [10.0,40.0]:
            if n < 1000:
                kt,lt=1.0,2.0
            else:
                kt,lt=2.0,1.0
            cases.append(dict(n=n,scaled_spectral_width=w,kiops_seconds=kt,leja_seconds=lt))
    c=fit_threshold_selector(cases,machine_label='unit-test')
    assert c.leja_min_size == 1024
    assert c.training_cases == 6
    assert c.max_slowdown == 1.0
