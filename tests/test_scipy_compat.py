import numpy as np
import pyexpint.backends._scipy_compat as compat


def test_gmres_compat_old_tol_signature(monkeypatch):
    seen = {}
    def fake(A, b, *, tol, atol, restart, **kwargs):
        seen.update(tol=tol, atol=atol, restart=restart)
        return np.asarray(b), 0
    monkeypatch.setattr(compat, "_scipy_gmres", fake)
    monkeypatch.setattr(compat, "_GMRES_USES_RTOL", False)
    x, info = compat.gmres_compat(object(), np.ones(2), rtol=1e-7, atol=0.0, restart=5)
    assert info == 0
    assert seen == {"tol": 1e-7, "atol": 0.0, "restart": 5}
    assert np.all(x == 1)


def test_gmres_compat_new_rtol_signature(monkeypatch):
    seen = {}
    def fake(A, b, *, rtol, atol, restart, **kwargs):
        seen.update(rtol=rtol, atol=atol, restart=restart)
        return np.asarray(b), 0
    monkeypatch.setattr(compat, "_scipy_gmres", fake)
    monkeypatch.setattr(compat, "_GMRES_USES_RTOL", True)
    x, info = compat.gmres_compat(object(), np.ones(2), rtol=2e-8, atol=0.0, restart=6)
    assert info == 0
    assert seen == {"rtol": 2e-8, "atol": 0.0, "restart": 6}
    assert np.all(x == 1)
