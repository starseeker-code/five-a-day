"""Tests for comms.services.email_service — EmailService class."""

import pytest
from django.core import mail
from django.template import TemplateDoesNotExist

from comms.services.email_service import EmailService, email_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_outbox():
    mail.outbox.clear()


@pytest.fixture
def svc():
    return EmailService()


class TestSendEmail:
    def test_basic_send(self, svc):
        result = svc.send_email(
            template_name="happy_birthday",
            recipients="test@example.com",
            subject="Test email",
            context={"name": "Ana"},
        )
        assert result is True
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "Test email"
        assert mail.outbox[0].to == ["test@example.com"]

    def test_string_recipient_converted_to_list(self, svc):
        svc.send_email(
            template_name="happy_birthday",
            recipients="single@example.com",
            subject="Test",
            context={"name": "Test"},
        )
        assert mail.outbox[0].to == ["single@example.com"]

    def test_multiple_recipients(self, svc):
        svc.send_email(
            template_name="happy_birthday",
            recipients=["a@example.com", "b@example.com"],
            subject="Test",
            context={"name": "Test"},
        )
        assert mail.outbox[0].to == ["a@example.com", "b@example.com"]

    def test_cc_and_bcc(self, svc):
        svc.send_email(
            template_name="happy_birthday",
            recipients="to@example.com",
            subject="Test",
            context={"name": "Test"},
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
        )
        assert mail.outbox[0].cc == ["cc@example.com"]
        assert mail.outbox[0].bcc == ["bcc@example.com"]

    def test_html_alternative_attached(self, svc):
        svc.send_email(
            template_name="happy_birthday",
            recipients="test@example.com",
            subject="Test",
            context={"name": "Test"},
        )
        msg = mail.outbox[0]
        # EmailMultiAlternatives stores HTML in alternatives
        assert len(msg.alternatives) == 1
        content, mimetype = msg.alternatives[0]
        assert mimetype == "text/html"
        assert "Test" in content or "birthday" in content.lower() or len(content) > 0

    def test_default_context_values(self, svc):
        svc.send_email(
            template_name="happy_birthday",
            recipients="test@example.com",
            subject="Test",
            context={"name": "Test"},
        )
        # Verify the email was sent (context defaults are internal, but email must not crash)
        assert len(mail.outbox) == 1

    def test_with_attachments(self, svc):
        svc.send_email(
            template_name="happy_birthday",
            recipients="test@example.com",
            subject="Test",
            context={"name": "Test"},
            attachments=[("report.pdf", b"%PDF-1.4 test content", "application/pdf")],
        )
        msg = mail.outbox[0]
        assert len(msg.attachments) == 1
        filename, content, mimetype = msg.attachments[0]
        assert filename == "report.pdf"

    def test_nonexistent_template_fails_silently(self, svc):
        result = svc.send_email(
            template_name="nonexistent_template_xyz",
            recipients="test@example.com",
            subject="Test",
            fail_silently=True,
        )
        assert result is False
        assert len(mail.outbox) == 0

    def test_nonexistent_template_raises(self, svc):
        with pytest.raises(TemplateDoesNotExist):
            svc.send_email(
                template_name="nonexistent_template_xyz",
                recipients="test@example.com",
                subject="Test",
                fail_silently=False,
            )

    def test_global_instance_works(self):
        result = email_service.send_email(
            template_name="happy_birthday",
            recipients="global@example.com",
            subject="Global test",
            context={"name": "Global"},
        )
        assert result is True
        assert len(mail.outbox) == 1


class TestSendBulkEmails:
    def test_bulk_send_counts(self, svc):
        data = [
            {"recipient": "a@example.com", "subject": "Email A", "context": {"name": "A"}},
            {"recipient": "b@example.com", "subject": "Email B", "context": {"name": "B"}},
            {"recipient": "c@example.com", "subject": "Email C", "context": {"name": "C"}},
        ]
        results = svc.send_bulk_emails("happy_birthday", data)
        assert results["sent"] == 3
        assert results["failed"] == 0
        assert len(mail.outbox) == 3

    def test_bulk_with_bad_template_fails_gracefully(self, svc):
        data = [
            {"recipient": "a@example.com", "subject": "Email A", "context": {"name": "A"}},
        ]
        results = svc.send_bulk_emails("nonexistent_xyz", data, fail_silently=True)
        assert results["failed"] >= 1
