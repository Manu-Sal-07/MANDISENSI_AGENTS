from mandisense_ai.core.agents.external_factors_agent.processing.external_fusion import compute_external_impact


def test_compute_external_impact_all_agree():
    result = compute_external_impact(
        weather_signal=0.5,
        news_signal=0.2,
        policy_signal=0.3,
        weather_conf=0.9,
        news_conf=0.8,
        policy_conf=0.7,
    )

    assert result["impact_score"] > 0
    assert result["confidence"] > 0
    assert result["components"]["weather"] == 0.5 * 0.9
    assert result["components"]["news"] == 0.2 * 0.8
    assert result["components"]["policy"] == 0.3 * 0.7
    assert result["impact_score"] <= 0.02
    assert result["confidence"] <= 1.0


def test_compute_external_impact_conflict_reduces_magnitude():
    positive_result = compute_external_impact(
        weather_signal=0.5,
        news_signal=0.0,
        policy_signal=0.0,
        weather_conf=1.0,
        news_conf=0.0,
        policy_conf=0.0,
    )
    conflict_result = compute_external_impact(
        weather_signal=0.5,
        news_signal=-0.3,
        policy_signal=0.0,
        weather_conf=1.0,
        news_conf=1.0,
        policy_conf=0.0,
    )

    assert abs(conflict_result["impact_score"]) < abs(positive_result["impact_score"])
    assert conflict_result["confidence"] < positive_result["confidence"]


def test_compute_external_impact_zero_signals():
    result = compute_external_impact(
        weather_signal=0.0,
        news_signal=0.0,
        policy_signal=0.0,
        weather_conf=0.0,
        news_conf=0.0,
        policy_conf=0.0,
    )

    assert result["impact_score"] == 0.0
    assert result["confidence"] == 0.0
    assert result["components"] == {"weather": 0.0, "policy": 0.0, "news": 0.0}


def test_compute_external_impact_clamps_to_max_bias():
    result = compute_external_impact(
        weather_signal=1.0,
        news_signal=1.0,
        policy_signal=1.0,
        weather_conf=1.0,
        news_conf=1.0,
        policy_conf=1.0,
    )

    assert result["impact_score"] <= 0.02
    assert result["impact_score"] >= -0.02
    assert result["confidence"] == 1.0


def test_compute_external_impact_handles_non_numeric_values():
    result = compute_external_impact(
        weather_signal="0.4",
        news_signal=None,
        policy_signal=0.5,
        weather_conf="0.8",
        news_conf=None,
        policy_conf=0.6,
    )

    assert result["components"]["weather"] == 0.4 * 0.8
    assert result["components"]["news"] == 0.0
    assert result["impact_score"] != float("nan")
