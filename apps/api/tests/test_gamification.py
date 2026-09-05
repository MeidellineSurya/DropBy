import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.drops import DropRarity
from app.models.gamification import Badge, BadgeCriteriaType, PerkType, PowerupType, UserPerk
from app.services.gamification import (
    BASE_POWERUP_CAP,
    EXTRA_POWERUP_SLOT_BONUS,
    MILESTONE_LEVEL_INTERVAL,
    POWERUP_TYPES,
    SPECIALIZATION_PERK_BONUS_PCT,
    STREAK_BONUS_CAP_PCT,
    STREAK_BONUS_PCT_PER_DAY,
    TIME_SPECIALIZATION_BONUS_PCT,
    WEEKLY_CHALLENGE_CATEGORIES,
    XP_PER_LEVEL,
    apply_double_or_nothing,
    apply_xp_boost,
    approximate_utc_offset_hours,
    badge_is_satisfied,
    badge_xp_bonus_pct,
    current_challenge_category,
    level_for_xp,
    local_hour_for,
    location_cell_for,
    pending_perk_choices_count,
    powerup_cap,
    roll_powerup_count,
    roll_powerup_type,
    specialization_bonus_pct,
    squad_bonus_for,
    streak_bonus_pct,
    time_bucket_for_hour,
    time_specialization_bonus_pct,
    week_key_for,
    xp_for_rarity,
)


@pytest.mark.parametrize(
    ("rarity", "base", "expected"),
    [
        (DropRarity.common, 10, 10),
        (DropRarity.uncommon, 10, 15),
        (DropRarity.rare, 10, 20),
        (DropRarity.epic, 10, 30),
        (DropRarity.legendary, 10, 50),
        ("legendary", 10, 50),
    ],
)
def test_xp_for_rarity_applies_the_rarity_multiplier(rarity, base, expected) -> None:
    assert xp_for_rarity(base, rarity) == expected


def test_squad_bonus_is_zero_for_solo_drops() -> None:
    assert squad_bonus_for(100, member_count=1) == 0


def test_squad_bonus_applies_for_group_drops() -> None:
    assert squad_bonus_for(250, member_count=4) == 75


@pytest.mark.parametrize(
    ("xp_total", "expected_level"),
    [(0, 1), (499, 1), (500, 2), (999, 2), (1000, 3)],
)
def test_level_for_xp_steps_every_500_xp(xp_total, expected_level) -> None:
    assert level_for_xp(xp_total) == expected_level


@pytest.mark.parametrize(
    ("xp_total", "expected_into_level"),
    [(0, 0), (26, 26), (499, 499), (500, 0), (526, 26), (1000, 0)],
)
def test_xp_into_level_wraps_at_each_level_boundary(xp_total, expected_into_level) -> None:
    assert xp_total % XP_PER_LEVEL == expected_into_level


def _badge(criteria_type: BadgeCriteriaType, criteria_config: dict) -> Badge:
    return Badge(
        id=uuid.uuid4(),
        code="test-badge",
        name="Test Badge",
        criteria_type=criteria_type,
        criteria_config=criteria_config,
    )


def test_drop_count_badge_unlocks_at_threshold() -> None:
    badge = _badge(BadgeCriteriaType.drop_count, {"count": 10})
    stats = {"total_drops_completed": 9, "rarity_counts": {}, "category_counts": {}, "cities_explored": {}, "squad_leader_count": 0}

    assert badge_is_satisfied(badge, stats) is False
    stats["total_drops_completed"] = 10
    assert badge_is_satisfied(badge, stats) is True


def test_rarity_collected_badge_checks_the_configured_rarity() -> None:
    badge = _badge(BadgeCriteriaType.rarity_collected, {"rarity": "legendary", "count": 1})
    stats = {"total_drops_completed": 5, "rarity_counts": {"rare": 5}, "category_counts": {}, "cities_explored": {}, "squad_leader_count": 0}

    assert badge_is_satisfied(badge, stats) is False
    stats["rarity_counts"]["legendary"] = 1
    assert badge_is_satisfied(badge, stats) is True


def test_category_explored_badge_checks_the_configured_category() -> None:
    badge = _badge(BadgeCriteriaType.category_explored, {"category": "food_dining", "count": 5})
    stats = {"total_drops_completed": 5, "rarity_counts": {}, "category_counts": {"food_dining": 4}, "cities_explored": {}, "squad_leader_count": 0}

    assert badge_is_satisfied(badge, stats) is False
    stats["category_counts"]["food_dining"] = 5
    assert badge_is_satisfied(badge, stats) is True


def test_city_progress_badge_counts_distinct_locations() -> None:
    badge = _badge(BadgeCriteriaType.city_progress, {"count": 3})
    stats = {"total_drops_completed": 3, "rarity_counts": {}, "category_counts": {}, "cities_explored": {"a": 1, "b": 2}, "squad_leader_count": 0}

    assert badge_is_satisfied(badge, stats) is False
    stats["cities_explored"]["c"] = 1
    assert badge_is_satisfied(badge, stats) is True


def test_squad_leader_count_badge_checks_leadership_count() -> None:
    badge = _badge(BadgeCriteriaType.squad_leader_count, {"count": 5})
    stats = {"total_drops_completed": 5, "rarity_counts": {}, "category_counts": {}, "cities_explored": {}, "squad_leader_count": 4}

    assert badge_is_satisfied(badge, stats) is False
    stats["squad_leader_count"] = 5
    assert badge_is_satisfied(badge, stats) is True


@pytest.mark.parametrize("rarity", [DropRarity.common, DropRarity.uncommon])
def test_common_and_uncommon_never_grant_a_powerup(rarity) -> None:
    assert roll_powerup_count(rarity, rng=lambda: 0.0) == 0


def test_rare_grants_a_powerup_only_below_its_50_percent_chance() -> None:
    assert roll_powerup_count(DropRarity.rare, rng=lambda: 0.49) == 1
    assert roll_powerup_count(DropRarity.rare, rng=lambda: 0.51) == 0


def test_epic_grants_a_powerup_only_below_its_75_percent_chance() -> None:
    assert roll_powerup_count(DropRarity.epic, rng=lambda: 0.74) == 1
    assert roll_powerup_count(DropRarity.epic, rng=lambda: 0.76) == 0


def test_legendary_always_grants_at_least_one_powerup() -> None:
    assert roll_powerup_count(DropRarity.legendary, rng=lambda: 0.999) == 1


def test_legendary_occasionally_grants_a_second_powerup() -> None:
    # First roll (guaranteed grant) and second roll (bonus chance) both need
    # to land under their thresholds — a constant-0.0 rng always does.
    assert roll_powerup_count(DropRarity.legendary, rng=lambda: 0.0) == 2


def test_roll_powerup_type_covers_every_type_across_its_range() -> None:
    step = 1 / len(POWERUP_TYPES)
    seen = {roll_powerup_type(rng=lambda i=i: i * step + 0.001) for i in range(len(POWERUP_TYPES))}
    assert seen == set(POWERUP_TYPES)


def test_xp_boost_applies_the_1_5x_multiplier() -> None:
    assert apply_xp_boost(20) == 30


def test_double_or_nothing_doubles_xp_on_success() -> None:
    assert apply_double_or_nothing(26, made_it=True) == 52


def test_double_or_nothing_zeroes_xp_on_failure() -> None:
    assert apply_double_or_nothing(26, made_it=False) == 0


def test_extra_slot_powerup_type_exists() -> None:
    assert PowerupType.extra_slot in POWERUP_TYPES


def _bonus_badge(pct: float, category: str | None) -> Badge:
    return Badge(
        id=uuid.uuid4(), code=f"bonus-{uuid.uuid4()}", name="Bonus Badge",
        criteria_type=BadgeCriteriaType.drop_count, criteria_config={},
        xp_bonus_pct=pct, xp_bonus_category=category,
    )


def test_badge_bonus_with_no_category_applies_to_every_drop() -> None:
    badges = [_bonus_badge(0.01, None)]
    assert badge_xp_bonus_pct(badges, "food_dining") == pytest.approx(0.01)
    assert badge_xp_bonus_pct(badges, "nightlife") == pytest.approx(0.01)


def test_badge_bonus_with_a_category_only_applies_to_that_category() -> None:
    badges = [_bonus_badge(0.02, "food_dining")]
    assert badge_xp_bonus_pct(badges, "food_dining") == pytest.approx(0.02)
    assert badge_xp_bonus_pct(badges, "nightlife") == 0.0


def test_badge_bonuses_stack_across_multiple_held_badges() -> None:
    badges = [_bonus_badge(0.02, "food_dining"), _bonus_badge(0.01, None)]
    assert badge_xp_bonus_pct(badges, "food_dining") == pytest.approx(0.03)


def test_no_held_badges_means_no_bonus() -> None:
    assert badge_xp_bonus_pct([], "food_dining") == 0.0


@pytest.mark.parametrize(
    ("level", "perks_taken", "expected_pending"),
    [
        (1, 0, 0),
        (4, 0, 0),
        (5, 0, 1),
        (9, 0, 1),
        (10, 0, 2),
        (10, 1, 1),
        (10, 2, 0),
        (23, 3, 1),  # crossed milestones at 5, 10, 15, 20 (4 total) minus 3 taken
    ],
)
def test_pending_perk_choices_count(level, perks_taken, expected_pending) -> None:
    assert pending_perk_choices_count(level, perks_taken) == expected_pending
    assert MILESTONE_LEVEL_INTERVAL == 5


def test_powerup_cap_starts_at_base_with_no_perks() -> None:
    assert powerup_cap(0) == BASE_POWERUP_CAP


def test_powerup_cap_increases_per_extra_slot_perk() -> None:
    assert powerup_cap(2) == BASE_POWERUP_CAP + 2 * EXTRA_POWERUP_SLOT_BONUS


def _specialization_perk(category: str) -> UserPerk:
    return UserPerk(
        id=uuid.uuid4(), user_id=uuid.uuid4(), milestone_level=5,
        type=PerkType.category_specialization, category=category,
    )


def _radius_perk() -> UserPerk:
    return UserPerk(
        id=uuid.uuid4(), user_id=uuid.uuid4(), milestone_level=5, type=PerkType.bigger_radius,
    )


def test_specialization_bonus_only_applies_to_its_own_category() -> None:
    perks = [_specialization_perk("food_dining")]
    assert specialization_bonus_pct(perks, "food_dining") == pytest.approx(SPECIALIZATION_PERK_BONUS_PCT)
    assert specialization_bonus_pct(perks, "nightlife") == 0.0


def test_specialization_bonus_stacks_across_repeat_picks_of_same_category() -> None:
    perks = [_specialization_perk("food_dining"), _specialization_perk("food_dining")]
    assert specialization_bonus_pct(perks, "food_dining") == pytest.approx(2 * SPECIALIZATION_PERK_BONUS_PCT)


def test_specialization_bonus_ignores_non_specialization_perks() -> None:
    perks = [_radius_perk()]
    assert specialization_bonus_pct(perks, "food_dining") == 0.0


def test_streak_bonus_is_zero_on_day_one() -> None:
    assert streak_bonus_pct(1) == 0.0


def test_streak_bonus_grows_by_one_percent_per_day() -> None:
    assert streak_bonus_pct(5) == pytest.approx(4 * STREAK_BONUS_PCT_PER_DAY)


def test_streak_bonus_caps_and_never_goes_negative() -> None:
    assert streak_bonus_pct(50) == pytest.approx(STREAK_BONUS_CAP_PCT)
    assert streak_bonus_pct(0) == 0.0


# --- Time-of-day specialization ---


@pytest.mark.parametrize(
    ("hour", "expected"),
    [
        (21, "night"), (23, "night"), (0, "night"), (1, "night"),  # 9pm-2am wraps midnight
        (2, None), (4, None),
        (5, "morning"), (7, "morning"), (8, "morning"),
        (9, None), (12, None), (20, None),
    ],
)
def test_time_bucket_for_hour(hour, expected) -> None:
    assert time_bucket_for_hour(hour) == expected


@pytest.mark.parametrize(
    ("longitude", "expected_offset"),
    [(0, 0), (144.9674, 10), (-37.8, -3), (170, 11), (-170, -11)],  # Melbourne ~+10, not a real DST-aware lookup
)
def test_approximate_utc_offset_hours(longitude, expected_offset) -> None:
    assert approximate_utc_offset_hours(longitude) == expected_offset


def test_local_hour_for_falls_back_to_utc_without_a_known_location() -> None:
    utc_dt = datetime(2026, 9, 5, 3, 0, tzinfo=timezone.utc)
    assert local_hour_for(utc_dt, None) == 3


def test_local_hour_for_shifts_by_the_approximated_offset() -> None:
    utc_dt = datetime(2026, 9, 5, 20, 0, tzinfo=timezone.utc)  # 8pm UTC
    # Melbourne (+10) -> 6am local
    assert local_hour_for(utc_dt, 144.9674) == 6


def test_local_hour_for_wraps_past_midnight() -> None:
    utc_dt = datetime(2026, 9, 5, 23, 0, tzinfo=timezone.utc)
    assert local_hour_for(utc_dt, 144.9674) == 9  # 23 + 10 = 33 -> 9


def _time_perk(bucket: str) -> UserPerk:
    return UserPerk(id=uuid.uuid4(), user_id=uuid.uuid4(), milestone_level=5, type=PerkType.time_specialization, category=bucket)


def test_time_specialization_bonus_matches_the_held_bucket() -> None:
    perks = [_time_perk("night")]
    assert time_specialization_bonus_pct(perks, "night") == pytest.approx(TIME_SPECIALIZATION_BONUS_PCT)
    assert time_specialization_bonus_pct(perks, "morning") == 0.0


def test_time_specialization_bonus_is_zero_outside_any_window() -> None:
    perks = [_time_perk("night"), _time_perk("morning")]
    assert time_specialization_bonus_pct(perks, None) == 0.0


# --- Rarity-set-per-category badge ---


def test_rarity_set_badge_requires_every_configured_rarity() -> None:
    badge = _badge(
        BadgeCriteriaType.rarity_set_per_category,
        {"category": "food_dining", "rarities": ["common", "rare", "legendary"]},
    )
    stats = {
        "total_drops_completed": 3, "rarity_counts": {}, "category_counts": {},
        "cities_explored": {}, "squad_leader_count": 0,
        "category_rarity_sets": {"food_dining": ["common", "rare"]},
    }
    assert badge_is_satisfied(badge, stats) is False
    stats["category_rarity_sets"]["food_dining"].append("legendary")
    assert badge_is_satisfied(badge, stats) is True


def test_rarity_set_badge_is_scoped_to_its_own_category() -> None:
    badge = _badge(
        BadgeCriteriaType.rarity_set_per_category,
        {"category": "food_dining", "rarities": ["common"]},
    )
    stats = {
        "total_drops_completed": 1, "rarity_counts": {}, "category_counts": {},
        "cities_explored": {}, "squad_leader_count": 0,
        "category_rarity_sets": {"nightlife": ["common"]},
    }
    assert badge_is_satisfied(badge, stats) is False


# --- Location cell / weekly challenge rotation ---


def test_location_cell_for_rounds_to_a_coarse_grid() -> None:
    assert location_cell_for(-37.81194, 144.96745) == "-37.81:144.97"


def test_week_key_for_is_iso_week_formatted() -> None:
    assert week_key_for(date(2026, 9, 5)) == "2026-W36"


def test_current_challenge_category_is_deterministic_and_cycles() -> None:
    same_week_a = current_challenge_category(date(2026, 9, 1))  # Tuesday
    same_week_b = current_challenge_category(date(2026, 9, 4))  # Friday, same ISO week
    assert same_week_a == same_week_b
    assert same_week_a in WEEKLY_CHALLENGE_CATEGORIES


def test_current_challenge_category_rotates_across_weeks() -> None:
    base = date(2026, 1, 5)
    sampled = {current_challenge_category(base + timedelta(weeks=i)) for i in range(12)}
    assert len(sampled) > 1
