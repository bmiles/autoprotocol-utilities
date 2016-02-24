import pytest
from autoprotocol import Protocol
from autoprotocol.container import Well
from autoprotocol.unit import Unit
from autoprotocol_utilities.modules import createMastermix, autoseal


class TestCreateMastermix:
    p = Protocol()
    c = p.ref("testtube", id=None, cont_type="micro-1.5", discard=True)
    w = c.well(0)
    w.set_volume("1300:microliter")
    c2 = p.ref("testtube2", id=None, cont_type="micro-1.5", discard=True)
    w2 = c2.well(0)
    w2.set_volume("1300:microliter")

    @pytest.mark.parametrize("name, cont, rxt, res, om", [
        (1, "micro-1.5", 2, {"rs234": 4}, {w: 4}),
        ("myname1", 1, 2, {"rs234": 4}, {w: 4}),
        ("myname2", "micro-1.5", "str", {"rs234": 4}, {w: 4}),
        ("myname3", "micro-1.5", 2, {"234": 4}, {w: 4}),
        ("myname4", "micro-1.5", 2, {"rs234": "str"}, {w: 4}),
        ("myname5", "micro-1.5", 2, {"rs234": 4}, {"str": 4}),
        ("myname6", "micro-1.5", 2, {"234": 4}, {w: "str"}),
        ("myname7", "micro-1.5", 1, {"rs234": 2300}, {w: "str"})
    ])
    def test_wrong_input_types(self, name, cont, rxt, res, om):
        with pytest.raises(Exception):
            createMastermix(self.p, name, cont, rxt, res, om)

    @pytest.mark.parametrize(
        "i, res, om, use_dead_vol, use_safe_vol, ""mm_mult, r", [
            (0, {"rs123": 1}, {w: 1}, False, False, 1, 2),
            (1, {"rs123": 1}, {w: 1}, True, False, 1, 17),
            (2, {"rs123": 1}, {w: 1}, False, True, 1, 22),
            (3, {"rs123": 1}, {w: 1}, False, False, 2, 4),
            (4, {"rs123": 1}, {w: 1}, True, False, 2, 19),
            (5, {"rs123": 3}, {w: 1}, False, False, 2, 8),
            (6, {"rs123": 3}, {}, False, False, 2, 6),
            (7, {"rs123": 3}, {}, True, False, 2, 21),
            (8, {"rs123": 3, "rs1234": 2}, {}, True, False, 1, 20),
            (9, {}, {w: 2, w2: 2.5}, True, False, 1, 19.5),
            (10, {"rs123": 1000}, {}, False, False, 1.3, 1300),
            (11, {"rs123": Unit(1000, "microliter")}, {}, False,
             False, 1.3, 1300)
        ])
    def test_single_well(self, i, res, om, use_dead_vol, use_safe_vol,
                         mm_mult, r):
        mm = createMastermix(self.p, "single_well_test%s" % i, "micro-1.5",
                             1, res, om, mm_mult=mm_mult,
                             use_dead_vol=use_dead_vol,
                             use_safe_vol=use_safe_vol)
        assert isinstance(mm, list)
        assert isinstance(mm[0], Well)
        assert mm[0].volume.value == r

    @pytest.mark.parametrize("i, rxt, res, om, use_dead_vol, mm_mult, r", [
        (0, 10, {"rs123": 5, "rs1234": 5}, {}, False, 2, [145, 65]),
        (1, 10, {"rs123": 5, "rs1234": 5}, {}, True, 2, [148, 68]),
        (2, 10, {"rs123": Unit(5, "microliter"), "rs1234": 5}, {}, True,
         2, [148, 68]),
        (3, 2, {"rs123": Unit(5, "microliter"), "rs1234": 5},
         {w2: Unit(5, "microliter")}, True, 2, [68.01])
    ])
    def test_multiple_wells(self, i, rxt, res, om, use_dead_vol, mm_mult, r):
        print om
        mm = createMastermix(self.p, "multi_well_test%s" % i, "96-pcr",
                             rxt, res, om, mm_mult=mm_mult,
                             use_dead_vol=use_dead_vol)
        assert isinstance(mm, list)
        for i, x in enumerate(mm):
            assert isinstance(x, Well)
            assert x.volume.value == r[i]


class TestSeal:
    p = Protocol()

    def test_seal_fail(self):
        with pytest.raises(Exception):
            autoseal(self.p, "mywell")
