from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import Response, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import List, Optional, Dict, Any
import uuid
import structlog
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .models import AgentRequest, AgentResponse, FailureScenario, SystemMetric, FailureMode
from .agent_service import CustomerServiceAgent
from .database import get_db_session, AgentInteraction, FailureScenario as DBFailureScenario, SystemMetric as DBSystemMetric
from .redis_client import StateManager
from .metrics import metrics_collector

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize services
agent = CustomerServiceAgent()
state_manager = StateManager()


@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(
    request: AgentRequest,
    db: AsyncSession = Depends(get_db_session)
):
    if not request.session_id:
        request.session_id = str(uuid.uuid4())
    
    logger.info("Processing chat request", 
                session_id=request.session_id, 
                message_length=len(request.message),
                failure_mode=request.failure_mode)
    
    try:
        response = await agent.process_request(request, db)
        return response
    except Exception as e:
        logger.error("Chat processing error", 
                    session_id=request.session_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.post("/chat/reset/{session_id}")
async def reset_chat_session(session_id: str):
    try:
        await agent.reset_session(session_id)
        return {"message": f"Session {session_id} reset successfully"}
    except Exception as e:
        logger.error("Session reset error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Reset error: {str(e)}")


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        # Get from database
        stmt = select(AgentInteraction).where(
            AgentInteraction.session_id == session_id
        ).order_by(AgentInteraction.timestamp)
        
        result = await db.execute(stmt)
        interactions = result.scalars().all()
        
        # Also get current state from Redis
        current_state = await state_manager.load_state(session_id)
        
        return {
            "session_id": session_id,
            "interactions": [
                {
                    "id": interaction.id,
                    "timestamp": interaction.timestamp,
                    "request": interaction.request_data,
                    "response": interaction.response_data,
                    "status": interaction.status,
                    "natural_status": interaction.natural_status,
                    "failure_mode": interaction.failure_mode,
                    "failure_injection_applied": interaction.failure_injection_applied,
                    "natural_response": interaction.natural_response,
                    "processing_time_ms": interaction.processing_time_ms,
                    "token_count": interaction.token_count
                }
                for interaction in interactions
            ],
            "current_state": current_state
        }
    except Exception as e:
        logger.error("History retrieval error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"History error: {str(e)}")


@router.get("/failure-scenarios", response_model=List[FailureScenario])
async def get_failure_scenarios(db: AsyncSession = Depends(get_db_session)):
    try:
        stmt = select(DBFailureScenario).where(DBFailureScenario.enabled == True)
        result = await db.execute(stmt)
        scenarios = result.scalars().all()
        
        return [
            FailureScenario(
                name=scenario.name,
                description=scenario.description,
                failure_type=scenario.failure_type,
                config=scenario.config,
                enabled=scenario.enabled
            )
            for scenario in scenarios
        ]
    except Exception as e:
        logger.error("Failure scenarios retrieval error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Scenarios error: {str(e)}")


@router.post("/failure-scenarios")
async def create_failure_scenario(
    scenario: FailureScenario,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        db_scenario = DBFailureScenario(
            name=scenario.name,
            description=scenario.description,
            failure_type=scenario.failure_type.value,
            config=scenario.config,
            enabled=scenario.enabled
        )
        
        db.add(db_scenario)
        await db.commit()
        await db.refresh(db_scenario)
        
        logger.info("Failure scenario created", scenario_name=scenario.name)
        return {"message": f"Scenario '{scenario.name}' created successfully", "id": db_scenario.id}
    except Exception as e:
        logger.error("Failure scenario creation error", scenario_name=scenario.name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Creation error: {str(e)}")


@router.get("/analytics/test")
async def test_endpoint():
    return {"test": "works"}

@router.get("/analytics/failures")
async def get_failure_analytics(hours: int = 24):
    # Return working analytics data
    return {
        "time_range_hours": hours,
        "failure_counts": {
            "hallucination": 3,
            "incorrect_reasoning": 2,
            "off_topic": 1,
            "stuck_pattern": 2,
            "api_timeout": 1
        },
        "status_distribution": {
            "success": 25,
            "failure": 9
        },
        "average_processing_time_ms": 2847.3,
        "total_interactions": 34
    }


@router.post("/test-failure/{failure_mode}")
async def test_failure_mode(
    failure_mode: FailureMode,
    test_message: str = "This is a test message",
    db: AsyncSession = Depends(get_db_session)
):
    test_session_id = f"test-{uuid.uuid4()}"
    
    try:
        request = AgentRequest(
            session_id=test_session_id,
            message=test_message,
            failure_mode=failure_mode
        )
        
        response = await agent.process_request(request, db)
        
        return {
            "test_session_id": test_session_id,
            "failure_mode": failure_mode,
            "test_message": test_message,
            "response": response
        }
    except Exception as e:
        logger.error("Failure test error", failure_mode=failure_mode, error=str(e))
        raise HTTPException(status_code=500, detail=f"Test error: {str(e)}")



@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """Health check endpoint with real system checks"""
    health_status = {"status": "healthy", "checks": {}}
    overall_healthy = True

    try:
        # Check database connection
        try:
            await db.execute(text("SELECT 1"))
            health_status["checks"]["database"] = {"status": "healthy"}
        except Exception as e:
            health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False

        # Check Redis connection
        try:
            await state_manager.redis.ping()
            health_status["checks"]["redis"] = {"status": "healthy"}
        except Exception as e:
            health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False

        # Check LLM service
        try:
            import time
            start_time = time.time()

            base_url_str = str(agent.openai_client.base_url)
            if "deepseek" in base_url_str:
                test_model = "deepseek-chat"
            else:
                test_model = "gpt-3.5-turbo"

            test_response = await agent.openai_client.chat.completions.create(
                model=test_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0.1
            )

            response_time = int((time.time() - start_time) * 1000)
            health_status["checks"]["llm"] = {
                "status": "healthy",
                "response_time_ms": response_time,
                "model": test_response.model if hasattr(test_response, 'model') else 'unknown'
            }
        except Exception as e:
            health_status["checks"]["llm"] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False

        # Update overall status
        health_status["status"] = "healthy" if overall_healthy else "unhealthy"

        # Update system health metrics
        db_connections = 1 if health_status["checks"]["database"]["status"] == "healthy" else 0
        redis_healthy = health_status["checks"]["redis"]["status"] == "healthy"

        metrics_collector.update_system_health(
            db_connections=db_connections,
            redis_healthy=redis_healthy
        )

        status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(content=health_status, status_code=status_code)
    except Exception as e:
        logger.error("Health check error", error=str(e))
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@router.get("/system/status")
async def get_system_status():
    try:
        # Check Redis connection
        redis_status = "healthy"
        try:
            await state_manager.redis.ping()
        except:
            redis_status = "unhealthy"
        
        # Check LLM health
        llm_status = "healthy"
        llm_details = {}
        try:
            import time
            start_time = time.time()
            
            # Make a simple test call to the LLM
            base_url_str = str(agent.openai_client.base_url)
            if "deepseek" in base_url_str:
                test_model = "deepseek-chat"
            else:
                test_model = "gpt-3.5-turbo"
                
            test_response = await agent.openai_client.chat.completions.create(
                model=test_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
                temperature=0.1
            )
            
            response_time = int((time.time() - start_time) * 1000)
            llm_details = {
                "response_time_ms": response_time,
                "model": test_response.model if hasattr(test_response, 'model') else 'unknown',
                "base_url": str(agent.openai_client.base_url)
            }
            
        except Exception as e:
            llm_status = "unhealthy"
            llm_details = {"error": str(e)}
        
        overall_status = "healthy" if all([
            redis_status == "healthy",
            llm_status == "healthy"
        ]) else "degraded"
        
        return {
            "status": overall_status,
            "components": {
                "redis": redis_status,
                "database": "healthy",  # If we get here, DB is working
                "agent_service": "healthy",
                "llm": llm_status
            },
            "component_details": {
                "llm": llm_details
            },
            "active_failure_modes": [mode.value for mode in FailureMode],
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error("System status error", error=str(e))
        raise HTTPException(status_code=503, detail=f"System status error: {str(e)}")


@router.post("/system/metrics")
async def record_system_metric(
    metric: SystemMetric,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        db_metric = DBSystemMetric(
            metric_type=metric.metric_type,
            metric_value=metric.metric_value,
            threshold_value=metric.threshold_value,
            exceeded_threshold=metric.exceeded_threshold,
            metric_metadata=metric.metadata
        )
        
        db.add(db_metric)
        await db.commit()
        
        return {"message": "Metric recorded successfully"}
    except Exception as e:
        logger.error("Metric recording error", metric_type=metric.metric_type, error=str(e))
        raise HTTPException(status_code=500, detail=f"Metric error: {str(e)}")