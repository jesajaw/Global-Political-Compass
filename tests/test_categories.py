"""Category -> axis aggregation math (data/categories.py)."""

from ._helpers import fresh_store   # only for the sys.path setup


def run() -> None:
    from data.categories import CATEGORIES, axes_from_categories

    assert len(CATEGORIES) == 10

    scores = {c.id: 5 for c in CATEGORIES}    # +5 on every category
    lr, la = axes_from_categories(scores)
    # LR categories (economy, taxation, social_policy, state_ownership) all weight +1 -> mean 5 *10 = 50
    assert lr == 50.0, lr
    # LA categories: migration(+1), civil_liberties(-1), law_and_order(+1), nationalism(+1)
    # mean of (5, -5, 5, 5)/4 *10 = 25
    assert la == 25.0, la

    # a partial breakdown still produces a reasonable mean (missing categories excluded, not zeroed)
    lr2, la2 = axes_from_categories({"economy": 10})
    assert lr2 == 100.0 and la2 == 0.0

    # a category with no axis weight (environment, foreign_policy) never moves either axis
    lr3, la3 = axes_from_categories({"environment": 10, "foreign_policy": -10})
    assert lr3 == 0.0 and la3 == 0.0

    print("test_categories: OK")


if __name__ == "__main__":
    run()
