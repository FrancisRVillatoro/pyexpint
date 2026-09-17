from pyexpint import (
    PEC423, PECEC433, EGLM332, EGLM433, GENLAWSON43, MODGENLAWSON43,
)


def test_phase0_order_metadata_is_encoded():
    assert (PEC423.stage_order,PEC423.quadrature_order,PEC423.stiff_order)==(3,4,4)
    assert (PECEC433.stage_order,PECEC433.quadrature_order,PECEC433.stiff_order)==(3,4,4)
    assert (EGLM332.stage_order,EGLM332.quadrature_order,EGLM332.classical_order)==(2,4,3)
    assert (EGLM433.stage_order,EGLM433.quadrature_order,EGLM433.classical_order)==(3,5,4)
    assert (GENLAWSON43.stage_order,GENLAWSON43.quadrature_order,GENLAWSON43.weak_quadrature_order)==(3,3,4)
    assert (MODGENLAWSON43.stage_order,MODGENLAWSON43.quadrature_order)==(3,4)
