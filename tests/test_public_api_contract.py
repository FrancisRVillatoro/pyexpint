import pyexpint


STABLE_API_09 = {
    "SemilinearProblem",
    "Solution",
    "ExternalState",
    "MethodSpec",
    "get_method",
    "list_methods",
    "ALL_METHODS",
    "solve_fixed",
    "step_external",
    "AdaptiveOptions",
    "solve_adaptive",
    "ETD34Options",
    "solve_etd34",
    "ExactStartup",
    "OneStepStartup",
    "ZERO",
    "I",
    "phi",
    "resolvent",
    "DenseBackend",
    "DiagonalBackend",
    "KrylovBackend",
    "KrylovOptions",
    "KrylovConvergenceError",
    "KiopsBackend",
    "KiopsOptions",
    "KiopsConvergenceError",
    "LejaBackend",
    "LejaOptions",
    "LejaConvergenceError",
    "ScipyKiopsBackend",
    "AutoBackend",
    "SelectorCalibration",
    "fit_threshold_selector",
    "CalibratedAutoBackend",
    "estimated_backend_workspace_bytes",
}


def test_public_all_has_no_duplicate_names():
    assert len(pyexpint.__all__) == len(set(pyexpint.__all__))


def test_stable_09_api_is_exported_and_bound():
    exported = set(pyexpint.__all__)

    missing_exports = STABLE_API_09 - exported
    missing_attributes = {
        name
        for name in STABLE_API_09
        if not hasattr(pyexpint, name)
    }

    assert not missing_exports
    assert not missing_attributes


def test_method_catalogue_has_stable_lookup_contract():
    names = pyexpint.list_methods()

    assert names
    assert len(names) == len(set(names))

    for name in names:
        method = pyexpint.get_method(name)
        assert isinstance(method, pyexpint.MethodSpec)
        assert method.name == name
