import time
import asyncio
import os
from typing import Dict, Any, Optional
import openai
import tiktoken
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AgentRequest, AgentResponse, InteractionStatus, FailureMode, FailureType
from .failure_injector import FailureInjector
from .redis_client import StateManager
from .database import AgentInteraction, get_db_session
from .metrics import metrics_collector, track_agent_performance

logger = structlog.get_logger(__name__)


class CustomerServiceAgent:
    def __init__(self):
        # Configure failure injection from environment variables
        probabilistic_failures = os.getenv("PROBABILISTIC_FAILURES", "false").lower() == "true"
        failure_rate_multiplier = float(os.getenv("FAILURE_RATE_MULTIPLIER", "1.0"))

        logger.info("Configuring failure injection",
                   probabilistic_mode=probabilistic_failures,
                   failure_rate_multiplier=failure_rate_multiplier)

        self.failure_injector = FailureInjector(
            probabilistic_mode=probabilistic_failures,
            failure_rate_multiplier=failure_rate_multiplier
        )
        self.state_manager = StateManager()

        # Configure AI client with environment variables
        api_key = os.getenv("AI_API_KEY")
        base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")  # Default to OpenAI
        model = os.getenv("AI_MODEL", "gpt-3.5-turbo")
        
        logger.info("Configuring AI client", 
                   base_url=base_url, 
                   model=model, 
                   api_key_configured=bool(api_key and len(api_key) > 10))
        
        self.openai_client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # Configure token encoding based on environment variable
        encoding_name = os.getenv("AI_ENCODING", "cl100k_base")  # Default to modern encoding
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except ValueError:
            logger.warning(f"Unknown encoding '{encoding_name}', falling back to cl100k_base")
            self.encoding = tiktoken.get_encoding("cl100k_base")

    @track_agent_performance(failure_type="chat_completion")
    async def process_request(self, request: AgentRequest, db_session: AsyncSession) -> AgentResponse:
        start_time = time.time()
        
        try:
            # Load agent state from Redis
            agent_state = await self.state_manager.load_state(request.session_id)
            if not agent_state:
                agent_state = {
                    "conversation_history": [],
                    "context": request.context or {},
                    "failure_count": 0,
                    "recovery_count": 0
                }
            
            # Create checkpoint before processing
            await self.state_manager.create_checkpoint(
                request.session_id, 
                "pre_request", 
                agent_state
            )
            
            # Add current message to conversation history
            agent_state["conversation_history"].append({
                "role": "user",
                "content": request.message,
                "timestamp": time.time()
            })
            
            # Check if we should inject a failure
            should_fail, failure_mode = await self.failure_injector.should_inject_failure(
                request.session_id, 
                request.message, 
                request.failure_mode
            )
            
            # Count tokens in conversation
            token_count = self._count_tokens(agent_state["conversation_history"])
            
            # Always generate the natural response first
            natural_response = await self._generate_normal_response(
                request, agent_state, token_count, db_session
            )
            
            # Apply failure injection if needed
            if should_fail and failure_mode:
                response = await self._apply_failure_injection(
                    request, agent_state, failure_mode, natural_response, token_count, db_session
                )
            else:
                response = natural_response
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Update agent state
            agent_state["conversation_history"].append({
                "role": "assistant",
                "content": response.response,
                "timestamp": time.time(),
                "failure_mode": failure_mode.value if failure_mode else None
            })
            
            # Save updated state
            await self.state_manager.save_state(request.session_id, agent_state)
            
            # Log interaction to database
            interaction = AgentInteraction(
                session_id=request.session_id,
                request_data=request.dict(),
                response_data=response.dict(),
                status=response.status.value,
                natural_status=response.natural_status.value,
                failure_mode=failure_mode.value if failure_mode else None,
                failure_injection_applied=response.failure_injection_applied,
                natural_response=response.natural_response,
                processing_time_ms=processing_time,
                token_count=token_count,
                model_used=request.model
            )
            
            db_session.add(interaction)
            await db_session.commit()
            
            return response
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error("Unexpected error in agent processing", 
                        session_id=request.session_id, 
                        error=str(e))
            
            error_response = AgentResponse(
                session_id=request.session_id,
                response=f"I encountered an unexpected error: {str(e)}",
                status=InteractionStatus.ERROR,
                natural_status=InteractionStatus.ERROR,
                failure_injection_applied=False,
                natural_response=None,
                processing_time_ms=processing_time,
                token_count=0,
                model_used=request.model
            )
            
            # Log error interaction
            interaction = AgentInteraction(
                session_id=request.session_id,
                request_data=request.dict(),
                response_data=error_response.dict(),
                status=InteractionStatus.ERROR.value,
                processing_time_ms=processing_time,
                token_count=0,
                model_used=request.model
            )
            
            db_session.add(interaction)
            await db_session.commit()
            
            return error_response
    
    async def _generate_normal_response(
        self, 
        request: AgentRequest, 
        agent_state: Dict[str, Any], 
        token_count: int,
        db_session: AsyncSession
    ) -> AgentResponse:
        try:
            # Prepare messages for OpenAI
            messages = [
                {
                    "role": "system",
                    "content": """You are a helpful customer service agent. You assist users with their questions and problems in a friendly, professional manner. 
                    Keep your responses concise but helpful. If you don't know something, admit it and offer to escalate or find more information."""
                }
            ]
            
            # Add conversation history (limit to recent messages to manage token count)
            recent_history = agent_state["conversation_history"][-6:]  # Last 3 exchanges
            for msg in recent_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Make OpenAI API call
            logger.info("Making LLM API call", 
                       session_id=request.session_id, 
                       model=request.model, 
                       base_url=self.openai_client.base_url,
                       message_count=len(messages))
            
            response = await self.openai_client.chat.completions.create(
                model=request.model,
                messages=messages,
                max_tokens=min(request.max_tokens or 500, 500),
                temperature=0.7
            )

            # Add token tracking if you have access to usage data
            try:
                if hasattr(response, 'usage') and response.usage:
                    metrics_collector.record_token_usage(
                        model=request.model or "gpt-3.5-turbo",
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens
                    )
            except Exception as e:
                logger.warning(f"Failed to record token metrics: {e}")

            logger.info("LLM API call successful",
                       session_id=request.session_id,
                       response_length=len(response.choices[0].message.content) if response.choices else 0)
            
            agent_response = response.choices[0].message.content
            
            return AgentResponse(
                session_id=request.session_id,
                response=agent_response,
                status=InteractionStatus.SUCCESS,
                natural_status=InteractionStatus.SUCCESS,
                failure_injection_applied=False,
                natural_response=agent_response,
                processing_time_ms=0,  # Will be set by caller
                token_count=token_count,
                model_used=request.model
            )
            
        except openai.APITimeoutError as e:
            metrics_collector.record_failure_injection("api_timeout", "natural")
            return await self._handle_api_timeout(request, str(e))
        except openai.RateLimitError as e:
            metrics_collector.record_failure_injection("rate_limiting", "natural")
            return await self._handle_rate_limit(request, str(e))
        except Exception as e:
            metrics_collector.record_failure_injection("unknown_error", "natural")
            logger.error("OpenAI API error", session_id=request.session_id, error=str(e))
            return AgentResponse(
                session_id=request.session_id,
                response="I'm sorry, I'm having trouble processing your request right now. Please try again in a moment.",
                status=InteractionStatus.FAILURE,
                natural_status=InteractionStatus.FAILURE,
                failure_injection_applied=False,
                natural_response="I'm sorry, I'm having trouble processing your request right now. Please try again in a moment.",
                processing_time_ms=0,
                token_count=token_count,
                model_used=request.model,
                failure_mode=FailureMode.SERVICE_UNAVAILABLE
            )
    
    async def _apply_failure_injection(
        self,
        request: AgentRequest,
        agent_state: Dict[str, Any],
        failure_mode: FailureMode,
        natural_response: AgentResponse,
        token_count: int,
        db_session: AsyncSession
    ) -> AgentResponse:
        agent_state["failure_count"] += 1
        await self.state_manager.track_failure_count(request.session_id)

        # Record the failure injection in metrics
        metrics_collector.record_failure_injection(failure_mode.value, "injected")

        try:
            failure_type = self.failure_injector.failure_scenarios[failure_mode]["type"]
            
            if failure_type == FailureType.OUTPUT_QUALITY:
                failed_response_text = await self.failure_injector.inject_output_quality_failure(
                    request.session_id, failure_mode, natural_response.response
                )
                status = InteractionStatus.FAILURE
                
            elif failure_type == FailureType.BEHAVIORAL:
                failed_response_text = await self.failure_injector.inject_behavioral_failure(
                    request.session_id, failure_mode, request.message
                )
                status = InteractionStatus.FAILURE
                
            elif failure_type == FailureType.INTEGRATION:
                await self.failure_injector.inject_integration_failure(
                    request.session_id, failure_mode
                )
                # This should raise an exception, but in case it doesn't:
                failed_response_text = "Integration failure occurred"
                status = InteractionStatus.ERROR
                
            elif failure_type == FailureType.RESOURCE:
                await self.failure_injector.inject_resource_failure(
                    request.session_id, failure_mode, token_count
                )
                # This should raise an exception, but in case it doesn't:
                failed_response_text = "Resource limit exceeded"
                status = InteractionStatus.ERROR
            
            else:
                failed_response_text = "An unknown failure occurred"
                status = InteractionStatus.FAILURE
            
            # Create response with both natural and observed data
            return AgentResponse(
                session_id=request.session_id,
                response=failed_response_text,  # What user sees
                status=status,                   # Observed status
                natural_status=natural_response.status,  # What LLM actually produced
                failure_mode=failure_mode,
                failure_injection_applied=True,
                natural_response=natural_response.response,  # Original LLM response
                processing_time_ms=0,  # Will be set by caller
                token_count=token_count,
                model_used=request.model
            )
            
        except Exception as e:
            # Handle integration and resource failures that throw exceptions
            return AgentResponse(
                session_id=request.session_id,
                response=f"Service error: {str(e)}",
                status=InteractionStatus.ERROR,
                natural_status=natural_response.status,
                failure_mode=failure_mode,
                failure_injection_applied=True,
                natural_response=natural_response.response,
                processing_time_ms=0,
                token_count=token_count,
                model_used=request.model
            )
    
    async def _handle_failure(
        self, 
        request: AgentRequest, 
        agent_state: Dict[str, Any], 
        failure_mode: FailureMode,
        token_count: int,
        db_session: AsyncSession
    ) -> AgentResponse:
        agent_state["failure_count"] += 1
        await self.state_manager.track_failure_count(request.session_id)
        
        try:
            failure_type = self.failure_injector.failure_scenarios[failure_mode]["type"]
            
            if failure_type == FailureType.OUTPUT_QUALITY:
                failed_response = await self.failure_injector.inject_output_quality_failure(
                    request.session_id, failure_mode, "Normal response would go here"
                )
                status = InteractionStatus.FAILURE
                
            elif failure_type == FailureType.BEHAVIORAL:
                failed_response = await self.failure_injector.inject_behavioral_failure(
                    request.session_id, failure_mode, request.message
                )
                status = InteractionStatus.FAILURE
                
            elif failure_type == FailureType.INTEGRATION:
                await self.failure_injector.inject_integration_failure(
                    request.session_id, failure_mode
                )
                # This should raise an exception, but in case it doesn't:
                failed_response = "Integration failure occurred"
                status = InteractionStatus.FAILURE
                
            elif failure_type == FailureType.RESOURCE:
                await self.failure_injector.inject_resource_failure(
                    request.session_id, failure_mode, token_count
                )
                # This should raise an exception, but in case it doesn't:
                failed_response = "Resource limit exceeded"
                status = InteractionStatus.FAILURE
            
            else:
                failed_response = "An unknown failure occurred"
                status = InteractionStatus.FAILURE
            
            return AgentResponse(
                session_id=request.session_id,
                response=failed_response,
                status=status,
                failure_mode=failure_mode,
                processing_time_ms=0,  # Will be set by caller
                token_count=token_count,
                model_used=request.model
            )
            
        except Exception as e:
            # Handle integration and resource failures that throw exceptions
            return AgentResponse(
                session_id=request.session_id,
                response=f"Service error: {str(e)}",
                status=InteractionStatus.ERROR,
                failure_mode=failure_mode,
                processing_time_ms=0,
                token_count=token_count,
                model_used=request.model
            )
    
    async def _handle_api_timeout(self, request: AgentRequest, error_msg: str) -> AgentResponse:
        return AgentResponse(
            session_id=request.session_id,
            response="I'm experiencing some delays right now. Please try your request again in a moment.",
            status=InteractionStatus.TIMEOUT,
            natural_status=InteractionStatus.TIMEOUT,
            failure_injection_applied=False,
            natural_response="I'm experiencing some delays right now. Please try your request again in a moment.",
            failure_mode=FailureMode.API_TIMEOUT,
            processing_time_ms=0,
            token_count=0,
            model_used=request.model
        )
    
    async def _handle_rate_limit(self, request: AgentRequest, error_msg: str) -> AgentResponse:
        return AgentResponse(
            session_id=request.session_id,
            response="I'm currently handling a high volume of requests. Please try again in a few minutes.",
            status=InteractionStatus.FAILURE,
            natural_status=InteractionStatus.FAILURE,
            failure_injection_applied=False,
            natural_response="I'm currently handling a high volume of requests. Please try again in a few minutes.",
            failure_mode=FailureMode.RATE_LIMITING,
            processing_time_ms=0,
            token_count=0,
            model_used=request.model
        )
    
    def _count_tokens(self, conversation_history: list) -> int:
        total_tokens = 0
        for message in conversation_history:
            total_tokens += len(self.encoding.encode(message["content"]))
        return total_tokens
    
    async def reset_session(self, session_id: str):
        await self.state_manager.delete_state(session_id)
        await self.state_manager.reset_failure_count(session_id)
        self.failure_injector.reset_session_state(session_id)
        logger.info("Session reset", session_id=session_id)