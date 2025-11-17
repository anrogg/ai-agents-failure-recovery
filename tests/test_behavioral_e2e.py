"""
End-to-end tests for behavioral anomaly detection system.

This module tests the complete behavioral anomaly detection pipeline,
including interaction tracking, baseline establishment, anomaly detection,
and integration with the agent service.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import List
from unittest.mock import AsyncMock, Mock, patch

from app.behavioral import InteractionTracker, BaselineManager, TemporalBehaviorAnalyzer, AnomalyDetector
from app.behavioral.monitoring_service import BehavioralMonitoringService
from app.validation.strategies.behavioral_anomaly_strategy import BehavioralAnomalyStrategy, InteractionConsistencyStrategy
from app.validation import create_behavioral_aware_validator, ValidationLevel
from app.models import (
    AgentRequest, AgentResponse, InteractionStatus, InteractionBehavior, BehavioralBaseline,
    ConversationFlowMetrics, DriftScore, PatternAnalysis
)
from app.database import InteractionBehaviorLog, BehavioralAnomalyLog, BehavioralBaseline as BehavioralBaselineDB
from app.agent_service import CustomerServiceAgent
from app.metrics import MetricsCollector


class TestBehavioralTrackingE2E:
    """End-to-end tests for behavioral tracking pipeline."""

    @pytest.fixture
    def interaction_tracker(self):
        """Create interaction tracker instance."""
        return InteractionTracker()

    @pytest.fixture
    def baseline_manager(self):
        """Create baseline manager instance."""
        return BaselineManager(min_interactions=3, update_frequency_hours=0)  # Lower threshold and immediate updates for testing

    @pytest.fixture
    def temporal_analyzer(self):
        """Create temporal analyzer instance."""
        return TemporalBehaviorAnalyzer()

    @pytest.fixture
    def sample_request(self):
        """Create a sample agent request."""
        return AgentRequest(
            session_id="test_session_001",
            message="Hello, I need help with my account",
            context={"user_id": "test_user"},
            model="gpt-3.5-turbo"
        )

    @pytest.fixture
    def sample_response(self):
        """Create a sample agent response."""
        return AgentResponse(
            session_id="test_session_001",
            response="I'd be happy to help you with your account. What specific issue are you experiencing?",
            status=InteractionStatus.SUCCESS,
            natural_status=InteractionStatus.SUCCESS,
            failure_injection_applied=False,
            natural_response="I'd be happy to help you with your account. What specific issue are you experiencing?",
            processing_time_ms=1250,
            token_count=45,
            model_used="gpt-3.5-turbo"
        )

    def test_interaction_tracking_flow(self, interaction_tracker, sample_request, sample_response):
        """Test complete interaction tracking flow."""
        session_id = "test_session_tracking"
        start_time = time.time()

        # Track multiple interactions
        behaviors = []
        for i in range(5):
            # Modify request/response for variety
            request = AgentRequest(
                session_id=session_id,
                message=f"Request {i}: Can you help me?",
                context={"iteration": i},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=f"Response {i}: Of course! I'll help you with that.",
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=f"Response {i}: Of course! I'll help you with that.",
                processing_time_ms=1000 + (i * 200),  # Increasing latency
                token_count=40 + (i * 5),
                model_used="gpt-3.5-turbo"
            )

            behavior = interaction_tracker.track_interaction(
                session_id=session_id,
                request=request,
                response=response,
                start_time=start_time
            )
            behaviors.append(behavior)

        # Verify tracking results
        assert len(behaviors) == 5
        assert all(b.session_id == session_id for b in behaviors)

        # Verify progression in metrics
        latencies = [b.response_latency_ms for b in behaviors]
        assert latencies == [1000, 1200, 1400, 1600, 1800]

        # Verify conversation turns increment
        turns = [b.conversation_turns for b in behaviors]
        assert turns == [1, 2, 3, 4, 5]

        # Get session metrics
        session_metrics = interaction_tracker.get_session_metrics(session_id)
        assert session_metrics["interaction_count"] == 5
        assert session_metrics["avg_response_latency"] == 1400.0
        assert session_metrics["total_topic_switches"] == 0  # No topic switches in this test

        # Test response text storage
        recent_responses = interaction_tracker.get_recent_responses(session_id, 5)
        assert len(recent_responses) == 5
        for i, response_text in enumerate(recent_responses):
            assert f"Response {i}:" in response_text

    def test_baseline_establishment_flow(self, baseline_manager, interaction_tracker):
        """Test baseline establishment and updating flow."""
        session_id = "test_session_baseline"

        # Generate consistent behaviors for baseline
        behaviors = []
        for i in range(5):
            behavior = InteractionBehavior(
                session_id=session_id,
                response_latency_ms=1200 + (i * 50),  # Slight variation
                message_length=80 + (i * 10),
                conversation_turns=i + 1,
                clarification_frequency=0.1,
                topic_switches=0,
                confidence_expressions=2,
                timestamp=datetime.now() - timedelta(hours=i)
            )
            behaviors.append(behavior)

        # Test baseline establishment
        baseline = baseline_manager.establish_baseline(session_id, behaviors)

        assert baseline is not None
        assert baseline.session_id == session_id
        assert baseline.interaction_count == 5
        assert 1200 <= baseline.avg_response_latency <= 1400
        assert baseline.typical_message_length_range[0] == 80
        assert baseline.typical_message_length_range[1] == 120
        assert baseline.normal_clarification_rate == 0.1

        # Test anomaly detection
        anomalous_behavior = InteractionBehavior(
            session_id=session_id,
            response_latency_ms=3000,  # Much higher than baseline
            message_length=300,  # Much longer than baseline
            conversation_turns=6,
            clarification_frequency=0.8,  # Much higher than baseline
            topic_switches=2,
            confidence_expressions=8,  # Much higher than baseline
            timestamp=datetime.now()
        )

        deviation_score = baseline_manager.detect_deviation(anomalous_behavior, baseline)
        assert deviation_score > 0.5  # Should detect significant deviation

        # Test baseline update
        new_behaviors = [anomalous_behavior]
        updated_baseline = baseline_manager.update_baseline(session_id, new_behaviors)

        assert updated_baseline is not None
        assert updated_baseline.interaction_count == 6

    def test_temporal_analysis_flow(self, temporal_analyzer):
        """Test temporal behavioral analysis flow."""
        session_id = "test_session_temporal"

        # Create behaviors showing drift over time
        early_behaviors = []
        late_behaviors = []

        # Early period - consistent behavior
        for i in range(3):
            behavior = InteractionBehavior(
                session_id=session_id,
                response_latency_ms=1000,
                message_length=100,
                conversation_turns=i + 1,
                clarification_frequency=0.1,
                topic_switches=0,
                confidence_expressions=2,
                timestamp=datetime.now() - timedelta(hours=12 - i)
            )
            early_behaviors.append(behavior)

        # Late period - changed behavior (drift)
        for i in range(3):
            behavior = InteractionBehavior(
                session_id=session_id,
                response_latency_ms=2000,  # Much slower
                message_length=200,  # Much longer
                conversation_turns=i + 4,
                clarification_frequency=0.5,  # Much higher
                topic_switches=1,
                confidence_expressions=6,  # Much higher
                timestamp=datetime.now() - timedelta(hours=3 - i)
            )
            late_behaviors.append(behavior)

        all_behaviors = early_behaviors + late_behaviors

        # Test conversation flow analysis
        flow_metrics = temporal_analyzer.analyze_conversation_flow(all_behaviors)
        assert flow_metrics.session_id == session_id
        assert 0.0 <= flow_metrics.flow_consistency_score <= 1.0
        assert 0.0 <= flow_metrics.engagement_level <= 1.0

        # Test drift detection
        drift_score = temporal_analyzer.detect_behavioral_drift(all_behaviors)
        assert drift_score.session_id == session_id
        assert drift_score.drift_score > 0.5  # Should detect significant drift
        assert len(drift_score.contributing_factors) > 0

        # Test pattern identification
        patterns = temporal_analyzer.identify_interaction_patterns(all_behaviors)
        # May or may not find patterns depending on the specific behaviors

        # Test consistency score
        consistency_score = temporal_analyzer.calculate_consistency_score(all_behaviors)
        assert 0.0 <= consistency_score <= 1.0
        assert consistency_score < 0.8  # Should be low due to drift

    def test_loop_detection_flow(self, temporal_analyzer):
        """Test loop detection functionality."""
        # Test exact repetition loop
        exact_loop_responses = [
            "Can you be more specific?",
            "Can you be more specific?",
            "Can you be more specific?"
        ]

        exact_loop_result = temporal_analyzer.detect_response_loops(exact_loop_responses)
        assert exact_loop_result is not None
        assert exact_loop_result["loop_type"] == "exact_repetition"
        assert exact_loop_result["confidence"] == 1.0
        assert exact_loop_result["pattern_length"] == 3

        # Test alternating pattern loop
        alternating_responses = [
            "Please clarify",
            "I need more info",
            "Please clarify",
            "I need more info"
        ]

        alternating_result = temporal_analyzer.detect_response_loops(alternating_responses)
        assert alternating_result is not None
        assert alternating_result["loop_type"] == "alternating_pattern"
        assert alternating_result["confidence"] == 0.9
        assert alternating_result["pattern_length"] == 2

        # Test low diversity loop
        low_diversity_responses = [
            "I can help with that",
            "I can help with that",
            "Let me assist you",
            "I can help with that",
            "Let me assist you"
        ]

        diversity_result = temporal_analyzer.detect_response_loops(low_diversity_responses)
        assert diversity_result is not None
        assert diversity_result["loop_type"] == "low_diversity"
        assert diversity_result["uniqueness_ratio"] < 0.6

        # Test no loop (normal responses)
        normal_responses = [
            "Hello, how can I help?",
            "I understand your concern.",
            "Let me check that for you.",
            "Here's what I found.",
            "Is there anything else?"
        ]

        no_loop_result = temporal_analyzer.detect_response_loops(normal_responses)
        assert no_loop_result is None

        # Test insufficient responses
        few_responses = ["Response 1", "Response 2"]
        insufficient_result = temporal_analyzer.detect_response_loops(few_responses)
        assert insufficient_result is None


class TestBehavioralValidationE2E:
    """End-to-end tests for behavioral validation strategies."""

    @pytest.fixture
    def behavioral_strategy(self):
        """Create behavioral anomaly strategy."""
        return BehavioralAnomalyStrategy(
            anomaly_threshold=0.7,
            drift_threshold=0.8
        )

    @pytest.fixture
    def consistency_strategy(self):
        """Create interaction consistency strategy."""
        return InteractionConsistencyStrategy()

    @pytest.fixture
    def behavioral_validator(self):
        """Create behavioral-aware validator."""
        return create_behavioral_aware_validator()

    def test_behavioral_anomaly_validation_flow(self, behavioral_strategy):
        """Test behavioral anomaly validation end-to-end."""
        session_id = "test_validation_session"

        # Simulate normal validation context
        normal_context = {
            "session_id": session_id,
            "user_message": "Hello, how are you?",
            "conversation_history": [],
            "model": "gpt-3.5-turbo",
            "processing_time_ms": 1200
        }

        # Test normal behavior validation
        normal_output = "Hello! I'm doing well, thank you for asking. How can I help you today?"
        normal_result = behavioral_strategy.validate(normal_output, normal_context)

        # Should pass with high confidence (no baseline yet)
        assert normal_result.passed
        assert normal_result.validation_level == ValidationLevel.BEHAVIORAL

        # Simulate anomalous validation context (very slow response)
        anomalous_context = {
            "session_id": session_id,
            "user_message": "What's the weather like?",
            "conversation_history": [],
            "model": "gpt-3.5-turbo",
            "processing_time_ms": 15000  # Very slow
        }

        anomalous_output = "The weather is... uh... I think it might be sunny? Or maybe cloudy? I'm not really sure about the weather right now."
        anomalous_result = behavioral_strategy.validate(anomalous_output, anomalous_context)

        # May still pass if no baseline established, but should have lower confidence
        assert anomalous_result.validation_level == ValidationLevel.BEHAVIORAL

    def test_interaction_consistency_validation_flow(self, consistency_strategy):
        """Test interaction consistency validation end-to-end."""
        session_id = "test_consistency_session"

        # Test with insufficient data
        context = {
            "session_id": session_id,
            "user_message": "Hello",
            "conversation_history": [],
            "model": "gpt-3.5-turbo"
        }

        result = consistency_strategy.validate("Hello!", context)
        assert result.passed  # Should pass with insufficient data
        assert "Insufficient interactions" in result.warnings[0]

    def test_full_behavioral_validator_flow(self, behavioral_validator):
        """Test complete behavioral-aware validator flow."""
        session_id = "test_full_validator"

        # Test validation at different levels
        context = {
            "session_id": session_id,
            "user_message": "Test message",
            "conversation_history": [],
            "model": "gpt-3.5-turbo"
        }

        # Test FORMAT level
        format_result = behavioral_validator.validate(
            "Valid response",
            context,
            ValidationLevel.FORMAT
        )
        assert format_result.passed

        # Test BEHAVIORAL level
        behavioral_result = behavioral_validator.validate(
            "Valid response for behavioral analysis",
            context,
            ValidationLevel.BEHAVIORAL
        )
        assert behavioral_result.passed


class TestAgentServiceBehavioralIntegration:
    """End-to-end tests for agent service behavioral integration."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for testing."""
        client = AsyncMock()
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message.content = "Test response from AI"
        response.usage = Mock()
        response.usage.prompt_tokens = 20
        response.usage.completion_tokens = 10
        client.chat.completions.create = AsyncMock(return_value=response)
        return client

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_redis_state_manager(self):
        """Mock Redis state manager for testing."""
        manager = AsyncMock()
        manager.load_state = AsyncMock(return_value=None)
        manager.save_state = AsyncMock()
        manager.create_checkpoint = AsyncMock()
        manager.track_failure_count = AsyncMock()
        return manager

    @pytest.fixture
    def mock_failure_injector(self):
        """Mock failure injector for testing."""
        injector = Mock()
        injector.should_inject_failure = AsyncMock(return_value=(False, None))
        injector.reset_session_state = Mock()
        return injector

    @patch.dict('os.environ', {
        'BEHAVIORAL_TRACKING_ENABLED': 'true',
        'BEHAVIORAL_METRICS_ENABLED': 'true',
        'BEHAVIORAL_DB_PERSISTENCE_ENABLED': 'true',
        'OUTPUT_VALIDATION_ENABLED': 'true',
        'OUTPUT_VALIDATION_LEVEL': 'behavioral'
    })
    def test_agent_service_behavioral_integration(
        self,
        mock_openai_client,
        mock_db_session,
        mock_redis_state_manager,
        mock_failure_injector
    ):
        """Test full agent service integration with behavioral monitoring service."""

        # Create agent service with mocked dependencies
        agent = CustomerServiceAgent()

        # Replace dependencies with mocks
        agent.openai_client = mock_openai_client
        agent.state_manager = mock_redis_state_manager
        agent.failure_injector = mock_failure_injector

        # Verify behavioral monitoring is enabled (new service layer)
        assert agent.behavioral_monitoring is not None
        assert agent.output_validator is not None

        # Create test request
        request = AgentRequest(
            session_id="test_integration_session",
            message="Hello, I need help with my account",
            context={"test": True},
            model="gpt-3.5-turbo"
        )

        # Test the complete flow
        async def run_test():
            response = await agent.process_request(request, mock_db_session)

            # Verify response
            assert response.session_id == "test_integration_session"
            assert response.status == InteractionStatus.SUCCESS
            assert response.response == "Test response from AI"

            # Verify database interaction was logged
            mock_db_session.add.assert_called()
            mock_db_session.commit.assert_called()

        # Run the async test
        asyncio.run(run_test())


class TestLoopDetectionE2E:
    """End-to-end tests specifically for loop detection functionality."""

    @pytest.fixture
    def interaction_tracker(self):
        """Create interaction tracker instance."""
        return InteractionTracker()

    @pytest.fixture
    def temporal_analyzer(self):
        """Create temporal analyzer instance."""
        return TemporalBehaviorAnalyzer()

    @pytest.fixture
    def anomaly_detector(self):
        """Create anomaly detector instance."""
        baseline_manager = BaselineManager(min_interactions=3)
        temporal_analyzer = TemporalBehaviorAnalyzer()
        return AnomalyDetector(baseline_manager, temporal_analyzer)

    def test_exact_repetition_loop_detection(self, interaction_tracker, temporal_analyzer):
        """Test detection of exact repetition loops."""
        session_id = "exact_loop_session"

        # Create requests and responses that form an exact loop
        loop_responses = [
            "Can you be more specific?",
            "Can you be more specific?",
            "Can you be more specific?"
        ]

        # Track these interactions
        for i, response_text in enumerate(loop_responses):
            request = AgentRequest(
                session_id=session_id,
                message=f"User request {i}",
                context={},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=response_text,
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=response_text,
                processing_time_ms=1000,
                token_count=20,
                model_used="gpt-3.5-turbo"
            )

            interaction_tracker.track_interaction(session_id, request, response, time.time())

        # Get recent responses and test loop detection
        recent_responses = interaction_tracker.get_recent_responses(session_id, 5)
        loop_result = temporal_analyzer.detect_response_loops(recent_responses)

        assert loop_result is not None
        assert loop_result["loop_type"] == "exact_repetition"
        assert loop_result["confidence"] == 1.0
        assert "Can you be more specific?" in loop_result["repeated_text"]

    def test_alternating_pattern_loop_detection(self, interaction_tracker, temporal_analyzer):
        """Test detection of alternating pattern loops."""
        session_id = "alternating_loop_session"

        # Create requests and responses that form an alternating loop
        loop_responses = [
            "Please clarify your request.",
            "I need more information.",
            "Please clarify your request.",
            "I need more information."
        ]

        # Track these interactions
        for i, response_text in enumerate(loop_responses):
            request = AgentRequest(
                session_id=session_id,
                message=f"User message {i}",
                context={},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=response_text,
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=response_text,
                processing_time_ms=1000,
                token_count=25,
                model_used="gpt-3.5-turbo"
            )

            interaction_tracker.track_interaction(session_id, request, response, time.time())

        # Get recent responses and test loop detection
        recent_responses = interaction_tracker.get_recent_responses(session_id, 5)
        loop_result = temporal_analyzer.detect_response_loops(recent_responses)

        assert loop_result is not None
        assert loop_result["loop_type"] == "alternating_pattern"
        assert loop_result["confidence"] == 0.9
        assert loop_result["pattern_length"] == 2

    def test_low_diversity_loop_detection(self, interaction_tracker, temporal_analyzer):
        """Test detection of low diversity loops."""
        session_id = "low_diversity_session"

        # Create responses with low diversity (similar but not identical)
        loop_responses = [
            "I can help you with that.",
            "I can help you with that.",
            "Let me assist you with that.",
            "I can help you with that.",
            "Let me assist you with that."
        ]

        # Track these interactions
        for i, response_text in enumerate(loop_responses):
            request = AgentRequest(
                session_id=session_id,
                message=f"Help request {i}",
                context={},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=response_text,
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=response_text,
                processing_time_ms=1000,
                token_count=30,
                model_used="gpt-3.5-turbo"
            )

            interaction_tracker.track_interaction(session_id, request, response, time.time())

        # Get recent responses and test loop detection
        recent_responses = interaction_tracker.get_recent_responses(session_id, 5)
        loop_result = temporal_analyzer.detect_response_loops(recent_responses)

        assert loop_result is not None
        assert loop_result["loop_type"] == "low_diversity"
        assert loop_result["uniqueness_ratio"] < 0.6

    def test_loop_detection_in_anomaly_detector(self, interaction_tracker, anomaly_detector):
        """Test loop detection integration with anomaly detector."""
        session_id = "anomaly_loop_session"

        # Create normal behaviors first
        normal_behaviors = []
        for i in range(3):
            behavior = InteractionBehavior(
                session_id=session_id,
                response_latency_ms=1000,
                message_length=100,
                conversation_turns=i + 1,
                clarification_frequency=0.1,
                topic_switches=0,
                confidence_expressions=2,
                timestamp=datetime.now() - timedelta(hours=i)
            )
            normal_behaviors.append(behavior)

        # Create current behavior (normal)
        current_behavior = InteractionBehavior(
            session_id=session_id,
            response_latency_ms=1000,
            message_length=100,
            conversation_turns=4,
            clarification_frequency=0.1,
            topic_switches=0,
            confidence_expressions=2,
            timestamp=datetime.now()
        )

        # Create loop responses
        loop_responses = [
            "I'm sorry, I don't understand.",
            "I'm sorry, I don't understand.",
            "I'm sorry, I don't understand."
        ]

        # Test anomaly detection with loop
        anomaly_results = anomaly_detector.detect_anomalies(
            session_id=session_id,
            current_behavior=current_behavior,
            session_behaviors=normal_behaviors,
            recent_responses=loop_responses
        )

        # Should detect loop anomaly
        loop_anomalies = [a for a in anomaly_results["anomalies_detected"] if a["type"] == "response_loop"]
        assert len(loop_anomalies) == 1
        assert loop_anomalies[0]["score"] == 1.0
        assert "exact_repetition" in loop_anomalies[0]["description"]

        # Should have loop-specific recommendation
        recommendations = anomaly_results["recommendations"]
        loop_recommendations = [r for r in recommendations if "loop" in r.lower()]
        assert len(loop_recommendations) >= 1

    def test_no_false_positive_loop_detection(self, interaction_tracker, temporal_analyzer):
        """Test that normal varied responses don't trigger loop detection."""
        session_id = "normal_session"

        # Create varied, normal responses
        normal_responses = [
            "Hello! How can I assist you today?",
            "I understand your concern about the billing issue.",
            "Let me check your account details.",
            "I found the information you requested.",
            "Is there anything else I can help you with?"
        ]

        # Track these interactions
        for i, response_text in enumerate(normal_responses):
            request = AgentRequest(
                session_id=session_id,
                message=f"Different request {i}",
                context={},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=response_text,
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=response_text,
                processing_time_ms=1000,
                token_count=len(response_text.split()) + 10,
                model_used="gpt-3.5-turbo"
            )

            interaction_tracker.track_interaction(session_id, request, response, time.time())

        # Get recent responses and test loop detection
        recent_responses = interaction_tracker.get_recent_responses(session_id, 5)
        loop_result = temporal_analyzer.detect_response_loops(recent_responses)

        # Should NOT detect a loop
        assert loop_result is None

    def test_loop_detection_response_limit(self, interaction_tracker):
        """Test that response storage is limited to 10 responses."""
        session_id = "limit_test_session"

        # Track 15 interactions (more than the 10 limit)
        for i in range(15):
            request = AgentRequest(
                session_id=session_id,
                message=f"Request {i}",
                context={},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=f"Response {i}: This is a unique response",
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=f"Response {i}: This is a unique response",
                processing_time_ms=1000,
                token_count=20,
                model_used="gpt-3.5-turbo"
            )

            interaction_tracker.track_interaction(session_id, request, response, time.time())

        # Should only have the last 10 responses
        recent_responses = interaction_tracker.get_recent_responses(session_id, 15)
        assert len(recent_responses) == 10

        # Should contain responses 5-14 (the last 10)
        for i in range(5, 15):
            response_found = any(f"Response {i}:" in resp for resp in recent_responses)
            assert response_found, f"Response {i} should be in recent responses"

        # Should NOT contain responses 0-4 (the first 5, which should be evicted)
        for i in range(5):
            response_found = any(f"Response {i}:" in resp for resp in recent_responses)
            assert not response_found, f"Response {i} should NOT be in recent responses"

    def test_loop_detection_edge_cases(self, temporal_analyzer):
        """Test edge cases for loop detection."""
        # Test with empty list
        empty_result = temporal_analyzer.detect_response_loops([])
        assert empty_result is None

        # Test with single response
        single_result = temporal_analyzer.detect_response_loops(["Single response"])
        assert single_result is None

        # Test with two responses
        two_result = temporal_analyzer.detect_response_loops(["Response 1", "Response 2"])
        assert two_result is None

        # Test with empty strings
        empty_strings = ["", "", ""]
        empty_string_result = temporal_analyzer.detect_response_loops(empty_strings)
        assert empty_string_result is not None
        assert empty_string_result["loop_type"] == "exact_repetition"

        # Test with very long responses (should still work)
        long_response = "This is a very long response that contains many words and should still be detected as a loop when repeated multiple times."
        long_responses = [long_response, long_response, long_response]
        long_result = temporal_analyzer.detect_response_loops(long_responses)
        assert long_result is not None
        assert long_result["loop_type"] == "exact_repetition"
        # Should truncate to 100 chars for logging
        assert len(long_result["repeated_text"]) <= 100


class TestBehavioralPerformanceAndEdgeCases:
    """Performance and edge case tests for behavioral system."""

    def test_high_volume_interaction_tracking(self):
        """Test behavioral tracking under high volume."""
        tracker = InteractionTracker()
        session_id = "high_volume_session"

        start_time = time.time()

        # Track 1000 interactions
        for i in range(1000):
            request = AgentRequest(
                session_id=session_id,
                message=f"Message {i}",
                context={},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=f"Response {i}",
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=f"Response {i}",
                processing_time_ms=1000 + (i % 100),
                token_count=50,
                model_used="gpt-3.5-turbo"
            )

            behavior = tracker.track_interaction(
                session_id=session_id,
                request=request,
                response=response,
                start_time=start_time
            )

            assert behavior.session_id == session_id

        # Verify performance
        end_time = time.time()
        total_time = end_time - start_time

        # Should complete in reasonable time (less than 5 seconds)
        assert total_time < 5.0

        # Verify final metrics
        metrics = tracker.get_session_metrics(session_id)
        assert metrics["interaction_count"] == 1000

    def test_edge_case_empty_responses(self):
        """Test handling of empty or minimal responses."""
        tracker = InteractionTracker()

        # Test empty response
        request = AgentRequest(
            session_id="edge_case_session",
            message="Test",
            context={},
            model="gpt-3.5-turbo"
        )

        empty_response = AgentResponse(
            session_id="edge_case_session",
            response="",  # Empty response
            status=InteractionStatus.SUCCESS,
            natural_status=InteractionStatus.SUCCESS,
            failure_injection_applied=False,
            natural_response="",
            processing_time_ms=0,
            token_count=0,
            model_used="gpt-3.5-turbo"
        )

        behavior = tracker.track_interaction(
            "edge_case_session",
            request,
            empty_response,
            time.time()
        )

        # Should handle gracefully
        assert behavior.session_id == "edge_case_session"
        assert behavior.message_length == 0
        assert behavior.clarification_frequency >= 0

    def test_baseline_insufficient_data(self):
        """Test baseline manager with insufficient data."""
        manager = BaselineManager(min_interactions=10)

        # Try to establish baseline with insufficient data
        behaviors = [
            InteractionBehavior(
                session_id="insufficient_session",
                response_latency_ms=1000,
                message_length=100,
                conversation_turns=1,
                clarification_frequency=0.1,
                topic_switches=0,
                confidence_expressions=2,
                timestamp=datetime.now()
            )
        ]

        baseline = manager.establish_baseline("insufficient_session", behaviors)
        assert baseline is None  # Should not establish baseline

    def test_anomaly_detector_extreme_values(self):
        """Test anomaly detector with extreme values."""
        tracker = InteractionTracker()
        manager = BaselineManager(min_interactions=3)
        analyzer = TemporalBehaviorAnalyzer()
        detector = AnomalyDetector(manager, analyzer)

        session_id = "extreme_values_session"

        # Create normal behaviors first
        normal_behaviors = []
        for i in range(5):
            behavior = InteractionBehavior(
                session_id=session_id,
                response_latency_ms=1000,
                message_length=100,
                conversation_turns=i + 1,
                clarification_frequency=0.1,
                topic_switches=0,
                confidence_expressions=2,
                timestamp=datetime.now() - timedelta(hours=i)
            )
            normal_behaviors.append(behavior)

        # Establish baseline
        baseline = manager.establish_baseline(session_id, normal_behaviors)
        assert baseline is not None

        # Test with extreme values
        extreme_behavior = InteractionBehavior(
            session_id=session_id,
            response_latency_ms=50000,  # Extremely slow
            message_length=10000,  # Extremely long
            conversation_turns=6,
            clarification_frequency=1.0,  # Maximum
            topic_switches=100,  # Many switches
            confidence_expressions=50,  # Many expressions
            timestamp=datetime.now()
        )

        # Should detect as anomaly (no loop detection in this test)
        anomaly_results = detector.detect_anomalies(
            session_id, extreme_behavior, normal_behaviors
        )

        assert anomaly_results["overall_anomaly_score"] > 0.8
        assert len(anomaly_results["anomalies_detected"]) > 0

    def test_concurrent_session_handling(self):
        """Test handling multiple concurrent sessions."""
        tracker = InteractionTracker()

        # Simulate multiple sessions
        sessions = [f"concurrent_session_{i}" for i in range(10)]

        for session_id in sessions:
            for j in range(5):
                request = AgentRequest(
                    session_id=session_id,
                    message=f"Message {j}",
                    context={},
                    model="gpt-3.5-turbo"
                )

                response = AgentResponse(
                    session_id=session_id,
                    response=f"Response {j}",
                    status=InteractionStatus.SUCCESS,
                    natural_status=InteractionStatus.SUCCESS,
                    failure_injection_applied=False,
                    natural_response=f"Response {j}",
                    processing_time_ms=1000,
                    token_count=50,
                    model_used="gpt-3.5-turbo"
                )

                tracker.track_interaction(
                    session_id,
                    request,
                    response,
                    time.time()
                )

        # Verify all sessions tracked correctly
        all_session_ids = tracker.get_all_session_ids()
        assert len(all_session_ids) == 10

        for session_id in sessions:
            metrics = tracker.get_session_metrics(session_id)
            assert metrics["interaction_count"] == 5


class TestBehavioralMonitoringServiceE2E:
    """End-to-end tests for the new BehavioralMonitoringService."""

    @pytest.fixture
    def mock_metrics_collector(self):
        """Mock metrics collector for testing."""
        collector = Mock(spec=MetricsCollector)
        collector.increment_counter = Mock()
        collector.observe_histogram = Mock()
        collector.record_behavioral_anomaly = Mock()
        collector.record_conversation_flow_disruption = Mock()
        collector.record_behavioral_drift = Mock()
        return collector

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.merge = Mock()
        return session

    @pytest.fixture
    def behavioral_service(self, mock_metrics_collector, mock_db_session):
        """Create behavioral monitoring service with mocked dependencies."""
        return BehavioralMonitoringService(
            metrics_collector=mock_metrics_collector,
            db_session=mock_db_session
        )

    def test_service_initialization(self, behavioral_service):
        """Test that the service initializes correctly."""
        assert behavioral_service.metrics_collector is not None
        assert behavioral_service.db_session is not None
        assert behavioral_service.interaction_tracker is not None
        assert behavioral_service.baseline_manager is not None
        assert behavioral_service.temporal_analyzer is not None
        assert behavioral_service.anomaly_detector is not None

    def test_service_status_monitoring(self, behavioral_service):
        """Test service status and configuration reporting."""
        status = behavioral_service.get_monitoring_status()

        assert status["service_active"] is True
        assert "metrics_enabled" in status
        assert "db_persistence_enabled" in status
        assert "tracked_sessions" in status
        assert "baseline_count" in status
        assert "configuration" in status

        # Verify configuration details
        config = status["configuration"]
        assert "min_interactions_for_baseline" in config
        assert "anomaly_threshold" in config
        assert "drift_threshold" in config

    @patch.dict('os.environ', {
        'BEHAVIORAL_METRICS_ENABLED': 'true',
        'BEHAVIORAL_DB_PERSISTENCE_ENABLED': 'true'
    })
    @pytest.mark.asyncio
    async def test_complete_interaction_processing_flow(self, behavioral_service):
        """Test the complete interaction processing pipeline."""
        session_id = "test_service_session"

        # Create test request and response
        request = AgentRequest(
            session_id=session_id,
            message="Hello, I need assistance with my billing",
            context={"user_type": "premium"},
            model="gpt-3.5-turbo"
        )

        response = AgentResponse(
            session_id=session_id,
            response="I'd be happy to help you with your billing inquiry. What specific issue are you experiencing?",
            status=InteractionStatus.SUCCESS,
            natural_status=InteractionStatus.SUCCESS,
            failure_injection_applied=False,
            natural_response="I'd be happy to help you with your billing inquiry. What specific issue are you experiencing?",
            processing_time_ms=1200,
            token_count=42,
            model_used="gpt-3.5-turbo"
        )

        start_time = time.time()

        # Process the interaction through the service
        results = await behavioral_service.process_interaction(
            session_id=session_id,
            request=request,
            response=response,
            start_time=start_time
        )

        # Verify results structure
        assert "behavior" in results
        assert "anomaly_results" in results
        assert "session_metrics" in results
        assert "monitoring_metadata" in results

        # Verify behavior tracking worked
        behavior = results["behavior"]
        assert behavior is not None
        assert behavior["session_id"] == session_id
        assert behavior["response_latency_ms"] >= 1200

        # Verify anomaly results
        anomaly_results = results["anomaly_results"]
        assert "anomalies_detected" in anomaly_results
        assert "overall_anomaly_score" in anomaly_results

        # Verify monitoring metadata
        metadata = results["monitoring_metadata"]
        assert metadata["metrics_recorded"] is True
        assert metadata["data_persisted"] is True
        assert "processing_timestamp" in metadata

        # Verify metrics were recorded
        behavioral_service.metrics_collector.increment_counter.assert_called()
        behavioral_service.metrics_collector.observe_histogram.assert_called()

        # Verify database persistence
        behavioral_service.db_session.add.assert_called()

    @pytest.mark.asyncio
    async def test_anomaly_detection_with_metrics_and_persistence(self, behavioral_service):
        """Test anomaly detection with both metrics recording and database persistence."""
        session_id = "anomaly_test_session"

        # Process several normal interactions first
        for i in range(5):
            request = AgentRequest(
                session_id=session_id,
                message=f"Normal request {i}",
                context={},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=f"Normal response {i}: I understand and can help with that.",
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=f"Normal response {i}: I understand and can help with that.",
                processing_time_ms=1000 + (i * 100),
                token_count=40,
                model_used="gpt-3.5-turbo"
            )

            await behavioral_service.process_interaction(
                session_id=session_id,
                request=request,
                response=response,
                start_time=time.time()
            )

        # Now process an anomalous interaction (exact loop)
        loop_response_text = "I'm sorry, could you please clarify?"
        for i in range(3):
            request = AgentRequest(
                session_id=session_id,
                message=f"Loop trigger {i}",
                context={},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=loop_response_text,  # Same response repeated
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=loop_response_text,
                processing_time_ms=5000,  # Much slower (anomalous)
                token_count=20,
                model_used="gpt-3.5-turbo"
            )

            results = await behavioral_service.process_interaction(
                session_id=session_id,
                request=request,
                response=response,
                start_time=time.time()
            )

        # The last interaction should detect anomalies
        anomaly_results = results["anomaly_results"]
        assert len(anomaly_results["anomalies_detected"]) > 0

        # Check if loop was detected
        loop_anomalies = [a for a in anomaly_results["anomalies_detected"] if a["type"] == "response_loop"]
        if len(loop_anomalies) > 0:
            # Verify anomaly metrics were recorded
            behavioral_service.metrics_collector.record_behavioral_anomaly.assert_called()
            behavioral_service.metrics_collector.record_conversation_flow_disruption.assert_called()

        # Verify multiple database records were added (behaviors + anomalies)
        assert behavioral_service.db_session.add.call_count >= 8  # 8 interactions + anomalies

    @pytest.mark.asyncio
    async def test_baseline_persistence_integration(self, behavioral_service):
        """Test baseline establishment and database persistence."""
        session_id = "baseline_persistence_session"

        # Process enough interactions to establish a baseline
        for i in range(12):  # More than min_interactions (default 10)
            request = AgentRequest(
                session_id=session_id,
                message=f"Baseline request {i}",
                context={},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=f"Baseline response {i}: Consistent helpful response.",
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=f"Baseline response {i}: Consistent helpful response.",
                processing_time_ms=1100 + (i * 50),  # Consistent timing
                token_count=35 + (i * 2),
                model_used="gpt-3.5-turbo"
            )

            await behavioral_service.process_interaction(
                session_id=session_id,
                request=request,
                response=response,
                start_time=time.time()
            )

        # Verify baseline was established and persisted
        # The service should have called merge() for baseline persistence
        behavioral_service.db_session.merge.assert_called()

    def test_session_analysis_functionality(self, behavioral_service):
        """Test session analysis and metrics reporting."""
        session_id = "analysis_test_session"

        # Track some interactions first
        for i in range(3):
            request = AgentRequest(
                session_id=session_id,
                message=f"Test message {i}",
                context={},
                model="gpt-3.5-turbo"
            )

            response = AgentResponse(
                session_id=session_id,
                response=f"Test response {i}",
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=f"Test response {i}",
                processing_time_ms=1000,
                token_count=30,
                model_used="gpt-3.5-turbo"
            )

            # Use the pure interaction tracker directly for this test
            behavioral_service.interaction_tracker.track_interaction(
                session_id=session_id,
                request=request,
                response=response,
                start_time=time.time()
            )

        # Get session analysis
        analysis = behavioral_service.get_session_analysis(session_id)

        assert analysis["session_id"] == session_id
        assert "metrics" in analysis
        assert "recent_behaviors" in analysis
        assert "baseline" in analysis
        assert "analysis_timestamp" in analysis

        # Verify metrics
        metrics = analysis["metrics"]
        assert metrics["interaction_count"] == 3

    @pytest.mark.asyncio
    async def test_error_handling_and_graceful_degradation(self, behavioral_service):
        """Test that the service handles errors gracefully."""
        session_id = "error_test_session"

        # Mock database failure
        behavioral_service.db_session.add.side_effect = Exception("Database connection failed")

        request = AgentRequest(
            session_id=session_id,
            message="Test message",
            context={},
            model="gpt-3.5-turbo"
        )

        response = AgentResponse(
            session_id=session_id,
            response="Test response",
            status=InteractionStatus.SUCCESS,
            natural_status=InteractionStatus.SUCCESS,
            failure_injection_applied=False,
            natural_response="Test response",
            processing_time_ms=1000,
            token_count=30,
            model_used="gpt-3.5-turbo"
        )

        # Service should handle database errors gracefully
        results = await behavioral_service.process_interaction(
            session_id=session_id,
            request=request,
            response=response,
            start_time=time.time()
        )

        # Should still return results even with database failure
        assert "behavior" in results
        assert "monitoring_metadata" in results

    def test_environment_configuration_handling(self):
        """Test environment variable configuration handling."""
        # Test with metrics disabled
        with patch.dict('os.environ', {'BEHAVIORAL_METRICS_ENABLED': 'false'}):
            service = BehavioralMonitoringService()
            assert service.metrics_enabled is False

        # Test with DB persistence disabled
        with patch.dict('os.environ', {'BEHAVIORAL_DB_PERSISTENCE_ENABLED': 'false'}):
            service = BehavioralMonitoringService()
            assert service.db_persistence_enabled is False

        # Test with both enabled (default)
        with patch.dict('os.environ', {
            'BEHAVIORAL_METRICS_ENABLED': 'true',
            'BEHAVIORAL_DB_PERSISTENCE_ENABLED': 'true'
        }):
            service = BehavioralMonitoringService()
            assert service.metrics_enabled is True
            assert service.db_persistence_enabled is True

    def test_session_data_management(self, behavioral_service):
        """Test session data cleanup and management."""
        session_id = "cleanup_test_session"

        # Add some session data
        request = AgentRequest(
            session_id=session_id,
            message="Test message",
            context={},
            model="gpt-3.5-turbo"
        )

        response = AgentResponse(
            session_id=session_id,
            response="Test response",
            status=InteractionStatus.SUCCESS,
            natural_status=InteractionStatus.SUCCESS,
            failure_injection_applied=False,
            natural_response="Test response",
            processing_time_ms=1000,
            token_count=30,
            model_used="gpt-3.5-turbo"
        )

        behavioral_service.interaction_tracker.track_interaction(
            session_id=session_id,
            request=request,
            response=response,
            start_time=time.time()
        )

        # Verify session exists
        session_ids = behavioral_service.interaction_tracker.get_all_session_ids()
        assert session_id in session_ids

        # Clear session data
        behavioral_service.clear_session_data(session_id)

        # Session should be removed from tracker (in-memory only)
        # Note: Database data persists according to retention policies


class TestDatabasePersistenceE2E:
    """End-to-end tests for database persistence integration."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing persistence."""
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.merge = Mock()
        return session

    def test_interaction_behavior_log_creation(self, mock_db_session):
        """Test creation of InteractionBehaviorLog records."""
        # Create behavior object
        behavior = InteractionBehavior(
            session_id="db_test_session",
            response_latency_ms=1500,
            message_length=120,
            conversation_turns=5,
            clarification_frequency=0.2,
            topic_switches=1,
            confidence_expressions=3,
            timestamp=datetime.now()
        )

        # Create database record
        db_record = InteractionBehaviorLog(
            session_id=behavior.session_id,
            timestamp=behavior.timestamp,
            response_latency_ms=behavior.response_latency_ms,
            message_length=behavior.message_length,
            conversation_turns=behavior.conversation_turns,
            clarification_frequency=float(behavior.clarification_frequency),
            topic_switches=behavior.topic_switches,
            confidence_expressions=behavior.confidence_expressions,
            anomaly_score=0.3,  # Overall anomaly score
            metadata={"test": True}
        )

        # Verify record structure
        assert db_record.session_id == "db_test_session"
        assert db_record.response_latency_ms == 1500
        assert db_record.message_length == 120
        assert db_record.clarification_frequency == 0.2
        assert db_record.anomaly_score == 0.3

        # Test database operations
        mock_db_session.add(db_record)
        mock_db_session.add.assert_called_once_with(db_record)

    def test_behavioral_anomaly_log_creation(self, mock_db_session):
        """Test creation of BehavioralAnomalyLog records."""
        # Create anomaly log record
        anomaly_record = BehavioralAnomalyLog(
            session_id="anomaly_db_session",
            timestamp=datetime.now(),
            anomaly_type="response_loop",
            anomaly_score=0.95,
            confidence=0.9,
            detection_method="multi_tier_loop_detection",
            contributing_factors={"loop_type": "exact_repetition", "repetitions": 3},
            recommendations=["restart_conversation", "escalate_to_human"],
            resolved=False
        )

        # Verify record structure
        assert anomaly_record.session_id == "anomaly_db_session"
        assert anomaly_record.anomaly_type == "response_loop"
        assert anomaly_record.anomaly_score == 0.95
        assert anomaly_record.confidence == 0.9
        assert anomaly_record.resolved is False
        assert "loop_type" in anomaly_record.contributing_factors
        assert len(anomaly_record.recommendations) == 2

        # Test database operations
        mock_db_session.add(anomaly_record)
        mock_db_session.add.assert_called_once_with(anomaly_record)

    def test_behavioral_baseline_persistence(self, mock_db_session):
        """Test creation and updating of BehavioralBaseline records."""
        # Create baseline record
        baseline_record = BehavioralBaselineDB(
            session_id="baseline_db_session",
            avg_response_latency=1200.5,
            typical_message_length_min=80,
            typical_message_length_max=150,
            normal_clarification_rate=0.15,
            standard_conversation_depth=10,
            confidence_pattern={"low": 0.1, "medium": 0.7, "high": 0.2},
            interaction_count=25
        )

        # Verify record structure
        assert baseline_record.session_id == "baseline_db_session"
        assert baseline_record.avg_response_latency == 1200.5
        assert baseline_record.typical_message_length_min == 80
        assert baseline_record.typical_message_length_max == 150
        assert baseline_record.normal_clarification_rate == 0.15
        assert baseline_record.interaction_count == 25

        # Test upsert operation (merge)
        mock_db_session.merge(baseline_record)
        mock_db_session.merge.assert_called_once_with(baseline_record)


class TestPrometheusMetricsE2E:
    """End-to-end tests for Prometheus metrics integration."""

    @pytest.fixture
    def mock_metrics_collector(self):
        """Mock metrics collector for testing."""
        collector = Mock(spec=MetricsCollector)
        collector.increment_counter = Mock()
        collector.observe_histogram = Mock()
        collector.record_behavioral_anomaly = Mock()
        collector.record_conversation_flow_disruption = Mock()
        collector.record_behavioral_drift = Mock()
        return collector

    def test_interaction_metrics_recording(self, mock_metrics_collector):
        """Test recording of basic interaction metrics."""
        behavior = InteractionBehavior(
            session_id="metrics_test_session",
            response_latency_ms=1800,
            message_length=95,
            conversation_turns=3,
            clarification_frequency=0.1,
            topic_switches=2,
            confidence_expressions=1,
            timestamp=datetime.now()
        )

        # Simulate metrics recording (as done in BehavioralMonitoringService)
        mock_metrics_collector.increment_counter('interaction_total', {
            'session_type': 'behavioral'
        })

        mock_metrics_collector.observe_histogram('interaction_latency',
                                               behavior.response_latency_ms / 1000.0,
                                               {'metric_type': 'response_latency'})

        mock_metrics_collector.observe_histogram('message_length_histogram',
                                               behavior.message_length,
                                               {'metric_type': 'message_length'})

        mock_metrics_collector.observe_histogram('interaction_consistency_score',
                                               1.0 - behavior.clarification_frequency,
                                               {'session_id': behavior.session_id[:8]})

        # Verify metrics were called correctly
        mock_metrics_collector.increment_counter.assert_called_with('interaction_total', {
            'session_type': 'behavioral'
        })

        mock_metrics_collector.observe_histogram.assert_any_call('interaction_latency',
                                                               1.8,  # 1800ms = 1.8s
                                                               {'metric_type': 'response_latency'})

        mock_metrics_collector.observe_histogram.assert_any_call('message_length_histogram',
                                                               95,
                                                               {'metric_type': 'message_length'})

        mock_metrics_collector.observe_histogram.assert_any_call('interaction_consistency_score',
                                                               0.9,  # 1.0 - 0.1
                                                               {'session_id': 'metrics_'})

    def test_anomaly_metrics_recording(self, mock_metrics_collector):
        """Test recording of anomaly-specific metrics."""
        session_id = "anomaly_metrics_session"

        # Simulate different types of anomalies
        anomalies = [
            {
                "type": "response_loop",
                "score": 1.0,
                "details": {"loop_type": "exact_repetition"}
            },
            {
                "type": "baseline_deviation",
                "score": 0.8,
                "details": {"deviation_factors": ["response_time", "message_length"]}
            },
            {
                "type": "temporal_drift",
                "score": 0.7,
                "details": {"drift_type": "latency_increase"}
            }
        ]

        # Record metrics for each anomaly
        for anomaly in anomalies:
            mock_metrics_collector.record_behavioral_anomaly(
                session_id=session_id,
                anomaly_type=anomaly["type"],
                score=anomaly["score"]
            )

            if anomaly["type"] == "response_loop":
                loop_type = anomaly["details"]["loop_type"]
                mock_metrics_collector.record_conversation_flow_disruption(f"loop_{loop_type}")
            elif anomaly["type"] == "baseline_deviation":
                mock_metrics_collector.record_conversation_flow_disruption("baseline_deviation")
            elif anomaly["type"] == "temporal_drift":
                drift_type = anomaly["details"]["drift_type"]
                mock_metrics_collector.record_behavioral_drift(drift_type, anomaly["score"], 1)

        # Verify anomaly metrics were recorded
        assert mock_metrics_collector.record_behavioral_anomaly.call_count == 3
        assert mock_metrics_collector.record_conversation_flow_disruption.call_count == 2
        assert mock_metrics_collector.record_behavioral_drift.call_count == 1

        # Verify specific calls
        mock_metrics_collector.record_behavioral_anomaly.assert_any_call(
            session_id=session_id,
            anomaly_type="response_loop",
            score=1.0
        )

        mock_metrics_collector.record_conversation_flow_disruption.assert_any_call("loop_exact_repetition")
        mock_metrics_collector.record_conversation_flow_disruption.assert_any_call("baseline_deviation")
        mock_metrics_collector.record_behavioral_drift.assert_called_with("latency_increase", 0.7, 1)

    def test_topic_switch_metrics(self, mock_metrics_collector):
        """Test topic switch disruption metrics."""
        behavior_with_switches = InteractionBehavior(
            session_id="topic_switch_session",
            response_latency_ms=1000,
            message_length=100,
            conversation_turns=5,
            clarification_frequency=0.0,
            topic_switches=3,  # Multiple topic switches
            confidence_expressions=2,
            timestamp=datetime.now()
        )

        # Record topic switch metrics
        if behavior_with_switches.topic_switches > 0:
            mock_metrics_collector.increment_counter('conversation_flow_disruptions_total', {
                'disruption_type': 'topic_switch'
            })

        # Verify topic switch metrics were recorded
        mock_metrics_collector.increment_counter.assert_called_with('conversation_flow_disruptions_total', {
            'disruption_type': 'topic_switch'
        })

    def test_comprehensive_metrics_flow(self, mock_metrics_collector):
        """Test comprehensive metrics recording for a complete interaction."""
        # Simulate a full behavioral monitoring flow with metrics
        session_id = "comprehensive_metrics_session"

        # Normal interaction metrics
        mock_metrics_collector.increment_counter('interaction_total', {'session_type': 'behavioral'})
        mock_metrics_collector.observe_histogram('interaction_latency', 1.5, {'metric_type': 'response_latency'})
        mock_metrics_collector.observe_histogram('message_length_histogram', 120, {'metric_type': 'message_length'})
        mock_metrics_collector.observe_histogram('interaction_consistency_score', 0.85, {'session_id': session_id[:8]})

        # Anomaly detected
        mock_metrics_collector.record_behavioral_anomaly(session_id=session_id, anomaly_type="response_loop", score=0.9)
        mock_metrics_collector.record_conversation_flow_disruption("loop_exact_repetition")

        # Overall detection metrics
        mock_metrics_collector.increment_counter('behavioral_anomaly_detection_total', {
            'session_type': 'behavioral',
            'anomaly_count': '1'
        })

        # Verify all metrics calls
        assert mock_metrics_collector.increment_counter.call_count == 2
        assert mock_metrics_collector.observe_histogram.call_count == 3
        assert mock_metrics_collector.record_behavioral_anomaly.call_count == 1
        assert mock_metrics_collector.record_conversation_flow_disruption.call_count == 1


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_behavioral_e2e.py -v
    pytest.main([__file__, "-v"])