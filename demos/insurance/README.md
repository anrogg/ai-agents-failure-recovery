# Insurance Customer Support Failure Demo

This demo shows how AI agent failures can escalate customer frustration in a realistic insurance customer support scenario using **real LLM responses** and the existing failure injection system.

## Overview

The demo simulates a conversation between **Bixby McTesterson** (a frustrated insurance customer) and **InsureBot AI** (a customer support agent). During the conversation, various failures are strategically injected to demonstrate how system problems compound customer frustration.

**Key Feature**: This demo uses genuine LLM responses for the ✅ symbols and the existing failure injection system for the 🔴 symbols, giving you a real comparison between what the AI should say vs. what happens when failures occur.

## Symbol Legend

- **✅ = Real/Correct AI Response** - Genuine response from your configured LLM (what the agent should say)
- **🔴 = Injected Failure Response** - Simulated system failures, errors, or poor responses from the failure injection system

## Scenario

**Customer**: Bixby McTesterson
**Policy**: POL-887-DEMO-123
**Claim**: INS-2024-9876 (Auto accident from 8 days ago)
**Problem**: Customer needs claim status and rental car assistance
**Outcome**: Customer escalates from polite to furious and eventually disconnects

## Failure Types Demonstrated

1. **Integration Failures**: Service unavailable errors, system connectivity issues
2. **Resource Failures**: Specialist unavailability, system maintenance downtime
3. **Output Quality Failures**: Hallucinations with false information, incorrect reasoning
4. **Behavioral Failures**: Infinite loops asking for same information, refusing to progress

## Running the Demo

### Prerequisites

Services must be running:
- **FastAPI application** (port 8000)
- **Redis** (for session state management)
- **PostgreSQL** (for interaction logging)
- **AI_API_KEY** environment variable set for real LLM responses

### Start Services

```bash
# From the project root
docker-compose up
```

Wait for all services to be ready (usually 30-60 seconds).

### Run the Demo

```bash
# From the project root
python demos/insurance/run_demo.py
```

### What You'll See

The demo shows real-time progress with:

```
🔄 Step 1/10: Initial polite request
   💭 Customer: Hi, I need to check the status of my car accident...
   🤖 Agent: ✅ Hello! I'd be happy to help you check your claim...
   ⏱️  Response time: 4.2s

🔄 Step 2/10: System 'unavailable' when providing policy number
   💭 Customer: Sure, it's POL-887-DEMO-123
   🤖 Agent: 🔴 Service temporarily unavailable: 503 Service...
   ⏱️  Response time: 3.8s
   ⚠️  Failure injected: service_unavailable
   💡 Natural response: Let me look up your policy information...
```

## Demo Output

After completion, you'll see a complete analysis including:

### 1. Live Conversation Display
- Real-time step-by-step conversation progress
- Clear distinction between real LLM responses (✅) and injected failures (🔴)
- Response times and failure mode details
- Natural response preview when failures are injected

### 2. Complete Conversation Summary
- Full conversation formatted for easy reading
- Customer escalation from polite to furious
- Multiple failure types strategically placed to maximize frustration

### 3. Detailed Impact Analysis
- **Customer Impact**: ~$2,125 in direct costs + immeasurable frustration
- **Company Impact**: ~$8,300 in direct and indirect losses
- **Breakdown**: Transportation, rental, claim risks, reputation damage, lost referrals
- **Outcome**: Customer disconnects and plans to switch providers

### 4. Failure Statistics
- Total conversation steps: 10
- Failures injected: 6-7 (60-70% failure rate)
- Response time analysis
- Failure category breakdown

## Technical Implementation

✅ **Uses Real LLM**: All ✅ responses come from your configured AI model (DeepSeek, OpenAI, etc.)

✅ **Existing Failure System**: All 🔴 responses use the existing `FailureInjector` class

✅ **Live HTTP Calls**: Makes actual API calls to your running FastAPI application

✅ **Real State Management**: Uses Redis for session state and PostgreSQL for logging

✅ **No Code Modifications**: Leverages existing codebase without changes

## Educational Value

⚠️ **DISCLAIMER**: This is a fictional demonstration for educational purposes only. All scenarios, names, and companies are entirely fictitious.

**Key Insights Demonstrated**:
- Small technical failures cascade into major business impacts
- Customer patience decreases exponentially with repeated failures
- System integration problems create compound frustration
- Even brief moments of working service cannot recover lost trust
- Recovery becomes nearly impossible after multiple consecutive failures
- The difference between what AI should do vs. what happens when it fails

## Files in This Demo

- `run_demo.py` - Main demo with live LLM integration (recommended)
- `README.md` - This documentation