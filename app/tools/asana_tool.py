from typing import Optional, List, Dict, Any
import asana
from asana.rest import ApiException
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _get_asana_client():
    configuration = asana.Configuration()
    configuration.access_token = settings.asana_access_token
    return asana.ApiClient(configuration)


def _default_product_launch_tasks(launch_name: str = "Product Launch Checklist") -> List[Dict[str, Any]]:
    return [
        {
            "title": "Finalize launch plan",
            "description": f"{launch_name}: confirm scope, owners, and success criteria.",
            "priority": "high",
        },
        {
            "title": "Confirm feature readiness",
            "description": f"{launch_name}: verify features are complete and approved.",
            "priority": "high",
        },
        {
            "title": "Run QA and bug bash",
            "description": f"{launch_name}: complete final QA pass and fix critical issues.",
            "priority": "high",
        },
        {
            "title": "Prepare launch assets",
            "description": f"{launch_name}: finalize copy, visuals, and collateral.",
            "priority": "medium",
        },
        {
            "title": "Review analytics and tracking",
            "description": f"{launch_name}: validate dashboards, events, and metrics.",
            "priority": "medium",
        },
        {
            "title": "Brief support team",
            "description": f"{launch_name}: share FAQ, messaging, and escalation path.",
            "priority": "medium",
        },
        {
            "title": "Schedule launch-day monitoring",
            "description": f"{launch_name}: assign owners to monitor systems and issues.",
            "priority": "high",
        },
        {
            "title": "Publish launch announcement",
            "description": f"{launch_name}: send final internal and external communications.",
            "priority": "high",
        },
    ]


async def create_asana_task(
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: str = "medium",
    tags: Optional[List[str]] = None,
    assignee: Optional[str] = None,
    project_gid: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        client = _get_asana_client()
        tasks_api = asana.TasksApi(client)

        notes_parts = []
        if description:
            notes_parts.append(description)
        if priority:
            notes_parts.append(f"Priority: {priority}")
        if tags:
            notes_parts.append("Tags: " + ", ".join(tags))

        body = {
            "data": {
                "name": title,
                "workspace": settings.asana_workspace_gid,
                "projects": [project_gid or settings.asana_default_project_gid],
            }
        }

        if notes_parts:
            body["data"]["notes"] = "\n\n".join(notes_parts)
        if due_date:
            body["data"]["due_on"] = due_date
        if assignee:
            body["data"]["assignee"] = assignee

        task = tasks_api.create_task(body, {})

        logger.info("asana_task_created", task_gid=task["gid"], title=title)
        return {
            "success": True,
            "task_gid": task["gid"],
            "permalink_url": task.get("permalink_url", ""),
            "title": title,
            "due_date": due_date,
            "priority": priority,
            "tags": tags or [],
        }
    except ApiException as e:
        logger.error("asana_task_creation_failed", error=str(e))
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("asana_task_creation_failed", error=str(e))
        return {"success": False, "error": str(e)}


async def create_asana_task_batch(
    tasks: Optional[List[Dict[str, Any]]] = None,
    project_gid: Optional[str] = None,
    checklist_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create multiple Asana tasks at once.
    Always falls back to default product launch tasks if no tasks provided.
    """
    created = []
    failed = []

    normalized_tasks = tasks or []
    inferred_name = (checklist_name or "Product Launch Checklist").strip()

    # ALWAYS use default tasks if none provided — no keyword matching needed
    if not normalized_tasks:
        normalized_tasks = _default_product_launch_tasks(inferred_name)
        logger.info("using_default_launch_tasks", count=len(normalized_tasks))

    for task_data in normalized_tasks:
        result = await create_asana_task(
            title=task_data.get("title", "Untitled Task"),
            description=task_data.get("description"),
            due_date=task_data.get("due_date"),
            priority=task_data.get("priority", "medium"),
            tags=task_data.get("tags"),
            assignee=task_data.get("assignee"),
            project_gid=project_gid,
        )
        if result["success"]:
            created.append(result)
        else:
            failed.append({"title": task_data.get("title"), "error": result.get("error")})

    return {
        "success": len(created) > 0,
        "created_count": len(created),
        "failed_count": len(failed),
        "tasks": created,
        "errors": failed,
        "checklist_name": inferred_name,
    }


async def list_asana_tasks(
    project_gid: Optional[str] = None,
    completed: bool = False,
) -> Dict[str, Any]:
    try:
        client = _get_asana_client()
        tasks_api = asana.TasksApi(client)

        opts = {"completed_since": "now" if not completed else None, "limit": 50}
        tasks = list(
            tasks_api.get_tasks_for_project(
                project_gid or settings.asana_default_project_gid, opts
            )
        )

        return {
            "success": True,
            "tasks": [
                {
                    "gid": t["gid"],
                    "name": t["name"],
                    "completed": t.get("completed", False),
                    "due_on": t.get("due_on"),
                }
                for t in tasks
            ],
            "total": len(tasks),
        }
    except Exception as e:
        logger.error("asana_list_tasks_failed", error=str(e))
        return {"success": False, "error": str(e), "tasks": []}
