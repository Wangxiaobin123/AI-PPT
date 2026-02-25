"""Main intent engine that orchestrates the full pipeline.

The :class:`IntentEngine` ties together intent classification, parameter
extraction, conversation management, task decomposition, and task scheduling
into a single ``process`` entry-point.  A user's natural-language request
goes in, and either a ready-to-execute :class:`TaskPlan` or a
:class:`ClarificationResponse` comes out.
"""

from __future__ import annotations

import uuid

from src.core.intent.classifier import IntentClassifier, IntentResult
from src.core.intent.parameter_extractor import ParameterExtractor, GenerationParams
from src.core.intent.conversation import (
    ConversationManager,
    ClarificationResponse,
)
from src.core.task.decomposer import TaskDecomposer
from src.core.task.scheduler import TaskScheduler
from src.core.task.models import TaskPlan
from src.utils.logging import get_logger

logger = get_logger("intent.engine")


class IntentEngine:
    """Top-level orchestrator for intent understanding and task planning.

    Parameters
    ----------
    llm_client:
        An optional :class:`~src.core.llm.client.LLMClient`.  All sub-
        components receive this client and fall back to heuristics when it
        is ``None``.
    available_skills:
        Names of the skills currently registered in the system.  Passed to
        the classifier for context.
    """

    def __init__(
        self,
        llm_client=None,
        available_skills: list[str] | None = None,
    ):
        self.classifier = IntentClassifier(llm_client)
        self.extractor = ParameterExtractor(llm_client)
        self.conversation = ConversationManager(llm_client)
        self.decomposer = TaskDecomposer()
        self.scheduler = TaskScheduler()
        self.available_skills = available_skills or []

    async def process(
        self,
        user_input: str,
        session_id: str | None = None,
    ) -> TaskPlan | ClarificationResponse:
        """Process a user request end-to-end.

        Steps:
        1. Ensure a conversation session exists.
        2. Classify the user's intent.
        3. Extract structured parameters.
        4. Check whether essential information is missing.
           - If so, return a :class:`ClarificationResponse`.
        5. Decompose the intent into tasks.
        6. Schedule the tasks and return a :class:`TaskPlan`.

        Parameters
        ----------
        user_input:
            The raw natural-language request from the user.
        session_id:
            An optional session identifier for multi-turn conversations.
            If ``None``, a new session is created automatically.

        Returns
        -------
        TaskPlan | ClarificationResponse
            A plan ready for execution, or a follow-up question when more
            information is needed.
        """
        # 0. Session management.
        if session_id is None:
            session_id = uuid.uuid4().hex[:12]

        ctx = self.conversation.get_or_create_session(session_id)
        self.conversation.update_context(session_id, "user", user_input)

        logger.info(
            "process_start",
            session_id=session_id,
            input_len=len(user_input),
        )

        # 1. Classify intent.
        intent: IntentResult = await self.classifier.classify(
            user_input, self.available_skills,
        )
        logger.info(
            "intent_classified",
            session_id=session_id,
            intent_type=intent.intent_type,
            confidence=intent.confidence,
        )
        self.conversation.set_intent(session_id, intent.intent_type)

        # 2. Extract parameters.
        params: GenerationParams = await self.extractor.extract(
            user_input, intent.intent_type,
        )
        logger.info(
            "params_extracted",
            session_id=session_id,
            output_format=params.output_format,
            title=params.title,
        )
        self.conversation.merge_params(
            session_id,
            params.model_dump(exclude_none=True),
        )

        # 3. Check for missing required information.
        if await self.conversation.needs_clarification(
            intent.intent_type, params,
        ):
            clarification = await self.conversation.generate_clarification(
                intent.intent_type, params, user_input,
            )
            logger.info(
                "clarification_needed",
                session_id=session_id,
                missing_fields=clarification.missing_fields,
            )
            self.conversation.update_context(
                session_id, "assistant", clarification.question,
            )
            return clarification

        # 4. Decompose into tasks.
        tasks = self.decomposer.decompose(intent.intent_type, params)
        logger.info(
            "tasks_decomposed",
            session_id=session_id,
            task_count=len(tasks),
        )

        # 5. Schedule tasks.
        plan = self.scheduler.schedule(tasks, session_id=session_id)
        logger.info(
            "plan_scheduled",
            session_id=session_id,
            waves=len(plan.execution_order),
        )

        return plan

    async def process_followup(
        self,
        user_input: str,
        session_id: str,
    ) -> TaskPlan | ClarificationResponse:
        """Process a follow-up message in an existing conversation.

        Re-extracts parameters from the new message and merges them with
        previously accumulated values before re-running the clarification
        check and (if satisfied) producing a task plan.
        """
        ctx = self.conversation.get_or_create_session(session_id)
        self.conversation.update_context(session_id, "user", user_input)

        intent_type = ctx.current_intent or "unknown"

        # Re-extract parameters from the follow-up.
        new_params: GenerationParams = await self.extractor.extract(
            user_input, intent_type,
        )
        self.conversation.merge_params(
            session_id,
            new_params.model_dump(exclude_none=True),
        )

        # Build a merged GenerationParams from the accumulated dict.
        merged = GenerationParams(**{
            k: v for k, v in ctx.current_params.items()
            if k in GenerationParams.model_fields
        })

        # Check again.
        if await self.conversation.needs_clarification(intent_type, merged):
            clarification = await self.conversation.generate_clarification(
                intent_type, merged, user_input,
            )
            self.conversation.update_context(
                session_id, "assistant", clarification.question,
            )
            return clarification

        tasks = self.decomposer.decompose(intent_type, merged)
        plan = self.scheduler.schedule(tasks, session_id=session_id)
        return plan
