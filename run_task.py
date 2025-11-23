"""CLI interface (Agent A) for running tasks with the UI state capture agent."""

import argparse
import asyncio

from task_runner import TaskRunner

def main():
    """Run a task with the UI state capture agent."""
    parser = argparse.ArgumentParser(
        description="Run tasks with the UI state capture agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_task.py --task "How can I create a new page in Notion?"
  python run_task.py --task "how can I find my socks page in Notion?"
        """,
    )
    parser.add_argument(
        "--task", "-t", required=True, help="Natural language task description"
    )
    parser.add_argument(
        "--browser", "-b",
        default="arc",
        choices=["arc", "chrome", "chromium", "safari"],
        help="Browser to use (default: arc)"
    )

    args = parser.parse_args()

    print(f"Running task: {args.task}")
    print(f"Browser: {args.browser}")

    runner = TaskRunner(
        task_instruction=args.task,
        browser=args.browser,
    )

    try:
        task_run = asyncio.run(runner.run())

        print(f"\nTask completed: {task_run.status.value}")
        print(f"Total steps: {task_run.total_steps}")

        if runner.get_output_directory():
            print(f"Tutorial: {runner.get_output_directory() / 'tutorial.md'}")

    except Exception as e:
        print(f"\nTask failed: {e}")
        raise


if __name__ == "__main__":
    main()
