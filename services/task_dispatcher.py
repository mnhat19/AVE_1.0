from __future__ import annotations


def dispatch_tasks(tasks: list[dict]) -> dict:
    """Assign tasks to their agents and mark them as dispatched."""
    dispatch_map: dict[str, list[str]] = {}
    for task in tasks:
        agent = task.get("assigned_agent") or "UNASSIGNED"
        dispatch_map.setdefault(agent, []).append(task.get("id"))
        task["status"] = "DISPATCHED"
    return dispatch_map
