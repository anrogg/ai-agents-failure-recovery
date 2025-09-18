import random
import time
import asyncio
from typing import Dict, Any, Optional, Tuple
import structlog
from .models import FailureMode, FailureType

logger = structlog.get_logger(__name__)


class FailureInjector:
    def __init__(self, probabilistic_mode: bool = False, failure_rate_multiplier: float = 1.0):
        """
        Initialize FailureInjector with dual-mode support.

        Args:
            probabilistic_mode: If True, enables random failure injection based on probabilities
            failure_rate_multiplier: Multiplier for all failure probabilities (1.0 = normal rates)
        """
        self.probabilistic_mode = probabilistic_mode
        self.failure_rate_multiplier = failure_rate_multiplier

        self.failure_scenarios = {
            # Output Quality Failures
            FailureMode.HALLUCINATION: {
                "type": FailureType.OUTPUT_QUALITY,
                "probability": 0.3,
                "responses": [
                    "Our premium service includes quantum encryption and time-travel backup features.",
                    "According to the recent study by the Institute of Digital Wellness (which doesn't exist), 95% of users prefer this approach.",
                    "This feature was actually invented by Steve Jobs in 2025 during his posthumous innovation period.",
                    "The algorithm uses advanced AI trained on data from parallel universes to ensure accuracy."
                ]
            },
            FailureMode.INCORRECT_REASONING: {
                "type": FailureType.OUTPUT_QUALITY,
                "probability": 0.25,
                "logic_errors": [
                    "Since you're having login issues, you should definitely delete your account and create a new one.",
                    "The best way to fix network connectivity is to increase your password complexity.",
                    "If the application is slow, try using it on a different day of the week.",
                    "This error occurs because your computer's time zone is incompatible with our servers."
                ]
            },
            FailureMode.OFF_TOPIC: {
                "type": FailureType.OUTPUT_QUALITY,
                "probability": 0.2,
                "off_topic_responses": [
                    "That reminds me of a great recipe for chocolate chip cookies! Would you like me to share it?",
                    "Speaking of your technical issue, have you considered taking up meditation? It really helps with stress.",
                    "You know, the weather has been quite unpredictable lately. How's the weather where you are?",
                    "This is similar to my favorite movie plot. Have you seen The Matrix? It's all about questioning reality."
                ]
            },
            
            # Behavioral Failures
            FailureMode.INFINITE_LOOP: {
                "type": FailureType.BEHAVIORAL,
                "probability": 0.2,
                "loop_responses": [
                    "Could you please clarify what you mean by that?",
                    "I need a bit more information to help you better.",
                    "Can you provide more details about your specific situation?",
                    "To better assist you, could you elaborate on your request?"
                ],
                "max_iterations": 3
            },
            FailureMode.REFUSING_PROGRESS: {
                "type": FailureType.BEHAVIORAL,
                "probability": 0.15,
                "refusal_responses": [
                    "I'm not comfortable making assumptions about your specific use case.",
                    "This seems like it might require specialized knowledge that I don't possess.",
                    "I'd rather not guess at the solution - you should contact a human expert.",
                    "This is beyond my capabilities and I cannot provide useful assistance."
                ]
            },

            # Integration Failures
            FailureMode.API_TIMEOUT: {
                "type": FailureType.INTEGRATION,
                "probability": 0.1,
                "timeout_range": (5, 15),  # seconds
                "error_message": "External API request timed out"
            },
            FailureMode.AUTH_ERROR: {
                "type": FailureType.INTEGRATION,
                "probability": 0.08,
                "error_message": "Authentication failed: Invalid API key"
            },
            FailureMode.SERVICE_UNAVAILABLE: {
                "type": FailureType.INTEGRATION,
                "probability": 0.12,
                "error_message": "Service temporarily unavailable: 503 Service Unavailable"
            },

            # Resource Failures
            FailureMode.TOKEN_LIMIT: {
                "type": FailureType.RESOURCE,
                "probability": 0.05,
                "token_threshold": 1000,
                "error_message": "Token limit exceeded"
            },
            FailureMode.MEMORY_EXHAUSTION: {
                "type": FailureType.RESOURCE,
                "probability": 0.03,
                "error_message": "Memory limit exceeded: Unable to process request"
            },
            FailureMode.RATE_LIMITING: {
                "type": FailureType.RESOURCE,
                "probability": 0.07,
                "error_message": "Rate limit exceeded: Please try again later"
            }
        }
        
        self.session_states = {}
    
    async def should_inject_failure(self, session_id: str, message: str, failure_mode: Optional[FailureMode] = None) -> Tuple[bool, Optional[FailureMode]]:
        """
        Determine whether to inject a failure.

        Args:
            session_id: Session identifier
            message: User message
            failure_mode: If provided, forces this specific failure mode

        Returns:
            Tuple of (should_inject, failure_mode_to_inject)
        """
        # Case 1: Forced failure mode (maintains backward compatibility)
        if failure_mode:
            logger.info("Forced failure mode activated", session_id=session_id, failure_mode=failure_mode)
            return True, failure_mode

        # Case 2: Probabilistic failure injection
        if self.probabilistic_mode:
            return await self._evaluate_probabilistic_failure(session_id, message)

        # Case 3: Default behavior - no failures
        return False, None

    async def _evaluate_probabilistic_failure(self, session_id: str, message: str) -> Tuple[bool, Optional[FailureMode]]:
        """
        Evaluate whether to inject a failure based on probabilities and session state.
        """
        # Initialize session state if not exists
        if session_id not in self.session_states:
            self.session_states[session_id] = {
                "failure_count": 0,
                "last_failure_time": None,
                "last_failure_mode": None,
                "clarification_requests": 0,
                "message_count": 0
            }

        session_state = self.session_states[session_id]
        session_state["message_count"] += 1

        # Apply cooldown to prevent failure spam
        current_time = time.time()
        if session_state["last_failure_time"]:
            time_since_last_failure = current_time - session_state["last_failure_time"]
            if time_since_last_failure < 30:  # 30 second cooldown
                logger.debug("Failure cooldown active", session_id=session_id,
                           cooldown_remaining=30-time_since_last_failure)
                return False, None

        # Check each failure mode's probability
        for mode, config in self.failure_scenarios.items():
            adjusted_probability = config["probability"] * self.failure_rate_multiplier

            # Special logic for INFINITE_LOOP - increase probability if already in loop pattern
            if mode == FailureMode.INFINITE_LOOP and session_state["clarification_requests"] >= 1:
                adjusted_probability *= 2.0  # Double probability if already looping

            # Reduce probability if same failure mode was used recently
            if session_state["last_failure_mode"] == mode:
                adjusted_probability *= 0.3  # Reduce to 30% to avoid repetition

            # Roll for failure
            if random.random() < adjusted_probability:
                # Update session state
                session_state["failure_count"] += 1
                session_state["last_failure_time"] = current_time
                session_state["last_failure_mode"] = mode

                if mode == FailureMode.INFINITE_LOOP:
                    session_state["clarification_requests"] += 1
                else:
                    session_state["clarification_requests"] = 0  # Reset if not loop

                logger.info("Probabilistic failure triggered",
                           session_id=session_id,
                           failure_mode=mode,
                           probability=adjusted_probability,
                           session_failure_count=session_state["failure_count"])
                return True, mode

        return False, None
    
    async def inject_output_quality_failure(self, session_id: str, failure_mode: FailureMode, original_response: str) -> str:
        config = self.failure_scenarios[failure_mode]
        
        if failure_mode == FailureMode.HALLUCINATION:
            hallucinated_response = random.choice(config["responses"])
            logger.warning("Injecting hallucination", session_id=session_id, original_length=len(original_response))
            return hallucinated_response
        
        elif failure_mode == FailureMode.INCORRECT_REASONING:
            incorrect_response = random.choice(config["logic_errors"])
            logger.warning("Injecting incorrect reasoning", session_id=session_id)
            return incorrect_response
        
        elif failure_mode == FailureMode.OFF_TOPIC:
            off_topic_response = random.choice(config["off_topic_responses"])
            logger.warning("Injecting off-topic response", session_id=session_id)
            return off_topic_response
        
        return original_response
    
    async def inject_behavioral_failure(self, session_id: str, failure_mode: FailureMode, message: str) -> str:
        config = self.failure_scenarios[failure_mode]

        if failure_mode == FailureMode.INFINITE_LOOP:
            loop_response = random.choice(config["loop_responses"])
            logger.warning("Injecting infinite loop behavior", session_id=session_id)
            return loop_response

        elif failure_mode == FailureMode.REFUSING_PROGRESS:
            refusal_response = random.choice(config["refusal_responses"])
            logger.warning("Injecting refusing progress behavior", session_id=session_id)
            return refusal_response

        return "I understand your request and I'm processing it now."
    
    async def inject_integration_failure(self, session_id: str, failure_mode: FailureMode) -> Exception:
        config = self.failure_scenarios[failure_mode]

        if failure_mode == FailureMode.API_TIMEOUT:
            timeout_range = config.get("timeout_range", (5, 15))
            await asyncio.sleep(random.uniform(*timeout_range))  # Simulate slow response
            logger.warning("Injecting API timeout", session_id=session_id)
            raise asyncio.TimeoutError(config["error_message"])

        elif failure_mode == FailureMode.AUTH_ERROR:
            logger.warning("Injecting auth error", session_id=session_id)
            raise Exception(config["error_message"])

        elif failure_mode == FailureMode.SERVICE_UNAVAILABLE:
            logger.warning("Injecting service unavailable", session_id=session_id)
            raise Exception(config["error_message"])
    
    async def inject_resource_failure(self, session_id: str, failure_mode: FailureMode, token_count: int) -> Exception:
        config = self.failure_scenarios[failure_mode]

        if failure_mode == FailureMode.TOKEN_LIMIT:
            threshold = config.get("token_threshold", 1000)
            logger.warning("Injecting token limit exceeded", session_id=session_id, token_count=token_count, threshold=threshold)
            raise Exception(f"{config['error_message']}: {token_count}/{threshold} tokens used")

        elif failure_mode == FailureMode.MEMORY_EXHAUSTION:
            logger.warning("Injecting memory exhaustion", session_id=session_id)
            raise Exception(config["error_message"])

        elif failure_mode == FailureMode.RATE_LIMITING:
            logger.warning("Injecting rate limiting", session_id=session_id)
            raise Exception(config["error_message"])
    
    def reset_session_state(self, session_id: str):
        if session_id in self.session_states:
            del self.session_states[session_id]
            logger.debug("Session state reset", session_id=session_id)