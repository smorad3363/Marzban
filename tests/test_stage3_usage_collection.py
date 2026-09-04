from app.jobs.record_usages import aggregate_user_usages


def test_usage_only_on_second_node_is_accounted():
    result = aggregate_user_usages(
        {None: [], 2: [{"uid": 7, "value": 125}]},
        {None: 1, 2: 1},
    )
    assert result == [{"uid": 7, "value": 125}]


def test_usage_from_master_and_two_nodes_is_summed_once_per_user():
    result = aggregate_user_usages(
        {
            None: [{"uid": 7, "value": 100}],
            2: [{"uid": 7, "value": 50}],
            3: [{"uid": 7, "value": 25}, {"uid": 9, "value": 40}],
        },
        {None: 1, 2: 2, 3: 1},
    )
    assert sorted(result, key=lambda item: item["uid"]) == [
        {"uid": 7, "value": 225},
        {"uid": 9, "value": 40},
    ]
