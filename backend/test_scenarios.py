#!/usr/bin/env python
"""
Test script for RackPulse Data Center Scenarios

This script demonstrates how to run realistic data center scenarios
to test RackPulse AI capabilities.
"""
import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

def list_scenarios():
    """List all available scenarios"""
    response = requests.get(f"{BASE_URL}/api/v1/scenarios/list")
    print("Available Scenarios:")
    print(json.dumps(response.json(), indent=2))
    return response.json()

def run_scenario(scenario_name):
    """Run a specific scenario"""
    print(f"\n{'='*60}")
    print(f"Running Scenario: {scenario_name}")
    print(f"{'='*60}")
    
    response = requests.post(f"{BASE_URL}/api/v1/scenarios/run/{scenario_name}")
    result = response.json()
    
    print("\nScenario Details:")
    print(f"Description: {result['description']}")
    print(f"Duration: {result['duration_minutes']} minutes")
    print(f"Racks Created: {result['racks_created']}")
    print(f"Telemetry Records: {result['telemetry_records']}")
    
    print("\nExpected Problems:")
    for problem in result['expected_problems']:
        print(f"  - {problem}")
    
    print("\nNext Steps:")
    for step in result['next_steps']:
        print(f"  {step}")
    
    return result

def test_scenario_workflow():
    """Complete workflow to test a scenario"""
    print("RackPulse Scenario Testing")
    print("=" * 60)
    
    # Step 1: List available scenarios
    scenarios = list_scenarios()
    
    # Step 2: Run a specific scenario (Thermal Hotspot)
    print("\n" + "="*60)
    print("STEP 1: Running Thermal Hotspot Scenario")
    print("="*60)
    result = run_scenario("Thermal Hotspot Emergency")
    site_id = result['site_id']
    
    # Step 3: Check scenario status
    print(f"\n{'='*60}")
    print("STEP 2: Checking Scenario Status")
    print(f"{'='*60}")
    
    time.sleep(2)  # Wait for data to be processed
    
    response = requests.get(f"{BASE_URL}/api/v1/scenarios/status/{site_id}")
    status = response.json()
    
    print(f"Site: {status['site_name']}")
    print(f"Telemetry Records: {status['telemetry_records']}")
    print(f"Incidents: {status['incidents']}")
    
    if status['incidents_list']:
        print("\nIncidents Detected:")
        for incident in status['incidents_list']:
            print(f"  - {incident['severity']}: {incident['description']}")
    
    # Step 4: Now test RackPulse AI reasoning
    print(f"\n{'='*60}")
    print("STEP 3: Running RackPulse AI Reasoning")
    print(f"{'='*60}")
    print("Run the AI reasoning to address the thermal hotspot...")
    print("You can now:")
    print("1. Go to the Dashboard and click 'Run Ollama Reasoning Loop'")
    print("2. Monitor the Memory Dashboard for episode creation")
    print("3. Check the Reasoning Trace for AI decision-making")
    
    return {
        "scenario_result": result,
        "status": status,
        "site_id": site_id
    }

if __name__ == "__main__":
    try:
        # Test the complete workflow
        workflow_result = test_scenario_workflow()
        
        print(f"\n{'='*60}")
        print("Scenario Testing Complete!")
        print(f"{'='*60}")
        print(f"Site ID: {workflow_result['site_id']}")
        print("\nThe scenario has generated realistic data center telemetry")
        print("demonstrating the thermal hotspot problem that RackPulse AI solves.")
        print("\nNext: Run the AI reasoning to see how RackPulse addresses this issue.")
        
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to RackPulse backend.")
        print("Make sure the backend is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()