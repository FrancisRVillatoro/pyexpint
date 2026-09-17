import numpy as np
from numpy.testing import assert_allclose
from scipy.sparse import diags, csr_matrix
from scipy.sparse.linalg import LinearOperator

from pyexpint import (
    DenseBackend, DiagonalBackend, KrylovBackend,
    SemilinearProblem, solve_fixed,
    ETD4RK, KROGSTAD, ALL_METHODS,
)
from pyexpint.expressions import phi


def test_krylov_sparse_diagonal_phi_combinations_against_diagonal_backend():
    n = 80
    lam = np.linspace(-12.0, 0.5, n)
    A = diags(lam, format="csr")
    v = np.sin(np.linspace(0.1, 2.0, n))
    h = 0.04

    kctx = KrylovBackend(tol=2e-12, min_dim=8, max_dim=40, check_every=4).bind(A, h)
    dctx = DiagonalBackend().bind(lam, h)

    exprs = [
        phi(0),
        phi(1),
        phi(1) - 3*phi(2) + 4*phi(3),
        phi(1, 0.5) + 0.25*phi(2, 0.5) - 0.125*phi(3, 0.5),
    ]
    for expr in exprs:
        assert_allclose(expr.apply(kctx, v), expr.apply(dctx, v), rtol=2e-10, atol=2e-12)


def test_krylov_linear_operator_against_dense_reference():
    rng = np.random.default_rng(12)
    n = 28
    A = rng.normal(size=(n, n)) / 8.0 - 1.2*np.eye(n)
    v = rng.normal(size=n)
    h = 0.13
    op = LinearOperator(A.shape, matvec=lambda x: A @ x, dtype=A.dtype)

    kb = KrylovBackend(tol=1e-12, min_dim=8, max_dim=28, check_every=4)
    kctx = kb.bind(op, h)
    dctx = DenseBackend().bind(A, h)

    expr = phi(1) - 3*phi(2) + 4*phi(3)
    assert_allclose(expr.apply(kctx, v), expr.apply(dctx, v), rtol=5e-10, atol=5e-12)
    assert kb.stats()["matvecs"] > 0


def test_phi_combination_is_fused_into_one_krylov_projection():
    n = 60
    lam = np.linspace(-4.0, 0.2, n)
    A = diags(lam, format="csr")
    v = np.cos(np.linspace(0.0, 1.0, n))
    kb = KrylovBackend(tol=1e-11, min_dim=8, max_dim=32, check_every=4)
    ctx = kb.bind(A, 0.08)

    expr = phi(1) - 3*phi(2) + 4*phi(3)
    expr.apply(ctx, v)
    st = kb.stats()
    assert st["combination_actions"] == 1
    assert st["phi_terms_requested"] == 3
    assert st["krylov_projections"] == 1
    assert st["matvecs"] <= kb.options.max_dim


def test_all_47_methods_run_matrix_free_and_match_diagonal_reference():
    n = 24
    lam = np.linspace(-2.0, -0.1, n)
    op = LinearOperator((n, n), matvec=lambda x: lam*x, dtype=float)
    y0 = 0.05 + 0.01*np.sin(np.linspace(0, np.pi, n))
    T = 0.35
    h = 0.05

    p_diag = SemilinearProblem(lam, lambda t, y: 0.15*y*y, y0, (0.0, T))
    p_op = SemilinearProblem(op, lambda t, y: 0.15*y*y, y0, (0.0, T))

    for method in ALL_METHODS:
        ref = solve_fixed(p_diag, method, h, DiagonalBackend())
        kb = KrylovBackend(tol=2e-11, min_dim=6, max_dim=24, check_every=3)
        got = solve_fixed(p_op, method, h, kb)
        assert_allclose(got.y[-1], ref.y[-1], rtol=2e-8, atol=2e-10, err_msg=method.name)
        assert got.stats["backend_stats"]["matvecs"] > 0


def test_sparse_nondiagonal_solver_matches_dense_backend():
    n = 18
    main = -2.0*np.ones(n)
    off = 0.35*np.ones(n-1)
    A = diags([off, main, off], [-1,0,1], format="csr")
    Ad = A.toarray()
    y0 = np.linspace(0.02, 0.08, n)
    problem_sparse = SemilinearProblem(A, lambda t,y: 0.1*np.sin(y), y0, (0.0,0.12))
    problem_dense = SemilinearProblem(Ad, lambda t,y: 0.1*np.sin(y), y0, (0.0,0.12))

    kb = KrylovBackend(tol=1e-11, min_dim=6, max_dim=18, check_every=3)
    sol_k = solve_fixed(problem_sparse, ETD4RK, 0.04, kb)
    sol_d = solve_fixed(problem_dense, ETD4RK, 0.04, DenseBackend())
    assert_allclose(sol_k.y[-1], sol_d.y[-1], rtol=5e-9, atol=5e-11)


def test_zero_vector_action_needs_no_matvec():
    A = diags([-1.0, -2.0, -3.0], format="csr")
    kb = KrylovBackend()
    ctx = kb.bind(A, 0.1)
    out = (phi(1) + phi(2)).apply(ctx, np.zeros(3))
    assert_allclose(out, 0.0)
    assert kb.stats()["matvecs"] == 0
    assert kb.stats()["zero_actions"] == 1


def test_general_phi_linear_combination_with_distinct_rhs_vectors():
    rng = np.random.default_rng(44)
    n = 20
    A = rng.normal(size=(n,n))/10 - np.eye(n)
    op = LinearOperator(A.shape, matvec=lambda x: A@x, dtype=float)
    bs = {
        0: rng.normal(size=n),
        1: rng.normal(size=n),
        2: rng.normal(size=n),
        3: rng.normal(size=n),
    }
    h = 0.09
    kb = KrylovBackend(tol=1e-12, min_dim=8, max_dim=24, check_every=4)
    got = kb.bind(op,h).phi_linear_combination_action(bs, scale=1.0)
    dctx = DenseBackend().bind(A,h)
    ref = sum(dctx.phi_action(k,1.0,b) for k,b in bs.items())
    assert_allclose(got, ref, rtol=2e-10, atol=2e-11)
    st = kb.stats()
    assert st["linear_combination_actions"] == 1
    assert st["augmented_krylov_projections"] == 1


def test_eglm_sum_actions_trigger_augmented_fusion():
    n = 32
    lam = np.linspace(-2.0,-0.2,n)
    A = diags(lam, format="csr")
    y0 = 0.05*np.ones(n)
    problem = SemilinearProblem(A, lambda t,y: 0.05*y*y, y0, (0.0,0.1))
    kb = KrylovBackend(tol=1e-10, min_dim=6, max_dim=24, check_every=3)
    solve_fixed(problem, KROGSTAD, 0.05, kb)
    st = kb.stats()
    assert st["fused_sum_actions"] > 0
    assert st["linear_combination_actions"] > 0
