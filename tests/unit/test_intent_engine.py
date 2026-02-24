"""Tests for intent engine (keyword fallback mode, no LLM required)."""
import pytest
from src.core.task.models import TaskPlan
from src.core.intent.conversation import ClarificationResponse


class TestIntentClassifier:
    def test_classify_pptx(self):
        from src.core.intent.classifier import IntentClassifier
        classifier = IntentClassifier(llm_client=None)
        result = classifier._keyword_fallback("Create a presentation about AI")
        assert result.intent_type == "create_pptx"

    def test_classify_docx(self):
        from src.core.intent.classifier import IntentClassifier
        classifier = IntentClassifier(llm_client=None)
        result = classifier._keyword_fallback("Write a report on sales")
        assert result.intent_type == "create_docx"

    def test_classify_xlsx(self):
        from src.core.intent.classifier import IntentClassifier
        classifier = IntentClassifier(llm_client=None)
        result = classifier._keyword_fallback("Build an Excel spreadsheet")
        assert result.intent_type == "create_xlsx"

    def test_classify_pdf(self):
        from src.core.intent.classifier import IntentClassifier
        classifier = IntentClassifier(llm_client=None)
        result = classifier._keyword_fallback("Export this as PDF")
        assert result.intent_type == "create_pdf"

    def test_classify_html(self):
        from src.core.intent.classifier import IntentClassifier
        classifier = IntentClassifier(llm_client=None)
        result = classifier._keyword_fallback("Design a landing page")
        assert result.intent_type == "create_html"


class TestIntentEngine:
    @pytest.mark.asyncio
    async def test_process_pptx(self):
        from src.core.intent.engine import IntentEngine
        engine = IntentEngine(llm_client=None, available_skills=["pptx", "docx", "xlsx"])
        result = await engine.process("Create a presentation about AI trends")
        assert isinstance(result, TaskPlan)
        assert len(result.tasks) > 0
        assert result.tasks[0].skill_name == "pptx"

    @pytest.mark.asyncio
    async def test_process_docx(self):
        from src.core.intent.engine import IntentEngine
        engine = IntentEngine(llm_client=None, available_skills=["pptx", "docx"])
        result = await engine.process("Write a report on quarterly results")
        # May return TaskPlan or ClarificationResponse depending on parameter extraction
        assert isinstance(result, (TaskPlan, ClarificationResponse))
        if isinstance(result, TaskPlan):
            assert result.tasks[0].skill_name == "docx"
