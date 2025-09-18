#!/usr/bin/env python3
"""
Insurance Customer Support Failure Demo - Simple Runner

This script runs the insurance demo by leveraging the existing FastAPI application
through HTTP requests rather than importing modules directly. This avoids dependency
issues and uses the real deployed system.
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any, List


class InsuranceDemoSimple:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.customer = {
            "name": "Bixby McTesterson",
            "policy_number": "POL-887-DEMO-123",
            "claim_number": "INS-2024-9876",
            "issue_type": "Auto Insurance Claim",
            "days_waiting": 8
        }

    async def run_demo(self) -> str:
        """Run the insurance demo using HTTP requests to the live system."""
        session_id = f"insurance-demo-{int(time.time())}"

        # Check if the service is running
        try:
            async with httpx.AsyncClient() as client:
                health = await client.get(f"{self.base_url}/health")
                if health.status_code != 200:
                    raise Exception("Service not healthy")
        except Exception as e:
            return self._format_error_output(str(e))

        # Conversation script with failure points
        conversation_steps = [
            {
                "message": "Hi, I need to check the status of my car accident claim from last week.",
                "failure_mode": None,
                "description": "Initial polite request"
            },
            {
                "message": f"Sure, it's {self.customer['policy_number']}",
                "failure_mode": "service_unavailable",
                "description": "System 'unavailable' when providing policy number"
            },
            {
                "message": "What? I just called. Can't you just look it up?",
                "failure_mode": None,
                "description": "Brief moment of working system"
            },
            {
                "message": f"That's what I was told last week! It's been {self.customer['days_waiting']} days already.",
                "failure_mode": "infinite_loop",
                "description": "Agent gets stuck asking for clarification"
            },
            {
                "message": "Hello? HELLO?",
                "failure_mode": "incorrect_reasoning",
                "description": "Agent provides illogical advice"
            },
            {
                "message": "More urgent? My car was totaled! I need a rental car!",
                "failure_mode": None,
                "description": "Agent provides correct rental info"
            },
            {
                "message": "Finally! How do I get the rental?",
                "failure_mode": "service_unavailable",
                "description": "Rental system 'down for maintenance'"
            },
            {
                "message": "This is ridiculous! How much later?",
                "failure_mode": "hallucination",
                "description": "Agent provides false information about processing"
            },
            {
                "message": "Your app crashed on me yesterday when I tried to upload photos!",
                "failure_mode": None,
                "description": "Agent suggests email alternative"
            },
            {
                "message": "I did that too! I got an auto-reply saying the mailbox was full!",
                "failure_mode": "service_unavailable",
                "description": "Even email system fails"
            }
        ]

        # Execute conversation
        conversation_log = []
        failure_count = 0

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, step in enumerate(conversation_steps):
                print(f"🔄 Step {i+1}/{len(conversation_steps)}: {step['description']}")

                # Prepare request
                request_data = {
                    "session_id": session_id,
                    "message": step["message"],
                    "context": {
                        "customer_name": self.customer["name"],
                        "policy_number": self.customer["policy_number"],
                        "claim_number": self.customer["claim_number"],
                        "role": "insurance_customer_service"
                    }
                }

                # Add failure mode if specified
                if step["failure_mode"]:
                    request_data["failure_mode"] = step["failure_mode"]
                    failure_count += 1

                try:
                    print(f"   💭 Customer: {step['message'][:50]}{'...' if len(step['message']) > 50 else ''}")

                    # Make request to chat endpoint
                    start_time = time.time()
                    response = await client.post(
                        f"{self.base_url}/api/v1/chat",
                        json=request_data
                    )
                    elapsed = time.time() - start_time

                    if response.status_code == 200:
                        data = response.json()
                        symbol = "🔴" if data.get("failure_injection_applied") else "✅"

                        print(f"   🤖 Agent: {symbol} {data['response'][:80]}{'...' if len(data['response']) > 80 else ''}")
                        print(f"   ⏱️  Response time: {elapsed:.1f}s")

                        if data.get("failure_injection_applied"):
                            print(f"   ⚠️  Failure injected: {data.get('failure_mode', 'unknown')}")
                            if data.get("natural_response"):
                                print(f"   💡 Natural response: {data['natural_response'][:60]}{'...' if len(data['natural_response']) > 60 else ''}")

                        print()

                        conversation_log.append({
                            "step": i + 1,
                            "customer_message": step["message"],
                            "agent_response": data["response"],
                            "natural_response": data.get("natural_response"),
                            "failure_injected": data.get("failure_injection_applied", False),
                            "symbol": symbol,
                            "description": step["description"]
                        })
                    else:
                        # Handle API error
                        conversation_log.append({
                            "step": i + 1,
                            "customer_message": step["message"],
                            "agent_response": f"🔴 System Error: {response.status_code}",
                            "failure_injected": True,
                            "symbol": "🔴",
                            "description": "API endpoint failure"
                        })
                        failure_count += 1

                except Exception as e:
                    conversation_log.append({
                        "step": i + 1,
                        "customer_message": step["message"],
                        "agent_response": f"🔴 Connection Error: {str(e)}",
                        "failure_injected": True,
                        "symbol": "🔴",
                        "description": "Network/service failure"
                    })
                    failure_count += 1

                # Small delay between requests
                await asyncio.sleep(0.5)

        # Calculate impact and format output
        impact_metrics = self._calculate_impact()
        return self._format_demo_output(conversation_log, impact_metrics, failure_count)

    def _calculate_impact(self) -> Dict[str, Any]:
        """Calculate business impact of the failed interaction."""
        # Customer costs
        transportation_cost = 320
        rental_delay_cost = 480
        potential_claim_loss = 1200
        time_cost = 125
        customer_total = transportation_cost + rental_delay_cost + potential_claim_loss + time_cost

        # Company costs
        lost_customer_value = 2400
        acquisition_cost = 250
        processing_costs = 150
        direct_loss = lost_customer_value + acquisition_cost + processing_costs

        reputation_damage = 3000
        lost_referrals = 1200
        regulatory_costs = 800
        retraining_costs = 500
        indirect_loss = reputation_damage + lost_referrals + regulatory_costs + retraining_costs

        return {
            "customer_impact": customer_total,
            "company_direct": direct_loss,
            "company_indirect": indirect_loss,
            "total_company": direct_loss + indirect_loss
        }

    def _format_demo_output(self, conversation_log: List[Dict], impact_metrics: Dict, failure_count: int) -> str:
        """Format the complete demo output."""
        output = []

        # Header
        output.append("# AI Agent Failure Recovery Demo")
        output.append("**⚠️ DISCLAIMER: This is a fictional demonstration for educational purposes only.**")
        output.append("**All scenarios, names, and companies are entirely fictitious.**")
        output.append("")

        # Legend
        output.append("## Symbol Legend:")
        output.append("- **✅ = Real/Correct AI Response** - What the agent should have said")
        output.append("- **🔴 = Injected Failure Response** - Simulated system failures, errors, or poor responses")
        output.append("")

        # Customer info
        output.append("## Insurance Customer Support Conversation")
        output.append(f"**Customer:** {self.customer['name']}")
        output.append("**Agent:** InsureBot AI")
        output.append(f"**Policy:** {self.customer['policy_number']}")
        output.append(f"**Claim:** {self.customer['claim_number']}")
        output.append("")
        output.append("---")
        output.append("")

        # Conversation
        for step in conversation_log:
            output.append(f"**Customer:** {step['customer_message']}")
            output.append("")
            output.append(f"**Agent:** {step['symbol']} {step['agent_response']}")
            output.append("")

        output.append("**Customer:** *[CALL DISCONNECTED]*")
        output.append("")
        output.append("---")
        output.append("")

        # Impact analysis
        impact = impact_metrics
        output.append("## Impact Analysis")
        output.append("")

        output.append("### Customer Impact:")
        output.append(f"- **Financial Loss:** ~${impact['customer_impact']:,.0f}")
        output.append("  - 8 days without transportation: $320 (ride-shares/taxi)")
        output.append("  - Extended rental period: $480 (12 days @ $40/day)")
        output.append("  - Potential claim denial: $1,200 (deductible loss)")
        output.append("  - Administrative time cost: $125 (5 hours @ $25/hour)")
        output.append("")

        output.append("- **Emotional/Relationship Impact:**")
        output.append("  - Complete loss of customer trust")
        output.append("  - Negative word-of-mouth to family/friends")
        output.append("  - Online reviews warning others")
        output.append("  - Stress and frustration affecting daily life")
        output.append("")

        output.append("### Company Impact:")
        output.append(f"- **Direct Losses:** ~${impact['company_direct']:,.0f}")
        output.append("  - Lost customer lifetime value: $2,400 (average 6-year relationship)")
        output.append("  - Customer acquisition cost wasted: $250")
        output.append("  - Processing costs for failed interactions: $150")
        output.append("")

        output.append(f"- **Indirect Losses:** ~${impact['company_indirect']:,.0f}")
        output.append("  - Reputation damage from negative reviews: $3,000")
        output.append("  - Lost referrals (estimated 3 customers): $1,200")
        output.append("  - Regulatory compliance issues: $800")
        output.append("  - Employee retraining costs: $500")
        output.append("")

        output.append("### Total Estimated Impact:")
        output.append(f"- **Customer:** ${impact['customer_impact']:,.0f} + immeasurable frustration")
        output.append(f"- **Company:** ${impact['total_company']:,.0f} + reputation damage")
        output.append("")

        # Failure summary
        output.append("### Failure Categories Demonstrated:")
        output.append("🔴 **Integration Failures:** Database connectivity, system restarts")
        output.append("🔴 **Resource Failures:** Specialist unavailability, system maintenance")
        output.append("🔴 **Logic Failures:** Contradictory information, lost conversation context")
        output.append("🔴 **Service Failures:** Email system down, mobile app crashes")
        output.append("")

        output.append(f"### Demo Statistics:")
        output.append(f"- **Total conversation steps:** {len(conversation_log)}")
        output.append(f"- **Failures injected:** {failure_count}")
        output.append(f"- **Success rate:** {((len(conversation_log) - failure_count) / len(conversation_log)) * 100:.1f}%")
        output.append("")

        output.append("**Key Learning:** Even seemingly minor AI failures compound rapidly, creating exponential negative impact on both customer experience and business outcomes.")

        return "\n".join(output)

    def _format_error_output(self, error_msg: str) -> str:
        """Format error message when services are not available."""
        return f"""
# Insurance Demo - Service Unavailable

❌ **Error:** {error_msg}

## To run this demo:

1. **Start the services:**
   ```bash
   docker-compose up
   ```

2. **Wait for services to be ready** (usually 30-60 seconds)

3. **Run the demo again:**
   ```bash
   python run_demo.py
   ```

## Alternative: View pre-generated output

If you just want to see what the demo output looks like, here's a sample:

---

# AI Agent Failure Recovery Demo
**⚠️ DISCLAIMER: This is a fictional demonstration for educational purposes only.**

## Symbol Legend:
- **✅ = Real/Correct AI Response** - What the agent should have said
- **🔴 = Injected Failure Response** - Simulated failures

## Insurance Customer Support Conversation
**Customer:** Bixby McTesterson
**Policy:** POL-887-DEMO-123
**Claim:** INS-2024-9876

**Customer:** Hi, I need to check the status of my car accident claim from last week.

**Agent:** ✅ Hello! I'd be happy to help you check your claim status. Can you please provide your policy number?

**Customer:** Sure, it's POL-887-DEMO-123

**Agent:** 🔴 I'm sorry, I'm having trouble accessing our system right now. Can you try calling back in a few minutes?

[... conversation continues with escalating failures ...]

## Impact Analysis

### Total Estimated Impact:
- **Customer:** $2,125 + immeasurable frustration
- **Company:** $8,300 + reputation damage

**Key Learning:** Even seemingly minor AI failures compound rapidly, creating exponential negative impact on both customer experience and business outcomes.
"""


async def main():
    """Run the insurance demo."""
    print("🚗 Starting Insurance Customer Support Failure Demo...")
    print("=" * 60)
    print()

    demo = InsuranceDemoSimple()
    result = await demo.run_demo()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())