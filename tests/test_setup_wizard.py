from setup_wizard import (
    INTEGRATIONS_URL,
    TEMPLATE_URL,
    SetupWizardState,
)


def test_wizard_has_five_bounded_steps():
    state = SetupWizardState()

    assert state.total_steps == 5
    assert state.current_step == 0
    assert state.back() == 0

    for _ in range(10):
        state.advance()

    assert state.current_step == 4

    for _ in range(10):
        state.back()

    assert state.current_step == 0


def test_wizard_help_links_are_https():
    assert TEMPLATE_URL.startswith("https://")
    assert INTEGRATIONS_URL.startswith("https://")
