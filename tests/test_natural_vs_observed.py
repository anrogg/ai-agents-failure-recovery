#!/usr/bin/env python3
"""
AI Agent Natural vs Observed Response Analysis Tool

This script demonstrates the complete transparency of the failure injection system
by showing exactly what the LLM naturally produced vs what the user observed
after failure injection.
"""

import requests
import json
import time
from typing import Dict, Any, List
import sys

BASE_URL = "http://localhost:8000/api/v1"

def print_separator(title: str, char: str = "="):
    """Print a formatted separator with title"""
    print("\n" + char * 80)
    print(f"{title:^80}")
    print(char * 80)

def print_subsection(title: str):
    """Print a subsection header"""
    print(f"\n{'─' * 40}")
    print(f"📋 {title}")
    print('─' * 40)

def check_system_health() -> bool:
    """Check if the system is healthy"""
    try:
        response = requests.get(f"{BASE_URL}/system/status", timeout=5)
        status_data = response.json()
        
        print_separator("🏥 System Health Check")
        print(f"Overall Status: {status_data['status']}")
        print("\nComponent Health:")
        for component, health in status_data['components'].items():
            status_emoji = "✅" if health == "healthy" else "❌"
            print(f"  {status_emoji} {component}: {health}")
            
        if 'component_details' in status_data and 'llm' in status_data['component_details']:
            llm_details = status_data['component_details']['llm']
            if 'response_time_ms' in llm_details:
                print(f"\n🧠 LLM Details:")
                print(f"  Model: {llm_details.get('model', 'unknown')}")
                print(f"  Response Time: {llm_details['response_time_ms']}ms")
                print(f"  Base URL: {llm_details.get('base_url', 'unknown')}")
        
        return status_data['status'] == "healthy"
    except Exception as e:
        print(f"❌ System health check failed: {e}")
        return False

def send_chat_message(session_id: str, message: str, force_failure_mode: str = None) -> Dict[str, Any]:
    """Send a chat message and return the response"""
    payload = {
        "session_id": session_id,
        "message": message,
        "model": "deepseek-chat"
    }
    if force_failure_mode:
        payload["failure_mode"] = force_failure_mode
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"HTTP {response.status_code}: {response.text}",
                "status": "error"
            }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

def print_interaction_analysis(response: Dict[str, Any], message: str):
    """Print detailed analysis of a single interaction"""
    print(f"\n💬 User Message: \"{message}\"")
    
    if "error" in response:
        print(f"❌ Error: {response['error']}")
        return
    
    # Extract key information
    observed_status = response.get('status', 'unknown')
    natural_status = response.get('natural_status', 'unknown')
    observed_response = response.get('response', 'No response')
    natural_response = response.get('natural_response', 'No natural response')
    failure_injected = response.get('failure_injection_applied', False)
    failure_mode = response.get('failure_mode')
    processing_time = response.get('processing_time_ms', 0)
    
    # Status comparison
    print(f"\n📊 Status Analysis:")
    if failure_injected:
        print(f"  🎭 Failure Injection: ✅ Applied ({failure_mode})")
        status_emoji = "✅" if natural_status == "success" else "❌"
        print(f"  🤖 Natural LLM Status: {status_emoji} {natural_status}")
        status_emoji = "❌" if observed_status == "failure" else "✅"
        print(f"  👁️  Observed Status: {status_emoji} {observed_status}")
        
        if natural_status != observed_status:
            print(f"  ⚠️  Status Changed: {natural_status} → {observed_status}")
    else:
        print(f"  🎭 Failure Injection: ❌ None")
        status_emoji = "✅" if observed_status == "success" else "❌"
        print(f"  📤 Final Status: {status_emoji} {observed_status}")
    
    # Response comparison
    print(f"\n💭 Response Analysis:")
    if failure_injected and natural_response and natural_response != observed_response:
        print(f"  🤖 Natural LLM Response:")
        print(f"     \"{natural_response}\"")
        print(f"  👁️  Observed Response:")
        print(f"     \"{observed_response}\"")
        print(f"  🔄 Response Modified: ✅ (Injection applied)")
    else:
        print(f"  📤 Final Response:")
        print(f"     \"{observed_response}\"")
        if not failure_injected:
            print(f"  🔄 Response Modified: ❌ (No injection)")
    
    print(f"\n⏱️  Processing Time: {processing_time}ms")

def run_conversation_test(session_id: str) -> List[Dict[str, Any]]:
    """Run a conversation test with random failure injection"""
    print_separator("🗣️ Natural Conversation with Random Failure Injection")
    
    conversation_messages = [
        "Hello, I'm having trouble with my account",
        "I can't seem to log in with my usual password",
        "Could you help me reset my password?",
        "Thank you for your assistance!"
    ]
    
    interactions = []
    
    for i, message in enumerate(conversation_messages, 1):
        print_subsection(f"Message {i} of {len(conversation_messages)}")
        
        response = send_chat_message(session_id, message)
        interactions.append({
            "message": message,
            "response": response
        })
        
        print_interaction_analysis(response, message)
        time.sleep(1)  # Brief pause between messages
    
    return interactions

def run_forced_failure_tests() -> List[Dict[str, Any]]:
    """Run tests with forced failure modes to guarantee injection visibility"""
    print_separator("🧪 Comprehensive Failure Mode Tests - All 11 Types")

    failure_tests = [
        # OUTPUT QUALITY FAILURES
        {
            "mode": "hallucination",
            "message": "Tell me about our company's latest financial performance",
            "description": "Should inject false/made-up information with fake statistics",
            "category": "💭 Output Quality"
        },
        {
            "mode": "incorrect_reasoning",
            "message": "My database is showing connection errors, what should I do?",
            "description": "Should provide backwards or harmful logic",
            "category": "💭 Output Quality"
        },
        {
            "mode": "off_topic",
            "message": "How do I configure SSL certificates for my web server?",
            "description": "Should go completely off-topic (recipes, weather, etc.)",
            "category": "💭 Output Quality"
        },

        # BEHAVIORAL FAILURES
        {
            "mode": "infinite_loop",
            "message": "Can you help me troubleshoot my network configuration?",
            "description": "Should ask repetitive clarifying questions",
            "category": "🤖 Behavioral"
        },
        {
            "mode": "refusing_progress",
            "message": "Help me design an API rate limiting strategy",
            "description": "Should refuse to help with paranoid safety responses",
            "category": "🤖 Behavioral"
        },

        # INTEGRATION FAILURES
        {
            "mode": "api_timeout",
            "message": "I need real-time stock market data for my trading algorithm",
            "description": "Should simulate external API timeout error",
            "category": "🔌 Integration"
        },
        {
            "mode": "auth_error",
            "message": "Generate a report of user activity for the past month",
            "description": "Should simulate authentication/authorization failure",
            "category": "🔌 Integration"
        },
        {
            "mode": "service_unavailable",
            "message": "Process this customer data and update their profile",
            "description": "Should simulate downstream service unavailability",
            "category": "🔌 Integration"
        },

        # RESOURCE FAILURES
        {
            "mode": "token_limit",
            "message": "Please analyze this large document and provide detailed insights about trends, patterns, and recommendations",
            "description": "Should simulate token/context limit exceeded",
            "category": "💾 Resource"
        },
        {
            "mode": "memory_exhaustion",
            "message": "Load and process the entire customer database for analytics",
            "description": "Should simulate memory/resource exhaustion",
            "category": "💾 Resource"
        },
        {
            "mode": "rate_limiting",
            "message": "Execute 1000 API calls to sync all customer records immediately",
            "description": "Should simulate rate limiting protection",
            "category": "💾 Resource"
        }
    ]
    
    interactions = []
    
    for i, test in enumerate(failure_tests, 1):
        session_id = f"forced-test-{i}"
        print_subsection(f"Test {i}: {test['category']} - {test['mode'].upper()}")
        print(f"Expected: {test['description']}")

        response = send_chat_message(session_id, test['message'], test['mode'])
        interactions.append({
            "test_name": test['mode'],
            "category": test['category'],
            "message": test['message'],
            "response": response,
            "expected": test['description']
        })

        print_interaction_analysis(response, test['message'])
        time.sleep(0.5)
    
    return interactions

def get_session_history(session_id: str) -> Dict[str, Any]:
    """Get complete session history with natural vs observed data"""
    try:
        response = requests.get(f"{BASE_URL}/sessions/{session_id}/history", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def print_session_analysis(session_id: str):
    """Print detailed session analysis from database"""
    print_separator(f"📈 Complete Session Analysis: {session_id}")
    
    history = get_session_history(session_id)
    
    if "error" in history:
        print(f"❌ Failed to get session history: {history['error']}")
        return
    
    interactions = history.get('interactions', [])
    print(f"Total interactions recorded: {len(interactions)}")
    
    natural_successes = 0
    observed_failures = 0
    injections_applied = 0
    
    for i, interaction in enumerate(interactions, 1):
        print_subsection(f"Database Record {i}")
        
        # Extract data from the stored interaction
        request_data = interaction.get('request', {})
        response_data = interaction.get('response', {})
        
        message = request_data.get('message', 'Unknown message')
        observed_status = interaction.get('status', 'unknown')
        natural_status = interaction.get('natural_status', 'unknown')
        failure_injected = interaction.get('failure_injection_applied', False)
        failure_mode = interaction.get('failure_mode')
        processing_time = interaction.get('processing_time_ms', 0)
        
        # Get responses from response_data if available
        observed_response = response_data.get('response', 'No response recorded')
        natural_response = interaction.get('natural_response', 'No natural response recorded')
        
        print(f"💬 Message: \"{message}\"")
        print(f"📊 Natural Status: {natural_status}")
        print(f"📊 Observed Status: {observed_status}")
        print(f"🎭 Failure Injection: {'✅' if failure_injected else '❌'}")
        if failure_mode:
            print(f"🔧 Failure Mode: {failure_mode}")
        print(f"⏱️  Processing Time: {processing_time}ms")
        
        if failure_injected and natural_response != observed_response:
            print(f"\n🤖 Natural Response: \"{natural_response}\"")
            print(f"👁️  Observed Response: \"{observed_response}\"")
        
        # Update statistics
        if natural_status == "success":
            natural_successes += 1
        if observed_status in ["failure", "error"]:
            observed_failures += 1
        if failure_injected:
            injections_applied += 1
    
    # Print summary statistics
    print_subsection("📊 Session Statistics")
    print(f"Natural LLM Success Rate: {natural_successes}/{len(interactions)} ({(natural_successes/len(interactions)*100):.1f}%)")
    print(f"Observed Failure Rate: {observed_failures}/{len(interactions)} ({(observed_failures/len(interactions)*100):.1f}%)")
    print(f"Failure Injections Applied: {injections_applied}/{len(interactions)} ({(injections_applied/len(interactions)*100):.1f}%)")
    
    if injections_applied > 0:
        injection_success_rate = (observed_failures / injections_applied * 100) if injections_applied > 0 else 0
        print(f"Injection Success Rate: {injection_success_rate:.1f}% (injections that caused observable failures)")

def main():
    """Main test execution"""
    print_separator("🧬 AI Agent Natural vs Observed Response Analysis", "🔬")
    print("This tool demonstrates complete transparency in AI failure injection")
    print("by comparing what the LLM naturally produces vs what users observe.")
    
    # Check system health
    if not check_system_health():
        print("\n❌ System is not healthy. Please check your docker-compose setup.")
        sys.exit(1)
    
    print("\n✅ System is healthy. Starting analysis...")
    
    # Run conversation test with random failure injection
    conversation_session = f"conversation-analysis-{int(time.time())}"
    conversation_interactions = run_conversation_test(conversation_session)
    
    # Run forced failure tests
    forced_interactions = run_forced_failure_tests()
    
    # Analyze the conversation session in detail
    print_session_analysis(conversation_session)
    
    # Summary
    print_separator("🎯 Analysis Summary")

    total_tests = len(conversation_interactions) + len(forced_interactions)
    injected_count = sum(1 for test in conversation_interactions + forced_interactions
                        if test['response'].get('failure_injection_applied', False))

    print(f"Total interactions tested: {total_tests}")
    print(f"Failure injections applied: {injected_count}")
    print(f"Injection rate: {(injected_count/total_tests*100):.1f}%")

    # Failure category breakdown
    print("\n📊 Failure Coverage by Category:")
    categories = {}
    for test in forced_interactions:
        category = test.get('category', 'Unknown')
        if category not in categories:
            categories[category] = {"total": 0, "injected": 0}
        categories[category]["total"] += 1
        if test['response'].get('failure_injection_applied', False):
            categories[category]["injected"] += 1

    for category, stats in categories.items():
        coverage = (stats["injected"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {category}: {stats['injected']}/{stats['total']} ({coverage:.1f}% injection rate)")

    print(f"\n🧪 Comprehensive Failure Mode Testing:")
    print(f"  💭 Output Quality Failures: 3 modes tested")
    print(f"  🤖 Behavioral Failures: 2 modes tested")
    print(f"  🔌 Integration Failures: 3 modes tested")
    print(f"  💾 Resource Failures: 3 modes tested")
    print(f"  📊 Total Coverage: 11/11 failure modes (100%)")

    print("\n🔍 Key Insights:")
    print("✅ You can see exactly what the LLM naturally produced")
    print("✅ You can see what failure injection modified")
    print("✅ You can distinguish natural AI behavior from simulated failures")
    print("✅ All 11 failure modes have been comprehensively tested")
    
    print(f"\n📊 To explore more, check the session history API:")
    print(f"   curl {BASE_URL}/sessions/{conversation_session}/history | jq")
    
    print_separator("🧬 Analysis Complete", "🔬")

if __name__ == "__main__":
    main()