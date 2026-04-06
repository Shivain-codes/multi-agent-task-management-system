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


async def create_asana_task(
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: str = "medium",
    tags: Optional[List[str]] = None,
    assignee: Optional[str] = None,
    project_gid: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a task in Asana.

    Args:
        title: Task name
        description: Task notes/description
        due_date: Due date string 'YYYY-MM-DD'
        priority: 'low', 'medium', 'high', 'urgent'
        tags: List of tag names
        assignee: Assignee email or GID
        project_gid: Override default project GID

    Returns:
        dict with task_gid, permalink_url, and status
    """
    try:
        client = _get_asana_client()
        tasks_api = asana.TasksApi(client)

        body = {
            "data": {
                "name": title,
                "workspace": settings.asana_workspace_gid,
                "projects": [project_gid or settings.asana_default_project_gid],
            }
        }
        if description:
            body["data"]["notes"] = description
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
        }
    except ApiException as e:
        logger.error("asana_task_creation_failed", error=str(e))
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("asana_task_creation_failed", error=str(e))
        return {"success": False, "error": str(e)}


async def create_asana_task_batch(
    tasks: List[Dict[str, Any]],
    project_gid: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create multiple Asana tasks at once (e.g. a full checklist).

    Args:
        tasks: List of task dicts, each with keys: title, description, due_date, priority
        project_gid: Target project GID

    Returns:
        dict with list of created tasks and success count
    """
    created = []
    failed = []

    for task_data in tasks:
        result = await create_asana_task(
            title=task_data.get("title", "Untitled Task"),
            description=task_data.get("description"),
            due_date=task_data.get("due_date"),
            priority=task_data.get("priority", "medium"),
            project_gid=project_gid,
        )
        if result["success"]:
            created.append(result)
        else:
            failed.append({"title": task_data.get("title"), "error": result.get("error")})

    return {
        "success": len(failed) == 0,
        "created_count": len(created),
        "failed_count": len(failed),
        "tasks": created,
        "errors": failed,
    }


async def list_asana_tasks(
    project_gid: Optional[str] = None,
    completed: bool = False,
) -> Dict[str, Any]:
    """
    List tasks in an Asana project.

    Args:
        project_gid: Project GID (uses default if not provided)
        completed: Include completed tasks

    Returns:
        dict with list of tasks
    """
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
