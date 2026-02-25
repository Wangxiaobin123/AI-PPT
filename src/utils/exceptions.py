class ContentProducerError(Exception):
    """Base exception for the content production system."""


class SkillNotFoundError(ContentProducerError):
    def __init__(self, skill_name: str):
        self.skill_name = skill_name
        super().__init__(f"Skill not found: {skill_name}")


class SkillExecutionError(ContentProducerError):
    def __init__(self, skill_name: str, detail: str):
        self.skill_name = skill_name
        super().__init__(f"Skill '{skill_name}' execution failed: {detail}")


class ParserError(ContentProducerError):
    def __init__(self, format_type: str, detail: str):
        self.format_type = format_type
        super().__init__(f"Failed to parse {format_type}: {detail}")


class GeneratorError(ContentProducerError):
    def __init__(self, format_type: str, detail: str):
        self.format_type = format_type
        super().__init__(f"Failed to generate {format_type}: {detail}")


class IntentError(ContentProducerError):
    pass


class LLMError(ContentProducerError):
    def __init__(self, provider: str, detail: str):
        self.provider = provider
        super().__init__(f"LLM error ({provider}): {detail}")


class QAValidationError(ContentProducerError):
    def __init__(self, checks: list[str]):
        self.checks = checks
        super().__init__(f"QA validation failed: {', '.join(checks)}")


class FileStorageError(ContentProducerError):
    pass
