from src.services.items._batch_ids import as_id_list


def test_as_id_list_none_becomes_empty_list():
    assert as_id_list(None) == []


def test_as_id_list_wraps_scalar_ids():
    assert as_id_list(123) == [123]
    assert as_id_list("abc") == ["abc"]


def test_as_id_list_materializes_iterables():
    assert as_id_list([1, 2]) == [1, 2]
    assert as_id_list((1, 2)) == [1, 2]
    assert as_id_list(i for i in [1, 2]) == [1, 2]
