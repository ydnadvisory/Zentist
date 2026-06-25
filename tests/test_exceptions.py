from zentist_rpa.core.exceptions import PortalAutomationError


def test_portal_error_includes_actionable_context() -> None:
    error = PortalAutomationError(
        portal="orangehrm",
        operation="upload_salary_attachment",
        reason="Attachment input missing",
    )

    assert str(error) == "orangehrm:upload_salary_attachment failed: Attachment input missing"
    assert error.portal == "orangehrm"
    assert error.operation == "upload_salary_attachment"
