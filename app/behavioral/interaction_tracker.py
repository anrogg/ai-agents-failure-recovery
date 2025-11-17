"""
Interaction tracking for behavioral anomaly detection.

This module tracks behavioral metrics for each agent interaction,
providing the foundation for baseline establishment and anomaly detection.
"""

import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from ..models import AgentRequest, AgentResponse, InteractionBehavior

logger = structlog.get_logger(__name__)


class InteractionTracker:
    """Tracks behavioral metrics for agent interactions."""

    def __init__(self):
        self.session_behaviors: Dict[str, List[InteractionBehavior]] = {}
        self.session_responses: Dict[str, List[str]] = {}  # Store response texts for loop detection

    def track_interaction(
        self,
        session_id: str,
        request: AgentRequest,
        response: AgentResponse,
        start_time: float
    ) -> InteractionBehavior:
        """
        Track behavioral metrics for a single interaction.

        Args:
            session_id: Session identifier
            request: The agent request
            response: The agent response
            start_time: When processing started (time.time())

        Returns:
            InteractionBehavior: Calculated behavioral metrics
        """
        response_latency_ms = response.processing_time_ms
        message_length = len(response.response)

        # Get conversation history for context
        conversation_turns = self._count_conversation_turns(session_id)

        # Calculate behavioral metrics
        clarification_frequency = self._calculate_clarification_frequency(
            response.response, conversation_turns
        )
        topic_switches = self._detect_topic_switches(session_id, request.message, response.response)
        confidence_expressions = self._count_confidence_expressions(response.response)

        behavior = InteractionBehavior(
            session_id=session_id,
            response_latency_ms=response_latency_ms,
            message_length=message_length,
            conversation_turns=conversation_turns,
            clarification_frequency=clarification_frequency,
            topic_switches=topic_switches,
            confidence_expressions=confidence_expressions,
            timestamp=datetime.now()
        )

        # Store behavior in session history
        if session_id not in self.session_behaviors:
            self.session_behaviors[session_id] = []
        self.session_behaviors[session_id].append(behavior)

        # Store response text for loop detection (keep last 10 responses)
        if session_id not in self.session_responses:
            self.session_responses[session_id] = []
        self.session_responses[session_id].append(response.response)
        if len(self.session_responses[session_id]) > 10:
            self.session_responses[session_id] = self.session_responses[session_id][-10:]

        logger.debug("Tracked interaction behavior",
                    session_id=session_id,
                    response_latency_ms=response_latency_ms,
                    message_length=message_length,
                    clarification_frequency=clarification_frequency,
                    confidence_expressions=confidence_expressions)

        return behavior

    def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Get aggregated behavioral metrics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict: Aggregated behavioral metrics
        """
        behaviors = self.session_behaviors.get(session_id, [])

        if not behaviors:
            return {
                "interaction_count": 0,
                "avg_response_latency": 0,
                "avg_message_length": 0,
                "total_topic_switches": 0,
                "avg_clarification_frequency": 0,
                "avg_confidence_expressions": 0
            }

        return {
            "interaction_count": len(behaviors),
            "avg_response_latency": sum(b.response_latency_ms for b in behaviors) / len(behaviors),
            "avg_message_length": sum(b.message_length for b in behaviors) / len(behaviors),
            "total_topic_switches": sum(b.topic_switches for b in behaviors),
            "avg_clarification_frequency": sum(b.clarification_frequency for b in behaviors) / len(behaviors),
            "avg_confidence_expressions": sum(b.confidence_expressions for b in behaviors) / len(behaviors),
            "latest_behavior": behaviors[-1].model_dump() if behaviors else None
        }

    def get_recent_behaviors(self, session_id: str, count: int = 10) -> List[InteractionBehavior]:
        """
        Get the most recent behavioral measurements for a session.

        Args:
            session_id: Session identifier
            count: Number of recent behaviors to return

        Returns:
            List[InteractionBehavior]: Recent behaviors, newest first
        """
        behaviors = self.session_behaviors.get(session_id, [])
        return behaviors[-count:] if behaviors else []

    def get_recent_responses(self, session_id: str, count: int = 5) -> List[str]:
        """
        Get the most recent response texts for a session.

        Args:
            session_id: Session identifier
            count: Number of recent responses to return

        Returns:
            List[str]: Recent response texts, newest first
        """
        responses = self.session_responses.get(session_id, [])
        return responses[-count:] if responses else []

    def _count_conversation_turns(self, session_id: str) -> int:
        """Count total conversation turns in the session."""
        behaviors = self.session_behaviors.get(session_id, [])
        return len(behaviors) + 1  # +1 for current turn

    def _calculate_clarification_frequency(self, response: str, total_turns: int) -> float:
        """
        Calculate frequency of clarification requests.

        Args:
            response: Agent response text
            total_turns: Total conversation turns

        Returns:
            float: Clarification frequency (0.0 to 1.0)
        """
        clarification_patterns = [
            r'\b(could you|can you|please)\s+(clarify|explain|tell me more)',
            r'\b(what do you mean|I don\'t understand|unclear)',
            r'\?(.*?)\?',  # Questions ending with question marks
            r'\b(help me understand|need more information)',
        ]

        clarification_count = 0
        response_lower = response.lower()

        for pattern in clarification_patterns:
            matches = re.findall(pattern, response_lower)
            clarification_count += len(matches)

        return min(clarification_count / max(total_turns, 1), 1.0)

    def _detect_topic_switches(self, session_id: str, user_message: str, agent_response: str) -> int:
        """
        Detect topic switches in the conversation.
        Simple implementation - counts when agent response doesn't relate to user message.

        Args:
            session_id: Session identifier
            user_message: User's message
            agent_response: Agent's response

        Returns:
            int: Number of topic switches detected (0 or 1 for single interaction)
        """
        # Simple heuristic: if agent response is very short and doesn't contain
        # key words from user message, it might be a topic switch
        user_words = set(user_message.lower().split())
        response_words = set(agent_response.lower().split())

        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        user_words = user_words - stop_words
        response_words = response_words - stop_words

        if len(user_words) == 0:
            return 0

        overlap = len(user_words.intersection(response_words))
        overlap_ratio = overlap / len(user_words)

        # If overlap is very low and response is substantial, might be topic switch
        if overlap_ratio < 0.2 and len(agent_response.split()) > 10:
            return 1

        return 0

    def _count_confidence_expressions(self, response: str) -> int:
        """
        Count expressions of confidence/uncertainty in the response.

        Args:
            response: Agent response text

        Returns:
            int: Number of confidence expressions
        """
        confidence_patterns = [
            r'\b(I think|I believe|I assume|probably|likely|maybe|perhaps)',
            r'\b(definitely|certainly|absolutely|sure|confident)',
            r'\b(not sure|uncertain|unclear|might be|could be)',
            r'\b(in my opinion|from my perspective)',
        ]

        confidence_count = 0
        response_lower = response.lower()

        for pattern in confidence_patterns:
            matches = re.findall(pattern, response_lower)
            confidence_count += len(matches)

        return confidence_count

    def clear_session_data(self, session_id: str) -> None:
        """Clear behavioral data for a session."""
        if session_id in self.session_behaviors:
            del self.session_behaviors[session_id]
        if session_id in self.session_responses:
            del self.session_responses[session_id]
        logger.info("Cleared behavioral data for session", session_id=session_id)

    def get_all_session_ids(self) -> List[str]:
        """Get all session IDs with tracked behavioral data."""
        return list(self.session_behaviors.keys())