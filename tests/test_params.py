from coldchain import params as P


def test_placeholders_block_publication():
    raised = False
    try:
        P.assert_publishable()
    except P.PlaceholderError:
        raised = True
    assert raised and "ea_kj_mol" in P.placeholders()


def test_every_param_has_valid_status_and_a_source_string():
    ok = {P.SOURCED, P.ANCHORED, P.ASSUMED, P.PLACEHOLDER}
    assert all(p.status in ok and isinstance(p.source, str) for p in P.PARAMS.values())
