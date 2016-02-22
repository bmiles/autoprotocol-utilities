import pytest
from random import sample
from autoprotocol import Protocol
from autoprotocol.container import Well, WellGroup, Container
from autoprotocol_utilities.container_helpers import list_of_filled_wells, first_empty_well, unique_containers, sort_well_group, stamp_shape, is_columnwise, volume_check, set_pipettable_volume, well_name
from autoprotocol_utilities.misc_helpers import make_list, flatten_list, char_limit, recursive_search


class TestContainerfunctions:
    p = Protocol()
    c = p.ref("testplate_pcr", id=None, cont_type="96-pcr", discard=True)
    c.wells_from(0, 30).set_volume("20:microliter")
    ws = c.wells_from(0, 8)
    w = c.well(0)

    @pytest.mark.parametrize("func, arg", [
        (list_of_filled_wells, w),
        (first_empty_well, w),
        (unique_containers, c),
        (sort_well_group, c),
        (stamp_shape, w),
        (is_columnwise, c),
        (volume_check, ws),
        (volume_check, c),
        (well_name, c),
        (well_name, ws)
        ])
    def test_asserts(self, func, arg):
        with pytest.raises(Exception):
            func(arg)

    def test_filled_wells(self):
        assert len(list_of_filled_wells(self.c)) == 30
        assert len(list_of_filled_wells(self.c, empty=True)) == 66
        assert isinstance(list_of_filled_wells(self.c)[0], Well)
        assert len(list_of_filled_wells(self.ws)) == 8
        assert len(list_of_filled_wells(self.ws, empty=True)) == 0

    def test_first_empty_well(self):
        assert first_empty_well(self.c) == 30
        assert first_empty_well(self.c, return_index=False).index == 30
        self.c.all_wells().set_volume("20:microliter")
        assert not first_empty_well(self.c)
        assert not first_empty_well(self.ws)

    def test_unique_containers(self):
        wells = self.ws
        assert len(unique_containers(wells)) == 1
        for i in range(4):
            cont = self.p.ref("unique%s" % i, id=None,
                              cont_type="micro-1.5", discard=True)
            wells.append(cont.well(0))
        assert len(unique_containers(wells)) == 5

    def test_sort_well_group(self):
        wells = self.c.all_wells()
        random_wells = sample(wells, len(wells))
        assert list(random_wells) != list(wells)
        assert list(sort_well_group(random_wells)) == list(wells)

    @pytest.mark.parametrize("wells, full, r", [
        (c.wells_from(0, 16, columnwise=True), False,
         [0, {"rows": 8, "columns": 2}, []]),
        (c.wells_from(0, 16), False, [0, {"rows": 1, "columns": 12},
         [12, 13, 14, 15]]),
        (c.wells(0, 1, 2, 3, 95, 94, 93, 92, 91, 83, 82, 81, 80, 79), False,
         [79, {"rows": 2, "columns": 5}, [0, 1, 2, 3]]),
        (c.wells(0, 1, 2, 3, 95, 94, 93, 92, 91, 83, 82, 81, 80, 79), True,
         [79, {"rows": 0, "columns": 0},
         [0, 1, 2, 3, 79, 80, 81, 82, 83, 91, 92, 93, 94, 95]])
    ])
    def test_shape(self, wells, full, r):
        res = stamp_shape(wells, full)
        assert res.start_well == r[0]
        assert res.shape == r[1]
        if len(r[2]) == 0:
            assert len(res.remaining_wells) == len(r[2])
        else:
            for i, well in enumerate(res.remaining_wells):
                assert well.index == r[2][i]

    @pytest.mark.parametrize("len_wells, columnwise, r", [
        (8, True, True),
        (8, False, False),
        (17, True, True)
    ])
    def test_is_columnwise(self, len_wells, columnwise, r):
        wells = self.c.wells_from(0, len_wells, columnwise=columnwise)
        assert is_columnwise(wells) is r

    def test_is_columnwise_uneven(self):
        wells = self.c.wells_from(0, 8, columnwise=True)
        wells.append(self.c.well(14))
        assert is_columnwise(wells) is False

    def test_set_pipettable_volume(self):
        old_vol = 20
        new_well = set_pipettable_volume(self.c.well(95))
        assert isinstance(new_well, Well)
        assert new_well.volume.value == old_vol - 3
        new_well = set_pipettable_volume(self.c.well(45), use_safe_vol=True)
        assert isinstance(new_well, Well)
        assert new_well.volume.value == old_vol - 5
        new_well = set_pipettable_volume(self.c.wells_from(90, 4))
        assert isinstance(new_well, WellGroup)
        for well in new_well:
            assert well.volume.value == old_vol - 3
        self.c.all_wells().set_volume("20:microliter")
        new_well = set_pipettable_volume(self.c)
        assert isinstance(new_well, Container)
        for well in new_well.all_wells():
            assert well.volume.value == old_vol - 3

    def test_volume_check(self):
        self.c.all_wells().set_volume("20:microliter")
        self.c.wells_from(15, 10).set_volume("2:microliter")
        self.c.wells_from(25, 5).set_volume("1:microliter")
        self.c.wells_from(30, 15).set_volume("4:microliter")
        assert volume_check(self.c.well(0), 1) is None
        assert volume_check(self.c.well(0), 18) is not None
        assert volume_check(self.c.well(15), 0) is not None
        assert volume_check(self.c.well(16), 0,
                            use_safe_dead_diff=True) is None
        assert volume_check(self.c.well(25), 0,
                            use_safe_vol=True) is not None

    def test_well_name(self):
        assert well_name(self.c.well(0)) == "testplate_pcr-0"
        assert well_name(self.c.well(0), 'pytest') == "pytest-0"
        self.c.well(0).set_name("mywell")
        assert well_name(self.c.well(0)) == "mywell"


class TestDataformattingfunctions:
    def test_make_list(self):
        s = "1,2,3,4"
        r1 = [1, 2, 3, 4]
        r2 = ["1", "2", "3", "4"]
        assert make_list(s) == r2
        assert make_list(s, integer=True) == r1

    def test_flatten_list(self):
        l = [[1, 2], [3, 4], [[5, 6], [[7, 8], [9, 10], 11], 12], 13]
        assert flatten_list(l) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

    @pytest.mark.parametrize("string, length, trunc, clip, r", [
        ('ILoveThis', 6, False, False, ['ILoveThis', 'The specified label']),
        ('ILoveThis', 6, False, True, ['veThis', None]),
        ('ILoveThis', 6, True, False, ['ILoveT', None]),
        ('ILoveThis', 6, True, True, ['ILoveT', None])
    ])
    def test_char_limit(self, string, length, trunc, clip, r):
        res = char_limit(string, length=length, trunc=trunc, clip=clip)
        print res
        assert res.label == r[0]
        if not r[1]:
            assert res.error_message == r[1]
        else:
            assert r[1] in res.error_message


class TestRecursiveParams:
    protocol = Protocol()
    c1 = protocol.ref("plate", None, "96-pcr", discard=True)
    w = c1.well(45).set_volume("50:microliter")
    well_list = [{"hidden_well": w}]
    well_dict = {"hidden_well": [w]}
    for i in range(10):
        w = c1.well(i)
        w.set_volume("100:microliter")
        well_list.append(w)
        well_dict["well_%s" % i] = w
    well_list = {"well_list": well_list}
    some_fields = ["1", "2", 3, 4]

    @pytest.mark.parametrize("params, cl, method, args, expected", [
        (well_list, Well, volume_check, {'usage_volume': 45}, 0),
        (well_dict, Well, volume_check, {'usage_volume': 75}, 1)
    ])
    def test_recursive_search_vol_check(self, params, cl, method,
                                        args, expected):
        assert len(recursive_search(params, cl,
                                    volume_check, args)) == expected

    @pytest.mark.parametrize("params, cl, expected", [
        (well_list, Well, 11),
        (well_dict, None, 22),
        (some_fields, None, 4)
    ])
    def test_recursive_search_instance(self, params, cl, expected):
        assert len(recursive_search(params, cl)) == expected
