import numpy as np
import pandas as pd
import pytest

from pipediff import DiffTracker


@pytest.fixture
def tracker() -> DiffTracker:
    return DiffTracker()


@pytest.fixture
def num_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "float_column": [1.0, 2.0, 3.0],
            "int_column": [1, 2, 3],
        }
    )


def test_default_attributes(tracker: DiffTracker) -> None:
    assert len(tracker.frame_logs) == 0


def test_log_empty_frame_and_access(tracker: DiffTracker) -> None:
    result = tracker.log_frame(pd.DataFrame(), return_result=True)
    fl = tracker.frame_logs

    assert len(fl) == 1
    pd.testing.assert_frame_equal(result, pd.DataFrame())
    pd.testing.assert_frame_equal(result, fl["df_0"])
    assert (
        id(result) == id(fl["df_0"]) == id(fl[0]) == id(fl[-1])
    ), "Different access methods should yield the same result reference!"

    for fl_ in (fl[0:], fl[0:1], fl[0::1], fl[-1:]):
        assert id(result) == id(fl_["df_0"]), "Slice does not contain expected result reference!"


def test_log_frame_with_name(tracker: DiffTracker) -> None:
    tracker.log_frame(pd.DataFrame(), key="my_frame")
    assert tracker.frame_logs.get("my_frame") is not None
    with pytest.raises(KeyError):
        tracker.log_frame(pd.DataFrame(), key="my_frame")


def test_reset_tracker_is_empty(tracker: DiffTracker) -> None:
    tracker.log_frame(pd.DataFrame())
    tracker.reset()
    assert len(tracker.frame_logs) == 0


def test_log_multiple_frames(tracker: DiffTracker) -> None:
    tracker.log_frame(pd.DataFrame())
    tracker.log_frame(pd.DataFrame())

    assert len(tracker.frame_logs) == 2


def test_log_nans() -> None:
    test_df = pd.DataFrame({"nan_column": [None, 2.0, 3.0, np.nan]})

    tracker = DiffTracker()
    tracker.log_frame(test_df, log_nans=True)

    result = tracker.frame_logs[0]
    assert all(result.columns == test_df.columns)
    assert result.loc["nans", "nan_column"] == 2


def test_agg_method_format_options_yield_same_result(tracker: DiffTracker, num_df: pd.DataFrame) -> None:

    for base_func in ["sum", "mean", "max", "min", lambda x: x.quantile(0.2)]:
        results = []
        # Functions can be differently formated, but they should result in a standardised result
        for func in (
            base_func,
            [base_func],
            {c: base_func for c in num_df.columns},
            {c: [base_func] for c in num_df.columns},
        ):
            result = tracker.log_frame(num_df, return_result=True, agg_func=func)
            results.append(result)

        # All results should be equal to the list func version of pandas.DataFrame.agg
        for res in results:
            pd.testing.assert_frame_equal(res, num_df.agg([base_func]))


def test_nans_and_agg(tracker: DiffTracker, num_df: pd.DataFrame) -> None:
    agg_func = ["sum", "mean", "max"]
    result = tracker.log_frame(num_df, log_nans=True, agg_func=agg_func, return_result=True)
    expected = pd.DataFrame(
        data=[[0.0, 0.0], [6.0, 6.0], [2.0, 2.0], [3.0, 3.0]], columns=num_df.columns, index=["nans", *agg_func]
    )
    pd.testing.assert_frame_equal(result, expected)


def test_init_and_function_args_have_same_result(num_df: pd.DataFrame) -> None:
    kwargs = dict(log_nans=True, agg_func="sum", columns=["float_column"])

    tracker = DiffTracker()
    result_1 = tracker.log_frame(num_df, **kwargs, return_result=True)

    tracker = DiffTracker(**kwargs)
    result_2 = tracker.log_frame(num_df, return_result=True)

    pd.testing.assert_frame_equal(result_1, result_2)


def test_column_slicing(num_df: pd.DataFrame) -> None:
    kwargs = dict(log_nans=True, agg_func=["sum", "mean"], columns=["float_column"])

    tracker = DiffTracker(**kwargs)
    result = tracker.log_frame(num_df, return_result=True)

    expected = pd.DataFrame(data=[[0.0], [6.0], [2.0]], columns=kwargs["columns"], index=["nans", *kwargs["agg_func"]])
    pd.testing.assert_frame_equal(result, expected)
