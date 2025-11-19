"""
Helper script to check the status of a Celery task.
Usage: python check_task_status.py <task_id>
"""
import sys
import os
from dotenv import load_dotenv
from celery_app import app

load_dotenv()


def check_task_status(task_id: str):
    """
    Check the status and result of a Celery task.
    """
    try:
        task = app.AsyncResult(task_id)
        
        print(f"\n{'='*60}")
        print(f"Task ID: {task_id}")
        print(f"{'='*60}")
        
        # Check task state
        state = task.state
        print(f"Status: {state}")
        
        if state == 'PENDING':
            print("Task is waiting to be processed...")
        elif state == 'PROGRESS':
            print("Task is in progress...")
            print(f"Progress: {task.info}")
        elif state == 'SUCCESS':
            print("✅ Task completed successfully!")
            result = task.result
            if isinstance(result, dict):
                print("\nResults:")
                print(f"  Total shops: {result.get('total_shops', 'N/A')}")
                print(f"  Companies saved: {result.get('companies_saved', 'N/A')}")
                print(f"  Contacts saved: {result.get('contacts_saved', 'N/A')}")
                print(f"  Errors: {result.get('errors', 'N/A')}")
            else:
                print(f"Result: {result}")
        elif state == 'FAILURE':
            print("❌ Task failed!")
            print(f"Error: {task.info}")
        else:
            print(f"State: {state}")
            print(f"Info: {task.info}")
        
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"Error checking task status: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_task_status.py <task_id>")
        print("\nExample:")
        print("  python check_task_status.py bc5eb523-9f49-46b1-a1d8-028b4870a69c")
        sys.exit(1)
    
    task_id = sys.argv[1]
    check_task_status(task_id)

