"""CLI interface (Agent A) for running tasks with Agent B."""

import argparse

from agent_b.task_runner import TaskRunner


def main():
    """Run a task with Agent B."""
    parser = argparse.ArgumentParser(
        description="Run tasks with Agent B (UI state capture agent)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agent_a.agent_a --task "How can I create a new page in Notion?"
  python -m agent_a.agent_a --task "how can I find my socks page in Notion?"
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

    task_run = runner.run()

    print(f"\nTask completed: {task_run.status.value}")
    print(f"Total steps: {task_run.total_steps}")

    if runner.get_output_directory():
        print(f"Tutorial: {runner.get_output_directory() / 'tutorial.md'}")


if __name__ == "__main__":
    main()

